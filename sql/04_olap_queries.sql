-- ==============================================================================
-- ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ONLINE RETAIL DATA WAREHOUSE)
-- GIAI ĐOẠN 4: TRUY VẤN PHÂN TÍCH ĐA CHIỀU (OLAP & ADVANCED SQL ANALYTICS)
-- File: 04_olap_queries.sql
-- Cơ sở dữ liệu: retail_dwh.db
-- ==============================================================================

-- ==============================================================================
-- TRUY VẤN 1: PHÂN TÍCH DOANH THU THEO THỜI GIAN & TĂNG TRƯỞNG THEO THÁNG (MoM)
-- Nghiệp vụ: Đánh giá xu hướng kinh doanh theo tháng, tăng trưởng tháng so với
--            tháng trước (MoM Growth %) và doanh thu lũy kế trong năm (Running Total).
-- Kỹ thuật SQL: Window Functions (LAG, SUM OVER PARTITION).
-- ==============================================================================
WITH MonthlySales AS (
    SELECT 
        d.Year,
        d.Month,
        d.YearMonth,
        COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
        SUM(f.Quantity) AS TotalUnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS MonthlyRevenue
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY d.Year, d.Month, d.YearMonth
)
SELECT 
    YearMonth,
    TotalOrders,
    TotalUnitsSold,
    MonthlyRevenue,
    -- Doanh thu tháng liền trước
    LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month) AS PrevMonthRevenue,
    -- Tỷ lệ tăng trưởng so với tháng trước (%)
    ROUND(
        (MonthlyRevenue - LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month)) * 100.0 
        / LAG(MonthlyRevenue, 1) OVER (ORDER BY Year, Month), 
        2
    ) AS MoM_Growth_Pct,
    -- Doanh thu lũy kế tính từ đầu năm đến tháng hiện tại (Year-to-Date Running Total)
    ROUND(SUM(MonthlyRevenue) OVER (
        PARTITION BY Year 
        ORDER BY Month 
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ), 2) AS YTD_Running_Total
FROM MonthlySales
ORDER BY Year, Month;


-- ==============================================================================
-- TRUY VẤN 2: PHÂN TÍCH THỊ TRƯỜNG ĐỊA LÝ & TỶ TRỌNG DOANH THU TOÀN CẦU
-- Nghiệp vụ: Đánh giá cơ cấu thị trường nội địa (UK) so với thị trường quốc tế,
--            tìm top 10 quốc gia đóng góp doanh thu lớn nhất.
-- Kỹ thuật SQL: Window Function (SUM OVER tính tỷ trọng %).
-- ==============================================================================
WITH CountrySales AS (
    SELECT 
        l.Country,
        l.RegionType,
        COUNT(DISTINCT f.InvoiceNo) AS TotalInvoices,
        COUNT(DISTINCT f.CustomerKey) AS TotalCustomers,
        SUM(f.Quantity) AS TotalUnits,
        ROUND(SUM(f.TotalRevenue), 2) AS CountryRevenue
    FROM Fact_Sales f
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    GROUP BY l.Country, l.RegionType
)
SELECT 
    Country,
    RegionType,
    TotalInvoices,
    TotalCustomers,
    TotalUnits,
    CountryRevenue,
    -- Tỷ trọng doanh thu của quốc gia trên tổng doanh thu toàn cầu (%)
    ROUND(CountryRevenue * 100.0 / SUM(CountryRevenue) OVER (), 2) AS Revenue_Share_Pct,
    -- Xếp hạng doanh thu
    RANK() OVER (ORDER BY CountryRevenue DESC) AS CountryRank
FROM CountrySales
ORDER BY CountryRevenue DESC
LIMIT 10;


-- ==============================================================================
-- TRUY VẤN 3: TOP 10 SẢN PHẨM BÁN CHẠY NHẤT VÀ TOP 10 SẢN PHẨM SINH LỜI CAO NHẤT
-- Nghiệp vụ: Xác định danh mục sản phẩm cốt lõi (Best-selling products & Top Revenue).
-- Kỹ thuật SQL: DENSE_RANK, CTE.
-- ==============================================================================
-- 3A: Top 10 sản phẩm bán chạy nhất về Số lượng (Quantity)
SELECT 
    p.StockCode,
    p.Description,
    SUM(f.Quantity) AS TotalQuantitySold,
    ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
    DENSE_RANK() OVER (ORDER BY SUM(f.Quantity) DESC) AS QuantityRank
FROM Fact_Sales f
JOIN Dim_Product p ON f.ProductKey = p.ProductKey
GROUP BY p.StockCode, p.Description
ORDER BY TotalQuantitySold DESC
LIMIT 10;

-- 3B: Top 10 sản phẩm đem lại Doanh thu cao nhất (Revenue)
SELECT 
    p.StockCode,
    p.Description,
    SUM(f.Quantity) AS TotalQuantitySold,
    ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
    ROUND(AVG(f.UnitPrice), 2) AS AvgSoldPrice,
    DENSE_RANK() OVER (ORDER BY SUM(f.TotalRevenue) DESC) AS RevenueRank
FROM Fact_Sales f
JOIN Dim_Product p ON f.ProductKey = p.ProductKey
GROUP BY p.StockCode, p.Description
ORDER BY TotalRevenue DESC
LIMIT 10;

-- 3C: Doanh thu theo danh mục hợp nhất (giao dịch Online Retail + danh mục chung)
SELECT
    COALESCE(p.Category, 'Chưa phân loại') AS Category,
    p.CategorySource,
    COUNT(DISTINCT p.ProductKey) AS SoldProducts,
    COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
    SUM(f.Quantity) AS TotalQuantitySold,
    ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
    ROUND(SUM(f.TotalRevenue) * 100.0 / SUM(SUM(f.TotalRevenue)) OVER (), 2) AS RevenueSharePct,
    DENSE_RANK() OVER (ORDER BY SUM(f.TotalRevenue) DESC) AS RevenueRank
FROM Fact_Sales f
JOIN Dim_Product p ON f.ProductKey = p.ProductKey
GROUP BY p.Category, p.CategorySource
ORDER BY TotalRevenue DESC;


-- ==============================================================================
-- TRUY VẤN 4: PHÂN TÍCH KHUNG GIỜ VÀNG MUA SẮM (PEAK SHOPPING HOURS)
-- Nghiệp vụ: Tìm khung giờ khách hàng đặt mua nhiều nhất để lên kế hoạch quảng cáo.
-- Kỹ thuật SQL: GROUP BY, ORDER BY, Aggregations.
-- ==============================================================================
SELECT 
    f.Hour AS ShoppingHour,
    COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
    SUM(f.Quantity) AS TotalUnitsSold,
    ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
    ROUND(SUM(f.TotalRevenue) / COUNT(DISTINCT f.InvoiceNo), 2) AS AvgRevenuePerOrder,
    ROUND(SUM(f.TotalRevenue) * 100.0 / SUM(SUM(f.TotalRevenue)) OVER (), 2) AS HourlySharePct
FROM Fact_Sales f
GROUP BY f.Hour
ORDER BY TotalOrders DESC;


-- ==============================================================================
-- TRUY VẤN 5: CHỈ SỐ KINH DOANH ĐƠN HÀNG (AOV & AVERAGE BASKET SIZE)
-- Nghiệp vụ: Đo lường Giá trị đơn hàng trung bình (Average Order Value) và kích thước
--            giỏ hàng trung bình (số lượng sản phẩm/đơn hàng) theo tháng.
-- ==============================================================================
WITH OrderMetrics AS (
    SELECT 
        f.InvoiceNo,
        d.YearMonth,
        SUM(f.Quantity) AS OrderUnits,
        SUM(f.TotalRevenue) AS OrderValue
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    GROUP BY f.InvoiceNo, d.YearMonth
)
SELECT 
    YearMonth,
    COUNT(InvoiceNo) AS NumberOfOrders,
    ROUND(SUM(OrderValue), 2) AS TotalRevenue,
    ROUND(AVG(OrderValue), 2) AS AOV,                  -- Average Order Value (GBP)
    ROUND(AVG(OrderUnits), 1) AS AvgItemsPerOrder       -- Average Basket Size
FROM OrderMetrics
GROUP BY YearMonth
ORDER BY YearMonth;


-- ==============================================================================
-- TRUY VẤN 6: PHÂN TÍCH TỶ LỆ KHÁCH HÀNG QUAY LẠI (REPEAT CUSTOMER RATE)
-- Nghiệp vụ: Đo lường mức độ trung thành của khách hàng (loại trừ khách vãng lai).
-- Kỹ thuật SQL: CASE WHEN, Subqueries.
-- ==============================================================================
WITH CustomerOrders AS (
    SELECT 
        c.CustomerKey,
        c.CustomerID,
        c.CustomerCode,
        COUNT(DISTINCT f.InvoiceNo) AS OrderFrequency,
        ROUND(SUM(f.TotalRevenue), 2) AS CustomerSpending
    FROM Fact_Sales f
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE c.IsGuestCustomer = 0 -- Chỉ xét khách hàng có đăng ký tài khoản định danh
    GROUP BY c.CustomerKey, c.CustomerID, c.CustomerCode
)
SELECT 
    COUNT(CustomerKey) AS TotalIdentifiedCustomers,
    SUM(CASE WHEN OrderFrequency = 1 THEN 1 ELSE 0 END) AS OneTimeBuyers,
    SUM(CASE WHEN OrderFrequency > 1 THEN 1 ELSE 0 END) AS RepeatCustomers,
    ROUND(
        SUM(CASE WHEN OrderFrequency > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(CustomerKey), 
        2
    ) AS RepeatCustomerRate_Pct,
    ROUND(AVG(CustomerSpending), 2) AS AvgSpendPerCustomer
FROM CustomerOrders;


-- ==============================================================================
-- TRUY VẤN 7: TOP 10 KHÁCH HÀNG VIP ĐÓNG GÓP DOANH THU CAO NHẤT
-- Nghiệp vụ: Chăm sóc tệp khách hàng giá trị cao (High-Value Customers / Wholesalers).
-- Kỹ thuật SQL: DENSE_RANK(), CTE.
-- ==============================================================================
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


-- ==============================================================================
-- TRUY VẤN 8: BÁO CÁO TỔNG HỢP DOANH THU ĐA CẤP (MÔ PHỎNG ROLLUP: NĂM -> QUÝ -> THÁNG)
-- Nghiệp vụ: Cung cấp báo cáo tài chính tổng hợp từ cấp chi tiết (Tháng) lên cấp Quý và Năm.
-- Kỹ thuật SQL: CTE + UNION ALL (chuẩn ANSI tương thích mọi CSDL).
-- ==============================================================================
-- Cấp 1: Chi tiết từng Tháng
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

-- Cấp 2: Tổng hợp theo Quý (Subtotal Quarter)
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

-- Cấp 3: Tổng hợp theo Năm (Subtotal Year)
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

