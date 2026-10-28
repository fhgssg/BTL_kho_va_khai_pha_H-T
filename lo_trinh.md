# LỘ TRÌNH THỰC HIỆN ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ROADMAP)

---

## TỔNG QUAN KẾ HOẠCH
- **Mục tiêu**: Hoàn thành toàn diện đồ án từ dữ liệu thô `data.csv` đến Kho dữ liệu hoàn chỉnh, phân tích nâng cao và Dashboard trực quan.
- **Thời lượng khuyến nghị**: 2 - 4 tuần (hoặc rút gọn trong 5 - 7 ngày tùy tiến độ bài tập).
- **Công nghệ sử dụng**:
  - Ngôn ngữ: `Python 3.11` (Pandas, Numpy, Scikit-learn, Mlxtend, SqlAlchemy).
  - Lakehouse chính: `MinIO` (S3) với các lớp raw/staging/curated, dữ liệu Parquet được xử lý bằng `DuckDB`.
  - Kho phục vụ phân tích: `PostgreSQL`; `SQLite` giữ làm phương án local/dự phòng.
  - Trực quan hóa: `Streamlit` (Dashboard web tương tác trực tiếp bằng Python) hoặc `Power BI`.

---

## CHI TIẾT CÁC GIAI ĐOẠN THỰC HIỆN

```
  [Giai đoạn 1]                [Giai đoạn 2]                [Giai đoạn 3]
 Khám phá & Làm sạch  ───► Thiết kế Mô hình Kho ───► Xây dựng ETL Pipeline
     (EDA & Clean)             (Star Schema)             (Extract-Transform-Load)
           │                                                        │
           ▼                                                        ▼
  [Giai đoạn 6]                [Giai đoạn 5]                [Giai đoạn 4]
 Báo cáo & Dashboard  ◄─── Khai phá Dữ liệu     ◄─── Truy vấn OLAP / SQL
(Streamlit / PowerBI)        (RFM & Apriori)          (Advanced Analytics)
```

---

### GIAI ĐOẠN 1: KHÁM PHÁ (EDA) & TIỀN XỬ LÝ DỮ LIỆU
**Mục tiêu**: Hiểu rõ cấu trúc dữ liệu, thống kê các dị biệt và xây dựng bộ lọc chuẩn hóa.

- [x] **Bước 1.1**: Đọc và kiểm tra cấu trúc `data.csv` (số dòng, số cột, kiểu dữ liệu, dung lượng bộ nhớ).
- [x] **Bước 1.2**: Thống kê dữ liệu khuyết thiếu:
  - Cột `CustomerID`: Xử lý các dòng không có mã khách hàng (tách nhóm khách hàng vãng lai).
  - Cột `Description`: Xử lý giá trị null và các giá trị vô nghĩa (ví dụ: "POSTAGE", "Manual", "AMAZON FEE").
- [x] **Bước 1.3**: Xử lý dữ liệu bất thường:
  - Lọc đơn hàng hủy: Các mã `InvoiceNo` có tiền tố `'C'`.
  - Xử lý các dòng có `Quantity <= 0` hoặc `UnitPrice <= 0`.
- [x] **Bước 1.4**: Xuất tập dữ liệu sạch ban đầu (`data_cleaned.csv` hoặc lưu vào staging).

*Thời gian dự kiến*: 1 - 2 ngày | *Đầu ra*: Jupyter Notebook hoặc script `01_eda_and_cleaning.py`.

---

### GIAI ĐOẠN 2: THIẾT KẾ MÔ HÌNH DỮ LIỆU ĐA CHIỀU (DATA MODELING)
**Mục tiêu**: Xác định các chiều phân tích và thiết kế mô hình hình sao (Star Schema).

- [x] **Bước 2.1**: Xác định các nghiệp vụ kinh doanh (Business Processes): Bán hàng (Sales / Orders).
- [x] **Bước 2.2**: Xác định độ hạt của Fact (Granularity): Từng dòng mặt hàng trong mỗi đơn hàng (Line item).
- [x] **Bước 2.3**: Thiết kế các bảng Dimension:
  - `Dim_Customer`: `CustomerKey`, `CustomerID`, `CustomerCode`, `IsGuestCustomer`, `Country`.
  - `Dim_Product`: `ProductKey`, `StockCode`, `Description`, `UnitPrice_Standard`.
  - `Dim_Date`: `DateKey`, `FullDate`, `Year`, `Quarter`, `Month`, `Day`, `DayOfWeek`, `IsWeekend`, `YearMonth`.
  - `Dim_Location`: `LocationKey`, `Country`, `RegionType`.
- [x] **Bước 2.4**: Thiết kế bảng Fact:
  - `Fact_Sales`: `SalesKey`, `InvoiceNo`, `InvoiceTimestamp`, `Hour`, `DateKey`, `CustomerKey`, `ProductKey`, `LocationKey`, `Quantity`, `UnitPrice`, `TotalRevenue`.
- [x] **Bước 2.5**: Vẽ sơ đồ kiến trúc dữ liệu ERD (Mermaid diagram, Data Dictionary chi tiết).

*Thời gian dự kiến*: 1 - 2 ngày | *Đầu ra*: Bản vẽ ERD & kịch bản tạo bảng `02_schema_ddl.sql`, tài liệu `02_data_modeling.md`.

---

### GIAI ĐOẠN 3: LAKEHOUSE VÀ ĐƯỜNG ỐNG ETL
**Mục tiêu**: Đưa CSV gốc vào MinIO raw trước, làm sạch từ bản raw đó, ghi staging → curated rồi nạp Star Schema curated vào PostgreSQL trước mọi phân tích tiếp theo.

- [x] **Bước 3.1**: Đưa CSV nguồn lên bucket `raw` của MinIO trước khi làm sạch.
- [x] **Bước 3.2**: Đọc CSV từ MinIO raw, chạy EDA/làm sạch; lưu dữ liệu sạch thành Parquet vào bucket `staging`.
- [x] **Bước 3.3**: Dùng DuckDB đọc lại staging, tạo Parquet Star Schema và lưu vào `curated`.
- [x] **Bước 3.4**: Nạp các bảng curated đọc lại từ MinIO vào PostgreSQL theo transaction, sau đó đối soát số dòng và doanh thu.
- [x] **Phương án dự phòng**: Giữ `03_etl_pipeline.py` để nạp riêng vào SQLite khi chạy local; không dùng thay cho luồng Lakehouse chính.

*Thời gian dự kiến*: 2 - 3 ngày | *Đầu ra*: `scripts/06_lakehouse_minio_postgres_etl.py`, các lớp Parquet trên MinIO và PostgreSQL DWH.

---

### GIAI ĐOẠN 4: TRUY VẤN PHÂN TÍCH ĐA CHIỀU (OLAP & ADVANCED SQL)
**Mục tiêu**: Sau khi Lakehouse ETL hoàn tất, truy vấn PostgreSQL DWH để giải quyết các câu hỏi kinh doanh cốt lõi.

- [x] **Bước 4.1**: Viết câu truy vấn tổng hợp theo các chiều:
  - Báo cáo doanh thu theo Tháng/Quý/Năm (Thời gian).
  - Báo cáo doanh thu và tỷ trọng theo Quốc gia (Địa lý).
  - Báo cáo Top 10 sản phẩm bán chạy nhất & 10 sản phẩm sinh lời cao nhất.
- [x] **Bước 4.2**: Áp dụng các kỹ thuật OLAP nâng cao:
  - Dùng CTE + UNION ALL mô phỏng `ROLLUP` đa cấp (Năm -> Quý -> Tháng).
  - Sử dụng Window Functions (`RANK()`, `DENSE_RANK()`, `SUM() OVER(PARTITION BY ...)`, `LAG()` tính tốc độ tăng trưởng MoM và YTD Running Total).
  - Tính toán các chỉ số kinh doanh: Tỷ lệ quay lại của khách hàng (65.58%), AOV (£533.17), khung giờ vàng mua sắm (Peak Hours).

*Thời gian dự kiến*: 1 - 2 ngày | *Đầu ra*: Tệp SQL `04_olap_queries.sql` & Script kiểm thử `04_run_olap_queries.py`.

---

### GIAI ĐOẠN 5: KHAI PHÁ DỮ LIỆU CHUYÊN SÂU (DATA MINING)
**Mục tiêu**: Ứng dụng mô hình hóa định lượng để phân nhóm khách hàng và tìm luật mua hàng.

- [x] **Bước 5.1 - Phân khúc khách hàng RFM (Recency, Frequency, Monetary)**:
  - Tính toán chỉ số R, F, M cho 4,338 khách hàng định danh từ `Fact_Sales`.
  - Chia điểm ngũ vị phân (Quantiles 1-5) và phân nhóm 8 phân khúc nghiệp vụ (Champions, Loyal, At Risk, Hibernating, v.v.).
  - Tách holdout khách hàng 80/20; so sánh K-Means log-RFM k=2..8 với baseline K-Means RFM thô. Lần chạy hiện tại chọn baseline k=2 (holdout Silhouette 0.6010 trong không gian log-RFM chung); xem `outputs/kmeans_holdout_evaluation.csv`. Độ đồng thuận được kiểm tra qua 5 seeds.
- [x] **Bước 5.2 - Phân tích Giỏ hàng (Market Basket Analysis)**:
  - Chuyển đổi 18,275 đơn hàng đa sản phẩm thành ma trận nhị phân (One-hot Transaction Matrix 18,275 x 3,775).
  - Chạy thuật toán **Apriori** (`min_support = 0.015`) tìm 912 tập mục phổ biến.
  - Trích xuất 992 luật kết hợp (Association Rules) với `Lift >= 1.2` và `Confidence lên đến 91.15%`.
  - Rút ra đề xuất chiến lược bán chéo các bộ sản phẩm quà tặng / đồ uống / trang trí.

*Thời gian dự kiến*: 2 - 3 ngày | *Đầu ra*: Script `scripts/05_data_mining.py`, `outputs/rfm_customer_segments.csv`, `outputs/market_basket_rules.csv`.

---

### GIAI ĐOẠN 6: TRỰC QUAN HÓA DASHBOARD & ĐÓNG GÓI BÁO CÁO
**Mục tiêu**: Đóng gói kết quả thành sản phẩm hoàn chỉnh để trình bày và bảo vệ đồ án.

- [x] **Bước 6.1**: Xây dựng Dashboard tương tác:
  - Sử dụng **Streamlit** kết hợp Plotly (`app.py`), lấy dữ liệu từ PostgreSQL DWH và các tệp kết quả khai phá `outputs/`.
- [x] **Bước 6.2**: Thiết kế các trang hiển thị chính:
  - Tab 1: Tổng quan kinh doanh & Chỉ số tài chính (KPIs, xu hướng MoM, khung giờ vàng).
  - Tab 2: Phân tích địa lý & Top sản phẩm sinh lời.
  - Tab 3: Khám phá phân khúc khách hàng RFM & gom cụm K-Means.
  - Tab 4: Công cụ gợi ý sản phẩm bán kèm tương tác (Cross-sell Recommender).
  - Tab 5: Kiến trúc Kho dữ liệu Star Schema & DDL.
  - Tab 6: Phân tích sản phẩm sau khi gộp Online Retail và DummyJSON.
- [x] **Bước 6.3**: Viết báo cáo tổng kết đồ án chi tiết (`BAO_CAO_DO_AN.md`).

*Thời gian dự kiến*: 2 - 3 ngày | *Đầu ra*: Ứng dụng Dashboard `app.py` & Báo cáo đồ án `BAO_CAO_DO_AN.md`.

---

## BẢNG TỔNG HỢP TIẾN ĐỘ & BÀN GIAO (MILESTONES)

| Giai đoạn | Nội dung chính | File bàn giao | Trạng thái |
|---|---|---|:---:|
| **Giai đoạn 1** | EDA & Tiền xử lý dữ liệu | `scripts/01_eda_and_cleaning.py` | ✅ Hoàn thành |
| **Giai đoạn 2** | Thiết kế Star Schema & DDL | `database/02_schema_ddl.sql`, `02_data_modeling.md` | ✅ Hoàn thành |
| **Giai đoạn 3** | Lakehouse ETL: MinIO → PostgreSQL | `scripts/06_lakehouse_minio_postgres_etl.py`, `raw/staging/curated`, PostgreSQL DWH | ✅ Hoàn thành |
| **Giai đoạn 4** | Truy vấn OLAP & Phân tích SQL | `sql/04_olap_queries.sql`, `scripts/04_run_olap_queries.py` | ✅ Hoàn thành |
| **Giai đoạn 5** | RFM Segmentation & Market Basket | `scripts/05_data_mining.py`, `outputs/` | ✅ Hoàn thành |
| **Giai đoạn 6** | Dashboard Web & Báo cáo hoàn chỉnh | `app.py` (6 tabs), `BAO_CAO_DO_AN.md` | ✅ Hoàn thành (100%) |
| **Tích hợp dữ liệu API bổ trợ** | **DummyJSON Products Catalog** | `scripts/07_api_enrichment.py`, MinIO raw/staging, hợp nhất vào `Dim_Product`, OLAP danh mục và tab phân tích hợp nhất trong `app.py` | ✅ **Gộp vào chiều sản phẩm, rồi phân tích; không tạo hóa đơn giả cho catalog** |
