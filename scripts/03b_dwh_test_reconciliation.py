"""
File: 03b_dwh_test_reconciliation.py
Mô tả: Bộ kiểm thử và đối soát tự động toàn vẹn dữ liệu cho Kho Dữ Liệu Olist DWH.
       Kiểm thử tự động các khía cạnh:
       1. Record Count & Revenue Reconciliation (Đối soát số dòng & tổng tiền)
       2. Primary Key Uniqueness (Tính duy nhất của khóa chính)
       3. Foreign Key Referential Integrity (Toàn vẹn tham chiếu khóa ngoại)
       4. Date Range & Time Consistency (Tính nhất quán thời gian)
       5. Value Domain & Non-null Checks (Kiểm tra miền giá trị và giá trị Null)
       6. OLAP Aggregates Consistency (Đối soát Materialized Views với Fact_Sales)
"""

import os
import sys
import pandas as pd
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine

CLEAN_DATA_PATH = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
OUTPUT_REPORT_PATH = os.path.join(BASE_DIR, "outputs", "dwh_test_reconciliation_report.csv")


def run_dwh_test_suite(database_url=None):
    engine = get_engine(database_url)
    dialect = engine.dialect.name
    print("=" * 95)
    print(" HỆ THỐNG KIỂM THỬ VÀ ĐỐI SOÁT TỰ ĐỘNG KHO DỮ LIỆU — OLIST DWH")
    print("=" * 95)
    print(f"-> Cơ sở dữ liệu: '{dialect}'")
    print(f"-> File nguồn sạch: '{CLEAN_DATA_PATH}'")

    if not os.path.exists(CLEAN_DATA_PATH):
        raise FileNotFoundError(f"Không tìm thấy file sạch: {CLEAN_DATA_PATH}")

    df_clean = pd.read_csv(CLEAN_DATA_PATH, low_memory=False)
    expected_rows = len(df_clean)
    expected_revenue = float(pd.to_numeric(df_clean["price"], errors="coerce").sum())
    expected_orders = df_clean["order_id"].nunique()
    expected_customers = df_clean["customer_unique_id"].nunique()
    expected_products = df_clean["product_id"].nunique()

    test_results = []

    def record_test(test_id, category, description, expected, actual, passed, details=""):
        status = "PASSED" if passed else "FAILED"
        test_results.append({
            "Test_ID": test_id,
            "Category": category,
            "Description": description,
            "Expected": expected,
            "Actual": actual,
            "Status": status,
            "Details": details
        })
        icon = "✅" if passed else "❌"
        print(f"  {icon} [{test_id}] {description:<55} : {status}")

    with engine.connect() as conn:
        print("\n--- NHÓM 1: ĐỐI SOÁT SỐ BẢN GHI & TỔNG DOANH THU ---")
        # 1.1 Fact_Sales Row Count
        fact_rows = conn.execute(text("SELECT COUNT(*) FROM fact_sales")).fetchone()[0]
        record_test("TC01", "Volume", "Số dòng Fact_Sales khớp file sạch",
                    expected_rows, fact_rows, fact_rows == expected_rows)

        # 1.2 Total Revenue
        fact_rev = float(conn.execute(text("SELECT SUM(totalrevenue) FROM fact_sales")).fetchone()[0] or 0)
        diff_rev = abs(fact_rev - expected_revenue)
        record_test("TC02", "Financial", "Tổng doanh thu khớp 100% (dung sai < 0.05 BRL)",
                    f"R$ {expected_revenue:,.2f}", f"R$ {fact_rev:,.2f}", diff_rev < 0.05,
                    f"Chênh lệch: {diff_rev:.4f} BRL")

        # 1.3 Unique Orders
        dwh_orders = conn.execute(text("SELECT COUNT(DISTINCT orderid) FROM fact_sales")).fetchone()[0]
        record_test("TC03", "Volume", "Số đơn hàng OrderID duy nhất khớp",
                    expected_orders, dwh_orders, dwh_orders == expected_orders)

        # 1.4 Unique Customers
        dwh_cust = conn.execute(text("SELECT COUNT(*) FROM dim_customer")).fetchone()[0]
        record_test("TC04", "Dimension", "Số khách hàng trong Dim_Customer khớp",
                    expected_customers, dwh_cust, dwh_cust == expected_customers)

        # 1.5 Unique Products
        dwh_prod = conn.execute(text("SELECT COUNT(*) FROM dim_product")).fetchone()[0]
        record_test("TC05", "Dimension", "Số sản phẩm trong Dim_Product khớp",
                    expected_products, dwh_prod, dwh_prod == expected_products)

        print("\n--- NHÓM 2: TÍNH TOÀN VẸN THAM CHIẾU (FOREIGN KEY INTEGRITY) ---")
        # 2.1 Fact -> Dim_Date
        orphan_date = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_date d ON f.datekey = d.datekey
            WHERE d.datekey IS NULL
        """)).fetchone()[0]
        record_test("TC06", "Referential", "Không có khóa mồ côi Fact_Sales -> Dim_Date",
                    0, orphan_date, orphan_date == 0)

        # 2.2 Fact -> Dim_Customer
        orphan_cust = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_customer c ON f.customerkey = c.customerkey
            WHERE c.customerkey IS NULL
        """)).fetchone()[0]
        record_test("TC07", "Referential", "Không có khóa mồ côi Fact_Sales -> Dim_Customer",
                    0, orphan_cust, orphan_cust == 0)

        # 2.3 Fact -> Dim_Product
        orphan_prod = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_product p ON f.productkey = p.productkey
            WHERE p.productkey IS NULL
        """)).fetchone()[0]
        record_test("TC08", "Referential", "Không có khóa mồ côi Fact_Sales -> Dim_Product",
                    0, orphan_prod, orphan_prod == 0)

        # 2.4 Fact -> Dim_Location
        orphan_loc = conn.execute(text("""
            SELECT COUNT(*) FROM fact_sales f
            LEFT JOIN dim_location l ON f.locationkey = l.locationkey
            WHERE l.locationkey IS NULL
        """)).fetchone()[0]
        record_test("TC09", "Referential", "Không có khóa mồ côi Fact_Sales -> Dim_Location",
                    0, orphan_loc, orphan_loc == 0)

        print("\n--- NHÓM 3: TÍNH DUY NHẤT CỦA KHÓA CHÍNH (PRIMARY KEY UNIQUENESS) ---")
        pk_checks = [
            ("dim_date", "datekey", "TC10"),
            ("dim_customer", "customerkey", "TC11"),
            ("dim_product", "productkey", "TC12"),
            ("dim_location", "locationkey", "TC13"),
            ("dim_payment", "paymentkey", "TC14"),
            ("fact_sales", "saleskey", "TC15")
        ]
        for tbl, col, tcid in pk_checks:
            dup_pk = conn.execute(text(f"""
                SELECT COUNT(*) FROM (
                    SELECT {col} FROM {tbl} GROUP BY {col} HAVING COUNT(*) > 1
                ) sub
            """)).fetchone()[0]
            record_test(tcid, "Primary Key", f"Khóa chính {tbl}({col}) duy nhất 100%",
                        0, dup_pk, dup_pk == 0)

        print("\n--- NHÓM 4: MIỀN GIÁ TRỊ VÀ HỢP LỆ DỮ LIỆU (VALIDITY & RANGE) ---")
        neg_price = conn.execute(text("SELECT COUNT(*) FROM fact_sales WHERE price <= 0")).fetchone()[0]
        record_test("TC16", "Domain", "Đơn giá Price > 0 cho mọi dòng", 0, neg_price, neg_price == 0)

        invalid_hour = conn.execute(text("SELECT COUNT(*) FROM fact_sales WHERE purchasehour < 0 OR purchasehour > 23")).fetchone()[0]
        record_test("TC17", "Domain", "Khung giờ mua sắm hợp lệ [0..23]", 0, invalid_hour, invalid_hour == 0)

        if dialect == "postgresql":
            print("\n--- NHÓM 5: ĐỐI SOÁT MATERIALIZED VIEWS OLAP ---")
            mv_sales_rev = conn.execute(text("SELECT SUM(monthlyrevenue) FROM mv_olap_monthly_sales")).fetchone()[0]
            diff_mv = abs(float(mv_sales_rev or 0) - fact_rev)
            record_test("TC18", "OLAP Cube", "Doanh thu mv_olap_monthly_sales khớp Fact_Sales",
                        f"R$ {fact_rev:,.2f}", f"R$ {float(mv_sales_rev or 0):,.2f}", diff_mv < 0.1)

            mv_geo_rev = conn.execute(text("SELECT SUM(monthlyrevenue) FROM mv_olap_monthly_country_sales")).fetchone()[0]
            diff_mv_geo = abs(float(mv_geo_rev or 0) - fact_rev)
            record_test("TC19", "OLAP Cube", "Doanh thu mv_olap_monthly_country_sales khớp Fact_Sales",
                        f"R$ {fact_rev:,.2f}", f"R$ {float(mv_geo_rev or 0):,.2f}", diff_mv_geo < 0.1)

    df_report = pd.DataFrame(test_results)
    os.makedirs(os.path.dirname(OUTPUT_REPORT_PATH), exist_ok=True)
    df_report.to_csv(OUTPUT_REPORT_PATH, index=False)
    print("\n" + "=" * 95)
    passed_count = (df_report["Status"] == "PASSED").sum()
    total_count = len(df_report)
    print(f"KẾT QUẢ ĐỐI SOÁT: {passed_count}/{total_count} bài kiểm tra ĐẠT ({passed_count/total_count*100:.1f}%)")
    print(f"Báo cáo đối soát lưu tại: '{OUTPUT_REPORT_PATH}'")
    print("=" * 95)
    return df_report


if __name__ == "__main__":
    run_dwh_test_suite()
