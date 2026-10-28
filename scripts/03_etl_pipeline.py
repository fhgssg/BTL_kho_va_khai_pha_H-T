"""
File: 03_etl_pipeline.py
Mô tả: Đường ống ETL (Extract - Transform - Load) chuẩn hóa từ data_cleaned.csv
       vào Kho Dữ Liệu SQLite (retail_dwh.db) theo mô hình Star Schema.
       Mọi bước ETL được ghi log song song ra console và file logs/etl.log.
"""

import os
import sys
import time
import sqlite3
import logging
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

# ─── CẤU HÌNH LOGGING (song song Console + File) ────────────────────────────
def _setup_logger():
    """Tạo logger ghi đồng thời ra stdout và file logs/etl.log."""
    logger = logging.getLogger("ETL_Pipeline")
    logger.setLevel(logging.INFO)
    # Tránh tạo handler trùng khi gọi nhiều lần
    if logger.handlers:
        return logger
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-5s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    # File handler
    fh = logging.FileHandler(os.path.join(LOG_DIR, "etl.log"), encoding="utf-8", mode="a")
    fh.setLevel(logging.INFO)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    return logger

log = _setup_logger()
from product_catalog import build_unified_product_dimension, read_product_catalog


def run_etl_pipeline(
    csv_file=None,
    db_file=None,
    ddl_file=None
):
    if csv_file is None:
        csv_file = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
    if db_file is None:
        db_file = os.path.join(BASE_DIR, "database", "retail_dwh.db")
    if ddl_file is None:
        ddl_file = os.path.join(BASE_DIR, "database", "02_schema_ddl.sql")
    start_total_time = time.time()
    log.info("=" * 70)
    log.info("BẮT ĐẦU ĐƯỜNG ỐNG ETL - ONLINE RETAIL DATA WAREHOUSE")
    log.info("=" * 70)

    # --------------------------------------------------------------------------
    # BƯỚC 1: TRÍCH XUẤT (EXTRACT)
    # --------------------------------------------------------------------------
    log.info("[BƯỚC 1/4] EXTRACT: Đọc dữ liệu từ file làm sạch...")
    if not os.path.exists(csv_file):
        eda_script = os.path.join(BASE_DIR, "scripts", "01_eda_and_cleaning.py")
        if os.path.exists(eda_script):
            log.info(f"- Không tìm thấy '{csv_file}'. Tự động chạy '{eda_script}'...")
            from importlib.machinery import SourceFileLoader
            eda_module = SourceFileLoader("eda", eda_script).load_module()
            eda_module.run_eda_and_cleaning()
        else:
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {csv_file}")

    df = pd.read_csv(csv_file, dtype={'InvoiceNo': str}, low_memory=False)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    total_raw_rows = len(df)
    log.info(f"-> Đã trích xuất thành công {total_raw_rows:,} bản ghi giao dịch.")

    # --------------------------------------------------------------------------
    # BƯỚC 2: BIẾN ĐỔI (TRANSFORM) - TẠO CÁC BẢNG DIMENSION VÀ FACT
    # --------------------------------------------------------------------------
    log.info("[BƯỚC 2/4] TRANSFORM: Chuẩn bị các Dimension Tables và Fact Table...")
    
    # 2.1 Transform: Dim_Date (Bao phủ toàn bộ dải ngày từ min đến max)
    log.info("  -> Đang xây dựng Dim_Date...")
    min_date = df['InvoiceDate'].min().normalize()
    max_date = df['InvoiceDate'].max().normalize()
    date_range = pd.date_range(start=min_date, end=max_date, freq='D')
    
    dim_date = pd.DataFrame({'FullDate': date_range})
    dim_date['DateKey'] = dim_date['FullDate'].dt.strftime('%Y%m%d').astype(int)
    dim_date['Day'] = dim_date['FullDate'].dt.day
    dim_date['Month'] = dim_date['FullDate'].dt.month
    dim_date['MonthName'] = dim_date['FullDate'].dt.month_name()
    dim_date['Quarter'] = dim_date['FullDate'].dt.quarter
    dim_date['QuarterName'] = 'Q' + dim_date['Quarter'].astype(str)
    dim_date['Year'] = dim_date['FullDate'].dt.year
    dim_date['DayOfWeek'] = dim_date['FullDate'].dt.dayofweek + 1  # 1 = Monday, 7 = Sunday
    dim_date['DayName'] = dim_date['FullDate'].dt.day_name()
    dim_date['IsWeekend'] = dim_date['DayOfWeek'].apply(lambda x: 1 if x in [6, 7] else 0)
    dim_date['YearMonth'] = dim_date['FullDate'].dt.strftime('%Y-%m')
    dim_date['FullDate'] = dim_date['FullDate'].dt.strftime('%Y-%m-%d')
    log.info(f"     + Dim_Date: {len(dim_date):,} ngày (Từ {min_date.strftime('%Y-%m-%d')} đến {max_date.strftime('%Y-%m-%d')})")

    # 2.2 Transform: Dim_Location
    log.info("  -> Đang xây dựng Dim_Location...")
    unique_countries = sorted(df['Country'].dropna().unique().tolist())
    dim_location = pd.DataFrame({'Country': unique_countries})
    dim_location['LocationKey'] = range(1, len(dim_location) + 1)
    dim_location['RegionType'] = dim_location['Country'].apply(
        lambda c: 'Domestic' if c == 'United Kingdom' else 'International'
    )
    dim_location = dim_location[['LocationKey', 'Country', 'RegionType']]
    log.info(f"     + Dim_Location: {len(dim_location):,} quốc gia/vùng lãnh thổ")

    # 2.3 Transform: Dim_Customer
    log.info("  -> Đang xây dựng Dim_Customer...")
    customer_country_map = df.groupby('CustomerID_Clean')['Country'].agg(
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
    log.info(f"     + Dim_Customer: {len(dim_customer):,} khách hàng (bao gồm khách vãng lai GUEST)")

    # 2.4 Transform: Dim_Product
    log.info("  -> Đang xây dựng Dim_Product...")
    product_agg = df.groupby('StockCode').agg(
        Description=('Description', lambda x: x.mode().iloc[0] if not x.empty else 'NO DESCRIPTION'),
        UnitPrice_Standard=('UnitPrice', 'mean')
    ).reset_index()
    product_catalog = read_product_catalog()
    dim_product, product_merge_stats = build_unified_product_dimension(
        product_agg, product_catalog
    )
    log.info(
        f"     + Dim_Product hợp nhất: {len(dim_product):,} sản phẩm "
        f"(Online Retail: {product_merge_stats['retail_products']:,}; "
        f"DummyJSON: {product_merge_stats['catalog_products']:,}; "
        f"khớp khóa tin cậy: {product_merge_stats['matched_products']:,}; "
        f"có danh mục: {product_merge_stats['categorized_products']:,})"
    )

    # 2.5 Transform: Fact_Sales (Ghép nối Surrogate Keys)
    log.info("  -> Đang chuẩn bị Fact_Sales & ánh xạ khóa đại diện (Surrogate Keys)...")
    
    # Tạo map tra cứu nhanh (Dictionary Lookup để tối ưu tốc độ vượt trội)
    location_map = dict(zip(dim_location['Country'], dim_location['LocationKey']))
    customer_map = dict(zip(dim_customer['CustomerID'], dim_customer['CustomerKey']))
    retail_products = dim_product[dim_product['StockCode'].notna()]
    product_map = dict(
        zip(retail_products['StockCode'].astype(str), retail_products['ProductKey'])
    )

    fact_sales = pd.DataFrame()
    fact_sales['InvoiceNo'] = df['InvoiceNo'].astype(str)
    fact_sales['InvoiceTimestamp'] = df['InvoiceDate'].dt.strftime('%Y-%m-%d %H:%M:%S')
    fact_sales['Hour'] = df['InvoiceDate'].dt.hour
    fact_sales['DateKey'] = df['InvoiceDate'].dt.strftime('%Y%m%d').astype(int)
    
    # Map Foreign Keys
    fact_sales['CustomerKey'] = df['CustomerID_Clean'].astype(int).map(customer_map)
    fact_sales['ProductKey'] = df['StockCode'].astype(str).map(product_map)
    fact_sales['LocationKey'] = df['Country'].map(location_map)
    
    fact_sales['Quantity'] = df['Quantity'].astype(int)
    fact_sales['UnitPrice'] = df['UnitPrice'].round(2)
    fact_sales['TotalRevenue'] = (fact_sales['Quantity'] * fact_sales['UnitPrice']).round(2)
    
    fact_sales['SalesKey'] = range(1, len(fact_sales) + 1)
    
    # Sắp xếp đúng thứ tự cột DDL
    fact_cols = [
        'SalesKey', 'InvoiceNo', 'InvoiceTimestamp', 'Hour',
        'DateKey', 'CustomerKey', 'ProductKey', 'LocationKey',
        'Quantity', 'UnitPrice', 'TotalRevenue'
    ]
    fact_sales = fact_sales[fact_cols]
    log.info(f"     + Fact_Sales: {len(fact_sales):,} dòng giao dịch hoàn chỉnh")
    # --------------------------------------------------------------------------
    # BƯỚC 3: NẠP DỮ LIỆU VÀO DATABASE (LOAD)
    # --------------------------------------------------------------------------
    log.info(f"[BƯỚC 3/4] LOAD: Khởi tạo database và nạp dữ liệu vào '{db_file}'...")
    
    # Xóa database cũ nếu cần đảm bảo môi trường sạch
    if os.path.exists(db_file):
        os.remove(db_file)
        log.info(f"  -> Đã làm sạch file database cũ: {db_file}")

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Thực thi DDL khởi tạo schema
    if os.path.exists(ddl_file):
        log.info(f"  -> Thực thi DDL từ '{ddl_file}'...")
        with open(ddl_file, 'r', encoding='utf-8') as f:
            cursor.executescript(f.read())
        conn.commit()
    else:
        raise FileNotFoundError(f"Không tìm thấy kịch bản DDL: {ddl_file}")

    # Nạp dữ liệu các bảng theo thứ tự Dimension -> Fact
    load_start = time.time()
    
    log.info("  -> Đang nạp Dim_Date...")
    dim_date.to_sql('Dim_Date', conn, if_exists='append', index=False)
    
    log.info("  -> Đang nạp Dim_Location...")
    dim_location.to_sql('Dim_Location', conn, if_exists='append', index=False)
    
    log.info("  -> Đang nạp Dim_Customer...")
    dim_customer.to_sql('Dim_Customer', conn, if_exists='append', index=False)
    
    log.info("  -> Đang nạp Dim_Product...")
    dim_product.to_sql('Dim_Product', conn, if_exists='append', index=False)

    log.info("  -> Đang nạp Fact_Sales (Batch Load 50,000 dòng/batch)...")
    fact_sales.to_sql('Fact_Sales', conn, if_exists='append', index=False, chunksize=50000)
    
    conn.commit()
    load_duration = time.time() - load_start
    log.info(f"-> Nạp hoàn tất toàn bộ dữ liệu vào cơ sở dữ liệu trong {load_duration:.2f} giây!")

    # --------------------------------------------------------------------------
    # BƯỚC 3.5: TẠO CÁC KHỐI TỔNG HỢP TRƯỚC (OLAP AGGREGATE VIEWS / CUBES) - SLIDE 9
    # --------------------------------------------------------------------------
    log.info("  -> Khởi tạo 3 khối tổng hợp tính trước (OLAP Views) phục vụ phân tích đa chiều...")
    olap_views_sql = """
    CREATE VIEW IF NOT EXISTS mv_olap_monthly_sales AS
    SELECT
        d.Year AS year,
        d.Quarter AS quarter,
        d.Month AS month,
        d.YearMonth AS yearmonth,
        COUNT(DISTINCT f.InvoiceNo) AS total_orders,
        SUM(f.Quantity) AS total_units_sold,
        ROUND(SUM(f.TotalRevenue), 2) AS revenue_gbp
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth;

    CREATE VIEW IF NOT EXISTS mv_olap_monthly_country_sales AS
    SELECT
        d.Year AS year,
        d.Quarter AS quarter,
        d.Month AS month,
        d.YearMonth AS yearmonth,
        l.Country AS country,
        SUM(f.Quantity) AS total_units_sold,
        ROUND(SUM(f.TotalRevenue), 2) AS revenue_gbp
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth, l.Country;

    CREATE VIEW IF NOT EXISTS mv_olap_monthly_product_sales AS
    SELECT
        d.Year AS year,
        d.Quarter AS quarter,
        d.Month AS month,
        d.YearMonth AS yearmonth,
        p.StockCode AS stockcode,
        p.Description AS description,
        SUM(f.Quantity) AS total_units_sold,
        ROUND(SUM(f.TotalRevenue), 2) AS revenue_gbp
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth, p.StockCode, p.Description;
    """
    conn.executescript(olap_views_sql)
    conn.commit()
    log.info("     + Đã tạo thành công: mv_olap_monthly_sales, mv_olap_monthly_country_sales, mv_olap_monthly_product_sales.")

    conn.close()

    # --------------------------------------------------------------------------
    # BƯỚC 4: BỘ KIỂM THỬ VÀ ĐỐI SOÁT TỰ ĐỘNG (DWH AUTOMATED TEST SUITE)
    # --------------------------------------------------------------------------
    log.info("[BƯỚC 4/4] CHẠY BỘ KIỂM THỬ VÀ ĐỐI SOÁT TỰ ĐỘNG (DWH TEST SUITE)...")
    test_script = os.path.join(BASE_DIR, "scripts", "03b_dwh_test_reconciliation.py")
    if os.path.exists(test_script):
        from importlib.machinery import SourceFileLoader
        test_module = SourceFileLoader("dwh_test", test_script).load_module()
        test_module.run_dwh_test_suite(db_path=db_file, clean_csv=csv_file)
    else:
        log.warning(f"Không tìm thấy '{test_script}', bỏ qua kiểm thử mở rộng.")
    
    total_duration = time.time() - start_total_time
    log.info("=" * 70)
    log.info(f"HOÀN THÀNH ETL PIPELINE TRONG {total_duration:.2f} GIÂY!")
    log.info(f"File kho dữ liệu đã sẵn sàng: '{os.path.abspath(db_file)}'")
    log.info(f"Log chi tiết đã ghi tại: '{os.path.join(LOG_DIR, 'etl.log')}'")
    log.info("=" * 70)

if __name__ == '__main__':
    run_etl_pipeline()
