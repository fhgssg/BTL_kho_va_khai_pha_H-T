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
from sqlalchemy import text
from dwh_connection import get_engine

# ------------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG VÀ THIẾT KẾ GIAO DIỆN (STREAMLIT PAGE CONFIG & THEME)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Bảng điều khiển kho dữ liệu bán lẻ",
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

@st.cache_data(ttl=3600)
def load_product_data(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q = """
    SELECT 
        p.StockCode,
        p.Description,
        p.Category,
        SUM(f.Quantity) AS TotalQty,
        ROUND(SUM(f.TotalRevenue), 2) AS TotalRevenue,
        ROUND(AVG(f.UnitPrice), 2) AS AvgPrice
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY p.StockCode, p.Description, p.Category
    """
    df = pd.read_sql_query(text(q), conn, params=params)
    df = df.rename(columns={
        "stockcode": "StockCode", "description": "Description", "category": "Category",
        "totalqty": "TotalQty", "totalrevenue": "TotalRevenue", "avgprice": "AvgPrice"
    })
    conn.close()
    return df

@st.cache_data(ttl=3600)
def load_category_sales(region_type=None, customer_ids=None):
    conn = get_engine().connect()
    filter_sql, params = _sales_filter_clause(region_type, customer_ids)
    q = """
    SELECT
        COALESCE(p.Category, 'Chưa phân loại') AS Category,
        p.CategorySource,
        COUNT(DISTINCT p.ProductKey) AS Products,
        COUNT(DISTINCT f.InvoiceNo) AS Orders,
        SUM(f.Quantity) AS UnitsSold,
        ROUND(SUM(f.TotalRevenue), 2) AS Revenue
    FROM Fact_Sales f
    JOIN Dim_Product p ON f.ProductKey = p.ProductKey
    JOIN Dim_Location l ON f.LocationKey = l.LocationKey
    JOIN Dim_Customer c ON f.CustomerKey = c.CustomerKey
    WHERE 1 = 1
    """ + filter_sql + """
    GROUP BY p.Category, p.CategorySource
    ORDER BY Revenue DESC
    """
    df = pd.read_sql_query(text(q), conn, params=params)
    df = df.rename(columns={
        "category": "Category", "categorysource": "CategorySource",
        "products": "Products", "orders": "Orders",
        "unitssold": "UnitsSold", "revenue": "Revenue"
    })
    conn.close()
    return df

@st.cache_data(ttl=600)
def load_unified_products():
    query = """
    WITH sales_by_product AS (
        SELECT
            ProductKey,
            SUM(Quantity) AS TotalQuantity,
            SUM(TotalRevenue) AS TotalRevenue,
            COUNT(DISTINCT InvoiceNo) AS InvoiceCount
        FROM Fact_Sales
        GROUP BY ProductKey
    )
    SELECT
        p.ProductKey AS "ProductKey",
        p.StockCode AS "StockCode",
        p.Description AS "Description",
        p.SourceSystem AS "SourceSystem",
        p.APIProductID AS "APIProductID",
        p.CatalogTitle AS "CatalogTitle",
        p.Category AS "Category",
        p.CategorySource AS "CategorySource",
        p.UnitPrice_Standard AS "RetailAveragePrice",
        p.CatalogPrice AS "CatalogPrice",
        p.CatalogDiscountPercentage AS "CatalogDiscountPercentage",
        p.CatalogRating AS "CatalogRating",
        p.CatalogStock AS "CatalogStock",
        p.Brand AS "Brand",
        p.CatalogMatchMethod AS "MatchMethod",
        s.TotalQuantity AS "TotalQuantity",
        s.TotalRevenue AS "TotalRevenue",
        s.InvoiceCount AS "InvoiceCount"
    FROM Dim_Product p
    LEFT JOIN sales_by_product s ON s.ProductKey = p.ProductKey
    ORDER BY p.SourceSystem, p.Description
    """
    with get_engine().connect() as conn:
        return pd.read_sql_query(text(query), conn)

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
        source_counts = pd.read_sql_query(
            text("""
                SELECT SourceSystem, COUNT(*) AS ProductCount
                FROM Dim_Product
                GROUP BY SourceSystem
            """),
            conn,
        )
        counts["Online_Retail_Products"] = int(
            source_counts.loc[
                source_counts["sourcesystem"].isin(
                    ["Online Retail", "Online Retail + DummyJSON"]
                ),
                "productcount",
            ].sum()
        )
        counts["DummyJSON_Products"] = int(
            source_counts.loc[
                source_counts["sourcesystem"].isin(
                    ["DummyJSON", "Online Retail + DummyJSON"]
                ),
                "productcount",
            ].sum()
        )
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
    st.markdown("### Bảng điều khiển kho dữ liệu")
    st.caption("Kho dữ liệu bán lẻ trực tuyến")
    
    st.markdown("---")
    st.markdown("#### 🔍 **Bộ lọc phân tích**")
    
    # Lọc khu vực
    region_options = ["Tất cả khu vực", "Trong nước (Vương quốc Anh)", "Quốc tế"]
    selected_region = st.selectbox("Thị trường", region_options)
    st.caption("Thị trường lọc giao dịch theo quốc gia phát sinh trong kho.")
    
    # Lọc phân khúc RFM
    if not df_rfm.empty:
        segment_translation = {
            "At Risk (Có nguy cơ rời bỏ)": "Có nguy cơ rời bỏ",
            "Can't Lose Them (VIP sắp mất)": "Nhóm VIP có nguy cơ rời bỏ",
            "Champions (VIP)": "Khách hàng VIP",
            "Hibernating / Lost (Ngủ đông / Đã mất)": "Đã lâu không mua hoặc đã mất",
            "Loyal Customers (Trung thành)": "Khách hàng trung thành",
            "Need Attention (Cần chăm sóc)": "Cần được chăm sóc",
            "New / Potential Loyalists (Mới & Tiềm năng)": "Khách hàng mới hoặc tiềm năng",
            "Promising (Hứa hẹn)": "Khách hàng triển vọng",
        }
        segment_options = sorted(
            df_rfm["Segment"].dropna().unique().tolist(),
            key=lambda segment: segment_translation.get(segment, segment),
        )
        segment_labels = {
            segment_translation.get(segment, segment): segment
            for segment in segment_options
        }
        all_segments = ["Tất cả"] + list(segment_labels)
        selected_segment = st.selectbox("Phân khúc RFM", all_segments)
        selected_segment_value = segment_labels.get(selected_segment, selected_segment)
    else:
        selected_segment = "Tất cả"
        selected_segment_value = "Tất cả"
    st.caption("Phân khúc lọc giao dịch của khách thuộc nhóm RFM đã chọn.")
        
    st.markdown("---")
    st.markdown("#### Thông tin kho dữ liệu")
    st.markdown(f"""
    - **Kho đang dùng**: PostgreSQL (bảng curated từ MinIO Lakehouse)
    - **Lakehouse**: MinIO raw → staging → curated (Parquet)
    - **SQLite**: Phương án local/dự phòng
    - **Mô hình**: Lược đồ hình sao Kimball
    - **Giao dịch**: {dwh_row_counts['Fact_Sales']:,} dòng
    - **Sản phẩm hợp nhất**: {dwh_row_counts['Dim_Product']:,} dòng
      - Online Retail: {dwh_row_counts['Online_Retail_Products']:,}
      - Catalog DummyJSON: {dwh_row_counts['DummyJSON_Products']:,}
    - **Khách hàng**: {dwh_row_counts['Dim_Customer']:,}
    - **Khoảng thời gian**: 12/2010 - 12/2011
    """)
    st.markdown("---")
    st.caption("Đồ án: Hồ dữ liệu hiện đại và phân tích bán lẻ")

region_type = {
    "Tất cả khu vực": None,
    "Trong nước (Vương quốc Anh)": "Domestic",
    "Quốc tế": "International",
}[selected_region]
segment_customer_ids = None
if selected_segment != "Tất cả":
    segment_customer_ids = tuple(sorted(
        int(customer_id)
        for customer_id in df_rfm.loc[
            df_rfm["Segment"] == selected_segment_value, "CustomerID"
        ].dropna()
    ))

df_monthly = load_kpi_and_monthly(region_type, segment_customer_ids)
df_country = load_country_data(region_type, segment_customer_ids)
df_products = load_product_data(region_type, segment_customer_ids)
df_category = load_category_sales(region_type, segment_customer_ids)
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
st.markdown('<div class="main-title">Bảng điều khiển phân tích bán lẻ</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Kho dữ liệu đa chiều, hợp nhất hai nguồn sản phẩm rồi phân tích doanh thu, khách hàng và gợi ý mua kèm</div>', unsafe_allow_html=True)

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
        <div class="metric-label">Doanh thu theo bộ lọc</div>
        <div class="metric-value">£{total_revenue:,.2f}</div>
        <div class="metric-delta" style="color: #10B981;">▲ Tổng doanh thu giao dịch phù hợp bộ lọc</div>
    </div>
    """, unsafe_allow_html=True)

with kpi2:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Số đơn hàng theo bộ lọc</div>
        <div class="metric-value">{total_orders:,}</div>
        <div class="metric-delta" style="color: #3B82F6;">● {total_units:,} sản phẩm bán ra</div>
    </div>
    """, unsafe_allow_html=True)

with kpi3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Giá trị đơn trung bình</div>
        <div class="metric-value">£{avg_aov:,.2f}</div>
        <div class="metric-delta" style="color: #6366F1;">● Đặc thù khách buôn & quà tặng</div>
    </div>
    """, unsafe_allow_html=True)

with kpi4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">Khách định danh trong phân tích</div>
        <div class="metric-value">{len(df_rfm_analysis):,}</div>
        <div class="metric-delta" style="color: #F59E0B;">★ {repeat_customer_pct:.2f}% khách quay lại mua</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ------------------------------------------------------------------------------
# 5. CÁC TABS PHÂN TÍCH CHUYÊN SÂU
# ------------------------------------------------------------------------------
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📈 Doanh thu và thời gian",
    "🌍 Thị trường và sản phẩm",
    "👥 Phân khúc khách hàng",
    "🧺 Gợi ý mua kèm",
    "🏗️ Mô hình kho dữ liệu",
    "🔗 Phân tích sản phẩm hợp nhất",
])

active_filters = []
if selected_region != "Tất cả khu vực":
    active_filters.append(selected_region)
if selected_segment != "Tất cả":
    active_filters.append(selected_segment)
st.caption(
    "Phạm vi đang xem: " + (" • ".join(active_filters) if active_filters else "Toàn bộ dữ liệu")
    + ". Luật Apriori và nhãn K-Means là kết quả đã tính trước; bộ lọc không chạy lại mô hình."
)
if df_monthly.empty:
    st.warning("Không có giao dịch phù hợp với bộ lọc hiện tại.")

# ==============================================================================
# TAB 1: XU HƯỚNG DOANH THU & THỜI GIAN
# ==============================================================================
with tab1:
    st.subheader("1. Xu hướng doanh thu theo tháng và tăng trưởng so với tháng trước")
    
    col_t1, col_t2 = st.columns([7, 3])
    
    with col_t1:
        fig_revenue = go.Figure()
        fig_revenue.add_trace(go.Bar(
            x=df_monthly['YearMonth'],
            y=df_monthly['MonthlyRevenue'],
            name='Doanh thu (bảng Anh)',
            marker_color='#3B82F6',
            opacity=0.85
        ))
        fig_revenue.add_trace(go.Scatter(
            x=df_monthly['YearMonth'],
            y=df_monthly['TotalOrders'] * 500,  # Scaled for secondary view
            name='Đơn hàng (đã quy đổi để so sánh)',
            line=dict(color='#F59E0B', width=3),
            mode='lines+markers'
        ))
        fig_revenue.update_layout(
            title="Doanh thu hàng tháng và quy mô đơn hàng (12/2010 - 12/2011)",
            xaxis_title="Tháng",
            yaxis_title="Doanh thu (bảng Anh)",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            margin=dict(l=20, r=20, t=50, b=20),
            height=400
        )
        st.plotly_chart(fig_revenue, width="stretch")

    with col_t2:
        st.markdown("##### Tốc độ tăng trưởng so với tháng trước (%)")
        df_display_mom = (
            df_monthly[['YearMonth', 'MonthlyRevenue', 'MoM_Growth_Pct']]
            .dropna()
            .rename(columns={
                "YearMonth": "Tháng",
                "MonthlyRevenue": "Doanh thu",
                "MoM_Growth_Pct": "Tăng trưởng so với tháng trước (%)",
            })
        )
        st.dataframe(
            df_display_mom.style.format({
                'Doanh thu': '£{:,.2f}',
                'Tăng trưởng so với tháng trước (%)': '{:+.2f}%'
            }),
            height=360,
            width="stretch"
        )

    st.markdown("---")
    st.subheader("2. Khung giờ mua sắm vàng trong ngày")
    
    col_h1, col_h2 = st.columns([7, 3])
    with col_h1:
        fig_hour = px.area(
            df_hourly,
            x='Hour',
            y='Orders',
            title="Phân bố số hóa đơn theo khung giờ trong ngày (0h - 23h)",
            labels={'Hour': 'Khung giờ', 'Orders': 'Số hóa đơn'},
            color_discrete_sequence=['#0D9488']
        )
        fig_hour.add_vline(x=12, line_width=2, line_dash="dash", line_color="#EF4444", annotation_text="Đỉnh: 12h Trưa")
        fig_hour.update_layout(height=350, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_hour, width="stretch")
        
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
        **Chiến lược kinh doanh phù hợp:**
        - **Khung giờ vàng**: Từ **10:00 đến 15:00** chiếm **{peak_share:.1f}%** số đơn trong phạm vi đang lọc.
        - **Giờ cao điểm**: **{peak_hour_label}** với **{peak_hour_orders:,}** đơn hàng.
        - **Đề xuất**: Cân nhắc tập trung quảng cáo và email trước khung giờ cao điểm của nhóm khách/thị trường đang xem.
        """)

# ==============================================================================
# TAB 2: ĐỊA LÝ & SẢN PHẨM CHỦ LỰC
# ==============================================================================
with tab2:
    st.subheader("1. Cơ cấu thị trường địa lý theo bộ lọc")
    col_g1, col_g2 = st.columns([6, 4])
    
    with col_g1:
        # Top 10 quốc gia
        top10_countries = df_country.head(10).copy()
        fig_country = px.bar(
            top10_countries,
            x='Revenue',
            y='Country',
            orientation='h',
            title="Top 10 quốc gia đóng góp doanh thu cao nhất theo bộ lọc",
            labels={'Revenue': 'Doanh thu (bảng Anh)', 'Country': 'Quốc gia'},
            color='Revenue',
            color_continuous_scale='Blues'
        )
        fig_country.update_layout(yaxis=dict(autorange="reversed"), height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_country, width="stretch")
        
    with col_g2:
        # Tỷ lệ UK vs Quốc tế
        domestic_rev = df_country[df_country['RegionType'] == 'Domestic']['Revenue'].sum()
        intl_rev = df_country[df_country['RegionType'] == 'International']['Revenue'].sum()
        df_region = pd.DataFrame({
            'Vùng': ['Vương quốc Anh', 'Thị trường quốc tế'],
            'Doanh thu': [domestic_rev, intl_rev]
        })
        fig_region = px.pie(
            df_region,
            names='Vùng',
            values='Doanh thu',
            title="Tỷ trọng thị trường: Vương quốc Anh và quốc tế",
            hole=0.45,
            color_discrete_sequence=['#1E3A8A', '#0D9488']
        )
        fig_region.update_layout(height=380, margin=dict(l=20, r=20, t=40, b=20))
        st.plotly_chart(fig_region, width="stretch")

    st.markdown("---")
    st.subheader("2. Doanh thu theo danh mục hợp nhất")
    st.caption(
        "Danh mục dùng chung cho hai nguồn: sản phẩm DummyJSON giữ danh mục catalog; "
        "sản phẩm bán lẻ được gán danh mục bằng luật từ khóa, rồi mới tính doanh thu."
    )
    if df_category.empty:
        st.info("Không có dữ liệu danh mục cho bộ lọc hiện tại.")
    else:
        fig_category = px.bar(
            df_category,
            x="Revenue",
            y="Category",
            orientation="h",
            title="Doanh thu giao dịch theo danh mục sản phẩm hợp nhất",
            labels={"Revenue": "Doanh thu (bảng Anh)", "Category": "Danh mục"},
            color="Revenue",
            color_continuous_scale="Teal",
        )
        fig_category.update_layout(
            yaxis=dict(autorange="reversed"),
            height=380,
            margin=dict(l=20, r=20, t=40, b=20),
        )
        st.plotly_chart(fig_category, width="stretch")
        st.dataframe(
            df_category.rename(columns={
                "Category": "Danh mục",
                "CategorySource": "Cách gán danh mục",
                "Products": "Số sản phẩm có bán",
                "Orders": "Số hóa đơn",
                "UnitsSold": "Số lượng bán",
                "Revenue": "Doanh thu (bảng Anh)",
            }),
            width="stretch",
            hide_index=True,
        )

    st.markdown("---")
    st.subheader("3. Top sản phẩm chủ lực")
    
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        st.markdown("##### Top 10 mặt hàng bán chạy nhất theo số lượng")
        top_qty = df_products.sort_values(by='TotalQty', ascending=False).head(10)
        fig_top_qty = px.bar(
            top_qty,
            x='TotalQty',
            y='Description',
            orientation='h',
            color='TotalQty',
            color_continuous_scale='Viridis'
        )
        fig_top_qty.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_qty, width="stretch")
        
    with col_p2:
        st.markdown("##### Top 10 mặt hàng đem lại doanh thu cao nhất")
        top_rev = df_products.sort_values(by='TotalRevenue', ascending=False).head(10)
        fig_top_rev = px.bar(
            top_rev,
            x='TotalRevenue',
            y='Description',
            orientation='h',
            color='TotalRevenue',
            color_continuous_scale='Cividis'
        )
        fig_top_rev.update_layout(yaxis=dict(autorange="reversed"), height=350, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig_top_rev, width="stretch")

# ==============================================================================
# TAB 3: PHÂN KHÚC KHÁCH HÀNG (RFM & K-MEANS)
# ==============================================================================
with tab3:
    st.subheader("1. Chân dung và phân khúc khách hàng theo mô hình RFM")
    st.caption("RFM và biểu đồ khách hàng được giới hạn theo bộ lọc. Nhãn K-Means vẫn là nhãn đã tính trên toàn bộ tập khách hàng.")
    
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
                title="Quy mô doanh thu và số khách theo từng phân khúc RFM"
            )
            fig_rfm_treemap.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_rfm_treemap, width="stretch")

        with col_rfm2:
            fig_segment_pie = px.pie(
                segment_counts,
                names='Segment',
                values='Khách_Hàng',
                title="Cơ cấu tỷ lệ khách hàng (%)",
                hole=0.4
            )
            fig_segment_pie.update_layout(height=400, margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig_segment_pie, width="stretch")

        st.markdown("---")
        cluster_count = df_rfm['KMeans_Cluster'].nunique()
        st.subheader(f"2. Đối chiếu thuật toán gom cụm K-Means (k = {cluster_count} cụm)")
        
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
                title="Phân cụm khách hàng K-Means (trục Y: log giá trị chi tiêu, kích thước: tần suất mua)",
                color_discrete_sequence=['#3B82F6', '#10B981', '#F59E0B', '#EF4444']
            )
            fig_scatter.update_layout(height=420, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig_scatter, width="stretch")
            
        with col_km2:
            st.markdown("##### Bảng thống kê phân khúc")
            st.dataframe(
                segment_counts.style.format({
                    'Doanh_Thu': '£{:,.0f}',
                    'Recency_TB': '{:.1f} ngày',
                    'Frequency_TB': '{:.1f} đơn',
                    'Monetary_TB': '£{:,.1f}'
                }),
                height=380,
                width="stretch"
            )

        st.markdown("---")
        st.subheader("3. Danh sách khách hàng theo phân khúc đang lọc")
        champions_df = df_rfm_analysis.sort_values(by='Monetary', ascending=False)
        st.dataframe(
            champions_df[['CustomerCode', 'Country', 'Recency', 'Frequency', 'Monetary', 'KMeans_Label']].head(15).style.format({
                'Monetary': '£{:,.2f}'
            }),
            width="stretch"
        )
    else:
        st.warning("Chưa tìm thấy file `outputs/rfm_customer_segments.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# ==============================================================================
# TAB 4: GỢI Ý BÁN CHÉO (MARKET BASKET ANALYSIS)
# ==============================================================================
with tab4:
    st.subheader("1. Công cụ gợi ý bán kèm sản phẩm")
    st.write("Dựa trên thuật toán khai phá luật kết hợp Apriori từ hơn 18.000 giỏ hàng.")
    st.caption("Các luật Apriori được khai phá trước trên toàn bộ dữ liệu, không được tính lại theo bộ lọc thị trường hoặc RFM.")
    
    if not df_rules.empty:
        # Lấy danh sách các sản phẩm tiền đề (Antecedents)
        unique_antecedents = sorted(df_rules['antecedents_str'].unique().tolist())
        
        col_rec1, col_rec2 = st.columns([5, 5])
        with col_rec1:
            selected_item = st.selectbox(
                "Chọn sản phẩm khách hàng đang xem hoặc đã bỏ vào giỏ hàng:",
                options=unique_antecedents,
                index=0
            )
            
        filtered_rules = df_rules[df_rules['antecedents_str'] == selected_item].sort_values(by=['lift', 'confidence'], ascending=[False, False])
        
        with col_rec2:
            st.metric(
                label="Số lượng sản phẩm gợi ý phù hợp",
                value=f"{len(filtered_rules)} mặt hàng",
                delta=f"Hệ số tăng cao nhất: {filtered_rules['lift'].max():.2f} lần" if not filtered_rules.empty else None
            )

        if not filtered_rules.empty:
            st.markdown("##### Danh sách sản phẩm được mua kèm nhiều nhất")
            
            for idx, r in filtered_rules.head(5).iterrows():
                conf_pct = r['confidence'] * 100
                lift_val = r['lift']
                supp_pct = r['support'] * 100
                
                st.success(f"""
                **Gợi ý mua kèm**: **{r['consequents_str']}**
                - **Độ tin cậy**: **{conf_pct:.1f}%** *(Có {conf_pct:.1f}% khách hàng mua sản phẩm này khi đã mua sản phẩm đã chọn)*
                - **Hệ số tăng**: **{lift_val:.2f} lần** *(Xác suất mua cùng cao gấp {lift_val:.2f} lần so với mua ngẫu nhiên)*
                - **Độ hỗ trợ**: **{supp_pct:.2f}%** đơn hàng
                """)
        else:
            st.info("Chưa có luật kết hợp trực tiếp cho sản phẩm này trong ngưỡng lọc.")

        st.markdown("---")
        st.subheader("2. Top 15 luật kết hợp có hệ số tăng cao nhất toàn hệ thống")
        display_rules = df_rules.head(15)[['antecedents_str', 'consequents_str', 'support', 'confidence', 'lift']].copy()
        display_rules['support'] = (display_rules['support'] * 100).round(2).astype(str) + '%'
        display_rules['confidence'] = (display_rules['confidence'] * 100).round(2).astype(str) + '%'
        display_rules['lift'] = display_rules['lift'].round(2)
        display_rules.columns = ['Nếu khách mua', 'Gợi ý mua kèm', 'Độ hỗ trợ', 'Độ tin cậy', 'Hệ số tăng']
        st.dataframe(display_rules, width="stretch")
    else:
        st.warning("Chưa tìm thấy file `outputs/market_basket_rules.csv`. Hãy chạy `python scripts/05_data_mining.py` trước.")

# ==============================================================================
# TAB 5: KIẾN TRÚC KHO DỮ LIỆU (STAR SCHEMA)
# ==============================================================================
with tab5:
    st.subheader("Mô hình kho dữ liệu hình sao")
    
    col_dwh1, col_dwh2 = st.columns([6, 4])
    
    with col_dwh1:
        table_counts = {
            'Fact_Sales': dwh_row_counts['Fact_Sales'],
            'Dim_Product': dwh_row_counts['Dim_Product'],
            'Dim_Customer': dwh_row_counts['Dim_Customer'],
        }
        st.markdown(f"""
        #### 🌟 Cấu trúc mô hình dữ liệu
        Mô hình gồm **1 bảng giao dịch** ở trung tâm và **4 bảng chiều**:
        - **`Fact_Sales`** *({table_counts['Fact_Sales']:,} dòng)*: số lượng, đơn giá, doanh thu và khóa thời gian/khách hàng/sản phẩm/địa lý.
        - **`Dim_Date`** *(374 dòng)*: ngày, tháng, quý, năm và ngày trong tuần.
        - **`Dim_Customer`** *({table_counts['Dim_Customer']:,} dòng)*: mã và quốc gia khách hàng.
        - **`Dim_Product`** *({table_counts['Dim_Product']:,} dòng)*: chiều sản phẩm hợp nhất từ Online Retail và DummyJSON.
        - **`Dim_Location`** *(38 dòng)*: quốc gia và vùng thị trường.

        Hai nguồn được gộp vào `Dim_Product` trước khi phân tích. Sản phẩm DummyJSON giữ
        danh mục catalog; sản phẩm bán lẻ được gán danh mục dùng chung. Chỉ sản phẩm có
        giao dịch Online Retail mới có doanh thu; sản phẩm chỉ có trong catalog không
        được gán hóa đơn giả.
        """)
        
    with col_dwh2:
        st.markdown("#### Thống kê bảng kho dữ liệu")
        tables = [
            ('dim_date', 'Dim_Date'), ('dim_location', 'Dim_Location'),
            ('dim_customer', 'Dim_Customer'), ('dim_product', 'Dim_Product'),
            ('fact_sales', 'Fact_Sales')
        ]
        table_labels = {
            "dim_date": "Chiều thời gian",
            "dim_location": "Chiều địa lý",
            "dim_customer": "Chiều khách hàng",
            "dim_product": "Chiều sản phẩm hợp nhất",
            "fact_sales": "Giao dịch bán hàng",
        }
        stats = []
        with get_engine().connect() as conn:
            for table_name, _ in tables:
                cnt = conn.execute(text(f"SELECT COUNT(*) FROM {table_name}")).fetchone()[0]
                stats.append({'Bảng': table_labels[table_name], 'Số bản ghi': f"{cnt:,}"})
        st.table(pd.DataFrame(stats))

    st.markdown("---")
    st.subheader("Kịch bản tạo lược đồ và khóa liên kết")
    ddl_path = os.path.join(BASE_DIR, "database", "02_schema_ddl.sql")
    if os.path.exists(ddl_path):
        with open(ddl_path, 'r', encoding='utf-8') as f:
            st.code(f.read()[:1500] + "\n\n-- [Xem chi tiết toàn bộ trong file database/02_schema_ddl.sql] --", language='sql')

# ==============================================================================
# TAB 6: PHÂN TÍCH SẢN PHẨM HỢP NHẤT
# ==============================================================================
with tab6:
    st.subheader("Phân tích sau khi gộp hai nguồn sản phẩm")
    st.markdown(
        "Giao dịch Online Retail và catalog DummyJSON được đưa vào cùng chiều `Dim_Product`, "
        "gán danh mục dùng chung, rồi mới phân tích. Doanh thu chỉ lấy từ hóa đơn bán lẻ. "
        "Sản phẩm chỉ có trong catalog được đối chiếu cơ cấu danh mục, không bị gán hóa đơn giả."
    )

    products = load_unified_products()
    matched_products = products[products["SourceSystem"] == "Online Retail + DummyJSON"]
    retail_count = int(products["StockCode"].notna().sum())
    api_count = int(products["APIProductID"].notna().sum())
    matched_count = len(matched_products)

    metric1, metric2, metric3, metric4 = st.columns(4)
    metric1.metric("Tổng sản phẩm hợp nhất", f"{len(products):,}")
    metric2.metric("Có mã hàng bán lẻ", f"{retail_count:,}")
    metric3.metric("Có bản ghi catalog", f"{api_count:,}")
    metric4.metric("Khớp khóa tin cậy", f"{matched_count:,}")

    if matched_count == 0:
        st.info(
            "Hai nguồn không dùng chung mã hàng, nên chưa có bản ghi khớp SKU hoặc tên "
            "chính xác. Phân tích dưới đây vẫn chạy trên chiều hợp nhất: doanh thu theo "
            "danh mục dùng chung và đối chiếu cơ cấu catalog với mặt hàng đang bán."
        )

    st.markdown("#### Phân bố sản phẩm theo nguồn")
    source_labels = {
        "Online Retail": "Chỉ bán lẻ",
        "DummyJSON": "Chỉ catalog",
        "Online Retail + DummyJSON": "Đã khớp hai nguồn",
    }
    source_summary = (
        products.groupby("SourceSystem", as_index=False)
        .size()
        .rename(columns={"SourceSystem": "Nguồn", "size": "Số sản phẩm"})
    )
    source_summary["Nguồn"] = source_summary["Nguồn"].map(source_labels)
    st.plotly_chart(
        px.bar(
            source_summary,
            x="Nguồn",
            y="Số sản phẩm",
            color="Nguồn",
            title="Số sản phẩm trong chiều dữ liệu hợp nhất",
            text="Số sản phẩm",
        ),
        width="stretch",
    )

    st.markdown("#### Đối chiếu danh mục: hàng đang bán và catalog")
    category_options = ["Tất cả"] + sorted(products["Category"].dropna().unique().tolist())
    selected_category = st.selectbox("Lọc theo danh mục hợp nhất", category_options)
    scoped_products = products
    scoped_sales = df_category.copy()
    if selected_category != "Tất cả":
        scoped_products = products[products["Category"] == selected_category]
        scoped_sales = df_category[df_category["Category"] == selected_category]

    catalog_in_scope = scoped_products[scoped_products["APIProductID"].notna()]
    sold_in_scope = scoped_products[scoped_products["TotalRevenue"].fillna(0) > 0]
    compare_metrics = st.columns(4)
    compare_metrics[0].metric("Sản phẩm trong danh mục", f"{len(scoped_products):,}")
    compare_metrics[1].metric("Có doanh thu bán lẻ", f"{len(sold_in_scope):,}")
    compare_metrics[2].metric("Có trong catalog", f"{len(catalog_in_scope):,}")
    if not scoped_sales.empty:
        compare_metrics[3].metric(
            "Doanh thu danh mục",
            f"£{scoped_sales['Revenue'].sum():,.2f}",
        )
    else:
        compare_metrics[3].metric("Doanh thu danh mục", "£0.00")

    assortment = (
        scoped_products.groupby("Category", as_index=False)
        .agg(
            Tong_san_pham=("ProductKey", "count"),
            Co_trong_catalog=("APIProductID", "count"),
            Co_doanh_thu=("TotalRevenue", lambda values: (pd.to_numeric(values, errors="coerce").fillna(0) > 0).sum()),
            Doanh_thu=("TotalRevenue", "sum"),
        )
        .sort_values("Doanh_thu", ascending=False)
    )
    assortment = assortment.rename(columns={
        "Category": "Danh mục",
        "Tong_san_pham": "Tổng sản phẩm",
        "Co_trong_catalog": "Có trong catalog",
        "Co_doanh_thu": "Có doanh thu",
        "Doanh_thu": "Doanh thu (bảng Anh)",
    })
    st.plotly_chart(
        px.bar(
            assortment.head(12),
            x="Danh mục",
            y=["Có doanh thu", "Có trong catalog"],
            barmode="group",
            title="Số mặt hàng đang bán so với số mặt hàng trong catalog theo danh mục",
            labels={"value": "Số sản phẩm", "variable": "Nhóm"},
        ),
        width="stretch",
    )
    st.dataframe(assortment, width="stretch", hide_index=True)

    if not matched_products.empty:
        st.markdown("#### Đối chiếu giá các sản phẩm đã khớp hai nguồn")
        matched_view = matched_products.rename(columns={
            "Description": "Tên sản phẩm bán lẻ",
            "CatalogTitle": "Tên catalog",
            "RetailAveragePrice": "Giá bán trung bình (bảng Anh)",
            "CatalogPrice": "Giá niêm yết catalog (đô la Mỹ)",
            "TotalRevenue": "Doanh thu (bảng Anh)",
            "MatchMethod": "Cách ghép",
        })
        st.dataframe(
            matched_view[[
                "Tên sản phẩm bán lẻ",
                "Tên catalog",
                "Giá bán trung bình (bảng Anh)",
                "Giá niêm yết catalog (đô la Mỹ)",
                "Doanh thu (bảng Anh)",
                "Cách ghép",
            ]],
            width="stretch",
            hide_index=True,
        )

    st.markdown("#### Danh sách sản phẩm hợp nhất")
    source_filter_labels = {
        "Tất cả nguồn": None,
        "Chỉ bán lẻ": "Online Retail",
        "Chỉ catalog": "DummyJSON",
        "Đã khớp hai nguồn": "Online Retail + DummyJSON",
    }
    selected_source_label = st.selectbox(
        "Lọc theo nguồn dữ liệu", list(source_filter_labels)
    )
    filtered_products = scoped_products
    selected_source = source_filter_labels[selected_source_label]
    if selected_source:
        filtered_products = filtered_products[
            filtered_products["SourceSystem"] == selected_source
        ]
    display_products = filtered_products.rename(columns={
        "ProductKey": "Mã sản phẩm hợp nhất",
        "StockCode": "Mã hàng bán lẻ",
        "Description": "Tên sản phẩm",
        "SourceSystem": "Nguồn dữ liệu",
        "APIProductID": "Mã catalog",
        "Category": "Danh mục",
        "CategorySource": "Cách gán danh mục",
        "RetailAveragePrice": "Giá bán trung bình (bảng Anh)",
        "CatalogPrice": "Giá niêm yết catalog (đô la Mỹ)",
        "CatalogRating": "Đánh giá catalog",
        "CatalogStock": "Tồn kho catalog",
        "Brand": "Thương hiệu",
        "TotalQuantity": "Số lượng đã bán",
        "TotalRevenue": "Doanh thu (bảng Anh)",
        "InvoiceCount": "Số hóa đơn",
        "MatchMethod": "Cách ghép bản ghi",
    })
    visible_columns = [
        "Mã sản phẩm hợp nhất",
        "Mã hàng bán lẻ",
        "Tên sản phẩm",
        "Nguồn dữ liệu",
        "Danh mục",
        "Cách gán danh mục",
        "Mã catalog",
        "Giá bán trung bình (bảng Anh)",
        "Giá niêm yết catalog (đô la Mỹ)",
        "Đánh giá catalog",
        "Tồn kho catalog",
        "Thương hiệu",
        "Số lượng đã bán",
        "Doanh thu (bảng Anh)",
        "Số hóa đơn",
        "Cách ghép bản ghi",
    ]
    st.dataframe(
        display_products[visible_columns],
        width="stretch",
        hide_index=True,
    )

# Footer
st.markdown("---")
st.markdown("<div style='text-align: center; color: #94A3B8; font-size: 0.9rem;'>Đồ án kho dữ liệu và phân tích bán lẻ • MinIO, PostgreSQL và Streamlit</div>", unsafe_allow_html=True)
