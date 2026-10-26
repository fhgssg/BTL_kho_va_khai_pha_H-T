"""
File: 03b_dwh_test_reconciliation.py
Mô tả: Bộ kiểm thử và đối soát toàn diện Kho Dữ Liệu (DWH Automated Test & Reconciliation Suite):
       1. Đối chiếu số dòng (Row count reconciliation) giữa file sạch và Fact/Dim.
       2. Đối chiếu số lượng (Quantity) và doanh thu (TotalRevenue) với ngưỡng sai số nghiêm ngặt.
       3. Kiểm tra tính toàn vẹn khóa ngoại (Referential Integrity: 0 orphan keys).
       4. Kiểm tra ràng buộc không chứa NULL trong các khóa và measures của Fact.
       5. Kiểm tra tuân thủ các quy tắc nghiệp vụ (không có đơn hủy, không có số lượng/đơn giá <= 0).
       6. Đối soát khách vãng lai (Guest Customer Mapping).
       7. Kiểm tra đối chiếu trên các lát cắt phân tích (Slice & Dice Spot-checks: UK, Tháng 11/2011, Top SKU).
       8. Đối soát doanh thu các khối tổng hợp OLAP trên PostgreSQL.
       9. Xuất báo cáo kiểm thử nghiệm thu (PASS/FAIL) ra file outputs/dwh_test_reconciliation_report.csv.
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import pandas as pd
import numpy as np
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine

CLEAN_CSV = os.path.join(BASE_DIR, "data", "processed", "data_cleaned.csv")
REPORT_PATH = os.path.join(BASE_DIR, "outputs", "dwh_test_reconciliation_report.csv")

class _QueryAdapter:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, query):
        return self.connection.execute(text(query))

def run_dwh_test_suite(db_path=None, clean_csv=None, output_report=None, verbose=True):
    if clean_csv is None:
        clean_csv = CLEAN_CSV
    if output_report is None:
        output_report = REPORT_PATH

    print("=" * 95)
    print(" HỆ THỐNG KIỂM THỬ VÀ ĐỐI SOÁT TỰ ĐỘNG KHO DỮ LIỆU (DWH TEST & RECONCILIATION SUITE)")
    print("=" * 95)

    if not os.path.exists(clean_csv):
        raise FileNotFoundError(f"Không tìm thấy file dữ liệu sạch tại: '{clean_csv}'")

    database_url = None
    if db_path:
        database_url = db_path if "://" in db_path else f"sqlite:///{os.path.abspath(db_path).replace(os.sep, '/')}"
    engine = get_engine(database_url)
    print(f"-> Cơ sở dữ liệu: '{engine.url.get_backend_name()}'")
    print(f"-> File nguồn sạch: '{clean_csv}'")

    # Đọc dữ liệu nguồn sạch để đối chiếu
    df_clean = pd.read_csv(clean_csv, dtype={'InvoiceNo': str, 'StockCode': str}, low_memory=False)
    df_clean['InvoiceDate'] = pd.to_datetime(df_clean['InvoiceDate'])
    
    conn = engine.connect()
    cursor = _QueryAdapter(conn)

    tests_results = []
    test_counter = 1

    def record_test(test_id, category, description, expected, actual, diff, criteria, passed):
        status = "PASS" if passed else "FAIL"
        tests_results.append({
            "Test_ID": test_id,
            "Category": category,
            "Test_Description": description,
            "Expected_Value": expected,
            "Actual_Value": actual,
            "Discrepancy": diff,
            "Acceptance_Criteria": criteria,
            "Status": status
        })
        if verbose:
            tag = "✅ [PASS]" if passed else "❌ [FAIL]"
            print(f"  {tag} {test_id} ({category}): {description}")
            print(f"       + Kỳ vọng (Expected): {expected}")
            print(f"       + Thực tế (Actual):   {actual} | Chênh lệch (Diff): {diff} (Tiêu chí: {criteria})")

    # --------------------------------------------------------------------------
    # NHÓM 1: ĐỐI CHIẾU SỐ LƯỢNG DÒNG (ROW COUNT RECONCILIATION)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 1/7] ĐỐI CHIẾU SỐ DÒNG CÁC BẢNG (ROW COUNT RECONCILIATION)")
    print("-" * 80)

    # 1.1 Fact_Sales Row Count
    src_fact_rows = len(df_clean)
    dwh_fact_rows = cursor.execute("SELECT COUNT(*) FROM Fact_Sales").fetchone()[0]
    diff_fact_rows = abs(src_fact_rows - dwh_fact_rows)
    record_test(
        f"TC{test_counter:02d}", "Row Count", "Khớp số dòng Fact_Sales với dữ liệu nguồn sạch",
        f"{src_fact_rows:,} dòng", f"{dwh_fact_rows:,} dòng", diff_fact_rows, "Diff == 0",
        diff_fact_rows == 0
    )
    test_counter += 1

    # 1.2 Dim_Date Row Count
    expected_days = (df_clean['InvoiceDate'].max().normalize() - df_clean['InvoiceDate'].min().normalize()).days + 1
    dwh_date_rows = cursor.execute("SELECT COUNT(*) FROM Dim_Date").fetchone()[0]
    diff_date_rows = abs(expected_days - dwh_date_rows)
    record_test(
        f"TC{test_counter:02d}", "Row Count", "Khớp số ngày Dim_Date bao phủ toàn dải thời gian",
        f"{expected_days:,} ngày", f"{dwh_date_rows:,} ngày", diff_date_rows, "Diff == 0",
        diff_date_rows == 0
    )
    test_counter += 1

    # 1.3 Dim_Location Row Count
    src_countries = df_clean['Country'].dropna().nunique()
    dwh_loc_rows = cursor.execute("SELECT COUNT(*) FROM Dim_Location").fetchone()[0]
    diff_loc_rows = abs(src_countries - dwh_loc_rows)
    record_test(
        f"TC{test_counter:02d}", "Row Count", "Khớp số quốc gia trong Dim_Location",
        f"{src_countries:,} quốc gia", f"{dwh_loc_rows:,} quốc gia", diff_loc_rows, "Diff == 0",
        diff_loc_rows == 0
    )
    test_counter += 1

    # 1.4 Dim_Customer Row Count (Khách định danh + 1 khách vãng lai GUEST)
    src_cust = df_clean['CustomerID_Clean'].nunique()
    dwh_cust_rows = cursor.execute("SELECT COUNT(*) FROM Dim_Customer").fetchone()[0]
    diff_cust_rows = abs(src_cust - dwh_cust_rows)
    record_test(
        f"TC{test_counter:02d}", "Row Count", "Khớp số khách hàng trong Dim_Customer (gồm GUEST)",
        f"{src_cust:,} khách", f"{dwh_cust_rows:,} khách", diff_cust_rows, "Diff == 0",
        diff_cust_rows == 0
    )
    test_counter += 1

    # 1.5 Dim_Product Row Count
    src_prod = df_clean['StockCode'].nunique()
    dwh_prod_rows = cursor.execute("SELECT COUNT(*) FROM Dim_Product").fetchone()[0]
    diff_prod_rows = abs(src_prod - dwh_prod_rows)
    record_test(
        f"TC{test_counter:02d}", "Row Count", "Khớp số mặt hàng SKU trong Dim_Product",
        f"{src_prod:,} sản phẩm", f"{dwh_prod_rows:,} sản phẩm", diff_prod_rows, "Diff == 0",
        diff_prod_rows == 0
    )
    test_counter += 1

    # --------------------------------------------------------------------------
    # NHÓM 2: ĐỐI CHIẾU ĐỘ ĐO TÀI CHÍNH & SẢN LƯỢNG (MEASURES RECONCILIATION)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 2/7] ĐỐI CHIẾU ĐỘ ĐO SẢN LƯỢNG & DOANH THU (MEASURES RECONCILIATION)")
    print("-" * 80)

    # 2.1 Total Quantity
    src_qty = int(df_clean['Quantity'].sum())
    dwh_qty = int(cursor.execute("SELECT SUM(Quantity) FROM Fact_Sales").fetchone()[0])
    diff_qty = abs(src_qty - dwh_qty)
    record_test(
        f"TC{test_counter:02d}", "Measures", "Đối chiếu tổng số lượng hàng bán (Total Quantity)",
        f"{src_qty:,} đơn vị", f"{dwh_qty:,} đơn vị", diff_qty, "Diff == 0",
        diff_qty == 0
    )
    test_counter += 1

    # 2.2 Total Revenue
    rev_col = 'LineRevenue' if 'LineRevenue' in df_clean.columns else 'TotalAmount'
    src_rev = round(float(df_clean[rev_col].sum()), 2)
    dwh_rev = round(float(cursor.execute("SELECT SUM(TotalRevenue) FROM Fact_Sales").fetchone()[0]), 2)
    diff_rev = round(abs(src_rev - dwh_rev), 4)
    record_test(
        f"TC{test_counter:02d}", "Measures", "Đối chiếu tổng doanh thu toàn hệ thống (Total Revenue)",
        f"£{src_rev:,.2f}", f"£{dwh_rev:,.2f}", f"£{diff_rev:.4f}", "Diff < 0.01 GBP",
        diff_rev < 0.01
    )
    test_counter += 1

    # --------------------------------------------------------------------------
    # NHÓM 3: TÍNH TOÀN VẸN THAM CHIẾU & RÀNG BUỘC KHÓA (REFERENTIAL INTEGRITY)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 3/7] KIỂM TRA RÀNG BUỘC KHÓA NGOẠI (REFERENTIAL INTEGRITY & NULL CHECKS)")
    print("-" * 80)

    orphan_queries = [
        ("DateKey mồ côi (không tồn tại trong Dim_Date)", "SELECT COUNT(*) FROM Fact_Sales WHERE DateKey NOT IN (SELECT DateKey FROM Dim_Date)"),
        ("CustomerKey mồ côi (không tồn tại trong Dim_Customer)", "SELECT COUNT(*) FROM Fact_Sales WHERE CustomerKey NOT IN (SELECT CustomerKey FROM Dim_Customer)"),
        ("ProductKey mồ côi (không tồn tại trong Dim_Product)", "SELECT COUNT(*) FROM Fact_Sales WHERE ProductKey NOT IN (SELECT ProductKey FROM Dim_Product)"),
        ("LocationKey mồ côi (không tồn tại trong Dim_Location)", "SELECT COUNT(*) FROM Fact_Sales WHERE LocationKey NOT IN (SELECT LocationKey FROM Dim_Location)")
    ]

    for desc, q in orphan_queries:
        orphan_cnt = cursor.execute(q).fetchone()[0]
        record_test(
            f"TC{test_counter:02d}", "Integrity", desc,
            "0 bản ghi", f"{orphan_cnt} bản ghi", orphan_cnt, "Orphans == 0",
            orphan_cnt == 0
        )
        test_counter += 1

    # 3.2 Null check in Fact_Sales
    q_nulls = """
    SELECT COUNT(*) FROM Fact_Sales 
    WHERE SalesKey IS NULL OR InvoiceNo IS NULL OR DateKey IS NULL 
       OR CustomerKey IS NULL OR ProductKey IS NULL OR LocationKey IS NULL 
       OR Quantity IS NULL OR UnitPrice IS NULL OR TotalRevenue IS NULL
    """
    null_records = cursor.execute(q_nulls).fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Integrity", "Kiểm tra giá trị NULL trong các khóa và measures của Fact",
        "0 bản ghi", f"{null_records} bản ghi", null_records, "Nulls == 0",
        null_records == 0
    )
    test_counter += 1

    # --------------------------------------------------------------------------
    # NHÓM 4: KIỂM TRA TUÂN THỦ QUY TẮC NGHIỆP VỤ (BUSINESS RULES INTEGRITY)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 4/7] KIỂM TRA TUÂN THỦ QUY TẮC NGHIỆP VỤ SAU ETL (BUSINESS RULES)")
    print("-" * 80)

    # 4.1 Không có đơn hủy trong Fact_Sales
    canc_in_fact = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE InvoiceNo LIKE 'C%'").fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Business Rules", "Fact_Sales không chứa hóa đơn hủy (bắt đầu bằng 'C')",
        "0 bản ghi", f"{canc_in_fact} bản ghi", canc_in_fact, "Cancelled == 0",
        canc_in_fact == 0
    )
    test_counter += 1

    # 4.2 Quantity > 0
    neg_q_fact = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE Quantity <= 0").fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Business Rules", "Fact_Sales không chứa số lượng bán <= 0",
        "0 bản ghi", f"{neg_q_fact} bản ghi", neg_q_fact, "Quantity <= 0 is 0",
        neg_q_fact == 0
    )
    test_counter += 1

    # 4.3 UnitPrice > 0
    neg_p_fact = cursor.execute("SELECT COUNT(*) FROM Fact_Sales WHERE UnitPrice <= 0").fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Business Rules", "Fact_Sales không chứa đơn giá bán <= 0",
        "0 bản ghi", f"{neg_p_fact} bản ghi", neg_p_fact, "UnitPrice <= 0 is 0",
        neg_p_fact == 0
    )
    test_counter += 1

    # 4.4 Đẳng thức dòng: TotalRevenue = Quantity * UnitPrice
    q_calc_diff = "SELECT COUNT(*) FROM Fact_Sales WHERE ABS(TotalRevenue - ROUND(Quantity * UnitPrice, 2)) > 0.01"
    calc_err_count = cursor.execute(q_calc_diff).fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Business Rules", "Khớp phép tính dòng: TotalRevenue == ROUND(Quantity * UnitPrice, 2)",
        "0 bản ghi", f"{calc_err_count} bản ghi", calc_err_count, "Calculation Errors == 0",
        calc_err_count == 0
    )
    test_counter += 1

    # 4.5 Khách vãng lai: Nối đúng về bản ghi Guest (CustomerID = -1)
    expected_guest_rows = (df_clean['IsGuestCustomer'] == 1).sum()
    dwh_guest_rows = cursor.execute("""
        SELECT COUNT(*) FROM Fact_Sales f 
        JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey 
        WHERE c.CustomerID = -1
    """).fetchone()[0]
    diff_guest = abs(expected_guest_rows - dwh_guest_rows)
    record_test(
        f"TC{test_counter:02d}", "Business Rules", "Ánh xạ chính xác khách vãng lai (IsGuestCustomer -> CustomerID = -1)",
        f"{expected_guest_rows:,} dòng", f"{dwh_guest_rows:,} dòng", diff_guest, "Diff == 0",
        diff_guest == 0
    )
    test_counter += 1

    # --------------------------------------------------------------------------
    # NHÓM 5: ĐỐI SOÁT TRÊN CÁC LÁT CẮT NGHIỆP VỤ (SLICE & DICE SPOT-CHECKS)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 5/7] KIỂM TRA ĐỐI CHIẾU TRÊN CÁC LÁT CẮT NGHIỆP VỤ (SLICE & DICE SPOT-CHECKS)")
    print("-" * 80)

    # 5.1 Lát cắt Thị trường nội địa: United Kingdom
    src_uk_rev = round(float(df_clean[df_clean['Country'] == 'United Kingdom'][rev_col].sum()), 2)
    dwh_uk_rev = round(float(cursor.execute("""
        SELECT SUM(f.TotalRevenue) FROM Fact_Sales f 
        JOIN Dim_Location l ON f.LocationKey = l.LocationKey 
        WHERE l.Country = 'United Kingdom'
    """).fetchone()[0]), 2)
    diff_uk_rev = round(abs(src_uk_rev - dwh_uk_rev), 4)
    record_test(
        f"TC{test_counter:02d}", "Spot Check", "Đối soát doanh thu thị trường United Kingdom",
        f"£{src_uk_rev:,.2f}", f"£{dwh_uk_rev:,.2f}", f"£{diff_uk_rev:.4f}", "Diff < 0.01 GBP",
        diff_uk_rev < 0.01
    )
    test_counter += 1

    # 5.2 Lát cắt Thời gian: Tháng cao điểm 11/2011
    src_nov_rev = round(float(df_clean[(df_clean['InvoiceDate'].dt.year == 2011) & (df_clean['InvoiceDate'].dt.month == 11)][rev_col].sum()), 2)
    dwh_nov_rev = round(float(cursor.execute("""
        SELECT SUM(f.TotalRevenue) FROM Fact_Sales f 
        JOIN Dim_Date d ON f.DateKey = d.DateKey 
        WHERE d.Year = 2011 AND d.Month = 11
    """).fetchone()[0]), 2)
    diff_nov_rev = round(abs(src_nov_rev - dwh_nov_rev), 4)
    record_test(
        f"TC{test_counter:02d}", "Spot Check", "Đối soát doanh thu tháng cao điểm 11/2011 (Black Friday Peak)",
        f"£{src_nov_rev:,.2f}", f"£{dwh_nov_rev:,.2f}", f"£{diff_nov_rev:.4f}", "Diff < 0.01 GBP",
        diff_nov_rev < 0.01
    )
    test_counter += 1

    # 5.3 Lát cắt Sản phẩm: Top SKU 85123A (WHITE HANGING HEART T-LIGHT HOLDER)
    src_sku_qty = int(df_clean[df_clean['StockCode'] == '85123A']['Quantity'].sum())
    dwh_sku_qty = int(cursor.execute("""
        SELECT SUM(f.Quantity) FROM Fact_Sales f 
        JOIN Dim_Product p ON f.ProductKey = p.ProductKey 
        WHERE p.StockCode = '85123A'
    """).fetchone()[0])
    diff_sku_qty = abs(src_sku_qty - dwh_sku_qty)
    record_test(
        f"TC{test_counter:02d}", "Spot Check", "Đối soát số lượng bán của sản phẩm chủ lực SKU 85123A",
        f"{src_sku_qty:,} chiếc", f"{dwh_sku_qty:,} chiếc", diff_sku_qty, "Diff == 0",
        diff_sku_qty == 0
    )
    test_counter += 1

    # --------------------------------------------------------------------------
    # NHÓM 6: KIỂM TRA TÍNH ĐƠN NHẤT CỦA KHÓA (KEY UNIQUENESS)
    # --------------------------------------------------------------------------
    print("\n[PHẦN 6/7] KIỂM TRA TÍNH ĐƠN NHẤT CỦA KHÓA (KEY UNIQUENESS)")
    print("-" * 80)

    # 6.1 Khóa chính Fact_Sales đơn nhất (không bị duplicate dòng khi nạp)
    dup_saleskey_count = cursor.execute("""
        SELECT COUNT(*) FROM (
            SELECT SalesKey FROM Fact_Sales GROUP BY SalesKey HAVING COUNT(*) > 1
        ) AS duplicate_sales_keys
    """).fetchone()[0]
    record_test(
        f"TC{test_counter:02d}", "Uniqueness", "Tính đơn nhất của khóa chính SalesKey trong Fact_Sales",
        "0 bản ghi trùng", f"{dup_saleskey_count} bản ghi trùng", dup_saleskey_count, "Duplicates == 0",
        dup_saleskey_count == 0
    )
    test_counter += 1

    # 6.2 Tính đơn nhất của Natural Keys trong các Dimensions
    dim_dup_queries = [
        ("Dim_Customer", "CustomerID", "SELECT COUNT(*) FROM (SELECT CustomerID FROM Dim_Customer GROUP BY CustomerID HAVING COUNT(*) > 1) AS duplicate_customer_keys"),
        ("Dim_Product", "StockCode", "SELECT COUNT(*) FROM (SELECT StockCode FROM Dim_Product GROUP BY StockCode HAVING COUNT(*) > 1) AS duplicate_product_keys"),
        ("Dim_Location", "Country", "SELECT COUNT(*) FROM (SELECT Country FROM Dim_Location GROUP BY Country HAVING COUNT(*) > 1) AS duplicate_location_keys"),
        ("Dim_Date", "DateKey", "SELECT COUNT(*) FROM (SELECT DateKey FROM Dim_Date GROUP BY DateKey HAVING COUNT(*) > 1) AS duplicate_date_keys")
    ]

    for tbl, nat_key, q in dim_dup_queries:
        dup_cnt = cursor.execute(q).fetchone()[0]
        record_test(
            f"TC{test_counter:02d}", "Uniqueness", f"Tính đơn nhất của Natural Key '{nat_key}' trong '{tbl}'",
            "0 bản ghi trùng", f"{dup_cnt} bản ghi trùng", dup_cnt, "Duplicates == 0",
            dup_cnt == 0
        )
        test_counter += 1

    if engine.url.get_backend_name() == "postgresql":
        print("\n[PHẦN 7/7] ĐỐI SOÁT CÁC KHỐI TỔNG HỢP OLAP")
        for view_name in (
            "mv_olap_monthly_sales",
            "mv_olap_monthly_country_sales",
            "mv_olap_monthly_product_sales",
        ):
            cube_revenue = cursor.execute(
                f"SELECT COALESCE(SUM(revenue_gbp), 0) FROM {view_name}"
            ).fetchone()[0]
            fact_revenue = cursor.execute(
                "SELECT COALESCE(SUM(TotalRevenue), 0) FROM Fact_Sales"
            ).fetchone()[0]
            difference = abs(float(cube_revenue) - float(fact_revenue))
            record_test(
                f"TC{test_counter:02d}",
                "Aggregate Reconciliation",
                f"Đối soát doanh thu {view_name} với Fact_Sales",
                f"{float(fact_revenue):,.2f} GBP",
                f"{float(cube_revenue):,.2f} GBP",
                f"{difference:.2f} GBP",
                "Difference <= 0.01 GBP",
                difference <= 0.01,
            )
            test_counter += 1

    conn.close()

    # --------------------------------------------------------------------------
    # TỔNG KẾT & XUẤT BÁO CÁO NGHIỆM THU
    # --------------------------------------------------------------------------
    df_report = pd.DataFrame(tests_results)
    os.makedirs(os.path.dirname(output_report), exist_ok=True)
    df_report.to_csv(output_report, index=False, encoding='utf-8')

    total_tests = len(df_report)
    passed_tests = (df_report['Status'] == 'PASS').sum()
    failed_tests = total_tests - passed_tests

    print("\n" + "=" * 95)
    print(" KẾT QUẢ TỔNG HỢP KIỂM THỬ KHO DỮ LIỆU:")
    print("=" * 95)
    print(f"-> Tổng số phép kiểm tra (Total Tests):    {total_tests}")
    print(f"-> Số phép kiểm tra ĐẠT (Passed Tests):    {passed_tests} ({passed_tests/total_tests*100:.1f}%)")
    print(f"-> Số phép kiểm tra THẤT BẠI (Failed):     {failed_tests}")
    print(f"-> Báo cáo chi tiết đã lưu tại:            '{output_report}'")

    if failed_tests > 0:
        failed_cases = df_report[df_report['Status'] == 'FAIL']['Test_ID'].tolist()
        error_msg = f"❌ KIỂM THỬ THẤT BẠI: Có {failed_tests} phép kiểm tra không đạt ({', '.join(failed_cases)})!"
        print(error_msg)
        raise AssertionError(error_msg)
    else:
        print("\n🎉 XÁC NHẬN: 100% CÁC PHÉP KIỂM TRA ĐỀU ĐẠT TIÊU CHUẨN NGHIỆM THU (ALL PASS)!")
        print(" Kho Dữ Liệu hoàn toàn sẵn sàng cho phân tích OLAP, Khai phá RFM & Khai phá Giỏ hàng!")
        print("=" * 95)

    return df_report

if __name__ == '__main__':
    run_dwh_test_suite()
