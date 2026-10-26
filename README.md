# ĐỒ ÁN: KHO DỮ LIỆU & PHÂN TÍCH BÁN LẺ (ONLINE RETAIL DATA LAKEHOUSE & ANALYTICS)

Dự án nghiên cứu, thiết kế và hiện thực hóa kiến trúc **Hồ Dữ Liệu & Kho Dữ Liệu Hiện Đại (Modern Data Lakehouse)** kết hợp Phân tích kinh doanh và Trực quan hóa dữ liệu (Business Intelligence).

---

## 🌟 LUỒNG CHÍNH LAKEHOUSE (SYSTEM ARCHITECTURE)

```
[ data/raw/data.csv ] -> [ MinIO raw ] -> [ EDA & Cleaning ] -> [ MinIO staging ]
                                                                    ↓
                                                                curated
                                                                    ↓
                                                  [ PostgreSQL Star Schema DWH ]
                                                       ┌────────────┴──────────┐
                                                       ▼                       ▼
                                                 [ OLAP & Mining ]       [ Dashboards ]

SQLite là phương án local/dự phòng; không nằm trong luồng triển khai chính.
```

MinIO là Lakehouse bắt buộc, nơi dữ liệu đi qua các lớp raw, staging (Parquet) và
curated (Star Schema dạng Parquet). Pipeline chỉ nạp curated sang PostgreSQL sau khi
các đối tượng đã được ghi và đọc lại từ MinIO. OLAP, RFM, Apriori và Streamlit dùng
PostgreSQL làm nguồn chính. SQLite được giữ làm phương án local/dự phòng.

---

## 📂 CẤU TRÚC THƯ MỤC DỰ ÁN (PROJECT STRUCTURE)

```
E:\ổ D\Kho\B\
│
├── docker-compose.yml          # Hạ tầng Container: MinIO + PostgreSQL + Apache Superset
├── requirements.txt            # Danh sách thư viện Python cần thiết
│
├── data/                       # Dữ liệu phục vụ hệ thống
│   ├── raw/data.csv            # Dữ liệu giao dịch thô ban đầu
│   ├── raw/ecommerce_products_raw.json # Snapshot phản hồi từ E-Commerce REST API
│   └── processed/              # Dữ liệu sạch và dữ liệu bị loại kèm lý do
│
├── database/                   # Kho dữ liệu & Tài liệu thiết kế
│   ├── retail_dwh.db           # Kho SQLite dự phòng/local
│   ├── 02_schema_ddl.sql       # Kịch bản DDL Star Schema
│   └── 02_data_modeling.md     # Tài liệu thiết kế mô hình đa chiều Kimball
│
├── scripts/                    # Toàn bộ mã nguồn Python thực thi các giai đoạn
│   ├── 01_eda_and_cleaning.py  # Giai đoạn 1: EDA & Làm sạch dữ liệu
│   ├── 03_etl_pipeline.py      # ETL SQLite dự phòng/local
│   ├── 04_run_olap_queries.py  # Giai đoạn 4: Thực thi truy vấn phân tích OLAP
│   ├── 05_data_mining.py       # Giai đoạn 5: RFM, K-Means & Market Basket
│   ├── 03b_dwh_test_reconciliation.py # Kiểm thử và đối soát kho dữ liệu (28 Test Cases)
│   ├── 06_lakehouse_minio_postgres_etl.py  # ETL chính: MinIO Lakehouse -> PostgreSQL
│   └── 07_api_enrichment.py    # Tích hợp E-Commerce REST API (DummyJSON)
│
├── sql/                        # Kịch bản SQL phân tích
│   ├── 02_schema_ddl.sql       # DDL tạo Schema
│   ├── 04_olap_queries.sql     # Các truy vấn OLAP & SQL nâng cao
│   └── 05_olap_aggregate_cubes.sql # Các khối tổng hợp vật lý cho PostgreSQL
│
├── outputs/                    # Kết quả khai phá, danh mục E-Commerce và báo cáo audit/test
│   ├── ecommerce_product_catalog.csv # 194 sản phẩm trích xuất từ E-Commerce API
│   ├── ecommerce_category_benchmarks.csv # 24 ngành hàng chuẩn hóa và điểm đánh giá
│   ├── rfm_customer_segments.csv   # Kết quả phân khúc khách hàng RFM & K-Means
│   └── market_basket_rules.csv     # 992 luật kết hợp gợi ý bán chéo (Apriori)
│
├── app.py                      # Ứng dụng Web Dashboard tương tác (Streamlit)
├── notebooks/                  # Notebook thử nghiệm và phân tích tương tác
│   └── kmeans_k_experiment.ipynb # Thử nhiều giá trị K cho phân cụm khách hàng
├── BAO_CAO_DO_AN.md            # Báo cáo tổng kết đồ án chi tiết (Word/Markdown)
├── lo_trinh.md                 # Lộ trình tổng thể và trạng thái hoàn thành từng giai đoạn
├── yeu_cau.md                  # Đề bài gốc ban đầu
├── yeu_cau_moi.md              # Yêu cầu hạ tầng Container mới (Docker, MinIO, Postgres)
└── README.md                   # Hướng dẫn tổng quan và khởi chạy hệ thống
```

---

## 🚀 THÔNG TIN DỊCH VỤ & CỔNG TRUY CẬP (SERVICES DIRECTORY)

| Dịch vụ | Địa chỉ Web / Endpoint | Tài khoản truy cập | Mô tả |
|---|---|---|---|
| **MinIO Console** | `http://localhost:9001` | `minioadmin` / `minioadmin123` | Giao diện quản lý Hồ dữ liệu S3 (Buckets: `raw`, `staging`, `curated`) |
| **MinIO API (S3)** | `http://localhost:9000` | `minioadmin` / `minioadmin123` | S3 Endpoint dùng trong code Python / DuckDB |
| **PostgreSQL DWH** | `localhost:5432` | `dataeng` / `dataeng123` (DB: `dwh`) | Cơ sở dữ liệu Kho Dữ Liệu chuẩn Star Schema |
| **Apache Superset** | `http://localhost:8088` | `admin` / `admin` | Nền tảng Business Intelligence chuyên nghiệp |
| **Streamlit Dashboard**| `http://localhost:8501` | Truy cập trực tiếp | Dashboard tương tác tùy biến với công cụ gợi ý bán chéo |

---

## 🛠️ HƯỚNG DẪN KHỞI CHẠY HỆ THỐNG

### ⚡ CÁCH 1: KHỞI CHẠY TỰ ĐỘNG BẰNG 1 CÂU LỆNH DUY NHẤT (KHUYẾN NGHỊ BÁO CÁO)

Hệ thống được trang bị script điều phối master tự động hóa 100% các bước (Bật Docker -> API -> ETL MinIO -> Star Schema DWH -> Kiểm thử 28 Test Cases -> OLAP -> Data Mining -> Mở Web Dashboard):

- **Cách 1 (Windows CMD / Nhấp đúp chuột):**
  ```bat
  run.bat
  ```
- **Cách 2 (PowerShell):**
  ```powershell
  .\run.ps1
  ```
- **Cách 3 (Python trực tiếp):**
  ```powershell
  python run_all.py
  ```

> **Các tùy chọn bổ trợ hữu ích:**
> - `python run_all.py --skip-etl`: Bỏ qua nạp ETL nếu dữ liệu DWH đã có sẵn, chỉ chạy phân tích & mở Dashboard.
> - `python run_all.py --sqlite`: Tự động chạy chế độ cục bộ SQLite (dành cho máy không cài Docker).
> - `python run_all.py --only-dashboard`: Chỉ mở nhanh Streamlit Web App.

---

### 📝 CÁCH 2: CHẠY THỦ CÔNG TỪNG BƯỚC

1. **Khởi động hạ tầng Lakehouse**:
   ```bash
   docker compose up -d
   ```
2. **Trích xuất dữ liệu từ E-Commerce REST API** (làm giàu dữ liệu sản phẩm & chuẩn hóa ngành hàng):
   ```bash
   python scripts\07_api_enrichment.py
   ```
3. **Chạy ETL chính** — pipeline đưa dữ liệu gốc lên MinIO trước, sau đó đọc bản raw từ MinIO để làm sạch, tạo staging/curated và nạp vào PostgreSQL:
   ```bash
   python scripts\06_lakehouse_minio_postgres_etl.py
   ```
4. **Kiểm thử DWH (28 Test Cases), sau đó chạy OLAP và khai phá**:
   ```bash
   python scripts\03b_dwh_test_reconciliation.py
   python scripts\04_run_olap_queries.py
   python scripts\05_data_mining.py
   ```
5. **Mở Web Dashboard tương tác (Streamlit)**:
   ```bash
   python -m streamlit run app.py
   ```

### Khối tổng hợp và 5 thao tác OLAP

ETL PostgreSQL tạo/làm mới ba materialized view theo tháng, quốc gia và sản phẩm.
Sau khi chạy ETL, `python scripts\03b_dwh_test_reconciliation.py` đối soát doanh thu
của từng khối với Fact; `python scripts\04_run_olap_queries.py` in ví dụ Slice, Dice,
Drill-down, Roll-up và Pivot. Các view này thuộc PostgreSQL, không được tạo trong
chế độ SQLite.

### Đánh giá K-Means có holdout và baseline

Script `scripts\05_data_mining.py` dùng train (80%) để chọn giữa K=2..8 của K-Means
log-RFM và baseline K-Means RFM chưa log-transform; holdout (20%) chỉ dùng để báo
Silhouette. CSV `outputs\kmeans_holdout_evaluation.csv` có các chỉ số train/test.
Hai mô hình được đánh giá trong cùng không gian log-RFM chuẩn hóa. Mô hình có điểm
Silhouette cao hơn không mặc nhiên có giá trị nghiệp vụ cao hơn; cần xem profile cụm.
Clustering không có nhãn thật nên không dùng confusion matrix.

### Thử nghiệm nhiều giá trị K bằng Jupyter Notebook

Sau khi PostgreSQL đã được nạp dữ liệu, cài thư viện từ `requirements.txt`, mở
`notebooks\kmeans_k_experiment.ipynb` trong VS Code và chạy lần lượt các cell. Notebook
đọc RFM từ PostgreSQL, thử các giá trị K có thể chỉnh ở biến `K_MIN`/`K_MAX`, so sánh
Inertia (Elbow) và Silhouette, rồi hiển thị đặc điểm từng cụm. Sau khi chạy mục 4,
notebook ghi kết quả lần chạy gần nhất vào bảng riêng
`public.kmeans_k_experiment_results`; bảng này không làm thay đổi các bảng DWH hay
đầu ra của pipeline chính.

### Vẽ kết quả thử K trên Superset

1. Khởi động Superset và PostgreSQL bằng `docker compose up -d postgres superset`.
2. Chạy notebook đến hết mục 4 để tạo/cập nhật bảng
   `public.kmeans_k_experiment_results`.
3. Đăng nhập Superset tại `http://localhost:8088`. Dùng kết nối PostgreSQL có sẵn
   nếu đã cấu hình; nếu chưa, thêm kết nối với URI
   `postgresql+psycopg2://dataeng:dataeng123@postgres:5432/dwh`
   (dùng host `postgres` vì Superset chạy trong Docker).
4. Vào **Data → Datasets → + Dataset**, chọn database PostgreSQL, schema `public`,
   bảng `kmeans_k_experiment_results`, rồi tạo dataset nếu chưa có.
5. Tạo hai biểu đồ **Line Chart** từ dataset:
   - **Elbow — Inertia theo K**: X-axis `K`, metric `Inertia_WCSS`.
   - **Silhouette theo K**: X-axis `K`, metric `Silhouette`.
6. Lưu cả hai biểu đồ. Muốn đặt cạnh nhau, tạo dashboard mới và thêm hai biểu đồ đó.

Trong Superset hiện tại của dự án, hai biểu đồ đã được lưu trong dashboard
**K-Means - Chon K** và publish tại `http://localhost:8088/superset/dashboard/1/`.
Sau mỗi lần chạy lại notebook, làm mới dashboard để xem số liệu K mới nhất.
Dashboard và charts hiện nằm trong Docker volume Superset, chưa được quản lý phiên
bản cùng mã nguồn. Trên máy mới cần tạo lại Dataset/charts/dashboard theo các bước
trên; dashboard không tự xuất hiện chỉ bằng `git clone` và `docker compose up`.

---

## 👥 HƯỚNG DẪN THÀNH VIÊN NHÓM CÀI ĐẶT VÀ CHẠY DỰ ÁN

### 1. Chuẩn bị

- Cài **Git** và **Python 3.10 trở lên**.
- Cài **Docker Desktop** và khởi động Docker để chạy MinIO và PostgreSQL (bắt buộc cho luồng chính). Superset là tùy chọn.
- Clone repository về máy:

  ```powershell
  git clone https://github.com/fhgssg/BTL_kho_va_khai_pha_H-T.git
  cd BTL_kho_va_khai_pha_H-T
  ```

### 2. Tạo môi trường Python và cài thư viện

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Nếu PowerShell không cho phép kích hoạt môi trường, mở Command Prompt và chạy:

```bat
.\.venv\Scripts\activate.bat
```

### 3. Cung cấp dữ liệu nguồn

Các file dữ liệu CSV và database được loại khỏi Git để tránh đẩy các file lớn lên repository. Thành viên cần nhận file dữ liệu nguồn `data.csv` từ người quản lý dự án và đặt vào đúng vị trí:

```text
data\raw\data.csv
```

Nếu chưa có thư mục `data\raw`, hãy tạo thư mục đó trước khi chép file.

### 4. Tạo dữ liệu sạch, nạp Lakehouse/DWH và phân tích

Chạy các lệnh từ thư mục gốc dự án, sau khi đã kích hoạt môi trường Python:

```powershell
python scripts\07_api_enrichment.py
docker compose up -d minio minio-init postgres
python scripts\06_lakehouse_minio_postgres_etl.py
python scripts\03b_dwh_test_reconciliation.py
python scripts\04_run_olap_queries.py
python scripts\05_data_mining.py
```

Script 06 đưa CSV gốc lên MinIO raw trước, tải bản raw đó để chạy EDA/làm sạch,
sau đó ghi dữ liệu sạch vào staging, tạo curated và nạp PostgreSQL. Các file CSV sạch,
bị loại và báo cáo audit vẫn được lưu cục bộ trong `data\processed` và `outputs`.
Script 01 có thể chạy độc lập để khảo sát/làm sạch thủ công, nhưng không cần chạy trước
pipeline chính. Script 07 là tùy chọn nếu cần trích xuất dữ liệu thương mại điện tử (DummyJSON E-Commerce REST API); nó lưu snapshot và
CSV để làm giàu dữ liệu (Data Enrichment) cho sản phẩm và phân tích trên Dashboard.
Chỉ chạy kiểm thử, OLAP, khai phá và dashboard sau khi pipeline Lakehouse hoàn tất.

### 5. Chạy Dashboard

```powershell
python -m streamlit run app.py
```

Mở địa chỉ được Streamlit in trong terminal, thường là `http://localhost:8501`. Để dừng Dashboard, nhấn `Ctrl+C` trong terminal đang chạy.

### 6. Hạ tầng Lakehouse

MinIO và PostgreSQL là thành phần bắt buộc của luồng chính; Superset là giao diện BI tùy chọn.

```powershell
docker compose up -d
python scripts\06_lakehouse_minio_postgres_etl.py
```

SQLite được giữ làm phương án local/dự phòng. Để dùng SQLite cho các script phân tích,
đặt `DWH_DATABASE_URL=sqlite:///database/retail_dwh.db` và nạp riêng bằng
`python scripts\03_etl_pipeline.py`. Luồng SQLite bỏ qua Lakehouse nên không thay thế ETL chính.

Để dừng các dịch vụ mà giữ dữ liệu trong Docker volumes:

```powershell
docker compose stop
```

Docker volumes nằm trên máy của từng thành viên và không được chia sẻ qua Git. Không chạy `docker compose down -v` nếu chưa sao lưu hoặc chưa chủ động muốn xóa dữ liệu volumes.
