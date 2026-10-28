"""
File: 06_lakehouse_minio_postgres_etl.py
Mô tả: Đường ống Lakehouse chính theo kiến trúc hiện đại:
       1. Đẩy dữ liệu lên MinIO (S3 Lakehouse: raw/ -> staging/ -> curated/).
       2. Dùng DuckDB đọc/ghi định dạng Parquet nén tối ưu.
       3. Nạp toàn bộ Star Schema vào PostgreSQL Data Warehouse (dwh:5432).

       MinIO raw -> staging -> curated -> PostgreSQL DWH.
       OLAP, khai phá dữ liệu và dashboard sử dụng PostgreSQL làm nguồn chính.
"""

import os
import sys
import importlib.util
import tempfile
import time
import s3fs
import duckdb
import pandas as pd
from sqlalchemy import create_engine, text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_RAW_CSV = os.path.join(BASE_DIR, "data", "raw", "data.csv")
DATA_CLEAN_CSV = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
DATA_REJECTED_CSV = os.path.join(BASE_DIR, "data", "processed", "data_rejected.csv")
CLEANING_AUDIT_CSV = os.path.join(BASE_DIR, "outputs", "data_cleaning_audit.csv")
PRODUCT_CATALOG_RAW_JSON = os.path.join(BASE_DIR, "data", "raw", "products_raw.json")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from product_catalog import build_unified_product_dimension, read_product_catalog

CFG = {
    "s3_endpoint": "localhost:9000",
    "s3_key": "minioadmin",
    "s3_secret": "minioadmin123",
    "pg_dwh": "postgresql+psycopg2://dataeng:dataeng123@localhost:5432/dwh"
}
CFG["pg_dwh"] = os.getenv("DWH_DATABASE_URL") or (
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        user=os.getenv("PGUSER", "dataeng"),
        password=os.getenv("PGPASSWORD", "dataeng123"),
        host=os.getenv("PGHOST", "localhost"),
        port=os.getenv("PGPORT", "5432"),
        database=os.getenv("PGDATABASE", "dwh")
    )
)

def run_lakehouse_pipeline():
    start_time = time.time()
    print("=" * 75)
    print("ĐƯỜNG ỐNG CHÍNH: MINIO RAW -> STAGING -> CURATED -> POSTGRESQL DWH")
    print("=" * 75)

    # --------------------------------------------------------------------------
    # BƯỚC 1: KẾT NỐI MINIO S3 & KIỂM TRA BUCKETS
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 1/4] KẾT NỐI HỒ DỮ LIỆU MINIO S3...")
    fs = s3fs.S3FileSystem(
        key=CFG["s3_key"],
        secret=CFG["s3_secret"],
        client_kwargs={"endpoint_url": f"http://{CFG['s3_endpoint']}"}
    )
    
    # Đảm bảo các buckets tồn tại
    for b in ["raw", "staging", "curated"]:
        if not fs.exists(b):
            fs.mkdir(b)
            print(f"  + Đã tạo bucket '{b}'")
        else:
            print(f"  + Bucket '{b}' đã sẵn sàng")

    # --------------------------------------------------------------------------
    # BƯỚC 2: INGESTION VÀO MINIO (RAW -> STAGING -> CURATED)
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 2/4] INGESTION VÀO HỒ DỮ LIỆU (3-TIER LAKEHOUSE ARCHITECTURE)...")
    
    # 2.1 Tầng Raw: Upload file csv gốc
    raw_s3_path = "raw/online_retail/data.csv"
    print(f"  -> Đang đẩy file gốc lên MinIO '{raw_s3_path}'...")
    if not os.path.exists(DATA_RAW_CSV):
        raise FileNotFoundError(f"Không tìm thấy dữ liệu raw: {DATA_RAW_CSV}")
    fs.put(DATA_RAW_CSV, raw_s3_path)
    print(f"     ✅ Hoàn tất upload Raw Data ({os.path.getsize(DATA_RAW_CSV)/(1024*1024):.2f} MB)")

    # Làm sạch bản raw đã lưu trong MinIO, không đọc trực tiếp bản local.
    print("  -> Đang đọc dữ liệu raw từ MinIO để khám phá và làm sạch...")
    raw_tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
    raw_tmp.close()
    try:
        fs.get(raw_s3_path, raw_tmp.name)
        cleaning_script = os.path.join(BASE_DIR, "scripts", "01_eda_and_cleaning.py")
        spec = importlib.util.spec_from_file_location("eda_and_cleaning", cleaning_script)
        if spec is None or spec.loader is None:
            raise ImportError(f"Không thể nạp script làm sạch: {cleaning_script}")
        cleaning_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cleaning_module)
        cleaning_module.run_eda_and_cleaning(
            input_file=raw_tmp.name,
            output_clean=DATA_CLEAN_CSV,
            output_rejected=DATA_REJECTED_CSV,
            output_audit=CLEANING_AUDIT_CSV
        )
    finally:
        os.unlink(raw_tmp.name)

    # 2.2 Tầng Staging: Chuyển dữ liệu sạch sang định dạng Parquet tối ưu nén
    staging_s3_path = "staging/online_retail/data_cleaned.parquet"
    print(f"  -> Đang chuyển đổi sang Parquet và đẩy lên MinIO '{staging_s3_path}'...")
    df_clean = pd.read_csv(DATA_CLEAN_CSV, dtype={'InvoiceNo': str}, low_memory=False)
    with fs.open(staging_s3_path, 'wb') as f:
        df_clean.to_parquet(f, index=False, engine='pyarrow', compression='snappy')
    print(f"     ✅ Đã lưu Staging Parquet ({len(df_clean):,} dòng, siêu nén tối ưu)")

    # 2.3 Tầng Curated: Dùng DuckDB đọc từ Staging Parquet và trích xuất các bảng Star Schema
    print("  -> Đang dùng DuckDB tạo các bảng Dimensional Model sang tầng 'curated/'...")
    
    # Đọc lại Parquet từ Lakehouse trước khi chuyển đổi sang mô hình chiều.
    staging_tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    staging_tmp.close()
    try:
        fs.get(staging_s3_path, staging_tmp.name)
        duck = duckdb.connect()
        try:
            df_clean = duck.execute(
                "SELECT * FROM read_parquet(?)", [staging_tmp.name]
            ).df()
        finally:
            duck.close()
    finally:
        os.unlink(staging_tmp.name)

    # Dim_Date
    min_date = pd.to_datetime(df_clean['InvoiceDate']).min().normalize()
    max_date = pd.to_datetime(df_clean['InvoiceDate']).max().normalize()
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    dim_date = pd.DataFrame({'FullDate': date_range})
    dim_date['DateKey'] = dim_date['FullDate'].dt.strftime('%Y%m%d').astype(int)
    dim_date['Day'] = dim_date['FullDate'].dt.day
    dim_date['Month'] = dim_date['FullDate'].dt.month
    dim_date['MonthName'] = dim_date['FullDate'].dt.month_name()
    dim_date['Quarter'] = dim_date['FullDate'].dt.quarter
    dim_date['QuarterName'] = 'Q' + dim_date['Quarter'].astype(str)
    dim_date['Year'] = dim_date['FullDate'].dt.year
    dim_date['DayOfWeek'] = dim_date['FullDate'].dt.dayofweek + 1
    dim_date['DayName'] = dim_date['FullDate'].dt.day_name()
    dim_date['IsWeekend'] = dim_date['DayOfWeek'].apply(lambda x: 1 if x in [6, 7] else 0)
    dim_date['YearMonth'] = dim_date['FullDate'].dt.strftime('%Y-%m')
    dim_date['FullDate'] = dim_date['FullDate'].dt.strftime('%Y-%m-%d')

    # Dim_Location
    unique_countries = sorted(df_clean['Country'].dropna().unique().tolist())
    dim_location = pd.DataFrame({'Country': unique_countries})
    dim_location['LocationKey'] = range(1, len(dim_location) + 1)
    dim_location['RegionType'] = dim_location['Country'].apply(
        lambda c: 'Domestic' if c == 'United Kingdom' else 'International'
    )
    dim_location = dim_location[['LocationKey', 'Country', 'RegionType']]

    # Dim_Customer
    customer_country_map = df_clean.groupby('CustomerID_Clean')['Country'].agg(
        lambda x: x.mode().iloc[0] if not x.empty else 'Unknown'
    ).reset_index()
    dim_customer = pd.DataFrame()
    dim_customer['CustomerID'] = customer_country_map['CustomerID_Clean'].astype(int)
    dim_customer['Country'] = customer_country_map['Country']
    dim_customer['CustomerKey'] = range(1, len(dim_customer) + 1)
    dim_customer['IsGuestCustomer'] = dim_customer['CustomerID'].apply(lambda cid: 1 if cid == -1 else 0)
    dim_customer['CustomerCode'] = dim_customer['CustomerID'].apply(
        lambda cid: 'GUEST' if cid == -1 else f"CUST-{cid}"
    )
    dim_customer = dim_customer[['CustomerKey', 'CustomerID', 'CustomerCode', 'IsGuestCustomer', 'Country']]

    # Dim_Product: hợp nhất giao dịch Online Retail với catalog DummyJSON
    product_agg = df_clean.groupby('StockCode').agg(
        Description=('Description', lambda x: x.mode().iloc[0] if not x.empty else 'NO DESCRIPTION'),
        UnitPrice_Standard=('UnitPrice', 'mean')
    ).reset_index()
    product_catalog = read_product_catalog()
    if product_catalog is not None:
        raw_catalog_key = "raw/online_retail/products_raw.json"
        staging_catalog_key = "staging/online_retail/products_catalog.parquet"
        if os.path.exists(PRODUCT_CATALOG_RAW_JSON):
            fs.put(PRODUCT_CATALOG_RAW_JSON, raw_catalog_key)
        with fs.open(staging_catalog_key, "wb") as catalog_file:
            product_catalog.to_parquet(
                catalog_file, index=False, engine="pyarrow", compression="snappy"
            )
        print(
            f"     ✅ MinIO staging: '{staging_catalog_key}' "
            f"({len(product_catalog):,} sản phẩm)"
        )
        catalog_staging_tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
        catalog_staging_tmp.close()
        try:
            fs.get(staging_catalog_key, catalog_staging_tmp.name)
            duck = duckdb.connect()
            try:
                product_catalog = duck.execute(
                    "SELECT * FROM read_parquet(?)", [catalog_staging_tmp.name]
                ).df()
            finally:
                duck.close()
        finally:
            os.unlink(catalog_staging_tmp.name)

    dim_product, product_merge_stats = build_unified_product_dimension(
        product_agg, product_catalog
    )
    print(
        "     ✅ Chiều sản phẩm hợp nhất: "
        f"{product_merge_stats['retail_products']:,} Online Retail + "
        f"{product_merge_stats['catalog_products']:,} DummyJSON; "
        f"{product_merge_stats['matched_products']:,} bản ghi khớp khóa tin cậy; "
        f"{product_merge_stats['categorized_products']:,} sản phẩm có danh mục phân tích."
    )

    # Fact_Sales
    location_map = dict(zip(dim_location['Country'], dim_location['LocationKey']))
    customer_map = dict(zip(dim_customer['CustomerID'], dim_customer['CustomerKey']))
    retail_products = dim_product[dim_product['StockCode'].notna()]
    product_map = dict(
        zip(retail_products['StockCode'].astype(str), retail_products['ProductKey'])
    )

    invoice_dt = pd.to_datetime(df_clean['InvoiceDate'])
    fact_sales = pd.DataFrame()
    fact_sales['SalesKey'] = range(1, len(df_clean) + 1)
    fact_sales['InvoiceNo'] = df_clean['InvoiceNo'].astype(str)
    fact_sales['InvoiceTimestamp'] = invoice_dt.dt.strftime('%Y-%m-%d %H:%M:%S')
    fact_sales['Hour'] = invoice_dt.dt.hour
    fact_sales['DateKey'] = invoice_dt.dt.strftime('%Y%m%d').astype(int)
    fact_sales['CustomerKey'] = df_clean['CustomerID_Clean'].astype(int).map(customer_map)
    fact_sales['ProductKey'] = df_clean['StockCode'].astype(str).map(product_map)
    fact_sales['LocationKey'] = df_clean['Country'].map(location_map)
    fact_sales['Quantity'] = df_clean['Quantity'].astype(int)
    fact_sales['UnitPrice'] = df_clean['UnitPrice'].round(2)
    fact_sales['TotalRevenue'] = (fact_sales['Quantity'] * fact_sales['UnitPrice']).round(2)

    # Đẩy các bảng Curated Parquet lên MinIO
    curated_tables = {
        "dim_date.parquet": dim_date,
        "dim_location.parquet": dim_location,
        "dim_customer.parquet": dim_customer,
        "dim_product.parquet": dim_product,
        "fact_sales.parquet": fact_sales
    }
    for fname, tdf in curated_tables.items():
        tdf.columns = tdf.columns.str.lower()
        cur_path = f"curated/online_retail/{fname}"
        with fs.open(cur_path, 'wb') as f:
            tdf.to_parquet(f, index=False, engine='pyarrow')
        print(f"     ✅ MinIO curated: '{cur_path}' ({len(tdf):,} rows)")

    curated_from_lake = {}
    for fname in curated_tables:
        with fs.open(f"curated/online_retail/{fname}", "rb") as curated_file:
            curated_from_lake[fname.removesuffix(".parquet")] = pd.read_parquet(curated_file)
    curated_tables = curated_from_lake

    # --------------------------------------------------------------------------
    # BƯỚC 3: KHỞI TẠO STAR SCHEMA TRÊN POSTGRESQL DATA WAREHOUSE
    # --------------------------------------------------------------------------
    print(f"\n[BƯỚC 3/4] TẠO SCHEMA VÀ KHÓA NGOẠI TRÊN POSTGRESQL (dwh:5432)...")
    engine = create_engine(CFG["pg_dwh"])
    
    pg_ddl = """
    CREATE TABLE IF NOT EXISTS dim_date (
        DateKey         INTEGER PRIMARY KEY,
        FullDate        DATE NOT NULL,
        Day             INTEGER NOT NULL,
        Month           INTEGER NOT NULL,
        MonthName       VARCHAR(20) NOT NULL,
        Quarter         INTEGER NOT NULL,
        QuarterName     VARCHAR(10) NOT NULL,
        Year            INTEGER NOT NULL,
        DayOfWeek       INTEGER NOT NULL,
        DayName         VARCHAR(20) NOT NULL,
        IsWeekend       INTEGER NOT NULL,
        YearMonth       VARCHAR(7) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_location (
        LocationKey     INTEGER PRIMARY KEY,
        Country         VARCHAR(100) NOT NULL UNIQUE,
        RegionType      VARCHAR(50) NOT NULL
    );

    CREATE TABLE IF NOT EXISTS dim_customer (
        CustomerKey     INTEGER PRIMARY KEY,
        CustomerID      INTEGER NOT NULL UNIQUE,
        CustomerCode    VARCHAR(50) NOT NULL,
        IsGuestCustomer INTEGER NOT NULL DEFAULT 0,
        Country         VARCHAR(100)
    );

    CREATE TABLE IF NOT EXISTS dim_product (
        ProductKey          INTEGER PRIMARY KEY,
        StockCode           VARCHAR(50) UNIQUE,
        Description         VARCHAR(255) NOT NULL,
        UnitPrice_Standard  DECIMAL(10, 2),
        SourceSystem        VARCHAR(50) NOT NULL DEFAULT 'Online Retail',
        APIProductID        INTEGER,
        CatalogTitle        VARCHAR(255),
        Category            VARCHAR(100),
        CategorySource      VARCHAR(40),
        CatalogPrice        DECIMAL(12, 2),
        CatalogDiscountPercentage DECIMAL(8, 2),
        CatalogRating       DECIMAL(4, 2),
        CatalogStock        INTEGER,
        Brand               VARCHAR(255),
        CatalogMatchMethod  VARCHAR(40)
    );

    ALTER TABLE dim_product ALTER COLUMN stockcode DROP NOT NULL;
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS sourcesystem VARCHAR(50);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS apiproductid INTEGER;
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalogtitle VARCHAR(255);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS category VARCHAR(100);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS categorysource VARCHAR(40);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalogprice DECIMAL(12, 2);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalogdiscountpercentage DECIMAL(8, 2);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalograting DECIMAL(4, 2);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalogstock INTEGER;
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS brand VARCHAR(255);
    ALTER TABLE dim_product ADD COLUMN IF NOT EXISTS catalogmatchmethod VARCHAR(40);
    UPDATE dim_product SET sourcesystem = 'Online Retail' WHERE sourcesystem IS NULL;
    ALTER TABLE dim_product ALTER COLUMN sourcesystem SET NOT NULL;
    CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_product_api_product_id
        ON dim_product(apiproductid) WHERE apiproductid IS NOT NULL;
    DROP TABLE IF EXISTS api_product_catalog;

    CREATE TABLE IF NOT EXISTS fact_sales (
        SalesKey            INTEGER PRIMARY KEY,
        InvoiceNo           VARCHAR(20) NOT NULL,
        InvoiceTimestamp    TIMESTAMP NOT NULL,
        Hour                INTEGER NOT NULL,
        DateKey             INTEGER NOT NULL REFERENCES dim_date(DateKey),
        CustomerKey         INTEGER NOT NULL REFERENCES dim_customer(CustomerKey),
        ProductKey          INTEGER NOT NULL REFERENCES dim_product(ProductKey),
        LocationKey         INTEGER NOT NULL REFERENCES dim_location(LocationKey),
        Quantity            INTEGER NOT NULL,
        UnitPrice           DECIMAL(10, 2) NOT NULL,
        TotalRevenue        DECIMAL(12, 2) NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_pg_fact_date ON fact_sales(DateKey);
    CREATE INDEX IF NOT EXISTS idx_pg_fact_customer ON fact_sales(CustomerKey);
    CREATE INDEX IF NOT EXISTS idx_pg_fact_product ON fact_sales(ProductKey);
    CREATE INDEX IF NOT EXISTS idx_pg_fact_location ON fact_sales(LocationKey);
    CREATE INDEX IF NOT EXISTS idx_pg_fact_invoiceno ON fact_sales(InvoiceNo);
    CREATE INDEX IF NOT EXISTS idx_dim_product_category ON dim_product(category);
    """
    
    # --------------------------------------------------------------------------
    # BƯỚC 4: NẠP DỮ LIỆU VÀO POSTGRESQL & KIỂM THỬ TOÀN VẸN
    # --------------------------------------------------------------------------
    print("\n[BƯỚC 4/4] NẠP DỮ LIỆU VÀO POSTGRESQL & ĐỐI CHIẾU DOANH SỐ...")
    
    load_start = time.time()
    dim_date = curated_tables["dim_date"]
    dim_location = curated_tables["dim_location"]
    dim_customer = curated_tables["dim_customer"]
    dim_product = curated_tables["dim_product"]
    fact_sales = curated_tables["fact_sales"]

    with engine.begin() as con:
        con.execute(text("DROP TABLE IF EXISTS dim_currency"))
        con.execute(text(pg_ddl))
        con.execute(text(
            "TRUNCATE TABLE fact_sales, dim_product, dim_customer, dim_location, dim_date"
        ))
        dim_date.to_sql('dim_date', con, if_exists='append', index=False, method='multi', chunksize=1000)
        dim_location.to_sql('dim_location', con, if_exists='append', index=False, method='multi')
        dim_customer.to_sql('dim_customer', con, if_exists='append', index=False, method='multi', chunksize=1000)
        dim_product.to_sql('dim_product', con, if_exists='append', index=False, method='multi', chunksize=1000)
        print(f"  -> Đang nạp fact_sales ({len(fact_sales):,} dòng) vào PostgreSQL...")
        fact_sales.to_sql('fact_sales', con, if_exists='append', index=False, chunksize=20000)

        aggregate_sql_path = os.path.join(BASE_DIR, "sql", "05_olap_aggregate_cubes.sql")
        with open(aggregate_sql_path, encoding="utf-8") as aggregate_sql_file:
            for statement in aggregate_sql_file.read().split(";"):
                if statement.strip():
                    con.execute(text(statement))
        for view_name in (
            "mv_olap_monthly_sales",
            "mv_olap_monthly_country_sales",
            "mv_olap_monthly_product_sales",
        ):
            con.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
        print("  -> Đã cập nhật 3 khối tổng hợp OLAP (tháng, quốc gia, sản phẩm).")
    print("  -> Đã khởi tạo schema và nạp dữ liệu curated vào PostgreSQL DWH.")
    load_duration = time.time() - load_start
    print(f"     ✅ Nạp thành công vào PostgreSQL trong {load_duration:.2f} giây!")

    # Kiểm tra số lượng bản ghi & doanh thu
    with engine.connect() as con:
        print("\n" + "-" * 55)
        print(f"{'Bảng PostgreSQL':<25} | {'Số bản ghi':>20}")
        print("-" * 55)
        for tbl in ['dim_date', 'dim_location', 'dim_customer', 'dim_product', 'fact_sales']:
            cnt = con.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()[0]
            print(f"{tbl:<25} | {cnt:>20,}")
        product_count_by_source = con.execute(text(
            "SELECT sourcesystem, COUNT(*) FROM dim_product GROUP BY sourcesystem ORDER BY sourcesystem"
        )).fetchall()
        for source_name, source_count in product_count_by_source:
            print(f"{source_name:<25} | {source_count:>20,}")

        # Đối chiếu doanh số
        pg_rev = con.execute(text("SELECT SUM(totalrevenue) FROM fact_sales")).fetchone()[0]
        source_rev = float(curated_tables["fact_sales"]["totalrevenue"].sum())
        print("-" * 55)
        print(f"Tổng doanh thu curated (MinIO):   £{source_rev:,.2f}")
        print(f"Tổng doanh thu trên Postgres DWH: £{pg_rev:,.2f}")
        print(f"Đối chiếu: {'✅ KHỚP HOÀN TOÀN 100%' if abs(float(source_rev) - float(pg_rev)) < 1.0 else '❌ SAI LỆCH'}")
        print("-" * 55)

    total_time = time.time() - start_time
    print(f"\n🎉 HOÀN THÀNH TOÀN BỘ ĐƯỜNG ỐNG DATA LAKEHOUSE TRONG {total_time:.2f} GIÂY!")
    print("=" * 75)

if __name__ == '__main__':
    run_lakehouse_pipeline()
