-- ==============================================================================
-- ĐỒ ÁN: KHO DỮ LIỆU — OLIST BRAZILIAN E-COMMERCE
-- File: 04_olap_queries.sql
-- Mô tả: 8 truy vấn phân tích OLAP đa chiều trên PostgreSQL DWH.
--        Nguồn: Fact_Sales + Dim_Date + Dim_Customer + Dim_Product + Dim_Location + Dim_Payment
-- ==============================================================================

-- ==============================================================================
-- BÀI TOÁN 1: DOANH THU THEO THÁNG & TỐC ĐỘ TĂNG TRƯỞNG (MoM GROWTH)
-- ==============================================================================
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
    YearMonth,
    TotalOrders,
    TotalItems,
    MonthlyRevenue,
    LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month) AS PrevMonthRevenue,
    ROUND(
        (MonthlyRevenue - LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month)) * 100.0
        / NULLIF(LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month), 0), 2
    ) AS MoM_Growth_Pct,
    ROUND(SUM(MonthlyRevenue) OVER (PARTITION BY Year ORDER BY Month)::numeric, 2) AS YTD_Running_Total
FROM MonthlySales
ORDER BY Year, Month;

-- ==============================================================================
-- BÀI TOÁN 2: TOP 10 BANG (TIỂU BANG) BRAZIL THEO DOANH THU
-- ==============================================================================
WITH StateSales AS (
    SELECT
        l.CustomerState,
        l.Region,
        COUNT(DISTINCT f.OrderID)              AS TotalOrders,
        COUNT(DISTINCT f.CustomerKey)          AS UniqueCustomers,
        ROUND(SUM(f.TotalRevenue)::numeric, 2) AS TotalRevenue,
        ROUND(SUM(f.FreightValue)::numeric, 2) AS TotalFreight
    FROM fact_sales f
    JOIN dim_location l ON f.LocationKey = l.LocationKey
    GROUP BY l.CustomerState, l.Region
),
TotalRev AS (SELECT SUM(TotalRevenue) AS Grand FROM StateSales)
SELECT
    s.CustomerState,
    s.Region,
    s.TotalOrders,
    s.UniqueCustomers,
    s.TotalRevenue,
    s.TotalFreight,
    ROUND(s.TotalRevenue * 100.0 / t.Grand, 2) AS RevShare_Pct,
    RANK() OVER (ORDER BY s.TotalRevenue DESC)  AS Rev_Rank
FROM StateSales s, TotalRev t
ORDER BY s.TotalRevenue DESC
LIMIT 10;

-- ==============================================================================
-- BÀI TOÁN 3: TOP 10 DANH MỤC SẢN PHẨM BÁN CHẠY NHẤT (THEO SỐ ĐƠN)
-- ==============================================================================
SELECT
    COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'Unknown') AS Category,
    COUNT(DISTINCT f.OrderID)                  AS TotalOrders,
    COUNT(*)                                   AS TotalItems,
    ROUND(SUM(f.TotalRevenue)::numeric, 2)     AS TotalRevenue,
    ROUND(AVG(f.Price)::numeric, 2)            AS AvgPrice,
    RANK() OVER (ORDER BY COUNT(*) DESC)       AS Items_Rank
FROM fact_sales f
JOIN dim_product p ON f.ProductKey = p.ProductKey
GROUP BY COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'Unknown')
ORDER BY TotalItems DESC
LIMIT 10;

-- ==============================================================================
-- BÀI TOÁN 4: ROLLUP ĐA CẤP (NĂM → QUÝ → THÁNG) — mô phỏng CUBE OLAP
-- ==============================================================================
WITH Base AS (
    SELECT d.Year, d.QuarterName, d.YearMonth,
           ROUND(SUM(f.TotalRevenue)::numeric, 2) AS Revenue,
           COUNT(DISTINCT f.OrderID) AS Orders
    FROM fact_sales f JOIN dim_date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.QuarterName, d.YearMonth
)
SELECT 'Tháng'   AS Level, Year, QuarterName, YearMonth, Revenue, Orders FROM Base
UNION ALL
SELECT 'Quý',   Year, QuarterName, NULL,
    ROUND(SUM(Revenue)::numeric, 2), SUM(Orders)
FROM Base GROUP BY Year, QuarterName
UNION ALL
SELECT 'Năm',   Year, NULL, NULL,
    ROUND(SUM(Revenue)::numeric, 2), SUM(Orders)
FROM Base GROUP BY Year
ORDER BY Year, QuarterName NULLS LAST, YearMonth NULLS LAST;

-- ==============================================================================
-- BÀI TOÁN 5: PHÂN TÍCH KHUNG GIỜ MUA SẮM (PEAK HOURS)
-- ==============================================================================
SELECT
    f.PurchaseHour                            AS Hour,
    COUNT(DISTINCT f.OrderID)                 AS TotalOrders,
    COUNT(*)                                  AS TotalItems,
    ROUND(SUM(f.TotalRevenue)::numeric, 2)    AS Revenue,
    RANK() OVER (ORDER BY COUNT(DISTINCT f.OrderID) DESC) AS Hour_Rank
FROM fact_sales f
GROUP BY f.PurchaseHour
ORDER BY f.PurchaseHour;

-- ==============================================================================
-- BÀI TOÁN 6: PHÂN TÍCH PHƯƠNG THỨC THANH TOÁN & TRẢ GÓP
-- ==============================================================================
SELECT
    pm.PaymentType,
    pm.PaymentTypeVN,
    COUNT(DISTINCT f.OrderID)                           AS TotalOrders,
    ROUND(AVG(f.PaymentInstallments)::numeric, 2)       AS AvgInstallments,
    ROUND(SUM(f.TotalPaymentValue)::numeric, 2)         AS TotalPaymentValue,
    ROUND(AVG(f.TotalPaymentValue)::numeric, 2)         AS AvgOrderValue,
    RANK() OVER (ORDER BY COUNT(DISTINCT f.OrderID) DESC) AS Usage_Rank
FROM fact_sales f
JOIN dim_payment pm ON f.PaymentKey = pm.PaymentKey
GROUP BY pm.PaymentType, pm.PaymentTypeVN
ORDER BY TotalOrders DESC;

-- ==============================================================================
-- BÀI TOÁN 7: TỶ LỆ GIAO HÀNG THÀNH CÔNG THEO VÙNG KINH TẾ
-- ==============================================================================
SELECT
    l.Region,
    l.CustomerState,
    COUNT(DISTINCT f.OrderID)                                          AS TotalOrders,
    SUM(f.IsDelivered)                                                 AS DeliveredOrders,
    ROUND(SUM(f.IsDelivered) * 100.0 / COUNT(DISTINCT f.OrderID), 2)  AS DeliveryRate_Pct,
    ROUND(AVG(f.FreightValue)::numeric, 2)                            AS AvgFreight
FROM fact_sales f
JOIN dim_location l ON f.LocationKey = l.LocationKey
GROUP BY l.Region, l.CustomerState
ORDER BY l.Region, DeliveryRate_Pct DESC;

-- ==============================================================================
-- BÀI TOÁN 8: AOV (AVERAGE ORDER VALUE) THEO THÁNG & VÙNG
--             Window Function: DENSE_RANK + LAG cho tăng trưởng AOV
-- ==============================================================================
WITH OrderRevenue AS (
    SELECT
        f.OrderID,
        d.YearMonth,
        d.Year,
        d.Month,
        l.Region,
        SUM(f.TotalRevenue) AS OrderValue
    FROM fact_sales f
    JOIN dim_date d     ON f.DateKey     = d.DateKey
    JOIN dim_location l ON f.LocationKey = l.LocationKey
    GROUP BY f.OrderID, d.YearMonth, d.Year, d.Month, l.Region
),
AOV_Monthly AS (
    SELECT
        YearMonth, Year, Month, Region,
        COUNT(OrderID)                          AS TotalOrders,
        ROUND(AVG(OrderValue)::numeric, 2)      AS AOV
    FROM OrderRevenue
    GROUP BY YearMonth, Year, Month, Region
)
SELECT
    YearMonth,
    Region,
    TotalOrders,
    AOV,
    LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month) AS PrevAOV,
    ROUND(
        (AOV - LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month)) * 100.0
        / NULLIF(LAG(AOV, 1) OVER (PARTITION BY Region ORDER BY Year, Month), 0),
    2) AS AOV_Growth_Pct,
    DENSE_RANK() OVER (PARTITION BY YearMonth ORDER BY AOV DESC) AS AOV_Region_Rank
FROM AOV_Monthly
ORDER BY YearMonth, Region;
