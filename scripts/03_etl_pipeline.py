"""
"""
File: 03_etl_pipeline.py
Mô tả: Đường ống ETL dự phòng/local cho Olist Brazilian E-Commerce.
       Nạp data_cleaned.csv (đã hợp nhất từ 5 bảng) vào SQLite Star Schema.
       Mọi bước ghi log đồng thời ra console và logs/etl.log.
       Đây là phương án LOCAL/DỰ PHÒNG — luồng chính dùng 06_lakehouse_minio_postgres_etl.py.
"""

import os
import sys
import time
import sqlite3
import logging
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR  = os.path.join(BASE_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

BRAZIL_REGION_MAP = {
    "SP": "Southeast", "RJ": "Southeast", "MG": "Southeast", "ES": "Southeast",
    "RS": "South",     "SC": "South",     "PR": "South",
    "BA": "Northeast", "PE": "Northeast", "CE": "Northeast", "MA": "Northeast",
    "PB": "Northeast", "RN": "Northeast", "AL": "Northeast", "SE": "Northeast",
    "PI": "Northeast",
    "AM": "North",     "PA": "North",     "RO": "North",     "AC": "North",
    "AP": "North",     "RR": "North",     "TO": "North",
    "DF": "Midwest",   "GO": "Midwest",   "MT": "Midwest",   "MS": "Midwest",
}

PAYMENT_VN = {
    "credit_card": "Thẻ tín dụng",
    "boleto":      "Boleto (hóa đơn tiền mặt)",
    "voucher":     "Voucher / Phiếu mua hàng",
    "debit_card":  "Thẻ ghi nợ",
    "not_defined": "Không xác định",
}


def _setup_logger():
    logger = logging.getLogger("ETL_Pipeline_Olist")
    logger.setLevel(logging.INFO)
    if logger.handlers:
        return logger
    fmt = logging.Formatter("%(asctime)s | %(levelname)-5s | %(message)s", "%Y-%m-%d %H:%M:%S")
    fh = logging.FileHandler(os.path.join(LOG_DIR, "etl.log"), encoding="utf-8", mode="a")
    fh.setFormatter(fmt); logger.addHandler(fh)
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt); logger.addHandler(ch)
    return logger


log = _setup_logger()


def run_etl_pipeline(csv_file=None, db_file=None, ddl_file=None):
    csv_file = csv_file or os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
    db_file  = db_file  or os.path.join(BASE_DIR, "database", "retail_dwh.db")
    ddl_file = ddl_file or os.path.join(BASE_DIR, "database", "02_schema_ddl.sql")

    start = time.time()
    log.info("=" * 70)
    log.info("ETL PIPELINE LOCAL (SQLite) — OLIST BRAZILIAN E-COMMERCE")
    log.info("=" * 70)

    # ── 1. Đọc data_cleaned.csv ──
    log.info(f"[1/6] Đọc '{csv_file}'...")
    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Không tìm thấy: {csv_file}. Hãy chạy 01_eda_and_cleaning.py trước.")
    df = pd.read_csv(csv_file, low_memory=False)
    log.info(f"  → {len(df):,} dòng × {len(df.columns)} cột")

    # Đảm bảo kiểu dữ liệu
    df["order_purchase_timestamp"] = pd.to_datetime(df["order_purchase_timestamp"], errors="coerce")
    df["price"]         = pd.to_numeric(df["price"],         errors="coerce").fillna(0)
    df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce").fillna(0)

    # ── 2. Khởi tạo SQLite ──
    log.info(f"[2/6] Kết nối SQLite '{db_file}'...")
    con = sqlite3.connect(db_file)
    cur = con.cursor()
    cur.executescript("PRAGMA foreign_keys = ON; PRAGMA journal_mode = WAL;")

    # Xóa bảng cũ & tạo lại từ DDL
    log.info(f"[3/6] Áp dụng DDL '{ddl_file}'...")
    if os.path.exists(ddl_file):
        with open(ddl_file, encoding="utf-8") as f:
            ddl_raw = f.read()
        # SQLite không hỗ trợ CASCADE → loại bỏ
        ddl_sqlite = ddl_raw.replace(" CASCADE", "").replace("::numeric", "").replace("::text", "")
        # Loại bỏ REFERENCES (SQLite cần PRAGMA foreign_keys nhưng không enforce inline)
        try:
            cur.executescript(ddl_sqlite)
            con.commit()
        except Exception as e:
            log.warning(f"  DDL warning (thử tiếp): {e}")
    else:
        log.warning("  DDL file không tìm thấy — bỏ qua, dùng CREATE IF NOT EXISTS inline.")

    # ── 3. Dim_Date ──
    log.info("[4/6] Xây dựng và nạp Dim_Date...")
    ts = df["order_purchase_timestamp"].dropna()
    date_range = pd.date_range(ts.min().normalize(), ts.max().normalize(), freq="D")
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
    cur.execute("DELETE FROM Dim_Date")
    dim_date.to_sql("Dim_Date", con, if_exists="append", index=False)
    log.info(f"  → Dim_Date: {len(dim_date):,} rows")

    # ── 4. Dim_Location ──
    loc = df[["customer_state","customer_city"]].dropna(subset=["customer_state"]).drop_duplicates().reset_index(drop=True)
    dim_location = loc.rename(columns={"customer_state":"CustomerState","customer_city":"CustomerCity"})
    dim_location["LocationKey"] = range(1, len(dim_location)+1)
    dim_location["Region"] = dim_location["CustomerState"].map(BRAZIL_REGION_MAP).fillna("Other")
    cur.execute("DELETE FROM Dim_Location")
    dim_location[["LocationKey","CustomerState","CustomerCity","Region"]].to_sql("Dim_Location", con, if_exists="append", index=False)
    log.info(f"  → Dim_Location: {len(dim_location):,} rows")

    # ── 5. Dim_Customer ──
    cust_agg = df.groupby("customer_unique_id").agg(
        CustomerState=("customer_state", lambda x: x.mode().iloc[0] if len(x) else ""),
        CustomerCity =("customer_city",  lambda x: x.mode().iloc[0] if len(x) else ""),
    ).reset_index().rename(columns={"customer_unique_id":"CustomerUniqueID"})
    cust_agg["CustomerKey"]  = range(1, len(cust_agg)+1)
    cust_agg["CustomerCode"] = cust_agg["CustomerUniqueID"].str[:6].str.upper().apply(lambda s: f"CUST-{s}")
    cur.execute("DELETE FROM Dim_Customer")
    cust_agg[["CustomerKey","CustomerUniqueID","CustomerCode","CustomerState","CustomerCity"]].to_sql(
        "Dim_Customer", con, if_exists="append", index=False)
    log.info(f"  → Dim_Customer: {len(cust_agg):,} rows")

    # ── 6. Dim_Product ──
    prod_cols = ["product_id","product_category_name","category",
                 "product_name_lenght","product_description_lenght",
                 "product_photos_qty","product_weight_g",
                 "product_length_cm","product_height_cm","product_width_cm"]
    prod_agg = df[[c for c in prod_cols if c in df.columns]].drop_duplicates(subset=["product_id"]).reset_index(drop=True)
    prod_agg["ProductKey"] = range(1, len(prod_agg)+1)
    prod_agg = prod_agg.rename(columns={
        "product_id":"ProductID","product_category_name":"CategoryNamePT","category":"CategoryNameEN",
        "product_name_lenght":"NameLength","product_description_lenght":"DescriptionLength",
        "product_photos_qty":"PhotosQty","product_weight_g":"WeightG",
        "product_length_cm":"LengthCm","product_height_cm":"HeightCm","product_width_cm":"WidthCm",
    })
    cur.execute("DELETE FROM Dim_Product")
    dim_prod_cols = ["ProductKey","ProductID","CategoryNamePT","CategoryNameEN",
                     "NameLength","DescriptionLength","PhotosQty","WeightG","LengthCm","HeightCm","WidthCm"]
    prod_agg[[c for c in dim_prod_cols if c in prod_agg.columns]].to_sql(
        "Dim_Product", con, if_exists="append", index=False)
    log.info(f"  → Dim_Product: {len(prod_agg):,} rows")

    # ── 7. Dim_Payment ──
    pay_types = sorted(df["payment_type"].dropna().unique().tolist()) if "payment_type" in df.columns else list(PAYMENT_VN.keys())
    pay_types = sorted(set(pay_types) | {"not_defined"})
    dim_payment = pd.DataFrame({
        "PaymentKey":   range(1, len(pay_types)+1),
        "PaymentType":  pay_types,
        "PaymentTypeVN":[PAYMENT_VN.get(p, p) for p in pay_types],
    })
    cur.execute("DELETE FROM Dim_Payment")
    dim_payment.to_sql("Dim_Payment", con, if_exists="append", index=False)
    log.info(f"  → Dim_Payment: {len(dim_payment)} rows")

    # ── 8. Fact_Sales ──
    loc_map  = {(r["CustomerState"], r["CustomerCity"]): r["LocationKey"] for _, r in dim_location.iterrows()}
    cust_map = dict(zip(cust_agg["CustomerUniqueID"], cust_agg["CustomerKey"]))
    prod_map = dict(zip(prod_agg["ProductID"], prod_agg["ProductKey"]))
    pay_map  = dict(zip(dim_payment["PaymentType"], dim_payment["PaymentKey"]))

    ts_col = pd.to_datetime(df["order_purchase_timestamp"])
    fact = pd.DataFrame()
    fact["SalesKey"]           = range(1, len(df)+1)
    fact["OrderID"]            = df["order_id"].astype(str)
    fact["OrderItemID"]        = pd.to_numeric(df.get("order_item_id", pd.Series(1, index=df.index)), errors="coerce").fillna(1).astype(int)
    fact["PurchaseTimestamp"]  = ts_col.dt.strftime("%Y-%m-%d %H:%M:%S")
    fact["PurchaseHour"]       = ts_col.dt.hour
    fact["DateKey"]            = ts_col.dt.strftime("%Y%m%d").astype(int)
    fact["CustomerKey"]        = df["customer_unique_id"].map(cust_map)
    fact["ProductKey"]         = df["product_id"].map(prod_map)
    fact["LocationKey"]        = df.apply(
        lambda r: loc_map.get((r.get("customer_state",""), r.get("customer_city","")), 1), axis=1)
    fact["PaymentKey"]         = df.get("payment_type", pd.Series(dtype=str)).map(pay_map)
    fact["Price"]              = df["price"].round(2)
    fact["FreightValue"]       = df["freight_value"].round(2)
    fact["TotalRevenue"]       = fact["Price"]
    fact["TotalPaymentValue"]  = pd.to_numeric(df.get("total_payment_value", pd.Series(dtype=float)), errors="coerce").round(2)
    fact["PaymentInstallments"]= pd.to_numeric(df.get("payment_installments", pd.Series(dtype=float)), errors="coerce")
    fact["IsDelivered"]        = df.get("is_delivered", pd.Series(0, index=df.index)).fillna(0).astype(int)

    cur.execute("DELETE FROM Fact_Sales")
    fact.to_sql("Fact_Sales", con, if_exists="append", index=False, chunksize=10000)
    log.info(f"  → Fact_Sales: {len(fact):,} rows | R$ {fact['Price'].sum():,.2f}")

    # ── Đối soát ──
    con.commit()
    log.info("[5/6] Đối soát số bản ghi SQLite...")
    for tbl in ["Dim_Date","Dim_Location","Dim_Customer","Dim_Product","Dim_Payment","Fact_Sales"]:
        cnt = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        log.info(f"  {tbl:<20}: {cnt:>10,}")

    sqlite_rev = cur.execute("SELECT SUM(Price) FROM Fact_Sales").fetchone()[0] or 0
    src_rev    = float(fact["Price"].sum())
    log.info(f"  Doanh thu SQLite  : R$ {sqlite_rev:,.2f}")
    log.info(f"  Doanh thu nguồn   : R$ {src_rev:,.2f}")
    log.info(f"  Đối chiếu: {'✅ KHỚP' if abs(sqlite_rev - src_rev) < 1 else '❌ SAI LỆCH'}")

    con.close()
    elapsed = time.time() - start
    log.info(f"[6/6] ✅ ETL HOÀN THÀNH TRONG {elapsed:.2f} GIÂY — SQLite: '{db_file}'")
    log.info("=" * 70)


if __name__ == "__main__":
    run_etl_pipeline()
