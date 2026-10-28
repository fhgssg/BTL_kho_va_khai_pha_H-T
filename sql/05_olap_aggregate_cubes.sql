-- ==============================================================================
-- ĐỒ ÁN: KHO DỮ LIỆU — OLIST BRAZILIAN E-COMMERCE
-- File: 05_olap_aggregate_cubes.sql
-- Mô tả: Tạo 3 Materialized Views tổng hợp OLAP phục vụ Dashboard & Báo cáo.
--        Chạy sau khi nạp đủ Fact_Sales + Dim_Date + Dim_Location + Dim_Product.
-- ==============================================================================

-- Xóa view cũ (nếu có từ schema Online Retail)
DROP MATERIALIZED VIEW IF EXISTS mv_olap_monthly_sales CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_olap_monthly_country_sales CASCADE;
DROP MATERIALIZED VIEW IF EXISTS mv_olap_monthly_product_sales CASCADE;

-- ==============================================================================
-- 1. MV: Doanh thu tổng hợp theo Tháng
-- ==============================================================================
CREATE MATERIALIZED VIEW mv_olap_monthly_sales AS
SELECT
    d.Year,
    d.Month,
    d.YearMonth,
    d.QuarterName,
    COUNT(DISTINCT f.OrderID)                    AS TotalOrders,
    COUNT(*)                                     AS TotalItems,
    COUNT(DISTINCT f.CustomerKey)                AS UniqueCustomers,
    ROUND(SUM(f.TotalRevenue)::numeric, 2)       AS MonthlyRevenue,
    ROUND(AVG(f.Price)::numeric, 2)              AS AvgItemPrice,
    ROUND(SUM(f.FreightValue)::numeric, 2)       AS TotalFreight,
    ROUND(SUM(f.TotalPaymentValue)::numeric, 2)  AS TotalPaymentValue
FROM fact_sales f
JOIN dim_date d ON f.DateKey = d.DateKey
GROUP BY d.Year, d.Month, d.YearMonth, d.QuarterName
ORDER BY d.Year, d.Month;

-- ==============================================================================
-- 2. MV: Doanh thu theo Tháng × Bang (Địa lý)
-- ==============================================================================
CREATE MATERIALIZED VIEW mv_olap_monthly_country_sales AS
SELECT
    d.Year,
    d.Month,
    d.YearMonth,
    l.CustomerState,
    l.Region,
    COUNT(DISTINCT f.OrderID)                AS TotalOrders,
    COUNT(DISTINCT f.CustomerKey)            AS UniqueCustomers,
    ROUND(SUM(f.TotalRevenue)::numeric, 2)   AS MonthlyRevenue,
    ROUND(SUM(f.FreightValue)::numeric, 2)   AS TotalFreight
FROM fact_sales f
JOIN dim_date d     ON f.DateKey     = d.DateKey
JOIN dim_location l ON f.LocationKey = l.LocationKey
GROUP BY d.Year, d.Month, d.YearMonth, l.CustomerState, l.Region
ORDER BY d.Year, d.Month, MonthlyRevenue DESC;

-- ==============================================================================
-- 3. MV: Doanh thu theo Tháng × Danh mục Sản phẩm
-- ==============================================================================
CREATE MATERIALIZED VIEW mv_olap_monthly_product_sales AS
SELECT
    d.Year,
    d.Month,
    d.YearMonth,
    p.CategoryNameEN,
    p.CategoryNamePT,
    COUNT(DISTINCT f.OrderID)                AS TotalOrders,
    COUNT(*)                                 AS TotalItems,
    ROUND(SUM(f.TotalRevenue)::numeric, 2)   AS MonthlyRevenue,
    ROUND(AVG(f.Price)::numeric, 2)          AS AvgPrice
FROM fact_sales f
JOIN dim_date d    ON f.DateKey    = d.DateKey
JOIN dim_product p ON f.ProductKey = p.ProductKey
GROUP BY d.Year, d.Month, d.YearMonth, p.CategoryNameEN, p.CategoryNamePT
ORDER BY d.Year, d.Month, MonthlyRevenue DESC;
