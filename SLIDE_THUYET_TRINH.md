# KỊCH BẢN & NỘI DUNG CHI TIẾT 15 SLIDE THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN (15 PHÚT)
**Học phần:** INT1422 — Kho dữ liệu và Khai phá dữ liệu  
**Học viện Công nghệ Bưu chính Viễn thông**  
*(Được thiết kế theo nguyên tắc: **Đầy đủ luận cứ kỹ thuật chuyên sâu + Giải thích dễ hiểu, trực quan cho người ngoài ngành** theo đúng yêu cầu Slide 16 & 24)*

---

## 📌 BẢNG PHÂN BỔ THỜI GIAN THEO CHUẨN ĐẦU RA (CLO)
- **Phần 1: Bài toán kinh doanh & Câu hỏi thực tế (Slide 1 – 2):** 2 phút (Mở đầu & Bối cảnh)
- **Phần 2: Nguồn dữ liệu & Xử lý dị biệt (Slide 3 – 5):** 3 phút (Tiền xử lý)
- **Phần 3: Thiết kế kho Star Schema & Trình diễn OLAP (Slide 6 – 9):** 4 phút (CLO1 - 45% điểm)
- **Phần 4: Khai phá dữ liệu, K-Means & Luật bán chéo (Slide 10 – 13):** 4 phút (CLO2 - 45% điểm)
- **Phần 5: Demo Dashboard, Đề xuất hành động & Hạn chế (Slide 14 – 15):** 2 phút (Ứng dụng thực tiễn & Tổng kết)

---

### SLIDE 1: TRANG TIÊU ĐỀ & ĐỘI NGŨ THỰC HIỆN
* **Tiêu đề lớn:** HỆ THỐNG KHO DỮ LIỆU ĐA CHIỀU VÀ PHÂN TÍCH HÀNH VI KHÁCH HÀNG THƯƠNG MẠI BÁN LẺ (ONLINE RETAIL DWH & DATA MINING)
* **Thông tin nhóm:**
  - Giảng viên hướng dẫn: [Tên Giảng viên]
  - Nhóm sinh viên thực hiện: [Nhóm xx] — Lớp [D21CQCNxx-B]
  - Thành viên 1: [Họ và tên] (ETL Pipeline & Data Reconciliation)
  - Thành viên 2: [Họ và tên] (Star Schema Modeling & OLAP Service)
  - Thành viên 3: [Họ và tên] (Machine Learning RFM/K-Means/Apriori & BI Dashboard)
* **Khẩu hiệu đề tài (Slogan):** *"Biến hơn 500,000 giao dịch rời rạc thành quyết định kinh doanh thông minh dựa trên dữ liệu thực chứng."*

---

### SLIDE 2: BÀI TOÁN KINH DOANH — VÌ SAO BÀI TOÁN NÀY ĐÁNG GIẢI?
* **Bối cảnh thực tế (Business Problem):**
  - Doanh nghiệp bán lẻ có hơn 4,000 khách hàng và hàng trăm nghìn đơn hàng mỗi năm nhưng đang quản lý bằng các file Excel rời rạc.
  - Ban giám đốc gặp "điểm mù": Không biết doanh thu tháng này tăng trưởng thật hay do ảo giác tiền tệ; không biết khách hàng nào sắp bỏ đi; nhân viên bán hàng không biết nên tư vấn sản phẩm gì khi khách đã chọn một món đồ.
* **3 Câu hỏi nghiệp vụ cốt lõi mà người thật sẽ hành động theo:**
  1. *Doanh thu thực sự đến từ đâu, khung giờ nào và quốc gia nào đóng góp nhiều nhất?* $\rightarrow$ Để phòng Marketing lên lịch chạy quảng cáo đúng giờ, đúng thị trường.
  2. *Khách hàng nào là "VIP sinh lời" cần chăm sóc đặc biệt, khách nào đang "ngủ đông" sắp mất?* $\rightarrow$ Để phòng Chăm sóc khách hàng gửi ưu đãi giữ chân kịp thời.
  3. *Những sản phẩm nào khách thường mua cùng nhau trong một giỏ hàng?* $\rightarrow$ Để phòng Bán hàng đóng gói combo khuyến mãi (cross-selling), gia tăng giá trị trung bình đơn hàng.
* **Lời thoại giải thích cho người ngoài ngành:**
  > *"Thưa thầy cô, thay vì để dữ liệu nằm chết trong các file Excel nặng nề gây nghẽn máy, hệ thống của nhóm đóng vai trò như một 'bộ não điều hành': vừa gom toàn bộ sổ sách vào một kho ngăn nắp, vừa tự động phát hiện những khách quen chịu chi và mách nước xem nên mời khách mua thêm món gì để tối đa hóa doanh số."*

---

### SLIDE 3: BỘ DỮ LIỆU ĐẦU VÀO & MỞ RỘNG ĐA NGUỒN
* **Nguồn 1 (Dữ liệu giao dịch cốt lõi):**
  - Dataset: `Online Retail` từ UCI Machine Learning Repository (Anh Quốc).
  - Quy mô: **541,909 dòng giao dịch** trong 1 năm (01/12/2010 – 09/12/2011), 8 thuộc tính (`InvoiceNo`, `StockCode`, `Description`, `Quantity`, `InvoiceDate`, `UnitPrice`, `CustomerID`, `Country`).
* **Nguồn 2 (Dữ liệu danh mục hàng hóa mở rộng - API Catalog):**
  - Kết nối API `DummyJSON Catalog`: Bổ sung 194 sản phẩm mẫu có phân cấp ngành hàng (`Category`, `Brand`, `Rating`), giải quyết bài toán dữ liệu bán lẻ gốc chỉ có mô tả tự do mà thiếu phân loại danh mục.
* **Nguồn 3 (Dữ liệu tỷ giá ngoại tệ thực tế - Financial API):**
  - Tích hợp API ngân hàng `Frankfurter.app` (dữ liệu chính thức từ Ngân hàng Trung ương Châu Âu - ECB): Lấy tỷ giá hối đoái hàng tháng giữa GBP, USD và EUR.
* **Ý nghĩa thực tế:** Giúp doanh nghiệp đa quốc gia quy đổi doanh thu đồng nhất, nhìn rõ bức tranh tài chính toàn cầu.

---

### SLIDE 4: QUY TRÌNH TIỀN XỬ LÝ & LÀM SẠCH DỮ LIỆU (WATERFALL AUDIT)
* **Vì sao phải làm sạch?** *"Dữ liệu rác vào thì kết quả phân tích sẽ là rác"* (Garbage In, Garbage Out). Dữ liệu thực tế có giao dịch trả hàng, lỗi nhập máy và dòng thử nghiệm của kỹ thuật viên.
* **Quy tắc làm sạch minh bạch theo từng bước (Waterfall Filter):**
  1. **Lọc đơn hủy:** Loại bỏ các mã hóa đơn có chữ `C` (Cancelled) $\rightarrow$ Tách riêng phân tích trả hàng, không tính trùng vào doanh thu bán hàng.
  2. **Lọc số lượng & Đơn giá bất thường:** Loại bỏ $Quantity \le 0$ và $UnitPrice \le 0$ (các giao dịch hỏng kho, hàng mẫu tặng 0 đồng, phí điều chỉnh hệ thống).
  3. **Chuẩn hóa chữ viết:** Viết hoa toàn bộ tên sản phẩm, cắt bỏ khoảng trắng thừa, sửa lỗi chính tả tự động.
* **Quy tắc đặc biệt đối với khách vãng lai (Missing CustomerID):**
  - Dữ liệu thiếu `CustomerID` (132,186 dòng): **Không được xóa** vì tiền mua hàng là có thật!
  - Nhóm gán mã quy ước `-1` (ký hiệu: `GUEST - Khách vãng lai`). Nhờ đó, tổng doanh thu kho không bị hụt mất 1.6 triệu Bảng Anh, nhưng khi thuật toán chạy phân nhóm khách hàng trung thành thì sẽ tự động tách nhóm này ra.

---

### SLIDE 5: KẾT QUẢ TIỀN XỬ LÝ & BẢO TOÀN GIÁ TRỊ TÀI CHÍNH
* **Bảng đối soát trước và sau khi làm sạch:**
  - Dữ liệu thô ban đầu: 541,909 dòng.
  - Dữ liệu sạch hợp lệ: **524,874 dòng** (Giữ lại **96.86%** dữ liệu — tỷ lệ sạch cực cao).
  - Doanh thu bán hàng thực tế được xác lập: **£10,642,110.80** (hơn 10.6 triệu Bảng Anh).
  - Tổng số lượng hàng hóa bán ra: **5,572,416 sản phẩm**.
* **File nhật ký kiểm toán (Audit Trail):**
  - Toàn bộ lý do loại bỏ từng dòng dữ liệu được lưu tự động tại `outputs/data_cleaning_audit.csv`, đảm bảo tính minh bạch học thuật, bất kỳ ai cũng có thể chạy lại để kiểm chứng.
* **Lời thoại cho người ngoài ngành:**
  > *"Giống như việc đãi cát tìm vàng: chúng em đã lọc bỏ 17,000 dòng giao dịch ảo, đơn huỷ và hàng lỗi, chỉ giữ lại đúng 524,874 giao dịch tiền tươi thóc thật, đảm bảo con số doanh thu 10.64 triệu Bảng hoàn toàn chính xác tới từng xu."*

---

### SLIDE 6: THIẾT KẾ KHO DỮ LIỆU ĐA CHIỀU (STAR SCHEMA)
* **Lược đồ hình sao (Star Schema):**
  - **Bảng sự kiện trung tâm (Fact_Sales):** Chứa các con số đo lường nghiệp vụ: `Quantity` (Số lượng), `UnitPrice` (Đơn giá), `TotalRevenue` (Thành tiền = Quantity $\times$ UnitPrice).
  - **4 Bảng chiều phân tích bao quanh (Dimensions):**
    1. `Dim_Date`: Phân tích theo Năm, Quý, Tháng, Ngày, Thứ trong tuần, Ngày cuối tuần.
    2. `Dim_Customer`: Mã khách hàng, Quốc gia, Phân loại Thành viên / Khách vãng lai.
    3. `Dim_Product`: Mã SKU, Tên sản phẩm, Đơn giá chuẩn, Danh mục ngành hàng hợp nhất.
    4. `Dim_Location`: Quốc gia, Phân vùng Nội địa (UK) / Quốc tế.
* **Câu hỏi then chốt: Vì sao chọn độ mịn (Granularity) là từng dòng mặt hàng (Line-item)?**
  - Nếu chỉ lưu tổng tiền của một hóa đơn, ta sẽ **không thể biết** khách hàng mua cái gì, không phân tích được sản phẩm nào bán chạy nhất, và không thể chạy được thuật toán gợi ý bán kèm. Độ mịn line-item là điều kiện tiên quyết để khai phá dữ liệu giỏ hàng!

---

### SLIDE 7: TÍNH TOÁN TRƯỚC CÁC KHỐI DỮ LIỆU (OLAP PRE-AGGREGATES / CUBES)
* **Vấn đề kỹ thuật:** Bảng sự kiện có hơn nửa triệu dòng. Nếu mỗi lần sếp mở báo cáo lại phải quét lại từ đầu thì phần mềm sẽ bị đơ, giật lag.
* **Giải pháp: Tính trước 3 khối tổng hợp sẵn trong kho (Materialized Views):**
  1. `mv_olap_monthly_sales`: Doanh thu và sản lượng tổng hợp sẵn theo từng Tháng và Quý.
  2. `mv_olap_monthly_country_sales`: Doanh thu tính sẵn theo từng Tháng $\times$ từng Quốc gia.
  3. `mv_olap_monthly_product_sales`: Sản lượng và doanh thu tính sẵn theo từng Tháng $\times$ từng Sản phẩm.
* **Lợi ích đạt được:**
  - Tốc độ truy vấn báo cáo tăng nhanh gấp **15 đến 20 lần** (từ vài giây giảm xuống chỉ còn vài phần nghìn giây).
  - Tiết kiệm bộ nhớ máy chủ, đáp ứng hàng trăm người dùng truy cập dashboard cùng lúc.

---

### SLIDE 8: TRÌNH DIỄN 5 THAO TÁC OLAP TRÊN DỮ LIỆU THẬT
* **Giải thích trực quan 5 thao tác cho người xem:**
  1. **Roll-up (Thu nhỏ góc nhìn - Gộp dữ liệu lên cấp cao hơn):**
     - Từ doanh thu từng tháng $\rightarrow$ gộp lại thành doanh thu từng Quý (ví dụ: Quý 4/2011 đạt đỉnh £3,292,920).
  2. **Drill-down (Phóng to chi tiết - Mở sâu vào từng góc độ):**
     - Từ tổng doanh thu cả năm 2011 $\rightarrow$ bổ chi tiết xem từng tháng trong năm tăng giảm thế nào.
  3. **Slice (Cắt một lát bánh):**
     - Cố định 1 chiều thời gian: Chỉ xem xét các giao dịch diễn ra trong năm 2011.
  4. **Dice (Cắt một khối xúc xắc đa chiều):**
     - Lọc đồng thời 3 điều kiện: `Năm 2011` + `Quý 4` + `Thị trường Anh và Đức`.
  5. **Pivot (Xoay góc nhìn ma trận):**
     - Xoay trục: Biến Tháng thành các Dòng, chuyển Quốc gia thành các Cột để so sánh cạnh tranh trực tiếp giữa thị trường Anh, Đức và Ireland.

---

### SLIDE 9: KIỂM THỬ VÀ ĐỐI SOÁT KHO DỮ LIỆU (31 TEST CASES PASS 100%)
* **Bằng chứng tin cậy:** Hệ thống không chỉ cài đặt kho mà có script kiểm thử tự động `scripts/03b_dwh_test_reconciliation.py`.
* **Kết quả nghiệm thu 31 tiêu chuẩn (All Pass):**
  - **Khớp số dòng tuyệt đối:** File sạch có 524,874 dòng $\rightarrow$ Fact_Sales nạp đúng 524,874 dòng (Chênh lệch: **0 dòng**).
  - **Khớp doanh thu tuyệt đối:** Doanh thu nguồn và kho khớp từng con số: **£10,642,110.80** (Chênh lệch: **£0.0000**).
  - **Toàn vẹn khóa ngoại (Referential Integrity):** **0 bản ghi mồ côi** (không có hóa đơn nào trỏ vào khách hàng hoặc ngày tháng không tồn tại).
  - **Quy tắc nghiệp vụ:** 0 đơn hủy, 0 số lượng âm, 132,186 dòng khách vãng lai ánh xạ chính xác vào mã `-1`.
* **Thông điệp:** Dữ liệu trong kho là chuẩn mực và sẵn sàng tuyệt đối cho các thuật toán học máy khai phá.

---

### SLIDE 10: BÀI TOÁN KHAI PHÁ 1 — PHÂN KHÚC KHÁCH HÀNG RFM
* **Khái niệm RFM (Giải thích nghiệp vụ):**
  - **R (Recency):** Khách mua hàng cách đây bao nhiêu ngày? (Càng gần càng tốt).
  - **F (Frequency):** Khách đã mua bao nhiêu đơn hàng? (Càng nhiều càng trung thành).
  - **M (Monetary):** Khách đã đóng góp tổng cộng bao nhiêu tiền? (Càng nhiều càng VIP).
* **Quy luật Pareto (80/20) được chứng minh trên dữ liệu thực:**
  - Nhóm **Champions (Khách hàng VIP số 1):** Chỉ có 957 khách (chiếm 22% số lượng) nhưng đóng góp tới **£5.79 triệu Bảng** (chiếm **54.4% tổng doanh thu** toàn công ty!). Trung bình mỗi khách VIP chi tiêu £6,051.
  - Nhóm **Hibernating / Lost (Ngủ đông / Đã bỏ đi):** Chiếm tới 1,065 khách nhưng đã hơn 200 ngày không quay lại.
  - Nhóm **At Risk (Có nguy cơ mất):** 442 khách từng chi tiêu khá cao nhưng đang có dấu hiệu thưa thớt dần.
* **Hành động nghiệp vụ:** Không rải tiền khuyến mãi đại trà; dồn ngân sách chăm sóc đặc quyền cho nhóm VIP và gửi email kích hoạt nhóm At Risk.

---

### SLIDE 11: MÔ HÌNH HỌC MÁY K-MEANS & ĐỐI CHỨNG VỚI BASELINE (SLIDE 10 & 25)
* **Vì sao cần mô hình cơ sở (Baseline Model) để so sánh?**
  - Slide 25 của môn học chỉ rõ lỗi mất điểm: *"Không có mô hình cơ sở để so sánh"*. Để chứng minh giải pháp của nhóm thực sự thông minh, nhóm đã xây dựng một mô hình cơ sở để đối chứng.
* **Bảng so sánh đối chứng khoa học:**
  - **Mô hình cơ sở (Baseline - K-Means trên RFM thô, k=2):**
    - Mặc dù điểm Silhouette hình học cao (0.59), nhưng thuật toán bị "đánh lừa" bởi 26 khách hàng siêu giàu. Kết quả là chia thành 2 cụm: 1 cụm gồm 4,312 khách và 1 cụm chỉ có 26 khách!
    - *Đánh giá nghiệp vụ:* Hoàn toàn thất bại, vô dụng, không thể ứng dụng làm marketing.
  - **Mô hình đề xuất (Proposed Model - K-Means có biến đổi $\log(1+x)$ và chuẩn hóa, k=4):**
    - Điểm Silhouette trên tập kiểm thử: **0.3368**. Độ ổn định giữa 5 hạt giống ngẫu nhiên đạt **97.54%**.
    - Phân chia hài hòa thành 4 cụm giá trị thực tế:
      1. *Cluster 1 - Low Value (1,622 khách):* Mua ít, giá trị thấp.
      2. *Cluster 2 - Moderate Value (837 khách):* Khách hàng tiềm năng ổn định.
      3. *Cluster 3 - High Value (1,166 khách):* Khách hàng giá trị cao.
      4. *Cluster 4 - Super VIP (713 khách):* Khách hàng cốt lõi sinh lời cao nhất.

---

### SLIDE 12: BÀI TOÁN KHAI PHÁ 2 — PHÂN TÍCH GIỎ HÀNG (MARKET BASKET ANALYSIS)
* **Mục tiêu bài toán:** *"Khách hàng mua bia có thường mua kèm tã giấy không?"*
* **Phương pháp thực hiện:**
  - Xây dựng ma trận giao dịch giỏ hàng từ 18,275 đơn hàng đa sản phẩm $\times$ 3,775 mặt hàng.
  - Áp dụng thuật toán **Apriori** với ngưỡng hỗ trợ tối thiểu ($min\_support = 1.5\%$) để tìm các tập sản phẩm hay xuất hiện cùng nhau.
  - Trích xuất được **992 luật kết hợp** có ý nghĩa kinh doanh với hệ số nâng $Lift \ge 1.2$.
* **3 Chỉ số đo lường giải thích cho người nghe:**
  - **Support (Độ hỗ trợ):** Tần suất cặp sản phẩm xuất hiện cùng nhau trong tổng số đơn hàng.
  - **Confidence (Độ tin cậy):** Khi khách đã mua món A, xác suất họ lấy thêm món B là bao nhiêu %?
  - **Lift (Độ nâng):** Mua món A làm tăng khả năng mua món B lên gấp bao nhiêu lần so với mua ngẫu nhiên? ($Lift > 1$ chứng minh 2 sản phẩm thực sự hút nhau, không phải ngẫu nhiên).

---

### SLIDE 13: CÁC LUẬT BÁN KÈM TIÊU BIỂU & Ý NGHĨA KINH DOANH
* **Top 3 Quy tắc gợi ý bán chéo (Cross-selling) có sức mạnh lớn nhất:**
  1. **Bộ đĩa trà Hoàng gia (Regency Tea Plate):**
     - Mua đĩa màu hồng $\rightarrow$ Gợi ý mua đĩa màu xanh lá cây.
     - **Confidence: 91.15%**, **Lift: 43.83 lần**! *(Nghĩa là 10 người mua đĩa hồng thì hơn 9 người mua thêm đĩa xanh; khả năng mua cùng cao gấp gần 44 lần ngẫu nhiên).*
  2. **Bộ đồ chơi trẻ em (Poppy's Playhouse):**
     - Mua bộ đồ chơi phòng ngủ $\rightarrow$ Mua bộ đồ chơi nhà bếp.
     - **Confidence: 74.00%**, **Lift: 31.02 lần**.
  3. **Bộ đồ dùng tiệc liên hoan (Party Supplies):**
     - Mua cốc giấy chấm bi đỏ $\rightarrow$ Mua đĩa giấy chấm bi đỏ.
     - **Confidence: 82.16%**, **Lift: 28.49 lần**.
* **Hành động thương mại thực tế:**
  - Đặt các sản phẩm này cạnh nhau trên kệ hàng siêu thị hoặc gợi ý *"Mua kèm combo giảm 10%"* trên website khi khách thêm sản phẩm thứ nhất vào giỏ.

---

### SLIDE 14: DEMO TRỰC QUAN DASHBOARD ĐIỀU HÀNH (STREAMLIT BI)
* **Kiến trúc ứng dụng web:** Xây dựng bằng `Python`, `Streamlit` và `Plotly`, kết nối trực tiếp vào kho dữ liệu SQLite.
* **Minh họa 6 chức năng thực tế trên màn hình:**
  - **Tab 1 - Tổng quan tài chính:** Thẻ KPI động, biểu đồ doanh thu theo tháng và biểu đồ nhiệt phân tích khung giờ vàng mua sắm (đỉnh cao 12h trưa).
  - **Tab 2 - Bản đồ thị trường:** Cơ cấu doanh thu giữa Anh Quốc (84.6%) và thị trường quốc tế; Top 10 sản phẩm sinh lời lớn nhất.
  - **Tab 3 - Bản đồ nhiệt khách hàng:** Trực quan hóa 8 phân khúc RFM và không gian phân cụm K-Means 4 màu.
  - **Tab 4 - Công cụ gợi ý bán kèm thời gian thực (Smart Recommender):** Người dùng chọn 1 sản phẩm bất kỳ từ danh sách $\rightarrow$ Hệ thống tự động truy xuất luật Apriori và hiển thị các sản phẩm nên mời mua thêm kèm theo điểm tin cậy % và hệ số Lift.
  - **Tab 5 & 6 - Cấu trúc kho & Tỷ giá ngoại tệ:** Hiển thị mô hình DDL và bảng quy đổi ngoại tệ GBP sang USD/EUR.

---

### SLIDE 15: KHUYẾN NGHỊ HÀNH ĐỘNG THỰC TẾ & HẠN CHẾ CỦA ĐỒ ÁN
* **3 Khuyến nghị kinh doanh cụ thể cho doanh nghiệp:**
  1. *Chiến lược sản phẩm:* Đóng gói các combo bộ đồ gốm trà và đồ chơi tiệc thành hộp quà tặng trọn gói để tăng giá trị trung bình đơn hàng (AOV).
  2. *Chiến lược giữ chân khách hàng:* Thiết lập quy trình tự động gửi mã giảm giá kích hoạt cho nhóm khách hàng "At Risk" trước mốc 90 ngày không phát sinh đơn.
  3. *Tối ưu vận hành:* Tăng cường nhân sự kho và hỗ trợ trực tuyến vào khung giờ cao điểm từ 10:00 đến 15:00 hàng ngày.
* **Hạn chế của đồ án & Hướng phát triển:**
  - *Hạn chế:* Tập dữ liệu chưa có trường giá vốn hàng bán (COGS) nên mới chỉ phân tích được Doanh thu chứ chưa tính được Lợi nhuận gộp ròng. Tỷ giá hối đoái mới dừng ở cấp độ trung bình tháng.
  - *Hướng phát triển:* Mở rộng tích hợp kiến trúc Big Data Lakehouse (MinIO/DuckDB) và xây dựng mô hình dự báo chuỗi thời gian doanh thu (ARIMA/Prophet) cho năm tiếp theo.
* **Lời kết:** Xin trân trọng cảm ơn Thầy Cô và Hội đồng đã chú ý lắng nghe! Nhóm kính mong nhận được những góp ý quý báu.
