# KỊCH BẢN THUYẾT TRÌNH BẢO VỆ ĐỒ ÁN (BẢN RÚT GỌN 5 PHÚT)
**Học phần:** INT1422 — Kho dữ liệu và Khai phá dữ liệu  
**Đề tài:** Hệ thống Kho Dữ Liệu Bán Lẻ Đa Chiều (Star Schema) và Khai Phá Hành Vi Khách Hàng  
**Tổng thời gian:** Chuẩn 5 phút (~750 – 850 từ, tốc độ nói vừa phải, dứt khoát, tự tin)

---

## ⏱️ PHÂN BỔ THỜI GIAN THEO TỪNG GIÂY

| Giai đoạn | Nội dung trọng tâm | Thời lượng | Mốc thời gian |
|---|---|:---:|:---:|
| **Phần 1** | Giới thiệu & Bài toán nghiệp vụ cốt lõi | 45 giây | `00:00 - 00:45` |
| **Phần 2** | Dữ liệu, Làm sạch & Kiểm toán tài chính | 45 giây | `00:45 - 01:30` |
| **Phần 3** | Thiết kế Star Schema & Trình diễn 5 phép OLAP | 75 giây | `01:30 - 02:45` |
| **Phần 4** | Khai phá RFM, K-Means ($k=4$) & Baseline | 60 giây | `02:45 - 03:45` |
| **Phần 5** | Luật bán chéo Apriori (Market Basket) | 45 giây | `03:45 - 04:30` |
| **Phần 6** | Demo Dashboard, Khuyến nghị & Kết thúc | 30 giây | `04:30 - 05:00` |

---

## 🎙️ LỜI THOẠI CHI TIẾT DÀNH CHO NGƯỜI THUYẾT TRÌNH (SPEAKER SCRIPT)

### 1. Giới thiệu & Bài toán nghiệp vụ (00:00 – 00:45)
> *"Kính thưa Thầy Cô và các bạn, em xin đại diện nhóm trình bày đề tài: **Xây dựng Kho dữ liệu bán lẻ đa chiều và Khai phá hành vi khách hàng**.*  
>
> *Xuất phát điểm của bài toán là: Một doanh nghiệp bán lẻ sở hữu hơn nửa triệu giao dịch nhưng quản lý bằng các file Excel rời rạc. Ban giám đốc gặp phải **3 điểm mù lớn**:*  
> 1. *Doanh thu tăng trưởng thật hay do biến động tỷ giá? Đâu là khung giờ vàng để chạy quảng cáo?*  
> 2. *Trong hơn 4,000 khách hàng, ai là VIP mang lại nguồn sống cho công ty, ai sắp bỏ đi cần giữ chân?*  
> 3. *Khách đã mua món này thì nên mời mua thêm món gì để tối ưu doanh thu giỏ hàng?*  
>
> *Hệ thống của nhóm em được xây dựng đóng vai trò như một **bộ não điều hành**, giải quyết trọn vẹn 3 câu hỏi trên."*

---

### 2. Dữ liệu, Làm sạch & Bảo toàn giá trị tài chính (00:45 – 01:30)
> *"Để giải bài toán, nhóm tích hợp 3 nguồn: bộ dữ liệu lõi **Online Retail** từ UCI với hơn 541,000 dòng, catalog sản phẩm chuẩn hóa từ **DummyJSON API**, và tỷ giá tiền tệ thực từ **Ngân hàng Trung ương Châu Âu (ECB)**.*  
>
> *Với phương châm dữ liệu sạch mới ra kết quả đúng, nhóm xây dựng quy trình lọc minh bạch:*  
> - *Loại bỏ toàn bộ đơn hủy và các dòng số lượng, đơn giá nhỏ hơn hoặc bằng 0.*  
> - *Đặc biệt, với 132,000 dòng thiếu mã khách hàng, nhóm **không xóa bỏ** mà gán mã quy ước `-1 GUEST` để bảo toàn chính xác 1.6 triệu Bảng tiền mua hàng.*  
>
> *Kết quả: Thu được **524,874 dòng giao dịch sạch**, xác lập doanh thu thực tế là **10.64 triệu Bảng Anh** và 5.57 triệu sản phẩm bán ra. Toàn bộ vết làm sạch được lưu tự động trong file audit trail."*

---

### 3. Thiết kế Star Schema & Trình diễn OLAP (01:30 – 02:45)
> *"Về kiến trúc kho dữ liệu, nhóm thiết kế theo mô hình **Star Schema** gồm bảng sự kiện trung tâm `Fact_Sales` và 4 chiều: Thời gian, Khách hàng, Sản phẩm và Địa lý.*  
>
> *Quyết định kỹ thuật then chốt là chọn **độ mịn (Granularity) ở cấp từng dòng mặt hàng (line-item)** thay vì cấp hóa đơn. Nhờ độ mịn này, doanh nghiệp mới biết chi tiết từng sản phẩm bán kèm nhau ra sao.*  
>
> *Để tránh việc quét nửa triệu dòng gây giật lag khi xem báo cáo, nhóm **tính trước 3 khối tổng hợp (OLAP Views)** theo Tháng, Quốc gia và Sản phẩm, giúp tốc độ truy vấn tăng gấp 15 lần.*  
>
> *Trên kho dữ liệu này, nhóm trình diễn trọn vẹn **5 thao tác OLAP chuẩn**:*  
> - ***Roll-up:** Gộp doanh thu tháng lên cấp Quý, phát hiện Quý 4/2011 đạt đỉnh gần 3.3 triệu Bảng.*  
> - ***Drill-down:** Phóng to xem chi tiết từng tháng và từng khách hàng VIP.*  
> - ***Slice & Dice:** Cắt lát doanh thu năm 2011 tại thị trường Anh và Đức.*  
> - ***Pivot:** Xoay ma trận so sánh trực diện cạnh tranh giữa các thị trường.*  
>
> *Toàn bộ kho dữ liệu đã vượt qua **31/31 bài kiểm thử tự động đạt 100% PASS**, chênh lệch số dòng bằng 0, chênh lệch doanh thu bằng £0.00."*

---

### 4. Khai phá RFM, Phân cụm K-Means & Đối chứng Baseline (02:45 – 03:45)
> *"Sang phần Khai phá dữ liệu: Nhóm tiếp cận bằng mô hình định lượng **RFM** và thuật toán gom cụm **K-Means**.*  
>
> *Dữ liệu thực tế chứng minh hoàn toàn quy luật 80/20: Nhóm **Champions (VIP)** chỉ chiếm **22%** khách hàng nhưng đóng góp tới **54.4% tổng doanh thu** (hơn 5.79 triệu Bảng). Ngược lại, có hơn 1,000 khách đã 'ngủ đông' trên 200 ngày.*  
>
> *Đặc biệt, tuân thủ yêu cầu học thuật của môn học, nhóm xây dựng **mô hình cơ sở (Baseline Model)** để đối chứng:*  
> - *Nếu chạy K-Means trên RFM thô như thông thường ($k=2$), mô hình bị 26 khách hàng siêu giàu làm méo mó, sinh ra cụm 4,312 khách đối đầu với 26 khách — hoàn toàn vô dụng cho kinh doanh.*  
> - *Mô hình cải tiến của nhóm áp dụng biến đổi **$\log(1+x)$ chuẩn hóa với $k=4$**, đạt điểm Silhouette holdout **0.3368** và độ ổn định giữa các hạt giống lên tới **97.54%**.*  
>
> *Thuật toán chia khách hàng thành 4 tầng định lượng rõ ràng: Low Value, Moderate, High Value và Super VIP, giúp đội ngũ bán hàng chăm sóc đúng đối tượng."*

---

### 5. Luật kết hợp Apriori & Gợi ý bán chéo (03:45 – 04:30)
> *"Bài toán thứ hai là phân tích giỏ hàng bằng thuật toán **Apriori** trên hơn 18,000 đơn hàng đa sản phẩm, trích xuất được **992 luật bán chéo** có hệ số nâng $Lift \ge 1.2$.*  
>
> *Các phát hiện thương mại nổi bật:*  
> - *Khách mua đĩa trà hoàng gia màu hồng thì có tới **91.15%** sẽ mua tiếp đĩa màu xanh, với hệ số **Lift lên đến 43.83 lần** — nghĩa là xác suất mua kèm cao gấp gần 44 lần so với mua ngẫu nhiên!*  
> - *Tương tự, các cặp đồ chơi trẻ em hay cốc đĩa tiệc chấm bi đều có độ nâng từ 28 đến 31 lần.*  
>
> *Hành động thực tế: Doanh nghiệp chỉ cần đóng gói combo hoặc gợi ý ngay trên web là có thể lập tức tăng giá trị đơn hàng trung bình."*

---

### 6. Demo Dashboard & Tổng kết khuyến nghị (04:30 – 05:00)
> *(Chuyển màn hình sang Dashboard Streamlit)*  
> *"Toàn bộ mô hình được đóng gói hoàn chỉnh lên ứng dụng web **Streamlit Dashboard 6 Tab**: Từ theo dõi KPI tài chính, bản đồ nhiệt khách hàng, đến công cụ chọn một sản phẩm tự động gợi ý món mua kèm theo thời gian thực.*  
>
> *Tóm lại, đồ án đã giải quyết trọn vẹn từ khâu gom dữ liệu thô, chuẩn hóa kho Star Schema, đến phân khúc khách hàng và luật bán chéo có thể ứng dụng được ngay vào doanh nghiệp.*  
>
> *Em xin trân trọng cảm ơn Quý Thầy Cô đã chú ý lắng nghe, nhóm chúng em rất mong nhận được những góp ý quý báu ạ!"*

---

## 💡 MẸO DÀNH CHO BẠN KHI NÓI TRONG 5 PHÚT:
1. **Dứt khoát ở các con số then chốt:** Nhấn mạnh: **524 nghìn dòng**, **10.64 triệu Bảng**, **31/31 test PASS**, **VIP chiếm 22% mang về 54% doanh thu**, và **Lift 43.8 lần**.
2. **Khi chuyển ý:** Dùng đúng từ khóa để người chấm chấm điểm CLO: *"Về kho dữ liệu CLO1...", "Về mô hình khai phá và baseline CLO2...", "Về kết quả ứng dụng thực tế..."*.
3. **Thao tác tay:** Khi nói đến 4:30, chỉ cần bấm chuột lướt nhanh 2-3 Tab trên giao diện `app.py` để chứng minh sản phẩm sống chạy thật.
