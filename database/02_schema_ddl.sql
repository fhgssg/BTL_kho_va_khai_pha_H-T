-- ==============================================================================
-- ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ — OLIST BRAZILIAN E-COMMERCE
-- GIAI ĐOẠN 2: THIẾT KẾ MÔ HÌNH DỮ LIỆU ĐA CHIỀU (STAR SCHEMA DDL)
-- File: 02_schema_ddl.sql
-- Mô tả: DDL tạo bảng Fact và 5 Dimension chuẩn Star Schema cho Olist dataset.
--        Tương thích: PostgreSQL (dwh), DuckDB, SQLite.
-- Nguồn dữ liệu: Brazilian E-Commerce Public Dataset by Olist (Kaggle)
-- ==============================================================================

-- Xóa bảng cũ theo thứ tự phụ thuộc khóa ngoại
DROP TABLE IF EXISTS Fact_Sales CASCADE;
DROP TABLE IF EXISTS Dim_Product CASCADE;
DROP TABLE IF EXISTS Dim_Customer CASCADE;
DROP TABLE IF EXISTS Dim_Location CASCADE;
DROP TABLE IF EXISTS Dim_Date CASCADE;
DROP TABLE IF EXISTS Dim_Payment CASCADE;

-- ==============================================================================
-- 1. BẢNG CHIỀU THỜI GIAN (Dim_Date)
-- Phục vụ: Phân tích xu hướng theo Ngày / Tháng / Quý / Năm / Giờ mua sắm
-- ==============================================================================
CREATE TABLE Dim_Date (
    DateKey         INTEGER PRIMARY KEY,         -- YYYYMMDD (vd: 20170101)
    FullDate        DATE NOT NULL,               -- Ngày đầy đủ (YYYY-MM-DD)
    Day             INTEGER NOT NULL,            -- Ngày trong tháng (1 - 31)
    Month           INTEGER NOT NULL,            -- Tháng (1 - 12)
    MonthName       VARCHAR(20) NOT NULL,        -- Tên tháng (January … December)
    Quarter         INTEGER NOT NULL,            -- Quý (1 - 4)
    QuarterName     VARCHAR(10) NOT NULL,        -- Tên quý (Q1 … Q4)
    Year            INTEGER NOT NULL,            -- Năm dương lịch
    DayOfWeek       INTEGER NOT NULL,            -- 1=Monday … 7=Sunday
    DayName         VARCHAR(20) NOT NULL,        -- Tên thứ (Monday … Sunday)
    IsWeekend       INTEGER NOT NULL,            -- 1: Cuối tuần, 0: Ngày thường
    YearMonth       VARCHAR(7) NOT NULL          -- YYYY-MM (vd: 2017-09)
);

-- ==============================================================================
-- 2. BẢNG CHIỀU VỊ TRÍ ĐỊA LÝ (Dim_Location)
-- Nguồn: customer_state, customer_city từ olist_customers_dataset.csv
-- ==============================================================================
CREATE TABLE Dim_Location (
    LocationKey     INTEGER PRIMARY KEY,         -- Surrogate Key
    CustomerState   VARCHAR(10) NOT NULL,        -- Mã bang Brazil (SP, RJ, MG, ...)
    CustomerCity    VARCHAR(100),                -- Tên thành phố (đã chuẩn hóa)
    Region          VARCHAR(50)                  -- Vùng kinh tế: Southeast, South, Northeast, North, Midwest
);

-- Index tra cứu nhanh theo bang
CREATE UNIQUE INDEX IF NOT EXISTS idx_dim_location_state_city
    ON Dim_Location(CustomerState, CustomerCity);

-- ==============================================================================
-- 3. BẢNG CHIỀU KHÁCH HÀNG (Dim_Customer)
-- Nguồn: olist_customers_dataset.csv
-- customer_unique_id là Natural Key theo dõi khách hàng đa đơn
-- ==============================================================================
CREATE TABLE Dim_Customer (
    CustomerKey         INTEGER PRIMARY KEY,         -- Surrogate Key
    CustomerUniqueID    VARCHAR(100) NOT NULL UNIQUE,-- Natural Key (customer_unique_id)
    CustomerCode        VARCHAR(50) NOT NULL,        -- Hiển thị: CUST-xxxxx (6 ký tự đầu)
    CustomerState       VARCHAR(10),                 -- Bang đăng ký
    CustomerCity        VARCHAR(100)                 -- Thành phố đăng ký
);

-- ==============================================================================
-- 4. BẢNG CHIỀU SẢN PHẨM (Dim_Product)
-- Nguồn: olist_products_dataset.csv + product_category_name_translation.csv
-- ==============================================================================
CREATE TABLE Dim_Product (
    ProductKey              INTEGER PRIMARY KEY,     -- Surrogate Key
    ProductID               VARCHAR(100) NOT NULL UNIQUE, -- Natural Key (product_id)
    CategoryNamePT          VARCHAR(100),            -- Tên danh mục tiếng Bồ Đào Nha
    CategoryNameEN          VARCHAR(100),            -- Tên danh mục tiếng Anh (đã dịch)
    NameLength              INTEGER,                 -- product_name_lenght
    DescriptionLength       INTEGER,                 -- product_description_lenght
    PhotosQty               INTEGER,                 -- Số lượng ảnh sản phẩm
    WeightG                 DECIMAL(10, 2),          -- Trọng lượng (gram)
    LengthCm               DECIMAL(10, 2),          -- Chiều dài (cm)
    HeightCm               DECIMAL(10, 2),          -- Chiều cao (cm)
    WidthCm                DECIMAL(10, 2)           -- Chiều rộng (cm)
);

-- ==============================================================================
-- 5. BẢNG CHIỀU PHƯƠNG THỨC THANH TOÁN (Dim_Payment)
-- Nguồn: olist_order_payments_dataset.csv (đã tổng hợp theo order_id)
-- ==============================================================================
CREATE TABLE Dim_Payment (
    PaymentKey          INTEGER PRIMARY KEY,         -- Surrogate Key
    PaymentType         VARCHAR(50) NOT NULL UNIQUE, -- credit_card, boleto, voucher, debit_card
    PaymentTypeVN       VARCHAR(100)                 -- Tên tiếng Việt
);

-- ==============================================================================
-- 6. BẢNG SỰ KIỆN DOANH SỐ (Fact_Sales)
-- Độ hạt (Granularity): Từng dòng order_item (1 sản phẩm trong 1 đơn hàng)
-- ==============================================================================
CREATE TABLE Fact_Sales (
    SalesKey                INTEGER PRIMARY KEY,     -- Surrogate Key dòng giao dịch
    OrderID                 VARCHAR(100) NOT NULL,   -- Degenerate Dimension: Mã đơn hàng (order_id)
    OrderItemID             INTEGER NOT NULL,        -- Thứ tự mặt hàng trong đơn (order_item_id)
    PurchaseTimestamp       TIMESTAMP NOT NULL,      -- Thời điểm đặt hàng (order_purchase_timestamp)
    PurchaseHour            INTEGER NOT NULL,        -- Khung giờ đặt hàng (0-23) - giờ vàng mua sắm
    DateKey                 INTEGER NOT NULL REFERENCES Dim_Date(DateKey),
    CustomerKey             INTEGER NOT NULL REFERENCES Dim_Customer(CustomerKey),
    ProductKey              INTEGER NOT NULL REFERENCES Dim_Product(ProductKey),
    LocationKey             INTEGER NOT NULL REFERENCES Dim_Location(LocationKey),
    PaymentKey              INTEGER          REFERENCES Dim_Payment(PaymentKey),
    -- Measures (Độ đo)
    Price                   DECIMAL(12, 2) NOT NULL, -- Giá sản phẩm (BRL) = LineRevenue
    FreightValue            DECIMAL(10, 2) NOT NULL, -- Phí vận chuyển (BRL)
    TotalRevenue            DECIMAL(12, 2) NOT NULL, -- = Price (độ hạt: 1 item)
    TotalPaymentValue       DECIMAL(12, 2),          -- Tổng thanh toán cả đơn (tổng hợp từ payments)
    PaymentInstallments     INTEGER,                 -- Số đợt trả góp
    IsDelivered             INTEGER NOT NULL DEFAULT 0 -- 1: Đã giao hàng thành công
);

-- ==============================================================================
-- 7. CHỈ MỤC HIỆU NĂNG (PERFORMANCE INDEXES)
-- ==============================================================================
CREATE INDEX IF NOT EXISTS idx_pg_fact_date        ON Fact_Sales(DateKey);
CREATE INDEX IF NOT EXISTS idx_pg_fact_customer    ON Fact_Sales(CustomerKey);
CREATE INDEX IF NOT EXISTS idx_pg_fact_product     ON Fact_Sales(ProductKey);
CREATE INDEX IF NOT EXISTS idx_pg_fact_location    ON Fact_Sales(LocationKey);
CREATE INDEX IF NOT EXISTS idx_pg_fact_payment     ON Fact_Sales(PaymentKey);
CREATE INDEX IF NOT EXISTS idx_pg_fact_orderid     ON Fact_Sales(OrderID);
CREATE INDEX IF NOT EXISTS idx_dim_date_yearmonth  ON Dim_Date(Year, Month);
CREATE INDEX IF NOT EXISTS idx_dim_product_cat     ON Dim_Product(CategoryNameEN);
CREATE INDEX IF NOT EXISTS idx_dim_cust_state      ON Dim_Customer(CustomerState);
