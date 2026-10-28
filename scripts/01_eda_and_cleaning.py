"""
File: 01_eda_and_cleaning.py
Mô tả: Giai đoạn 1 - Khám phá chất lượng dữ liệu (EDA) & Làm sạch / Hợp nhất
       bộ dữ liệu Olist Brazilian E-Commerce gồm 5 bảng nguồn:
         - olist_orders_dataset.csv
         - olist_order_items_dataset.csv
         - olist_customers_dataset.csv
         - olist_products_dataset.csv
         - olist_order_payments_dataset.csv
         - product_category_name_translation.csv (tra cứu danh mục)
       Đầu ra: data/processed/data_cleaned.csv & data/processed/data_rejected.csv
"""

import os
import sys
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR  = os.path.join(BASE_DIR, "data", "raw")

# ── Đường dẫn file nguồn ──
RAW_ORDERS      = os.path.join(RAW_DIR, "olist_orders_dataset.csv")
RAW_ITEMS       = os.path.join(RAW_DIR, "olist_order_items_dataset.csv")
RAW_CUSTOMERS   = os.path.join(RAW_DIR, "olist_customers_dataset.csv")
RAW_PRODUCTS    = os.path.join(RAW_DIR, "olist_products_dataset.csv")
RAW_PAYMENTS    = os.path.join(RAW_DIR, "olist_order_payments_dataset.csv")
RAW_CATEGORY    = os.path.join(RAW_DIR, "product_category_name_translation.csv")

# ── Đường dẫn đầu ra ──
CLEAN_DATA_PATH    = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
REJECTED_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_rejected.csv")
AUDIT_OUTPUT_PATH  = os.path.join(BASE_DIR, "outputs", "data_cleaning_audit.csv")

os.makedirs(os.path.join(BASE_DIR, "data", "processed"), exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "outputs"), exist_ok=True)


def run_eda_and_cleaning(
    raw_orders=None,
    raw_items=None,
    raw_customers=None,
    raw_products=None,
    raw_payments=None,
    raw_category=None,
    output_clean=None,
    output_rejected=None,
    output_audit=None,
):
    """
    Hàm EDA & làm sạch chính cho bộ dữ liệu Olist.
    Trả về: (df_clean, df_rejected, df_audit)
    """
    raw_orders    = raw_orders    or RAW_ORDERS
    raw_items     = raw_items     or RAW_ITEMS
    raw_customers = raw_customers or RAW_CUSTOMERS
    raw_products  = raw_products  or RAW_PRODUCTS
    raw_payments  = raw_payments  or RAW_PAYMENTS
    raw_category  = raw_category  or RAW_CATEGORY
    output_clean    = output_clean    or CLEAN_DATA_PATH
    output_rejected = output_rejected or REJECTED_DATA_PATH
    output_audit    = output_audit    or AUDIT_OUTPUT_PATH

    print("=" * 85)
    print(" GIAI ĐOẠN 1: KHÁM PHÁ CHẤT LƯỢNG DỮ LIỆU (EDA) & LÀM SẠCH — OLIST DATASET")
    print("=" * 85)

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 1: ĐỌC CÁC BẢNG NGUỒN & KIỂM TRA SƠ BỘ
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 1/6] ĐỌC 6 BẢNG NGUỒN OLIST & XÁC NHẬN CẤU TRÚC...")

    for path in [raw_orders, raw_items, raw_customers, raw_products, raw_payments, raw_category]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Không tìm thấy file nguồn: {path}")

    df_orders    = pd.read_csv(raw_orders,    dtype=str)
    df_items     = pd.read_csv(raw_items,     dtype=str)
    df_customers = pd.read_csv(raw_customers, dtype=str)
    df_products  = pd.read_csv(raw_products,  dtype=str)
    df_payments  = pd.read_csv(raw_payments,  dtype=str)
    df_category  = pd.read_csv(raw_category)

    print(f"  + orders    : {len(df_orders):>7,} dòng × {len(df_orders.columns)} cột")
    print(f"  + items     : {len(df_items):>7,} dòng × {len(df_items.columns)} cột")
    print(f"  + customers : {len(df_customers):>7,} dòng × {len(df_customers.columns)} cột")
    print(f"  + products  : {len(df_products):>7,} dòng × {len(df_products.columns)} cột")
    print(f"  + payments  : {len(df_payments):>7,} dòng × {len(df_payments.columns)} cột")
    print(f"  + category  : {len(df_category):>7,} dòng × {len(df_category.columns)} cột  (từ điển dịch)")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 2: HỢP NHẤT (JOIN) CÁC BẢNG THÀNH BẢNG PHẲNG PHÂN TÍCH
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 2/6] HỢP NHẤT CÁC BẢNG (JOIN THEO order_id / product_id)...")

    # 2.1 items ← customers qua orders
    df = (
        df_items
        .merge(df_orders,    on="order_id",   how="left", suffixes=("", "_order"))
        .merge(df_customers, on="customer_id", how="left", suffixes=("", "_cust"))
    )

    # 2.2 products + dịch category
    df_products_named = df_products.merge(
        df_category,
        on="product_category_name",
        how="left"
    )
    df = df.merge(df_products_named, on="product_id", how="left", suffixes=("", "_prod"))

    # 2.3 payments: lấy tổng tiền mỗi đơn (nhiều phương thức → tổng hợp)
    df_pay_agg = (
        df_payments
        .assign(payment_value=lambda x: pd.to_numeric(x["payment_value"], errors="coerce").fillna(0))
        .groupby("order_id")
        .agg(
            payment_type       =("payment_type",         lambda s: s.mode().iloc[0] if len(s) else "unknown"),
            payment_installments=("payment_installments", lambda s: pd.to_numeric(s, errors="coerce").max()),
            total_payment_value=("payment_value",         "sum"),
        )
        .reset_index()
    )
    df = df.merge(df_pay_agg, on="order_id", how="left")

    total_raw_rows = len(df)
    print(f"  → Bảng hợp nhất: {total_raw_rows:,} dòng × {len(df.columns)} cột (độ hạt: 1 dòng = 1 order_item)")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 3: KIỂM TRA CHẤT LƯỢNG DỮ LIỆU (MISSING, ANOMALIES, DUPLICATES)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 3/6] KIỂM TRA CHẤT LƯỢNG DỮ LIỆU NGUỒN...")

    # 3.1 Chuyển kiểu cho các cột số/ngày cần dùng
    df["price"]         = pd.to_numeric(df["price"],         errors="coerce")
    df["freight_value"] = pd.to_numeric(df["freight_value"], errors="coerce")
    df["order_item_id"] = pd.to_numeric(df["order_item_id"], errors="coerce")

    for col in ["order_purchase_timestamp", "order_approved_at",
                "order_delivered_carrier_date", "order_delivered_customer_date",
                "order_estimated_delivery_date", "shipping_limit_date"]:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # 3.2 Missing values
    null_counts = df.isnull().sum()
    null_pct    = (null_counts / total_raw_rows * 100).round(2)
    missing_df  = pd.DataFrame({"Missing_Count": null_counts, "Percentage(%)": null_pct})
    print("\n1. Thống kê dữ liệu khuyết thiếu (Missing Values):")
    print(missing_df[missing_df["Missing_Count"] > 0].to_string())

    # 3.3 Trùng lặp (order_id, order_item_id) — khóa tự nhiên của items
    exact_dups = df.duplicated()
    key_dups   = df.duplicated(subset=["order_id", "order_item_id"])
    print(f"\n2. Bản ghi trùng lặp tuyệt đối    : {exact_dups.sum():,} dòng")
    print(f"   Trùng khoá (order_id,item_id)  : {key_dups.sum():,} dòng")

    # 3.4 Phân bố order_status
    if "order_status" in df.columns:
        print("\n3. Phân bố trạng thái đơn hàng (order_status):")
        print(df["order_status"].value_counts().to_string())

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 4: ÁP DỤNG QUY TẮC LỌC & PHÂN LOẠI DỮ LIỆU BỊ LOẠI (WATERFALL)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 4/6] ÁP DỤNG QUY TẮC LÀM SẠCH (WATERFALL REJECTION)...")

    df_work = df.copy()
    rejection_reason = pd.Series(index=df_work.index, dtype="object")

    # Quy tắc 1: Trùng lặp tuyệt đối
    is_dup = df_work.duplicated(keep="first")
    rejection_reason[is_dup] = "EXACT_DUPLICATE"

    # Quy tắc 2: Đơn hàng không hoàn thành (canceled, unavailable)
    excluded_status = {"canceled", "unavailable"}
    is_bad_status = (~is_dup) & (
        df_work["order_status"].isin(excluded_status) if "order_status" in df_work.columns
        else pd.Series(False, index=df_work.index)
    )
    rejection_reason[is_bad_status] = "ORDER_CANCELED_OR_UNAVAILABLE"

    # Quy tắc 3: Giá <= 0 hoặc null
    price_invalid = (~is_dup) & (~is_bad_status) & (df_work["price"].isnull() | (df_work["price"] <= 0))
    rejection_reason[price_invalid] = "INVALID_PRICE_ZERO_OR_NULL"

    # Quy tắc 4: Thiếu order_id hoặc product_id (khoá chính null)
    is_missing_key = (~is_dup) & (~is_bad_status) & (~price_invalid) & (
        df_work["order_id"].isnull() | df_work["product_id"].isnull()
    )
    rejection_reason[is_missing_key] = "MISSING_PRIMARY_KEY"

    # Quy tắc 5: Thiếu thông tin khách hàng
    is_missing_cust = (~is_dup) & (~is_bad_status) & (~price_invalid) & (~is_missing_key) & (
        df_work["customer_id"].isnull() | df_work["customer_unique_id"].isnull()
    )
    rejection_reason[is_missing_cust] = "MISSING_CUSTOMER_INFO"

    # Quy tắc 6: order_purchase_timestamp null
    is_missing_date = (
        (~is_dup) & (~is_bad_status) & (~price_invalid) & (~is_missing_key) & (~is_missing_cust) &
        df_work["order_purchase_timestamp"].isnull()
    )
    rejection_reason[is_missing_date] = "MISSING_PURCHASE_DATE"

    rejected_mask = is_dup | is_bad_status | price_invalid | is_missing_key | is_missing_cust | is_missing_date
    df_rejected   = df_work[rejected_mask].copy()
    df_rejected["RejectReason"] = rejection_reason[rejected_mask]

    # Bảng đối soát Waterfall
    rules = [
        ("1. Tổng bảng hợp nhất ban đầu",             total_raw_rows,        df_work["order_id"].nunique(),         df_work["price"].fillna(0).sum()),
        ("2. Loại trùng lặp tuyệt đối",                is_dup.sum(),          df_work.loc[is_dup,"order_id"].nunique(),         df_work.loc[is_dup,"price"].fillna(0).sum()),
        ("3. Loại đơn hủy / unavailable",              is_bad_status.sum(),   df_work.loc[is_bad_status,"order_id"].nunique(),  df_work.loc[is_bad_status,"price"].fillna(0).sum()),
        ("4. Loại giá <= 0 hoặc null",                 price_invalid.sum(),   df_work.loc[price_invalid,"order_id"].nunique(),  df_work.loc[price_invalid,"price"].fillna(0).sum()),
        ("5. Loại thiếu khoá order/product",           is_missing_key.sum(),  0,                                                0),
        ("6. Loại thiếu thông tin khách hàng",         is_missing_cust.sum(), 0,                                                0),
        ("7. Loại thiếu ngày mua",                     is_missing_date.sum(), 0,                                                0),
        ("8. TẬP DỮ LIỆU SẠCH CUỐI CÙNG (CLEAN DATA)",
            (~rejected_mask).sum(),
            df_work.loc[~rejected_mask, "order_id"].nunique(),
            df_work.loc[~rejected_mask, "price"].fillna(0).sum()),
    ]
    df_audit = pd.DataFrame(rules, columns=["Bước / Quy tắc", "Số dòng", "Số đơn hàng", "Tổng price (BRL)"])
    df_audit["Tỷ lệ (%)"] = (df_audit["Số dòng"] / total_raw_rows * 100).round(2)
    print("\nBảng đối soát Waterfall:")
    print(df_audit.to_string(index=False))

    df_audit.to_csv(output_audit, index=False)
    df_rejected.to_csv(output_rejected, index=False)
    print(f"\n→ Đã lưu {len(df_rejected):,} dòng bị loại → '{output_rejected}' [OK]")

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 5: CHUẨN HÓA DỮ LIỆU SẠCH (TRANSFORMATION & ENRICHMENT)
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 5/6] CHUẨN HÓA DỮ LIỆU SẠCH...")

    df_clean = df_work[~rejected_mask].copy()

    # 5.1 Kiểu số
    df_clean["price"]         = df_clean["price"].round(2)
    df_clean["freight_value"] = pd.to_numeric(df_clean["freight_value"], errors="coerce").fillna(0).round(2)
    df_clean["total_payment_value"] = pd.to_numeric(df_clean["total_payment_value"], errors="coerce").fillna(0).round(2)

    # 5.2 Thêm cột LineRevenue = price (mỗi order_item_id = 1 đơn vị)
    df_clean["LineRevenue"] = df_clean["price"]

    # 5.3 Chuẩn hóa category: ưu tiên bản dịch tiếng Anh, fallback về Portuguese
    if "product_category_name_english" in df_clean.columns:
        df_clean["category"] = (
            df_clean["product_category_name_english"]
            .fillna(df_clean.get("product_category_name", pd.Series("unknown", index=df_clean.index)))
            .fillna("unknown")
            .str.strip()
            .str.lower()
            .replace("", "unknown")
        )
    else:
        df_clean["category"] = df_clean.get("product_category_name", "unknown").fillna("unknown")

    # 5.4 Cột trạng thái đơn giao hàng: is_delivered
    df_clean["is_delivered"] = (df_clean["order_status"] == "delivered").astype(int)

    # 5.5 Trích xuất chiều thời gian từ order_purchase_timestamp
    ts = df_clean["order_purchase_timestamp"]
    df_clean["purchase_year"]      = ts.dt.year
    df_clean["purchase_month"]     = ts.dt.month
    df_clean["purchase_yearmonth"] = ts.dt.strftime("%Y-%m")
    df_clean["purchase_day"]       = ts.dt.day
    df_clean["purchase_dayofweek"] = ts.dt.day_name()
    df_clean["purchase_hour"]      = ts.dt.hour

    # 5.6 Chuỗi khoá sạch
    for col in ["order_id", "product_id", "customer_id", "customer_unique_id",
                "seller_id", "customer_state", "customer_city"]:
        if col in df_clean.columns:
            df_clean[col] = df_clean[col].astype(str).str.strip()

    # ──────────────────────────────────────────────────────────────────────────
    # BƯỚC 6: ĐÁNH GIÁ MỨC ĐỘ PHÙ HỢP & LƯU KẾT QUẢ
    # ──────────────────────────────────────────────────────────────────────────
    print("\n[BƯỚC 6/6] ĐÁNH GIÁ & LƯU DỮ LIỆU SẠCH...")

    unique_orders     = df_clean["order_id"].nunique()
    unique_customers  = df_clean["customer_unique_id"].nunique()
    unique_products   = df_clean["product_id"].nunique()
    total_revenue_brl = df_clean["LineRevenue"].sum()

    print(f"\n📊 Tóm tắt bộ dữ liệu sạch:")
    print(f"   + Tổng dòng line-item : {len(df_clean):,}")
    print(f"   + Số đơn hàng duy nhất: {unique_orders:,}")
    print(f"   + Số khách hàng duy nhất (unique): {unique_customers:,}")
    print(f"   + Số sản phẩm duy nhất (product_id): {unique_products:,}")
    print(f"   + Tổng doanh thu (BRL) : R$ {total_revenue_brl:,.2f}")

    # Đánh giá phù hợp cho phân tích RFM
    cust_orders = df_clean.groupby("customer_unique_id")["order_id"].nunique()
    cust_spend  = df_clean.groupby("customer_unique_id")["LineRevenue"].sum()
    print(f"\n   → RFM: {unique_customers:,} KH | Đơn TB/KH: {cust_orders.mean():.2f} | Chi TB/KH: R$ {cust_spend.mean():,.2f}")

    # Đánh giá phù hợp cho Market Basket
    order_items = df_clean.groupby("order_id")["product_id"].nunique()
    multi_item  = (order_items >= 2).sum()
    print(f"   → MBA: {unique_orders:,} đơn hàng | {multi_item:,} đơn có ≥2 sản phẩm ({multi_item/unique_orders*100:.1f}%)")

    df_clean.to_csv(output_clean, index=False)
    print(f"\n✅ ĐÃ LƯU {len(df_clean):,} DÒNG SẠCH → '{output_clean}'")
    print("=" * 85)

    return df_clean, df_rejected, df_audit


if __name__ == "__main__":
    run_eda_and_cleaning()
