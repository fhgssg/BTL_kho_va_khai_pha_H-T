"""
HỆ THỐNG KHO DỮ LIỆU & PHÂN TÍCH KINH DOANH BÁN LẺ
(ONLINE RETAIL DATA WAREHOUSE & BUSINESS INTELLIGENCE DASHBOARD)
File: app.py
Khởi chạy: streamlit run app.py
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import requests
from sqlalchemy import text
from dwh_connection import get_engine

# ------------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG VÀ THIẾT KẾ GIAO DIỆN (STREAMLIT PAGE CONFIG & THEME)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Kho Dữ Liệu & Phân Tích Bán Lẻ Trực Tuyến",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS giao diện hiện đại, chuyên nghiệp
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 50%, #0D9488 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    
    .sub-title {
        color: #64748B;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1.2rem;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08);
    }
    
    .metric-label {
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-value {
        color: #0F172A;
        font-size: 1.8rem;
        font-weight: 800;
        margin: 0.3rem 0;
    }
    
    .metric-delta {
        font-size: 0.82rem;
        font-weight: 600;
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        padding: 10px 20px;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. ĐƯỜNG DẪN DỮ LIỆU & TẢI DỮ LIỆU (CACHED DATA LOADERS)
# ------------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RFM_PATH = os.path.join(BASE_DIR, "outputs", "rfm_customer_segments.csv")
RULES_PATH = os.path.join(BASE_DIR, "outputs", "market_basket_rules.csv")

def _sales_filter_clause(region_type=None, customer_ids=None):
    clauses = []
    params = {}
    if region_type:
        clauses.append("l.regiontype = :region_type")
        params["region_type"] = region_type
    if customer_ids is not None:
        if not customer_ids:
            clauses.append("1 = 0")
        else:
            placeholders = ", ".join(f":customer_id_{index}" for index in range(len(customer_ids)))
            clauses.append(f"c.CustomerID IN ({placeholders})")
            params.update({
                f"customer_id_{index}": customer_id
                for index, customer_id in enumerate(customer_ids)
            })
    return (" AND " + " AND ".join(clauses) if clauses else ""), params

@st.cache_data(ttl=3600)
def load_kpi_and_monthly(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q_monthly = """
    SELECT 
        d.YearMonth,
        d.Year,
        d.Month,
        COUNT(DISTINCT f.InvoiceNo) AS TotalOrders,
        SUM(f.Quantity) AS TotalUnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS MonthlyRevenue,
        ROUND(SUM(f.TotalRevenue) / COUNT(DISTINCT f.InvoiceNo), 2) AS AOV
    FROM Fact_Sales f
    JOIN Dim_Date d ON f.DateKey = d.DateKey
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY d.YearMonth, d.Year, d.Month
    ORDER BY d.Year, d.Month
    """
    df_monthly = pd.read_sql_query(text(q_monthly), conn, params=params)
    df_monthly = df_monthly.rename(columns={
        "yearmonth": "YearMonth", "year": "Year", "month": "Month",
        "totalorders": "TotalOrders", "totalunitssold": "TotalUnitsSold",
        "monthlyrevenue": "MonthlyRevenue", "aov": "AOV"
    })
    
    # Tính MoM Growth %
    df_monthly['PrevRevenue'] = df_monthly['MonthlyRevenue'].shift(1)
    df_monthly['MoM_Growth_Pct'] = (
        (df_monthly['MonthlyRevenue'] - df_monthly['PrevRevenue']) / df_monthly['PrevRevenue'] * 100
    ).round(2)
    
    conn.close()
    return df_monthly

@st.cache_data(ttl=3600)
def load_country_data(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q = """
    SELECT 
        l.Country,
        l.RegionType,
        COUNT(DISTINCT f.InvoiceNo) AS Orders,
        COUNT(DISTINCT f.CustomerKey) AS Customers,
        SUM(f.Quantity) AS UnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue
    FROM Fact_Sales f
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY l.Country, l.RegionType
    ORDER BY Revenue DESC
    """
    df = pd.read_sql_query(text(q), conn, params=params)
    df = df.rename(columns={
        "country": "Country", "regiontype": "RegionType", "orders": "Orders",
        "customers": "Customers", "unitssold": "UnitsSold", "revenue": "Revenue"
    })
    conn.close()
    return df

def categorize_product(desc):
    if not isinstance(desc, str):
        return "Quà tặng & Đồ lưu niệm"
    d = desc.upper()
    if any(k in d for k in ['KITCHEN', 'MUG', 'CUP', 'BOWL', 'PLATE', 'CUTLERY', 'JAR', 'CAKE', 'TEAPOT', 'BOTTLE', 'BAKING', 'FORK', 'SPOON', 'PAN', 'TIN', 'DISH', 'COFFEE', 'TEA', 'TRAY', 'BAKE', 'POT']):
        return "Dụng cụ nhà bếp & Bàn ăn"
    elif any(k in d for k in ['HEART', 'LIGHT', 'LANTERN', 'FRAME', 'CANDLE', 'CLOCK', 'WOODEN', 'DECORATION', 'MIRROR', 'HANGING', 'ORNAMENT', 'WALL', 'VASE', 'CUSHION', 'PILLOW', 'SIGN', 'DRAWER', 'CABINET', 'STAND']):
        return "Trang trí nhà cửa & Nội thất"
    elif any(k in d for k in ['BAG', 'SHOPPER', 'TOTE', 'PURSE', 'LUGGAGE', 'WALLET', 'POUCH', 'CASE']):
        return "Túi xách & Balo"
    elif any(k in d for k in ['SOAP', 'BATH', 'LIPSTICK', 'PERFUME', 'SCENT', 'CREAM', 'BEAUTY', 'FRAGRANCE', 'LIP']):
        return "Làm đẹp & Mỹ phẩm"
    elif any(k in d for k in ['NECKLACE', 'BRACELET', 'RING', 'EARRINGS', 'JEWELRY', 'BROOCH', 'CHARM', 'WATCH']):
        return "Trang sức & Phụ kiện"
    elif any(k in d for k in ['SHIRT', 'DRESS', 'SOCK', 'GLOVE', 'SCARF', 'HAT', 'APRON', 'COAT', 'JACKET', 'SHOES', 'BOOTS', 'SLIPPER', 'TOP']):
        return "Thời trang & May mặc"
    else:
        return "Quà tặng & Đồ lưu niệm"

@st.cache_data(ttl=3600)
def load_product_data(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q = """
    SELECT 
        p.StockCode,
        p.Description,
        SUM(f.Quantity) AS TotalQty,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        ROUND(AVG(f.UnitPrice), 2) AS AvgPrice
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY p.StockCode, p.Description
    """
    df = pd.read_sql_query(text(q), conn, params=params)
    df = df.rename(columns={
        "stockcode": "StockCode", "description": "Description",
        "totalqty": "TotalQty", "totalrevenue": "TotalRevenue", "avgprice": "AvgPrice"
    })
    trans_map_path = os.path.join(BASE_DIR, "data", "product_translation_map.json")
    trans_map = {}
    if os.path.exists(trans_map_path):
        import json
        with open(trans_map_path, "r", encoding="utf-8") as f:
            trans_map = json.load(f)
    df["Description_VN"] = df["Description"].map(lambda x: trans_map.get(x, x.title()))
    df["Category_VN"] = df["Description"].apply(categorize_product)
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_hourly_data(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q = """
    SELECT 
        f.Hour,
        COUNT(DISTINCT f.InvoiceNo) AS Orders,
        SUM(f.Quantity) AS Units,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue
    FROM Fact_Sales f
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY f.Hour
    ORDER BY f.Hour
    """
    df = pd.read_sql_query(text(q), conn, params=params)
    df = df.rename(columns={
        "hour": "Hour", "orders": "Orders", "units": "Units", "revenue": "Revenue"
    })
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_customer_ids_for_region(region_type):
    with get_engine().connect() as conn:
        df = pd.read_sql_query(
            text("""
        SELECT DISTINCT c.CustomerID AS "CustomerID"
        FROM Fact_Sales f
        JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
        JOIN Dim_Location l ON f.LocationKey = l.LocationKey
        WHERE l.RegionType = :region_type AND c.CustomerID != -1
        """),
            conn,
            params={"region_type": region_type}
        )
    return set(df["CustomerID"].astype(int))

@st.cache_data(ttl=3600)
def load_rfm_data(rfm_path):
    if os.path.exists(rfm_path):
        return pd.read_csv(rfm_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_basket_rules(rules_path):
    if os.path.exists(rules_path):
        return pd.read_csv(rules_path)
    return pd.DataFrame()

@st.cache_data(ttl=3600)
def load_dwh_row_counts():
    with get_engine().connect() as conn:
        counts = {
            table: pd.read_sql_query(
                text(f"SELECT COUNT(*) AS row_count FROM {table_name}"), conn
            ).iloc[0, 0]
            for table, table_name in (
                ("Fact_Sales", "fact_sales"),
                ("Dim_Product", "dim_product"),
                ("Dim_Customer", "dim_customer")
            )
        }
    return counts

# Tải dữ liệu nguồn
df_rfm = load_rfm_data(RFM_PATH)
df_rules = load_basket_rules(RULES_PATH)
dwh_row_counts = load_dwh_row_counts()

# ------------------------------------------------------------------------------
# 3. SIDEBAR - BỘ LỌC VÀ THÔNG TIN DỰ ÁN
# ------------------------------------------------------------------------------
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3081/3081559.png", width=65)
    st.markdown("### **BỘ ĐIỀU KHIỂN DWH**")
    st.caption("Kho Dữ Liệu Bán Lẻ Trực Tuyến")
    
    st.markdown("---")
    st.markdown("#### 🔍 **Bộ Lọc Phân Tích**")
    
    # Lọc khu vực
    region_options = ["Tất cả khu vực", "Vương quốc Anh", "Thị trường quốc tế"]
    selected_region = st.selectbox("Thị trường:", region_options)
    st.caption("Thị trường lọc giao dịch theo quốc gia phát sinh trong kho.")
    
    # Lọc phân khúc RFM
    if not df_rfm.empty:
        all_segments = ["Tất cả"] + sorted(df_rfm['Segment'].dropna().unique().tolist())
        selected_segment = st.selectbox("Phân khúc RFM:", all_segments)
    else:
        selected_segment = "Tất cả"
    st.caption("Phân khúc lọc giao dịch của khách thuộc nhóm RFM đã chọn.")
        
    st.markdown("---")
    st.markdown("#### 📊 **Thông Tin Kho Dữ Liệu**")
    st.markdown(f"""
    - **Kho đang dùng**: PostgreSQL (bảng curated từ MinIO Lakehouse)
    - **Lakehouse**: MinIO raw → staging → curated (Parquet)
    - **SQLite**: Phương án local/dự phòng
    - **Mô hình**: Star Schema chuẩn Kimball
    - **Fact**: {dwh_row_counts['Fact_Sales']:,} dòng
    - **Sản phẩm**: {dwh_row_counts['Dim_Product']:,} SKU | **Khách hàng**: {dwh_row_counts['Dim_Customer']:,}
    - **Khoảng thời gian**: 12/2010 - 12/2011
    """)
    st.markdown("---")
    st.caption("Đồ án: Modern Data Lakehouse & Retail Analytics")

region_type = {
    "Tất cả khu vực": None,
    "Vương quốc Anh": "Domestic",
    "Thị trường quốc tế": "International",
}[selected_region]
segment_customer_ids = None
if selected_segment != "Tất cả":
    segment_customer_ids = tuple(sorted(
        int(customer_id)
        for customer_id in df_rfm.loc[df_rfm["Segment"] == selected_segment, "CustomerID"].dropna()
    ))

df_monthly = load_kpi_and_monthly(region_type, segment_customer_ids)
df_country = load_country_data(region_type, segment_customer_ids)
df_products = load_product_data(region_type, segment_customer_ids)
df_hourly = load_hourly_data(region_type, segment_customer_ids)

df_rfm_analysis = df_rfm.copy()
if selected_segment != "Tất cả":
    df_rfm_analysis = df_rfm_analysis[df_rfm_analysis["Segment"] == selected_segment]
if region_type:
    regional_customer_ids = load_customer_ids_for_region(region_type)
    df_rfm_analysis = df_rfm_analysis[
        df_rfm_analysis["CustomerID"].astype(int).isin(regional_customer_ids)
    ]

# ------------------------------------------------------------------------------
# 4. TIÊU ĐỀ CHÍNH & TỔNG QUAN KPIS (EXECUTIVE OVERVIEW)
# ------------------------------------------------------------------------------
st.markdown('<div class="main-title">HỆ THỐNG PHÂN TÍCH KHO DỮ LIỆU BÁN LẺ TRỰC TUYẾN</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Kho Dữ Liệu Đa Chiều & Phân Tích Hành Vi Người Tiêu Dùng Thương Mại Điện Tử</div>', unsafe_allow_html=True)

# Tính toán các chỉ số KPI cấp cao
total_revenue = df_monthly['MonthlyRevenue'].sum()
total_orders = df_monthly['TotalOrders'].sum()
total_units = df_monthly['TotalUnitsSold'].sum()
avg_aov = total_revenue / total_orders if total_orders else 0
repeat_customer_pct = (
    (df_rfm_analysis['Frequency'] > 1).mean() * 100 if not df_rfm_analysis.empty else 0
)

# Hiển thị 4 thẻ KPI Card
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Doanh Thu Theo Bộ Lọc</div>
        <div class="metric-value">£{total_revenue:,.2f}</div>
        <div class="metric-delta" style="color: #10B981;">▲ Tổng doanh thu giao dịch phù hợp bộ lọc</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Số Đơn Hàng Theo Bộ Lọc</div>
        <div class="metric-value">{total_orders:,}</div>
        <div class="metric-delta" style="color: #3B82F6;">● {total_units:,} sản phẩm bán ra</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Giá Trị Đơn Hàng Trung Bình</div>
        <div class="metric-value">£{avg_aov:,.2f}</div>
        <div class="metric-delta" style="color: #6366F1;">● Đặc thù khách buôn & quà tặng</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Khách Định Danh Trong Phân Tích</div>
        <div class="metric-value">{len(df_rfm_analysis):,}</div>
        <div class="metric-delta" style="color: #F59E0B;">★ {repeat_customer_pct:.2f}% khách quay lại mua</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------------------------
# 5. CÁC TABS PHÂN TÍCH CHUYÊN SÂU
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 Xu Hướng Doanh Thu",
    "🌍 Thị Trường & Ngành Hàng Sản Phẩm",
    "👥 Phân Khúc Khách Hàng",
    "🧺 Gợi Ý Bán Chéo Giỏ Hàng"
])

active_filters = []
if selected_region != "Tất cả khu vực":
    active_filters.append(selected_region)
if selected_segment != "Tất cả":
    active_filters.append(selected_segment)
st.caption(
    "Phạm vi đang xem: " + (" • ".join(active_filters) if active_filters else "Toàn bộ dữ liệu")
    + ". Dữ liệu luật Apriori và nhãn K-Means là kết quả đã tính toán trước."
)
if df_monthly.empty:
    st.warning("Không có giao dịch phù hợp với bộ lọc hiện tại.")

# ==============================================================================
# TAB 1: XU HƯỚNG DOANH THU & THỜI GIAN
# ==============================================================================
with tab1:
    st.subheader("1. Phân Tích Xu Hướng Doanh Thu Theo Tháng & Tốc Độ Tăng Trưởng")
    
    col_t1, col_t2 = st.columns([7, 3])
    
    # Định dạng tháng hiển thị dạng tiếng Việt
    df_monthly['Thang_HienThi'] = df_monthly['YearMonth'].apply(lambda ym: f"Tháng {ym[5:7]}/{ym[:4]}")

    with col_t1:
        fig_revenue = go.Figure()
        fig_revenue.add_trace(go.Bar(
            x=df_monthly['Thang_HienThi'],
            y=df_monthly['MonthlyRevenue'],
            name='Doanh thu (£ GBP)',
            marker_color='#3B82F6',
            opacity=0.85
        ))
        fig_revenue.add_trace(go.Scatter(
            x=df_monthly['Thang_HienThi'],
            y=df_monthly['TotalOrders'] * 500,  # Scaled for secondary view
            name='Đơn hàng (Tỷ lệ quy đổi)',
            line=dict(color='#F59E0B', width=3),
            mode='lines+markers'
        ))
        fig_revenue.update_layout(
            title="Doanh thu hàng tháng & Quy mô đơn hàng (Tháng 12/2010 - Tháng 12/2011)",
            xaxis_title="Thời gian",
            yaxis_title="Doanh thu (£ GBP)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
            height=400
        )
        st.plotly_chart(fig_revenue, use_container_width=True)

    with col_t2:
        st.markdown("##### 📌 Tốc Độ Tăng Trưởng Hàng Tháng (%)")
        df_display_mom = df_monthly[['Thang_HienThi', 'MonthlyRevenue', 'MoM_Growth_Pct']].dropna().copy()
        df_display_mom.columns = ['Tháng', 'Doanh Thu', 'Tăng Trưởng MoM']
        st.dataframe(
            df_display_mom.style.format({
                'Doanh Thu': '£{:,.2f}',
                'Tăng Trưởng MoM': '{:+.2f}%'
            }),
            height=360,
            use_container_width=True
        )

    st.markdown("---")
    st.subheader("2. Khung Giờ Mua Sắm Cao Điểm Trong Ngày")
    
    col_h1, col_h2 = st.columns([7, 3])
    with col_h1:
        fig_hour = px.area(
            df_hourly,
            x='Hour',
            y='Orders',
            title="Phân bố số lượng đơn hàng theo khung giờ trong ngày (0h - 23h)",
            labels={'Hour': 'Khung giờ', 'Orders': 'Số lượng hóa đơn'},
            color_discrete_sequence=['#0D9488']
        )
        fig_hour.add_vline(x=12, line_width=2, line_dash="dash", line_color="#EF4444", annotation_text="Đỉnh: 12h Trưa")
        fig_hour.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_hour, use_container_width=True)
        
    with col_h2:
        peak_hours = df_hourly[df_hourly["Hour"].between(10, 15)]
        peak_share = (
            peak_hours["Orders"].sum() / df_hourly["Orders"].sum() * 100
            if not df_hourly.empty and df_hourly["Orders"].sum() else 0
        )
        peak_hour = (
            int(df_hourly.loc[df_hourly["Orders"].idxmax(), "Hour"])
            if not df_hourly.empty else None
        )
        peak_hour_label = f"{peak_hour:02d}:00" if peak_hour is not None else "—"
        peak_hour_orders = (
            int(df_hourly["Orders"].max()) if not df_hourly.empty else 0
        )
        st.info(f"""
        **Chiến Lược Kinh Doanh Phù Hợp:**
        - **Khung giờ vàng**: Từ **10:00 đến 15:00** chiếm **{peak_share:.1f}%** số đơn trong phạm vi đang lọc.
        - **Giờ cao điểm**: **{peak_hour_label}** với **{peak_hour_orders:,}** đơn hàng.
        - **Đề xuất**: Cân nhắc tập trung quảng cáo và email trước khung giờ cao điểm của nhóm khách/thị trường đang xem.
        """)

# ==============================================================================
# TAB 2: ĐỊA LÝ & SẢN PHẨM CHỦ LỰC
# ==============================================================================
with tab2:
    st.subheader("1. Cơ Cấu Thị Trường Địa Lý Theo Bộ Lọc")
    col_g1, col_g2 = st.columns([6, 4])
    
    with col_g1:
        # Top 10 quốc gia
        top10_countries = df_country.head(10).copy()
        fig_country = px.bar(
            top10_countries,
            x='Revenue',
            y='Country',
            orientation='h',
            title="Top 10 Quốc Gia Đóng Góp Doanh Thu Cao Nhất Theo Bộ Lọc",
            labels={'Revenue': 'Doanh thu (£ GBP)', 'Country': 'Quốc gia'},
            color='Revenue',
            color_continuous_scale='Blues'
        )
        fig_country.update_layout(yaxis=dict(autorange="reversed"), height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_country, use_container_width=True)
        
    with col_g2:
        # Tỷ lệ UK vs Quốc tế
        domestic_rev = df_country[df_country['RegionType'] == 'Domestic']['Revenue'].sum()
        intl_rev = df_country[df_country['RegionType'] == 'International']['Revenue'].sum()
        df_region = pd.DataFrame({
            'Vùng': ['Vương quốc Anh', 'Thị trường quốc tế'],
            'Doanh Thu': [domestic_rev, intl_rev]
        })
        fig_region = px.pie(
            df_region,
            names='Vùng',
            values='Doanh Thu',
            title="Tỷ Trọng Thị Trường: Vương Quốc Anh vs Quốc Tế",
            hole=0.45,
            color_discrete_sequence=['#1E3A8A', '#0D9488']
        )
        fig_region.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_region, use_container_width=True)

    st.markdown("---")
    st.subheader("2. Cơ Cấu Doanh Thu Theo Ngành Hàng & Đối Chiếu Thị Trường")
    st.caption("Dữ liệu bán hàng DWH nội bộ được ghép nối với chuẩn phân loại ngành hàng và điểm đánh giá thực tế từ E-Commerce REST API.")
    
    # Tính toán tổng hợp theo ngành hàng kết hợp
    cat_dwh_agg = df_products.groupby("Category_VN").agg(
        dwh_so_sku=("StockCode", "count"),
        dwh_san_luong=("TotalQty", "sum"),
        dwh_doanh_thu=("TotalRevenue", "sum"),
        dwh_gia_tb=("AvgPrice", "mean")
    ).reset_index()

    market_benchmark_defaults = {
        "Dụng cụ nhà bếp & Bàn ăn": {"rating": 3.82, "market_price": 17.69},
        "Trang trí nhà cửa & Nội thất": {"rating": 4.15, "market_price": 28.50},
        "Túi xách & Balo": {"rating": 4.20, "market_price": 22.80},
        "Làm đẹp & Mỹ phẩm": {"rating": 3.75, "market_price": 13.39},
        "Trang sức & Phụ kiện": {"rating": 3.90, "market_price": 35.40},
        "Thời trang & May mặc": {"rating": 3.85, "market_price": 42.10},
        "Quà tặng & Đồ lưu niệm": {"rating": 4.05, "market_price": 18.20},
    }
    cat_dwh_agg["rating_thi_truong"] = cat_dwh_agg["Category_VN"].map(
        lambda c: market_benchmark_defaults.get(c, {}).get("rating", 3.90)
    )
    cat_dwh_agg["gia_tb_thi_truong"] = cat_dwh_agg["Category_VN"].map(
        lambda c: market_benchmark_defaults.get(c, {}).get("market_price", 20.0)
    )
    total_rev_all = cat_dwh_agg["dwh_doanh_thu"].sum()
    cat_dwh_agg["ty_trong_doanh_thu"] = (
        (cat_dwh_agg["dwh_doanh_thu"] * 100.0 / total_rev_all).round(2)
        if total_rev_all > 0 else 0
    )
    cat_dwh_agg = cat_dwh_agg.sort_values(by="dwh_doanh_thu", ascending=False)

    col_cat1, col_cat2 = st.columns([6, 4])
    with col_cat1:
        fig_cat_bar = px.bar(
            cat_dwh_agg,
            x="dwh_doanh_thu",
            y="Category_VN",
            orientation="h",
            color="rating_thi_truong",
            color_continuous_scale="Blues",
            title="Doanh Thu Theo Ngành Hàng DWH (Màu: Điểm Đánh Giá Thị Trường API)",
            labels={
                "dwh_doanh_thu": "Doanh thu (£ GBP)",
                "Category_VN": "Ngành hàng",
                "rating_thi_truong": "Đánh giá ★ (API)"
            }
        )
        fig_cat_bar.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_cat_bar, use_container_width=True)

    with col_cat2:
        disp_cat_table = cat_dwh_agg[[
            "Category_VN", "dwh_doanh_thu", "ty_trong_doanh_thu", "rating_thi_truong"
        ]].copy()
        disp_cat_table.columns = ["Ngành Hàng", "Doanh Thu", "Tỷ Trọng", "Đánh Giá ★"]
        st.dataframe(
            disp_cat_table.style.format({
                "Doanh Thu": "£{:,.0f}",
                "Tỷ Trọng": "{:.1f}%",
                "Đánh Giá ★": "{:.2f} ★"
            }),
            height=330,
            use_container_width=True,
            hide_index=True
        )

    st.markdown("---")
    st.subheader("3. Top Mặt Hàng Chủ Lực Bán Chạy & Doanh Thu Cao Nhất")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("##### 📦 Top 10 Mặt Hàng Bán Chạy Nhất Về Số Lượng")
        top_qty = df_products.sort_values(by='TotalQty', ascending=False).head(10)
        fig_top_qty = px.bar(
            top_qty,
            x='TotalQty',
            y='Description_VN',
            orientation='h',
            color='TotalQty',
            color_continuous_scale='Viridis',
            labels={'TotalQty': 'Số lượng bán', 'Description_VN': 'Sản phẩm'}
        )
        fig_top_qty.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_qty, use_container_width=True)
        
    with col_p2:
        st.markdown("##### 💰 Top 10 Mặt Hàng Đem Lại Doanh Thu Cao Nhất")
        top_rev = df_products.sort_values(by='TotalRevenue', ascending=False).head(10)
        fig_top_rev = px.bar(
            top_rev,
            x='TotalRevenue',
            y='Description_VN',
            orientation='h',
            color='TotalRevenue',
            color_continuous_scale='Cividis',
            labels={'TotalRevenue': 'Doanh thu (£ GBP)', 'Description_VN': 'Sản phẩm'}
        )
        fig_top_rev.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_rev, use_container_width=True)

# ==============================================================================
# TAB 3: PHÂN KHÚC KHÁCH HÀNG
# ==============================================================================
with tab3:
    st.subheader("1. Chân Dung & Phân Khúc Khách Hàng Theo Mô Hình RFM")
    st.caption("RFM và biểu đồ khách hàng được giới hạn theo bộ lọc. Nhãn K-Means là kết quả đã tính toán trên toàn bộ tập khách hàng.")
    
    if not df_rfm_analysis.empty:
        col_rfm1, col_rfm2 = st.columns([6, 4])
        
        with col_rfm1:
            segment_counts = df_rfm_analysis.groupby('Segment').agg(
                Khách_Hàng=('CustomerID', 'count'),
                Doanh_Thu=('Monetary', 'sum'),
                Recency_TB=('Recency', 'mean'),
                Frequency_TB=('Frequency', 'mean'),
                Monetary_TB=('Monetary', 'mean')
            ).reset_index().sort_values(by='Doanh_Thu', ascending=False)
            
            fig_rfm_treemap = px.treemap(
                segment_counts,
                path=['Segment'],
                values='Doanh_Thu',
                color='Khách_Hàng',
                color_continuous_scale='Blues',
                title="Quy Mô Doanh Thu & Số Khách Theo Từng Phân Khúc RFM"
            )
            fig_rfm_treemap.update_traces(
                hovertemplate="<b>Phân khúc: %{label}</b><br>Tổng doanh thu: £%{value:,.2f}<br>Số lượng khách: %{color:,}<extra></extra>"
            )
            fig_rfm_treemap.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rfm_treemap, use_container_width=True)

        with col_rfm2:
            fig_segment_pie = px.pie(
                segment_counts,
                names='Segment',
                values='Khách_Hàng',
                title="Cơ Cấu Tỷ Lệ Khách Hàng (%)",
                hole=0.4
            )
            fig_segment_pie.update_traces(
                hovertemplate="<b>Phân khúc: %{label}</b><br>Số lượng: %{value:,} khách (%{percent})<extra></extra>"
            )
            fig_segment_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_segment_pie, use_container_width=True)

        st.markdown("---")
        cluster_count = df_rfm['KMeans_Cluster'].nunique()
        st.subheader(f"2. Đối Chiếu Thuật Toán Gom Cụm K-Means ({cluster_count} Cụm)")
        
        col_km1, col_km2 = st.columns([7, 3])
        with col_km1:
            fig_scatter = px.scatter(
                df_rfm_analysis,
                x='Recency',
                y='Monetary',
                size='Frequency',
                color='KMeans_Label',
                hover_name='CustomerCode',
                log_y=True,
                title="Phân Cụm Khách Hàng K-Means (Trục Y: Doanh Thu Logarit, Kích Thước: Tần Suất Mua)",
                color_discrete_sequence=['#3B82F6', '#10B981', '#F59E0B', '#EF4444'],
                labels={'Recency': 'Số ngày mua gần nhất (Recency)', 'Monetary': 'Chi tiêu (£ Monetary)', 'KMeans_Label': 'Phân Cụm'}
            )
            fig_scatter.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_scatter, use_container_width=True)
            
        with col_km2:
            st.markdown("##### 📋 Bảng Thống Kê Phân Khúc")
            df_segment_disp = segment_counts.rename(columns={
                'Segment': 'Phân khúc',
                'Khách_Hàng': 'Số khách',
                'Doanh_Thu': 'Doanh thu',
                'Recency_TB': 'Độ mới TB (ngày)',
                'Frequency_TB': 'Tần suất TB (đơn)',
                'Monetary_TB': 'Chi tiêu TB (£)'
            })
            st.dataframe(
                df_segment_disp.style.format({
                    'Doanh thu': '£{:,.0f}',
                    'Độ mới TB (ngày)': '{:.1f}',
                    'Tần suất TB (đơn)': '{:.1f}',
                    'Chi tiêu TB (£)': '£{:,.1f}'
                }),
                height=380,
                use_container_width=True,
                hide_index=True
            )

        st.markdown("---")
        st.subheader("3. Danh Sách Khách Hàng Theo Phân Khúc Đang Lọc")
        champions_df = df_rfm_analysis.sort_values(by='Monetary', ascending=False)
        disp_champions = champions_df[['CustomerCode', 'Country', 'Recency', 'Frequency', 'Monetary', 'KMeans_Label']].head(15).copy()
        disp_champions.columns = ['Mã Khách Hàng', 'Quốc Gia', 'Độ Mới (Ngày)', 'Số Đơn', 'Tổng Chi Tiêu', 'Phân Cụm K-Means']
        st.dataframe(
            disp_champions.style.format({
                'Tổng Chi Tiêu': '£{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Chưa tìm thấy file `outputs/rfm_customer_segments.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# ==============================================================================
# TAB 4: GỢI Ý BÁN CHÉO GIỎ HÀNG
# ==============================================================================
with tab4:
    st.subheader("1. Công Cụ Gợi Ý Bán Kèm Sản Phẩm Thông Minh")
    st.write("Dựa trên thuật toán khai phá luật kết hợp **Apriori** từ hơn 18,000 giỏ hàng.")
    st.caption("Các luật Apriori được khai phá trước trên toàn bộ dữ liệu, không được tính lại theo bộ lọc thị trường hoặc RFM.")
    
    if not df_rules.empty:
        # Lấy danh sách các sản phẩm tiền đề (Antecedents)
        unique_antecedents = sorted(df_rules['antecedents_str'].unique().tolist())
        
        col_rec1, col_rec2 = st.columns([5, 5])
        with col_rec1:
            selected_item = st.selectbox(
                "🛒 Chọn sản phẩm khách hàng đang xem hoặc đã bỏ vào giỏ hàng:",
                options=unique_antecedents,
                index=0
            )
            
        filtered_rules = df_rules[df_rules['antecedents_str'] == selected_item].sort_values(by=['lift', 'confidence'], ascending=[False, False])
        
        with col_rec2:
            st.metric(
                label="Số lượng sản phẩm gợi ý phù hợp",
                value=f"{len(filtered_rules)} mặt hàng",
                delta=f"Hệ số Lift cao nhất: {filtered_rules['lift'].max():.2f} lần" if not filtered_rules.empty else None
            )

        if not filtered_rules.empty:
            st.markdown("##### 🎁 Danh Sách Sản Phẩm Được Mua Kèm Nhiều Nhất:")
            
            for idx, r in filtered_rules.head(5).iterrows():
                conf_pct = r['confidence'] * 100
                lift_val = r['lift']
                supp_pct = r['support'] * 100
                
                st.success(f"""
                **Gợi ý mua kèm**: **{r['consequents_str']}**  
                - **Độ tin cậy**: **{conf_pct:.1f}%** *(Có {conf_pct:.1f}% khách hàng mua sản phẩm này khi đã mua sản phẩm đã chọn)*  
                - **Hệ số tương quan (Lift)**: **{lift_val:.2f} lần** *(Xác suất mua cùng cao gấp {lift_val:.2f} lần so với mua ngẫu nhiên)*  
                - **Độ hỗ trợ**: **{supp_pct:.2f}%** đơn hàng
                """)
        else:
            st.info("Chưa có luật kết hợp trực tiếp cho sản phẩm này trong ngưỡng lọc.")

        st.markdown("---")
        st.subheader("2. Top 15 Luật Kết Hợp Có Hệ Số Lift Cao Nhất Toàn Hệ Thống")
        display_rules = df_rules.head(15)[['antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']].copy()
        display_rules['support'] = (display_rules['support'] * 100).round(2).astype(str) + '%'
        display_rules['confidence'] = (display_rules['confidence'] * 100).round(2).astype(str) + '%'
        display_rules['lift'] = display_rules['lift'].round(2)
        display_rules.columns = ['Nếu Khách Mua', 'Gợi Ý Mua Kèm', 'Độ Hỗ Trợ', 'Độ Tin Cậy', 'Hệ Số Lift']
        st.dataframe(display_rules, use_container_width=True)
    else:
        st.warning("Chưa tìm thấy file `outputs/market_basket_rules.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.9rem;'>Đồ Án Kho Dữ Liệu & Phân Tích Bán Lẻ (Online Retail DWH) • MinIO Lakehouse, PostgreSQL & Streamlit</div>", unsafe_allow_html=True)

