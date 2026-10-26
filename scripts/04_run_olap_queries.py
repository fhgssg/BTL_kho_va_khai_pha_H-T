"""
File: 04_run_olap_queries.py
Mô tả: Thực thi truy vấn OLAP trên PostgreSQL DWH (SQLite có thể chọn qua DWH_DATABASE_URL).
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")
import pandas as pd
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine

def run_olap_analysis(database_url=None):
    engine = get_engine(database_url)
    pd.set_option('display.max_columns', 15)
    pd.set_option('display.width', 1000)
    
    print("=" * 80)
    print("BÁO CÁO PHÂN TÍCH ĐA CHIỀU OLAP & ADVANCED SQL - ONLINE RETAIL DWH")
    print("=" * 80)

    # -------------------------------------------------------------------------
    # BÀI TOÁN 1: DOANH THU THEO THỜI GIAN & TĂNG TRƯỞNG MoM
    # -------------------------------------------------------------------------
    print("\n[BÀI TOÁN 1] DOANH THU THEO THÁNG & TỐC ĐỘ TĂNG TRƯỞNG (MoM GROWTH %)")
    print("-" * 80)
    q1 = """
    WITH MonthlySales AS (
        SELECT 
            d.Year, d.Month, d.YearMonth,
            COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
            SUM(f.Quantity) AS TotalUnitsSold,
            ROUND(SUM(f.TotalRevenue), 2) AS MonthlyRevenue
        FROM Fact_Sales f
        JOIN Dim_Date d ON f.DateKey = d.DateKey
        GROUP BY d.Year, d.Month, d.YearMonth
    )
    SELECT 
        YearMonth, TotalOrders, TotalUnitsSold, MonthlyRevenue,
        LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month) AS PrevMonthRevenue,
        ROUND((MonthlyRevenue - LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month)) * 100.0 
              / LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month), 2) AS MoM_Growth_Pct,
        ROUND(SUM(MonthlyRevenue) OVER (PARTITION BY Year ORDER BY Month), 2) AS YTD_Running_Total
    FROM MonthlySales
    ORDER BY Year, Month;
    """
    with engine.connect() as conn:
        df_q1 = pd.read_sql_query(text(q1), conn)
    print(df_q1.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 2: PHÂN TÍCH THỊ TRƯỜNG ĐỊA LÝ & TỶ TRỌNG
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 2] TOP 10 THỊ TRƯỜNG ĐỊA LÝ & TỶ TRỌNG DOANH THU TOÀN CẦU")
    print("-" * 80)
    q2 = """
    WITH CountrySales AS (
        SELECT 
            l.Country, l.RegionType,
            COUNT(DISTINCT f.InvoiceNo) AS TotalInvoices,
            COUNT(DISTINCT f.CustomerKey) AS TotalCustomers,
            SUM(f.Quantity) AS TotalUnits,
            ROUND(SUM(f.TotalRevenue), 2) AS CountryRevenue
        FROM Fact_Sales f
        JOIN Dim_Location l ON f.LocationKey = l.LocationKey
        GROUP BY l.Country, l.RegionType
    )
    SELECT 
        Country, RegionType, TotalInvoices, TotalCustomers, TotalUnits, CountryRevenue,
        ROUND(CountryRevenue * 100.0 / SUM(CountryRevenue) OVER (), 2) AS Revenue_Share_Pct,
        RANK() OVER (ORDER BY CountryRevenue DESC) AS CountryRank
    FROM CountrySales
    ORDER BY CountryRevenue DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q2 = pd.read_sql_query(text(q2), conn)
    print(df_q2.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 3: TOP 10 SẢN PHẨM CHỦ LỰC (BÁN CHẠY NHẤT & DOANH THU CAO NHẤT)
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 3A] TOP 10 SẢN PHẨM BÁN CHẠY NHẤT VỀ SỐ LƯỢNG (QUANTITY)")
    print("-" * 80)
    q3a = """
    SELECT 
        p.StockCode, SUBSTR(p.Description, 1, 35) AS Description,
        SUM(f.Quantity) AS TotalQtySold,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        DENSE_RANK() OVER (ORDER BY SUM(f.Quantity) DESC) AS QtyRank
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    GROUP BY p.StockCode, p.Description
    ORDER BY TotalQtySold DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q3a = pd.read_sql_query(text(q3a), conn)
    print(df_q3a.to_string(index=False))

    print("\n[BÀI TOÁN 3B] TOP 10 SẢN PHẨM DOANH THU CAO NHẤT (REVENUE)")
    print("-" * 80)
    q3b = """
    SELECT 
        p.StockCode, SUBSTR(p.Description, 1, 35) AS Description,
        SUM(f.Quantity) AS TotalQtySold,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        ROUND(AVG(f.UnitPrice), 2) AS AvgPrice,
        DENSE_RANK() OVER (ORDER BY SUM(f.TotalRevenue) DESC) AS RevRank
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    GROUP BY p.StockCode, p.Description
    ORDER BY TotalRevenue DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q3b = pd.read_sql_query(text(q3b), conn)
    print(df_q3b.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 4: KHUNG GIỜ VÀNG MUA SẮM
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 4] PHÂN BỐ GIAO DỊCH THEO KHUNG GIỜ (PEAK SHOPPING HOURS)")
    print("-" * 80)
    q4 = """
    SELECT 
        f.Hour AS ShoppingHour,
        COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
        SUM(f.Quantity) AS TotalUnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        ROUND(SUM(f.TotalRevenue) / COUNT(DISTINCT f.InvoiceNo), 2) AS AvgOrderValue,
        ROUND(SUM(f.TotalRevenue) * 100.0 / SUM(SUM(f.TotalRevenue)) OVER (), 2) AS HourlySharePct
    FROM Fact_Sales f
    GROUP BY f.Hour
    ORDER BY TotalOrders DESC;
    """
    with engine.connect() as conn:
        df_q4 = pd.read_sql_query(text(q4), conn)
    print(df_q4.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 5: CHỈ SỐ KINH DOANH ĐƠN HÀNG (AOV & AVERAGE BASKET SIZE)
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 5] GIÁ TRỊ ĐƠN HÀNG TRUNG BÌNH (AOV) & BASKET SIZE THEO THÁNG")
    print("-" * 80)
    q5 = """
    WITH OrderMetrics AS (
        SELECT 
            f.InvoiceNo, d.YearMonth,
            SUM(f.Quantity) AS OrderUnits,
            SUM(f.TotalRevenue) AS OrderValue
        FROM Fact_Sales f
        JOIN Dim_Date d ON f.DateKey = d.DateKey
        GROUP BY f.InvoiceNo, d.YearMonth
    )
    SELECT 
        YearMonth,
        COUNT(InvoiceNo) AS TotalOrders,
        ROUND(SUM(OrderValue), 2) AS TotalRevenue,
        ROUND(AVG(OrderValue), 2) AS AOV_GBP,
        ROUND(AVG(OrderUnits), 1) AS AvgBasketSize
    FROM OrderMetrics
    GROUP BY YearMonth
    ORDER BY YearMonth;
    """
    with engine.connect() as conn:
        df_q5 = pd.read_sql_query(text(q5), conn)
    print(df_q5.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 6: TỶ LỆ KHÁCH HÀNG QUAY LẠI (REPEAT CUSTOMER RATE)
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 6] TỶ LỆ KHÁCH HÀNG QUAY LẠI (REPEAT CUSTOMER RATE)")
    print("-" * 80)
    q6 = """
    WITH CustomerOrders AS (
        SELECT 
            c.CustomerKey, c.CustomerID,
            COUNT(DISTINCT f.InvoiceNo) AS OrderFrequency,
            ROUND(SUM(f.TotalRevenue), 2) AS CustomerSpending
        FROM Fact_Sales f
        JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
        WHERE c.IsGuestCustomer = 0
        GROUP BY c.CustomerKey, c.CustomerID
    )
    SELECT 
        COUNT(CustomerKey) AS TotalIdentifiedCustomers,
        SUM(CASE WHEN OrderFrequency = 1 THEN 1 ELSE 0 END) AS OneTimeBuyers,
        SUM(CASE WHEN OrderFrequency > 1 THEN 1 ELSE 0 END) AS RepeatCustomers,
        ROUND(SUM(CASE WHEN OrderFrequency > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(CustomerKey), 2) AS RepeatCustomerRate_Pct,
        ROUND(AVG(CustomerSpending), 2) AS AvgSpendPerCustomer
    FROM CustomerOrders;
    """
    with engine.connect() as conn:
        df_q6 = pd.read_sql_query(text(q6), conn)
    print(df_q6.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 7: TOP 10 KHÁCH HÀNG VIP ĐÓNG GÓP DOANH THU CAO NHẤT (DENSE_RANK)
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 7] TOP 10 KHÁCH HÀNG VIP ĐÓNG GÓP DOANH THU CAO NHẤT")
    print("-" * 80)
    q7 = """
    SELECT 
        c.CustomerID,
        c.CustomerCode,
        c.Country,
        COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
        SUM(f.Quantity) AS TotalUnitsBought,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalSpent,
        ROUND(SUM(f.TotalRevenue) / COUNT(DISTINCT f.InvoiceNo), 2) AS AvgOrderValue,
        DENSE_RANK() OVER (ORDER BY SUM(f.TotalRevenue) DESC) AS SpendingRank
    FROM Fact_Sales f
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE c.IsGuestCustomer = 0
    GROUP BY c.CustomerID, c.CustomerCode, c.Country
    ORDER BY TotalSpent DESC
    LIMIT 10;
    """
    with engine.connect() as conn:
        df_q7 = pd.read_sql_query(text(q7), conn)
    print(df_q7.to_string(index=False))

    # -------------------------------------------------------------------------
    # BÀI TOÁN 8: BÁO CÁO TỔNG HỢP DOANH THU ĐA CẤP (MÔ PHỎNG ROLLUP NĂM -> QUÝ -> THÁNG)
    # -------------------------------------------------------------------------
    print("\n\n[BÀI TOÁN 8] BÁO CÁO TỔNG HỢP DOANH THU ĐA CẤP (MÔ PHỎNG ROLLUP)")
    print("-" * 80)
    q8 = """
    SELECT 
        CAST(d.Year AS TEXT) AS ReportYear,
        d.QuarterName AS ReportQuarter,
        d.MonthName AS ReportMonth,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue,
        'Month Level' AS AggregationLevel
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.QuarterName, d.Month, d.MonthName
    UNION ALL
    SELECT 
        CAST(d.Year AS TEXT) AS ReportYear,
        d.QuarterName AS ReportQuarter,
        '--- TOTAL QUARTER ---' AS ReportMonth,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue,
        'Quarter Subtotal' AS AggregationLevel
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.QuarterName
    UNION ALL
    SELECT 
        CAST(d.Year AS TEXT) AS ReportYear,
        '--- TOTAL YEAR ---' AS ReportQuarter,
        '--- TOTAL YEAR ---' AS ReportMonth,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue,
        'Year Total' AS AggregationLevel
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.Year
    ORDER BY ReportYear, ReportQuarter, ReportMonth;
    """
    with engine.connect() as conn:
        df_q8 = pd.read_sql_query(text(q8), conn)
    print(df_q8.head(15).to_string(index=False))

    olap_demos = [
        (
            "SLICE",
            "Chọn một lát dữ liệu: doanh thu theo tháng của năm 2011.",
            """SELECT yearmonth, revenue_gbp
               FROM mv_olap_monthly_sales
               WHERE year = 2011
               ORDER BY yearmonth
               LIMIT 5""",
        ),
        (
            "DICE",
            "Chọn đồng thời nhiều chiều: UK/Đức trong quý 4 năm 2011.",
            """SELECT yearmonth, country, revenue_gbp
               FROM mv_olap_monthly_country_sales
               WHERE year = 2011 AND quarter = 4
                 AND country IN ('United Kingdom', 'Germany')
               ORDER BY yearmonth, country""",
        ),
        (
            "DRILL-DOWN",
            "Đi từ tổng doanh thu năm xuống từng tháng trong năm.",
            """SELECT yearmonth, revenue_gbp
               FROM mv_olap_monthly_sales
               WHERE year = 2011
               ORDER BY yearmonth""",
        ),
        (
            "ROLL-UP",
            "Gộp dữ liệu tháng lên cấp quý.",
            """SELECT year, quarter, SUM(revenue_gbp) AS revenue_gbp
               FROM mv_olap_monthly_sales
               GROUP BY year, quarter
               ORDER BY year, quarter""",
        ),
        (
            "PIVOT",
            "Chuyển quốc gia thành cột để so sánh doanh thu theo tháng.",
            """SELECT yearmonth,
                      SUM(CASE WHEN country = 'United Kingdom' THEN revenue_gbp ELSE 0 END) AS uk_revenue,
                      SUM(CASE WHEN country = 'Germany' THEN revenue_gbp ELSE 0 END) AS germany_revenue,
                      SUM(CASE WHEN country = 'EIRE' THEN revenue_gbp ELSE 0 END) AS eire_revenue
               FROM mv_olap_monthly_country_sales
               GROUP BY yearmonth
               ORDER BY yearmonth
               LIMIT 5""",
        ),
    ]
    print("\n\n[OLAP] MINH HỌA ĐỦ 5 THAO TÁC SLICE, DICE, DRILL-DOWN, ROLL-UP, PIVOT")
    if engine.dialect.name == "sqlite":
        with engine.begin() as con:
            con.execute(text("""
            CREATE VIEW IF NOT EXISTS mv_olap_monthly_sales AS
            SELECT
                d.Year AS year, d.Quarter AS quarter, d.Month AS month, d.YearMonth AS yearmonth,
                COUNT(DISTINCT f.InvoiceNo) AS total_orders,
                SUM(f.Quantity) AS total_units_sold,
                SUM(f.TotalRevenue) AS revenue_gbp
            FROM Fact_Sales f
            JOIN Dim_Date d ON f.DateKey = d.DateKey
            GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth;
            """))
            con.execute(text("""
            CREATE VIEW IF NOT EXISTS mv_olap_monthly_country_sales AS
            SELECT
                d.Year AS year, d.Quarter AS quarter, d.Month AS month, d.YearMonth AS yearmonth,
                l.Country AS country,
                SUM(f.Quantity) AS total_units_sold,
                SUM(f.TotalRevenue) AS revenue_gbp
            FROM Fact_Sales f
            JOIN Dim_Date d ON f.DateKey = d.DateKey
            JOIN Dim_Location l ON f.LocationKey = l.LocationKey
            GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth, l.Country;
            """))
            con.execute(text("""
            CREATE VIEW IF NOT EXISTS mv_olap_monthly_product_sales AS
            SELECT
                d.Year AS year, d.Quarter AS quarter, d.Month AS month, d.YearMonth AS yearmonth,
                p.StockCode AS stockcode, p.Description AS description,
                SUM(f.Quantity) AS total_units_sold,
                SUM(f.TotalRevenue) AS revenue_gbp
            FROM Fact_Sales f
            JOIN Dim_Date d ON f.DateKey = d.DateKey
            JOIN Dim_Product p ON f.ProductKey = p.ProductKey
            GROUP BY d.Year, d.Quarter, d.Month, d.YearMonth, p.StockCode, p.Description;
            """))

    for operation, explanation, query in olap_demos:
        print(f"\n[{operation}] {explanation}")
        with engine.connect() as conn:
            demo_result = pd.read_sql_query(text(query), conn)
        print(demo_result.to_string(index=False))

    print("\n" + "=" * 80)
    print("HOÀN TẤT THỰC THI TRUY VẤN OLAP!")
    print("=" * 80)

if __name__ == '__main__':
    run_olap_analysis()
