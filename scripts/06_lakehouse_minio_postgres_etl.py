"""
File: 06_lakehouse_minio_postgres_etl.py
Mô tả: Đường ống Lakehouse chính cho bộ dữ liệu Olist Brazilian E-Commerce.
       Luồng: local raw CSVs → MinIO raw → EDA/cleaning → staging Parquet
              → curated Star Schema Parquet → PostgreSQL DWH
       Schema: Dim_Date, Dim_Location, Dim_Customer, Dim_Product,
               Dim_Payment, Fact_Sales (Olist)
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
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Raw file paths ──
RAW_FILES = {
    "orders":    os.path.join(RAW_DIR, "olist_orders_dataset.csv"),
    "items":     os.path.join(RAW_DIR, "olist_order_items_dataset.csv"),
    "customers": os.path.join(RAW_DIR, "olist_customers_dataset.csv"),
    "products":  os.path.join(RAW_DIR, "olist_products_dataset.csv"),
    "payments":  os.path.join(RAW_DIR, "olist_order_payments_dataset.csv"),
    "category":  os.path.join(RAW_DIR, "product_category_name_translation.csv"),
}
CLEAN_CSV    = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
REJECTED_CSV = os.path.join(BASE_DIR, "data", "processed", "data_rejected.csv")
AUDIT_CSV    = os.path.join(BASE_DIR, "outputs", "data_cleaning_audit.csv")

# ── Config ──
CFG = {
    "s3_endpoint": os.getenv("MINIO_ENDPOINT", "localhost:9000"),
    "s3_key":      os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
    "s3_secret":   os.getenv("MINIO_SECRET_KEY", "minioadmin123"),
}
CFG["pg_dwh"] = os.getenv("DWH_DATABASE_URL") or (
    "postgresql+psycopg2://{user}:{password}@{host}:{port}/{database}".format(
        user=    os.getenv("PGUSER",     "dataeng"),
        password=os.getenv("PGPASSWORD", "dataeng123"),
        host=    os.getenv("PGHOST",     "localhost"),
        port=    os.getenv("PGPORT",     "5432"),
        database=os.getenv("PGDATABASE", "dwh"),
    )
)

# ── Bang → Vùng kinh tế Brazil ──
BRAZIL_REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast",
    "ES": "Southeast",
    "RS": "South",     "SC": "South",     "PR": "South",
    "BA": "Northeast", "PE": "Northeast", "CE": "Northeast",
    "MA": "Northeast", "PB": "Northeast", "RN": "Northeast",
    "AL": "Northeast", "SE": "Northeast", "PI": "Northeast",
    "AM": "North",     "PA": "North",     "RO": "North",
    "AC": "North",     "AP": "North",     "RR": "North",
    "TO": "North",
    "DF": "Midwest",   "GO": "Midwest",   "MT": "Midwest",
    "MS": "Midwest",
}

PAYMENT_VN = {
    "credit_card": "Thẻ tín dụng",
    "boleto":      "Boleto (hóa đơn trả tiền mặt)",
    "voucher":     "Voucher / Phiếu mua hàng",
    "debit_card":  "Thẻ ghi nợ",
    "not_defined": "Không xác định",
}


# ==============================================================================
def _connect_minio():
    return s3fs.S3FileSystem(
        key=CFG["s3_key"],
        secret=CFG["s3_secret"],
        client_kwargs={"endpoint_url": f"http://{CFG['s3_endpoint']}"},
    )


def _ensure_buckets(fs, buckets=("raw", "staging", "curated")):
    for b in buckets:
        if not fs.exists(b):
            fs.mkdir(b)
            print(f"  + Đã tạo bucket '{b}'")
        else:
            print(f"  + Bucket '{b}' sẵn sàng")


# ==============================================================================
# BƯỚC 2 helper: upload raw CSVs lên MinIO
# ==============================================================================
def _upload_raw(fs):
    prefix = "raw/olist"
    for name, local_path in RAW_FILES.items():
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Thiếu file raw: {local_path}")
        s3_key = f"{prefix}/{os.path.basename(local_path)}"
        fs.put(local_path, s3_key)
        size_mb = os.path.getsize(local_path) / 1024 / 1024
        print(f"  ✅ Upload '{name}' → MinIO '{s3_key}' ({size_mb:.2f} MB)")
    return prefix


# ==============================================================================
# BƯỚC 2 helper: chạy EDA/cleaning từ MinIO raw
# ==============================================================================
def _run_cleaning(fs, raw_prefix):
    # Tải từng file về temp để EDA module đọc
    tmp_paths = {}
    tmp_files = []
    for name, local_path in RAW_FILES.items():
        s3_key = f"{raw_prefix}/{os.path.basename(local_path)}"
        tmp = tempfile.NamedTemporaryFile(suffix=".csv", delete=False)
        tmp.close()
        fs.get(s3_key, tmp.name)
        tmp_paths[name] = tmp.name
        tmp_files.append(tmp.name)

    try:
        cleaning_script = os.path.join(BASE_DIR, "scripts", "01_eda_and_cleaning.py")
        spec = importlib.util.spec_from_file_location("eda_and_cleaning", cleaning_script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        df_clean, df_rejected, df_audit = module.run_eda_and_cleaning(
            raw_orders=    tmp_paths["orders"],
            raw_items=     tmp_paths["items"],
            raw_customers= tmp_paths["customers"],
            raw_products=  tmp_paths["products"],
            raw_payments=  tmp_paths["payments"],
            raw_category=  tmp_paths["category"],
            output_clean=    CLEAN_CSV,
            output_rejected= REJECTED_CSV,
            output_audit=    AUDIT_CSV,
        )
    finally:
        for f in tmp_files:
            try:
                os.unlink(f)
            except Exception:
                pass

    return df_clean


# ==============================================================================
# BƯỚC 2 helper: đẩy staging Parquet lên MinIO
# ==============================================================================
def _upload_staging(fs, df_clean):
    staging_path = "staging/olist/data_cleaned.parquet"
    with fs.open(staging_path, "wb") as f:
        df_clean.to_parquet(f, index=False, engine="pyarrow", compression="snappy")
    print(f"  ✅ Staging Parquet → MinIO '{staging_path}' ({len(df_clean):,} dòng)")
    return staging_path


# ==============================================================================
# BƯỚC 2 helper: đọc lại staging từ MinIO qua DuckDB
# ==============================================================================
def _read_staging(fs, staging_path):
    tmp = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    tmp.close()
    try:
        fs.get(staging_path, tmp.name)
        duck = duckdb.connect()
        try:
            df = duck.execute("SELECT * FROM read_parquet(?)", [tmp.name]).df()
        finally:
            duck.close()
    finally:
        os.unlink(tmp.name)
    return df


# ==============================================================================
# BƯỚC 2 helper: xây dựng Star Schema DataFrames
# ==============================================================================
def _build_star_schema(df_clean):
    print("  → Xây dựng Dim_Date ...")
    min_date = pd.to_datetime(df_clean["order_purchase_timestamp"]).min().normalize()
    max_date = pd.to_datetime(df_clean["order_purchase_timestamp"]).max().normalize()
    date_range = pd.date_range(start=min_date, end=max_date, freq="D")
    dim_date = pd.DataFrame({"FullDate": date_range})
    dim_date["DateKey"]    = dim_date["FullDate"].dt.strftime("%Y%m%d").astype(int)
    dim_date["Day"]        = dim_date["FullDate"].dt.day
    dim_date["Month"]      = dim_date["FullDate"].dt.month
    dim_date["MonthName"]  = dim_date["FullDate"].dt.month_name()
    dim_date["Quarter"]    = dim_date["FullDate"].dt.quarter
    dim_date["QuarterName"]= "Q" + dim_date["Quarter"].astype(str)
    dim_date["Year"]       = dim_date["FullDate"].dt.year
    dim_date["DayOfWeek"]  = dim_date["FullDate"].dt.day_of_week + 1
    dim_date["DayName"]    = dim_date["FullDate"].dt.day_name()
    dim_date["IsWeekend"]  = dim_date["DayOfWeek"].apply(lambda x: 1 if x in [6, 7] else 0)
    dim_date["YearMonth"]  = dim_date["FullDate"].dt.strftime("%Y-%m")
    dim_date["FullDate"]   = dim_date["FullDate"].dt.strftime("%Y-%m-%d")
    print(f"     {len(dim_date):,} ngày ({dim_date['Year'].min()} – {dim_date['Year'].max()})")

    # ── Dim_Location ──
    print("  → Xây dựng Dim_Location (bang Brazil) ...")
    loc_cols = ["customer_state", "customer_city"]
    loc_unique = (
        df_clean[loc_cols].dropna(subset=["customer_state"])
        .drop_duplicates()
        .sort_values(loc_cols)
        .reset_index(drop=True)
    )
    dim_location = loc_unique.rename(columns={
        "customer_state": "CustomerState",
        "customer_city":  "CustomerCity",
    })
    dim_location["LocationKey"] = range(1, len(dim_location) + 1)
    dim_location["Region"] = dim_location["CustomerState"].map(BRAZIL_REGION_MAP).fillna("Other")
    dim_location = dim_location[["LocationKey", "CustomerState", "CustomerCity", "Region"]]
    print(f"     {len(dim_location):,} bản ghi (bang × thành phố)")

    # ── Dim_Customer ──
    print("  → Xây dựng Dim_Customer ...")
    cust_agg = (
        df_clean
        .groupby("customer_unique_id")
        .agg(
            CustomerState=("customer_state", lambda x: x.mode().iloc[0] if len(x) else ""),
            CustomerCity =("customer_city",  lambda x: x.mode().iloc[0] if len(x) else ""),
        )
        .reset_index()
    )
    dim_customer = cust_agg.rename(columns={"customer_unique_id": "CustomerUniqueID"})
    dim_customer["CustomerKey"]  = range(1, len(dim_customer) + 1)
    dim_customer["CustomerCode"] = dim_customer["CustomerUniqueID"].str[:6].str.upper().apply(
        lambda s: f"CUST-{s}"
    )
    dim_customer = dim_customer[["CustomerKey", "CustomerUniqueID", "CustomerCode",
                                  "CustomerState", "CustomerCity"]]
    print(f"     {len(dim_customer):,} khách hàng duy nhất")

    # ── Dim_Product ──
    print("  → Xây dựng Dim_Product ...")
    prod_cols = [
        "product_id", "product_category_name", "category",
        "product_name_lenght", "product_description_lenght",
        "product_photos_qty", "product_weight_g",
        "product_length_cm", "product_height_cm", "product_width_cm",
    ]
    avail_cols = [c for c in prod_cols if c in df_clean.columns]
    prod_agg = (
        df_clean[avail_cols]
        .drop_duplicates(subset=["product_id"])
        .reset_index(drop=True)
    )
    dim_product = prod_agg.copy()
    dim_product["ProductKey"] = range(1, len(dim_product) + 1)

    # Rename để khớp schema
    rename_map = {
        "product_id":                  "ProductID",
        "product_category_name":       "CategoryNamePT",
        "category":                    "CategoryNameEN",
        "product_name_lenght":         "NameLength",
        "product_description_lenght":  "DescriptionLength",
        "product_photos_qty":          "PhotosQty",
        "product_weight_g":            "WeightG",
        "product_length_cm":           "LengthCm",
        "product_height_cm":           "HeightCm",
        "product_width_cm":            "WidthCm",
    }
    dim_product = dim_product.rename(columns={k: v for k, v in rename_map.items() if k in dim_product.columns})
    for expected in ["ProductKey", "ProductID", "CategoryNamePT", "CategoryNameEN",
                     "NameLength", "DescriptionLength", "PhotosQty",
                     "WeightG", "LengthCm", "HeightCm", "WidthCm"]:
        if expected not in dim_product.columns:
            dim_product[expected] = None
    dim_product = dim_product[["ProductKey", "ProductID", "CategoryNamePT", "CategoryNameEN",
                                "NameLength", "DescriptionLength", "PhotosQty",
                                "WeightG", "LengthCm", "HeightCm", "WidthCm"]]
    print(f"     {len(dim_product):,} sản phẩm duy nhất")

    # ── Dim_Payment ──
    print("  → Xây dựng Dim_Payment ...")
    pay_types = (
        df_clean["payment_type"].dropna().unique().tolist()
        if "payment_type" in df_clean.columns
        else list(PAYMENT_VN.keys())
    )
    pay_types = sorted(set(pay_types) | {"not_defined"})
    dim_payment = pd.DataFrame({
        "PaymentKey":   range(1, len(pay_types) + 1),
        "PaymentType":  pay_types,
        "PaymentTypeVN": [PAYMENT_VN.get(p, p) for p in pay_types],
    })
    print(f"     {len(dim_payment)} loại phương thức thanh toán")

    # ── Fact_Sales ──
    print("  → Xây dựng Fact_Sales ...")
    # Lookup maps
    location_map = {}
    for _, row in dim_location.iterrows():
        location_map[(row["CustomerState"], row["CustomerCity"])] = row["LocationKey"]

    customer_map = dict(zip(dim_customer["CustomerUniqueID"], dim_customer["CustomerKey"]))
    product_map  = dict(zip(dim_product["ProductID"], dim_product["ProductKey"]))
    payment_map  = dict(zip(dim_payment["PaymentType"], dim_payment["PaymentKey"]))

    ts = pd.to_datetime(df_clean["order_purchase_timestamp"])
    fact_sales = pd.DataFrame()
    fact_sales["SalesKey"]          = range(1, len(df_clean) + 1)
    fact_sales["OrderID"]           = df_clean["order_id"].astype(str)
    fact_sales["OrderItemID"]       = pd.to_numeric(df_clean.get("order_item_id", pd.Series(1, index=df_clean.index)), errors="coerce").fillna(1).astype(int)
    fact_sales["PurchaseTimestamp"] = ts.dt.strftime("%Y-%m-%d %H:%M:%S")
    fact_sales["PurchaseHour"]      = ts.dt.hour
    fact_sales["DateKey"]           = ts.dt.strftime("%Y%m%d").astype(int)
    fact_sales["CustomerKey"]       = df_clean["customer_unique_id"].map(customer_map)
    fact_sales["ProductKey"]        = df_clean["product_id"].map(product_map)
    # LocationKey: map theo (state, city)
    fact_sales["LocationKey"] = df_clean.apply(
        lambda r: location_map.get((r.get("customer_state", ""), r.get("customer_city", "")), 1),
        axis=1,
    )
    fact_sales["PaymentKey"]          = df_clean.get("payment_type", pd.Series(dtype=str)).map(payment_map)
    fact_sales["Price"]               = pd.to_numeric(df_clean["price"], errors="coerce").round(2)
    fact_sales["FreightValue"]        = pd.to_numeric(df_clean.get("freight_value", pd.Series(0, index=df_clean.index)), errors="coerce").fillna(0).round(2)
    fact_sales["TotalRevenue"]        = fact_sales["Price"]
    fact_sales["TotalPaymentValue"]   = pd.to_numeric(df_clean.get("total_payment_value", pd.Series(dtype=float)), errors="coerce").round(2)
    fact_sales["PaymentInstallments"] = pd.to_numeric(df_clean.get("payment_installments", pd.Series(dtype=float)), errors="coerce").astype("Int64")
    fact_sales["IsDelivered"]         = df_clean.get("is_delivered", pd.Series(0, index=df_clean.index)).fillna(0).astype(int)

    print(f"     {len(fact_sales):,} dòng Fact_Sales | Doanh thu tổng: R$ {fact_sales['Price'].sum():,.2f}")

    return {
        "dim_date":     dim_date,
        "dim_location": dim_location,
        "dim_customer": dim_customer,
        "dim_product":  dim_product,
        "dim_payment":  dim_payment,
        "fact_sales":   fact_sales,
    }


# ==============================================================================
# BƯỚC 2 helper: đẩy curated Parquet lên MinIO
# ==============================================================================
def _upload_curated(fs, star_schema):
    prefix = "curated/olist"
    for name, df_tbl in star_schema.items():
        df_out = df_tbl.copy()
        df_out.columns = df_out.columns.str.lower()
        s3_path = f"{prefix}/{name}.parquet"
        with fs.open(s3_path, "wb") as f:
            df_out.to_parquet(f, index=False, engine="pyarrow", compression="snappy")
        print(f"  ✅ MinIO curated: '{s3_path}' ({len(df_out):,} dòng)")
    return prefix


# ==============================================================================
# BƯỚC 2 helper: đọc lại curated từ MinIO
# ==============================================================================
def _read_curated(fs, curated_prefix, table_names):
    result = {}
    for name in table_names:
        s3_path = f"{curated_prefix}/{name}.parquet"
        with fs.open(s3_path, "rb") as f:
            result[name] = pd.read_parquet(f)
    return result


# ==============================================================================
# BƯỚC 3: PostgreSQL DDL
# ==============================================================================
PG_DDL = """
DROP TABLE IF EXISTS fact_sales CASCADE;
DROP TABLE IF EXISTS dim_product CASCADE;
DROP TABLE IF EXISTS dim_customer CASCADE;
DROP TABLE IF EXISTS dim_location CASCADE;
DROP TABLE IF EXISTS dim_date CASCADE;
DROP TABLE IF EXISTS dim_payment CASCADE;

CREATE TABLE dim_date (
    DateKey      INTEGER PRIMARY KEY,
    FullDate     DATE NOT NULL,
    Day          INTEGER NOT NULL,
    Month        INTEGER NOT NULL,
    MonthName    VARCHAR(20) NOT NULL,
    Quarter      INTEGER NOT NULL,
    QuarterName  VARCHAR(10) NOT NULL,
    Year         INTEGER NOT NULL,
    DayOfWeek    INTEGER NOT NULL,
    DayName      VARCHAR(20) NOT NULL,
    IsWeekend    INTEGER NOT NULL,
    YearMonth    VARCHAR(7) NOT NULL
);

CREATE TABLE dim_location (
    LocationKey   INTEGER PRIMARY KEY,
    CustomerState VARCHAR(10) NOT NULL,
    CustomerCity  VARCHAR(100),
    Region        VARCHAR(50)
);
CREATE UNIQUE INDEX idx_dim_location_key ON dim_location(CustomerState, CustomerCity);

CREATE TABLE dim_customer (
    CustomerKey      INTEGER PRIMARY KEY,
    CustomerUniqueID VARCHAR(100) NOT NULL UNIQUE,
    CustomerCode     VARCHAR(50) NOT NULL,
    CustomerState    VARCHAR(10),
    CustomerCity     VARCHAR(100)
);

CREATE TABLE dim_product (
    ProductKey          INTEGER PRIMARY KEY,
    ProductID           VARCHAR(100) NOT NULL UNIQUE,
    CategoryNamePT      VARCHAR(100),
    CategoryNameEN      VARCHAR(100),
    NameLength          INTEGER,
    DescriptionLength   INTEGER,
    PhotosQty           INTEGER,
    WeightG             DECIMAL(10,2),
    LengthCm            DECIMAL(10,2),
    HeightCm            DECIMAL(10,2),
    WidthCm             DECIMAL(10,2)
);
CREATE INDEX idx_dim_product_cat ON dim_product(CategoryNameEN);

CREATE TABLE dim_payment (
    PaymentKey    INTEGER PRIMARY KEY,
    PaymentType   VARCHAR(50) NOT NULL UNIQUE,
    PaymentTypeVN VARCHAR(100)
);

CREATE TABLE fact_sales (
    SalesKey              INTEGER PRIMARY KEY,
    OrderID               VARCHAR(100) NOT NULL,
    OrderItemID           INTEGER NOT NULL,
    PurchaseTimestamp     TIMESTAMP NOT NULL,
    PurchaseHour          INTEGER NOT NULL,
    DateKey               INTEGER NOT NULL REFERENCES dim_date(DateKey),
    CustomerKey           INTEGER NOT NULL REFERENCES dim_customer(CustomerKey),
    ProductKey            INTEGER NOT NULL REFERENCES dim_product(ProductKey),
    LocationKey           INTEGER NOT NULL REFERENCES dim_location(LocationKey),
    PaymentKey            INTEGER REFERENCES dim_payment(PaymentKey),
    Price                 DECIMAL(12,2) NOT NULL,
    FreightValue          DECIMAL(10,2) NOT NULL DEFAULT 0,
    TotalRevenue          DECIMAL(12,2) NOT NULL,
    TotalPaymentValue     DECIMAL(12,2),
    PaymentInstallments   INTEGER,
    IsDelivered           INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX idx_fact_date     ON fact_sales(DateKey);
CREATE INDEX idx_fact_customer ON fact_sales(CustomerKey);
CREATE INDEX idx_fact_product  ON fact_sales(ProductKey);
CREATE INDEX idx_fact_location ON fact_sales(LocationKey);
CREATE INDEX idx_fact_payment  ON fact_sales(PaymentKey);
CREATE INDEX idx_fact_orderid  ON fact_sales(OrderID);
CREATE INDEX idx_dim_date_ym   ON dim_date(Year, Month);
CREATE INDEX idx_dim_cust_st   ON dim_customer(CustomerState);
"""


# ==============================================================================
# HÀM CHÍNH
# ==============================================================================
def run_lakehouse_pipeline():
    start_time = time.time()
    print("=" * 75)
    print("ĐƯỜNG ỐNG CHÍNH OLIST: MINIO RAW → STAGING → CURATED → POSTGRESQL DWH")
    print("=" * 75)

    # ── BƯỚC 1: Kết nối MinIO ──
    print("\n[BƯỚC 1/4] KẾT NỐI HỒ DỮ LIỆU MINIO S3...")
    fs = _connect_minio()
    _ensure_buckets(fs)

    # ── BƯỚC 2: Ingestion 3-tier ──
    print("\n[BƯỚC 2/4] INGESTION VÀO HỒ DỮ LIỆU (3-TIER LAKEHOUSE ARCHITECTURE)...")

    # 2.1 Raw: upload CSVs
    print("  2.1 [RAW] Upload 6 file CSV Olist lên MinIO...")
    raw_prefix = _upload_raw(fs)

    # 2.2 EDA/cleaning → data_cleaned.csv
    print("  2.2 [STAGING] Đọc từ MinIO raw → EDA & làm sạch...")
    df_clean = _run_cleaning(fs, raw_prefix)

    # 2.3 Staging: Parquet nén
    print("  2.3 [STAGING] Đẩy dữ liệu sạch lên staging Parquet...")
    staging_path = _upload_staging(fs, df_clean)

    # 2.4 Đọc lại staging qua DuckDB
    print("  2.4 [STAGING → CURATED] Đọc lại staging, xây dựng Star Schema...")
    df_staging = _read_staging(fs, staging_path)

    # 2.5 Xây dựng Star Schema
    star_schema = _build_star_schema(df_staging)

    # 2.6 Curated: Parquet Star Schema
    print("  2.6 [CURATED] Đẩy các bảng Star Schema lên curated Parquet...")
    curated_prefix = _upload_curated(fs, star_schema)

    # 2.7 Đọc lại curated từ MinIO (đảm bảo dữ liệu nạp từ lake)
    print("  2.7 [CURATED] Đọc lại curated từ MinIO để nạp vào PostgreSQL...")
    curated = _read_curated(fs, curated_prefix, list(star_schema.keys()))

    # ── BƯỚC 3: PostgreSQL DDL ──
    print(f"\n[BƯỚC 3/4] TẠO SCHEMA STAR SCHEMA TRÊN POSTGRESQL (dwh:5432)...")
    engine = create_engine(CFG["pg_dwh"])
    with engine.begin() as con:
        con.execute(text(PG_DDL))
    print("  ✅ Khởi tạo schema thành công")

    # ── BƯỚC 4: Nạp dữ liệu ──
    print(f"\n[BƯỚC 4/4] NẠP DỮ LIỆU CURATED VÀO POSTGRESQL DWH...")
    load_start = time.time()

    # Normalize column names: lowercase để khớp DDL
    def norm(df):
        df2 = df.copy()
        df2.columns = [c.lower() for c in df2.columns]
        return df2

    dim_date     = norm(curated["dim_date"])
    dim_location = norm(curated["dim_location"])
    dim_customer = norm(curated["dim_customer"])
    dim_product  = norm(curated["dim_product"])
    dim_payment  = norm(curated["dim_payment"])
    fact_sales   = norm(curated["fact_sales"])

    with engine.begin() as con:
        dim_date.to_sql("dim_date",     con, if_exists="append", index=False, method="multi", chunksize=2000)
        dim_location.to_sql("dim_location", con, if_exists="append", index=False, method="multi")
        dim_customer.to_sql("dim_customer", con, if_exists="append", index=False, method="multi", chunksize=2000)
        dim_product.to_sql("dim_product",   con, if_exists="append", index=False, method="multi", chunksize=2000)
        dim_payment.to_sql("dim_payment",   con, if_exists="append", index=False, method="multi")
        print(f"  → Đang nạp fact_sales ({len(fact_sales):,} dòng)...")
        fact_sales.to_sql("fact_sales", con, if_exists="append", index=False, chunksize=10000)

        # OLAP aggregate cubes
        aggregate_sql_path = os.path.join(BASE_DIR, "sql", "05_olap_aggregate_cubes.sql")
        if os.path.exists(aggregate_sql_path):
            with open(aggregate_sql_path, encoding="utf-8") as f:
                for stmt in f.read().split(";"):
                    if stmt.strip():
                        con.execute(text(stmt))
            for view_name in ("mv_olap_monthly_sales", "mv_olap_monthly_country_sales",
                              "mv_olap_monthly_product_sales"):
                try:
                    con.execute(text(f"REFRESH MATERIALIZED VIEW {view_name}"))
                except Exception:
                    pass
            print("  → Đã cập nhật 3 khối tổng hợp OLAP materialized views.")

    load_dur = time.time() - load_start
    print(f"  ✅ Nạp PostgreSQL trong {load_dur:.2f} giây")

    # ── Kiểm tra số bản ghi & đối soát doanh thu ──
    with engine.connect() as con:
        print("\n" + "-" * 55)
        print(f"{'Bảng PostgreSQL':<25} | {'Số bản ghi':>20}")
        print("-" * 55)
        for tbl in ["dim_date", "dim_location", "dim_customer",
                    "dim_product", "dim_payment", "fact_sales"]:
            cnt = con.execute(text(f"SELECT COUNT(*) FROM {tbl}")).fetchone()[0]
            print(f"{tbl:<25} | {cnt:>20,}")

        pg_rev   = con.execute(text("SELECT SUM(totalrevenue) FROM fact_sales")).fetchone()[0] or 0
        src_rev  = float(curated["fact_sales"]["totalrevenue"].sum())
        match_ok = abs(float(pg_rev) - src_rev) < 1.0
        print("-" * 55)
        print(f"Tổng doanh thu curated (MinIO): R$ {src_rev:,.2f}")
        print(f"Tổng doanh thu Postgres DWH   : R$ {float(pg_rev):,.2f}")
        print(f"Đối chiếu: {'✅ KHỚP HOÀN TOÀN 100%' if match_ok else '❌ SAI LỆCH'}")
        print("-" * 55)

    total_time = time.time() - start_time
    print(f"\n🎉 HOÀN THÀNH ĐƯỜNG ỐNG DATA LAKEHOUSE TRONG {total_time:.2f} GIÂY!")
    print("=" * 75)


if __name__ == "__main__":
    run_lakehouse_pipeline()
