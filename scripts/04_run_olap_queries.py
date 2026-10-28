"""
File: 04_run_olap_queries.py
Mô tả: Giai đoạn 4 - Thực thi 8 truy vấn phân tích OLAP đa chiều
       trên PostgreSQL DWH Olist Brazilian E-Commerce.
       Bao gồm minh hoạ đầy đủ 5 thao tác OLAP: SLICE, DICE, DRILL-DOWN, ROLL-UP, PIVOT.
"""

import os
import sys
import pandas as pd
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine


def run_olap_analysis(database_url=None):
    engine = get_engine(database_url)
    pd.set_option("display.max_columns", 15)
    pd.set_option("display.width", 1200)

    print("=" * 80)
    print("BÁO CÁO PHÂN TÍCH ĐA CHIỀU OLAP — OLIST BRAZILIAN E-COMMERCE DWH")
    print("=" * 80)

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 1: DOANH THU THEO THÁNG & TỐC ĐỘ TĂNG TRƯỞNG (MoM GROWTH)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n[BÀI TOÁN 1] DOANH THU THEO THÁNG & TỐC ĐỘ TĂNG TRƯỞNG (MoM GROWTH %)")
    print("-" * 80)
    q1 = """
    WITH MonthlySales AS (
        SELECT
            d.Year, d.Month, d.YearMonth,
            COUNT(DISTINCT f.OrderID)              AS TotalOrders,
            COUNT(*)                               AS TotalItems,
            ROUND(SUM(f.TotalRevenue)::numeric, 2) AS MonthlyRevenue
        FROM fact_sales f
        JOIN dim_date d ON f.DateKey = d.DateKey
        GROUP BY d.Year, d.Month, d.YearMonth
    )
    SELECT
        YearMonth, TotalOrders, TotalItems, MonthlyRevenue,
        LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month) AS PrevMonthRevenue,
        ROUND(
            (MonthlyRevenue - LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month)) * 100.0
            / NULLIF(LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month), 0),
        2) AS MoM_Growth_Pct,
        ROUND(SUM(MonthlyRevenue) OVER (PARTITION BY Year ORDER BY Month)::numeric, 2)
            AS YTD_Running_Total
    FROM MonthlySales
    ORDER BY Year, Month;
    """
    with engine.connect() as conn:
        df_q1 = pd.read_sql_query(text(q1), conn)
    print(df_q1.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 2: TOP 10 BANG BRAZIL THEO DOANH THU (TỶ TRỌNG ĐỊA LÝ)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 2] TOP 10 BANG BRAZIL THEO DOANH THU & TỶ TRỌNG")
    print("-" * 80)
    q2 = """
    WITH StateSales AS (
        SELECT
            l.CustomerState, l.Region,
            COUNT(DISTINCT f.OrderID)              AS TotalOrders,
            COUNT(DISTINCT f.CustomerKey)          AS UniqueCustomers,
            ROUND(SUM(f.TotalRevenue)::numeric, 2) AS TotalRevenue,
            ROUND(SUM(f.FreightValue)::numeric, 2) AS TotalFreight
        FROM fact_sales f
        JOIN dim_location l ON f.LocationKey = l.LocationKey
        GROUP BY l.CustomerState, l.Region
    ),
    GrandTotal AS (SELECT SUM(TotalRevenue) AS Grand FROM StateSales)
    SELECT
        s.CustomerState, s.Region, s.TotalOrders, s.UniqueCustomers,
        s.TotalRevenue, s.TotalFreight,
        ROUND(s.TotalRevenue * 100.0 / g.Grand, 2) AS RevShare_Pct,
        RANK() OVER (ORDER BY s.TotalRevenue DESC) AS Rev_Rank
    FROM StateSales s, GrandTotal g
    ORDER BY s.TotalRevenue DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q2 = pd.read_sql_query(text(q2), conn)
    print(df_q2.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 3: TOP 10 DANH MỤC SẢN PHẨM
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 3A] TOP 10 DANH MỤC SẢN PHẨM BÁN CHẠY NHẤT (SỐ ĐƠN)")
    print("-" * 80)
    q3a = """
    SELECT
        COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown') AS Category,
        COUNT(DISTINCT f.OrderID)                  AS TotalOrders,
        COUNT(*)                                   AS TotalItems,
        ROUND(SUM(f.TotalRevenue)::numeric, 2)     AS TotalRevenue,
        ROUND(AVG(f.Price)::numeric, 2)            AS AvgPrice,
        DENSE_RANK() OVER (ORDER BY COUNT(*) DESC) AS Items_Rank
    FROM fact_sales f
    JOIN dim_product p ON f.ProductKey = p.ProductKey
    GROUP BY COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown')
    ORDER BY TotalItems DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q3a = pd.read_sql_query(text(q3a), conn)
    print(df_q3a.to_string(index=False))

    print("\n[BÀI TOÁN 3B] TOP 10 DANH MỤC SẢN PHẨM DOANH THU CAO NHẤT")
    print("-" * 80)
    q3b = """
    SELECT
        COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown') AS Category,
        COUNT(DISTINCT f.OrderID)                    AS TotalOrders,
        COUNT(*)                                     AS TotalItems,
        ROUND(SUM(f.TotalRevenue)::numeric, 2)       AS TotalRevenue,
        ROUND(AVG(f.Price)::numeric, 2)              AS AvgPrice,
        DENSE_RANK() OVER (ORDER BY SUM(f.TotalRevenue) DESC) AS Rev_Rank
    FROM fact_sales f
    JOIN dim_product p ON f.ProductKey = p.ProductKey
    GROUP BY COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown')
    ORDER BY TotalRevenue DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q3b = pd.read_sql_query(text(q3b), conn)
    print(df_q3b.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 4: ROLLUP ĐA CẤP NĂM → QUÝ → THÁNG
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 4] ROLLUP ĐA CẤP: NĂM → QUÝ → THÁNG (mô phỏng CUBE OLAP)")
    print("-" * 80)
    q4 = """
    WITH Base AS (
        SELECT d.Year, d.QuarterName, d.YearMonth,
               ROUND(SUM(f.TotalRevenue)::numeric, 2) AS Revenue,
               COUNT(DISTINCT f.OrderID) AS Orders
        FROM fact_sales f JOIN dim_date d ON f.DateKey = d.DateKey
        GROUP BY d.Year, d.QuarterName, d.YearMonth
    )
    SELECT 'Tháng' AS Level, Year::text, QuarterName, YearMonth, Revenue, Orders FROM Base
    UNION ALL
    SELECT 'Quý',  Year::text, QuarterName, NULL,
        ROUND(SUM(Revenue)::numeric, 2), SUM(Orders)
    FROM Base GROUP BY Year, QuarterName
    UNION ALL
    SELECT 'Năm',  Year::text, NULL, NULL,
        ROUND(SUM(Revenue)::numeric, 2), SUM(Orders)
    FROM Base GROUP BY Year
    ORDER BY Year, QuarterName NULLS LAST, YearMonth NULLS LAST;
    """
    with engine.connect() as conn:
        df_q4 = pd.read_sql_query(text(q4), conn)
    print(df_q4.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 5: KHUNG GIỜ MUA SẮM (PEAK HOURS)
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 5] PHÂN BỐ GIỜ MUA SẮM (PEAK HOURS — 0 đến 23)")
    print("-" * 80)
    q5 = """
    SELECT
        f.PurchaseHour AS Hour,
        COUNT(DISTINCT f.OrderID)              AS TotalOrders,
        COUNT(*)                               AS TotalItems,
        ROUND(SUM(f.TotalRevenue)::numeric, 2) AS Revenue,
        ROUND(SUM(f.TotalRevenue) * 100.0 / SUM(SUM(f.TotalRevenue)) OVER (), 2) AS HourSharePct,
        RANK() OVER (ORDER BY COUNT(DISTINCT f.OrderID) DESC) AS Hour_Rank
    FROM fact_sales f
    GROUP BY f.PurchaseHour
    ORDER BY f.PurchaseHour;
    """
    with engine.connect() as conn:
        df_q5 = pd.read_sql_query(text(q5), conn)
    print(df_q5.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 6: PHƯƠNG THỨC THANH TOÁN & TRẢ GÓP
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 6] PHÂN TÍCH PHƯƠNG THỨC THANH TOÁN & SỐ ĐỢT TRẢ GÓP")
    print("-" * 80)
    q6 = """
    SELECT
        pm.PaymentType,
        pm.PaymentTypeVN,
        COUNT(DISTINCT f.OrderID)                         AS TotalOrders,
        ROUND(AVG(f.PaymentInstallments)::numeric, 2)     AS AvgInstallments,
        ROUND(SUM(f.TotalPaymentValue)::numeric, 2)       AS TotalPaymentValue,
        ROUND(AVG(f.TotalPaymentValue)::numeric, 2)       AS AvgOrderValue,
        RANK() OVER (ORDER BY COUNT(DISTINCT f.OrderID) DESC) AS Usage_Rank
    FROM fact_sales f
    JOIN dim_payment pm ON f.PaymentKey = pm.PaymentKey
    GROUP BY pm.PaymentType, pm.PaymentTypeVN
    ORDER BY TotalOrders DESC;
    """
    with engine.connect() as conn:
        df_q6 = pd.read_sql_query(text(q6), conn)
    print(df_q6.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 7: TỶ LỆ GIAO HÀNG THÀNH CÔNG THEO VÙNG KINH TẾ
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 7] TỶ LỆ GIAO HÀNG THÀNH CÔNG THEO VÙNG KINH TẾ BRAZIL")
    print("-" * 80)
    q7 = """
    SELECT
        l.Region,
        l.CustomerState,
        COUNT(DISTINCT f.OrderID) AS TotalOrders,
        SUM(f.IsDelivered) AS DeliveredOrders,
        ROUND(SUM(f.IsDelivered) * 100.0 / COUNT(DISTINCT f.OrderID), 2) AS DeliveryRate_Pct,
        ROUND(AVG(f.FreightValue)::numeric, 2) AS AvgFreight
    FROM fact_sales f
    JOIN dim_location l ON f.LocationKey = l.LocationKey
    GROUP BY l.Region, l.CustomerState
    ORDER BY l.Region, DeliveryRate_Pct DESC;
    """
    with engine.connect() as conn:
        df_q7 = pd.read_sql_query(text(q7), conn)
    print(df_q7.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # BÀI TOÁN 8: AOV (AVERAGE ORDER VALUE) THEO THÁNG & VÙNG — Window Functions
    # ─────────────────────────────────────────────────────────────────────────
    print("\n\n[BÀI TOÁN 8] AOV THEO THÁNG & VÙNG — DENSE_RANK + LAG (WINDOW FUNCTIONS)")
    print("-" * 80)
    q8 = """
    WITH OrderRevenue AS (
        SELECT
            f.OrderID, d.YearMonth, d.Year, d.Month, l.Region,
            SUM(f.TotalRevenue) AS OrderValue
        FROM fact_sales f
        JOIN dim_date d     ON f.DateKey     = d.DateKey
        JOIN dim_location l ON f.LocationKey = l.LocationKey
        GROUP BY f.OrderID, d.YearMonth, d.Year, d.Month, l.Region
    ),
    AOV_Monthly AS (
        SELECT YearMonth, Year, Month, Region,
               COUNT(OrderID)                     AS TotalOrders,
               ROUND(AVG(OrderValue)::numeric, 2) AS AOV
        FROM OrderRevenue
        GROUP BY YearMonth, Year, Month, Region
    )
    SELECT
        YearMonth, Region, TotalOrders, AOV,
        LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month) AS PrevAOV,
        ROUND(
            (AOV - LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month)) * 100.0
            / NULLIF(LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month), 0),
        2) AS AOV_Growth_Pct,
        DENSE_RANK() OVER (PARTITION BY YearMonth ORDER BY AOV DESC) AS AOV_Region_Rank
    FROM AOV_Monthly
    ORDER BY YearMonth, Region;
    """
    with engine.connect() as conn:
        df_q8 = pd.read_sql_query(text(q8), conn)
    print(df_q8.to_string(index=False))

    # ─────────────────────────────────────────────────────────────────────────
    # MINH HOẠ 5 THAO TÁC OLAP
    # ─────────────────────────────────────────────────────────────────────────
    olap_demos = [
        (
            "SLICE",
            "Chọn một lát dữ liệu: Doanh thu tháng của Đông Nam Brazil (Southeast).",
            """SELECT yearmonth, customerstate, monthlyrevenue
               FROM mv_olap_monthly_country_sales
               WHERE region = 'Southeast'
               ORDER BY yearmonth, customerstate
               LIMIT 10""",
        ),
        (
            "DICE",
            "Chọn đồng thời nhiều chiều: SP & RJ trong quý 4.",
            """SELECT yearmonth, customerstate, monthlyrevenue
               FROM mv_olap_monthly_country_sales
               WHERE customerstate IN ('SP', 'RJ')
               ORDER BY yearmonth, customerstate
               LIMIT 10""",
        ),
        (
            "DRILL-DOWN",
            "Từ tổng doanh thu năm → từng tháng.",
            """SELECT yearmonth, monthlyrevenue
               FROM mv_olap_monthly_sales
               ORDER BY yearmonth
               LIMIT 10""",
        ),
        (
            "ROLL-UP",
            "Gộp dữ liệu tháng lên cấp quý.",
            """SELECT quartername, SUM(monthlyrevenue) AS quarterly_revenue
               FROM mv_olap_monthly_sales
               GROUP BY quartername
               ORDER BY quartername""",
        ),
        (
            "PIVOT",
            "Chuyển bang thành cột: so sánh SP vs RJ vs MG theo tháng.",
            """SELECT yearmonth,
                       SUM(CASE WHEN customerstate = 'SP' THEN monthlyrevenue ELSE 0 END) AS SP,
                       SUM(CASE WHEN customerstate = 'RJ' THEN monthlyrevenue ELSE 0 END) AS RJ,
                       SUM(CASE WHEN customerstate = 'MG' THEN monthlyrevenue ELSE 0 END) AS MG
               FROM mv_olap_monthly_country_sales
               GROUP BY yearmonth
               ORDER BY yearmonth
               LIMIT 10""",
        ),
    ]
    print("\n\n[OLAP] MINH HOẠ ĐỦ 5 THAO TÁC: SLICE, DICE, DRILL-DOWN, ROLL-UP, PIVOT")
    for operation, explanation, query in olap_demos:
        print(f"\n[{operation}] {explanation}")
        with engine.connect() as conn:
            try:
                result = pd.read_sql_query(text(query), conn)
                print(result.to_string(index=False))
            except Exception as e:
                print(f"  ⚠ Lỗi khi thực thi {operation}: {e}")

    print("\n" + "=" * 80)
    print("✅ HOÀN TẤT THỰC THI TRUY VẤN OLAP — OLIST DWH!")
    print("=" * 80)


if __name__ == "__main__":
    run_olap_analysis()
