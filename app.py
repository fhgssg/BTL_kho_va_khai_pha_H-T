"""
HỆ THỐNG KHO DỮ LIỆU & PHÂN TÍCH KINH DOANH THƯƠNG MẠI ĐIỆN TỬ BRAZIL
Tệp: app.py | Khởi chạy: streamlit run app.py
Nguồn dữ liệu: Olist Thương mại điện tử Brazil (Kaggle)
Giao diện phong cách đơn sắc tối giản (Monochrome Minimalist Theme), loại bỏ hoàn toàn biểu tượng emoji nhiều màu.
"""

import os
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import text
from dwh_connection import get_engine

# ──────────────────────────────────────────────────────────────────────────────
# 1. CẤU HÌNH TRANG VÀ GIAO DIỆN CHUNG (ĐƠN SẮC - MONOCHROME THEME)
# ──────────────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Phân Tích Kinh Doanh Thương Mại Điện Tử Brazil",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown('<link href="https://unpkg.com/boxicons@2.1.4/css/boxicons.min.css" rel="stylesheet">', unsafe_allow_html=True)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
.main-title {
    font-size: 2.2rem; font-weight: 800;
    background: linear-gradient(90deg, #1E3A8A 0%, #3B82F6 50%, #0D9488 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.2rem;
}
.sub-title { color: #64748B; font-size: 1.05rem; margin-bottom: 1.2rem; }
div[data-testid="column"] {
    display: flex;
    flex-direction: column;
}
div[data-testid="column"] > div {
    flex: 1 1 auto;
    display: flex;
    flex-direction: column;
}
div[data-testid="column"] [data-testid="stMarkdownContainer"] {
    height: 100%;
}
.metric-card {
    background: #FFFFFF;
    border: 1px solid #E2E8F0;
    border-radius: 12px;
    padding: 1rem 1.1rem;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    height: 128px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-sizing: border-box;
}
.metric-card:hover { transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.08); }
.metric-label {
    color: #64748B;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.metric-value {
    color: #0F172A;
    font-size: 1.5rem;
    font-weight: 800;
    margin: 0.2rem 0;
    line-height: 1.2;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.metric-sub {
    color: #64748B;
    font-size: 0.75rem;
    line-height: 1.25;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
}
.stTabs [data-baseweb="tab-list"] { gap: 8px; }
.stTabs [data-baseweb="tab"] { padding: 10px 18px; border-radius: 8px; font-weight: 600; }
.filter-tag {
    display: inline-block; background: #EFF6FF; color: #1E40AF;
    border: 1px solid #BFDBFE;
    padding: 4px 10px; border-radius: 6px; font-size: 0.85rem; font-weight: 600; margin-right: 6px;
    margin-bottom: 4px;
}
.bx {
    color: #1E293B !important;
}
button[data-baseweb="tab"]:nth-child(1) p::before {
    font-family: 'boxicons' !important;
    content: "\\e9c6";
    font-size: 1.2rem;
    margin-right: 8px;
    vertical-align: -2px;
    color: #1E293B;
}
button[data-baseweb="tab"]:nth-child(2) p::before {
    font-family: 'boxicons' !important;
    content: "\\eb57";
    font-size: 1.2rem;
    margin-right: 8px;
    vertical-align: -2px;
    color: #1E293B;
}
button[data-baseweb="tab"]:nth-child(3) p::before {
    font-family: 'boxicons' !important;
    content: "\\eaff";
    font-size: 1.2rem;
    margin-right: 8px;
    vertical-align: -2px;
    color: #1E293B;
}
button[data-baseweb="tab"]:nth-child(4) p::before {
    font-family: 'boxicons' !important;
    content: "\\ea36";
    font-size: 1.2rem;
    margin-right: 8px;
    vertical-align: -2px;
    color: #1E293B;
}
button[data-baseweb="tab"]:nth-child(5) p::before {
    font-family: 'boxicons' !important;
    content: "\\ea87";
    font-size: 1.2rem;
    margin-right: 8px;
    vertical-align: -2px;
    color: #1E293B;
}
.olap-op-card {
    background: #F8FAFC;
    border: 1px solid #E2E8F0;
    border-left: 4px solid #2563EB;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
}
.olap-op-title {
    font-size: 0.88rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #1E40AF;
    margin-bottom: 0.3rem;
    display: flex;
    align-items: center;
    gap: 8px;
}
.olap-op-title i {
    font-size: 1.2rem;
    color: #1E40AF !important;
}
.olap-op-desc {
    font-size: 0.88rem;
    color: #475569;
}
div[data-testid="stSidebar"] [data-testid="stMultiSelect"]:nth-of-type(1) label p::before {
    font-family: 'boxicons' !important;
    content: "\\ea15";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
div[data-testid="stSidebar"] [data-testid="stMultiSelect"]:nth-of-type(2) label p::before {
    font-family: 'boxicons' !important;
    content: "\\eb58";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
div[data-testid="stSidebar"] [data-testid="stMultiSelect"]:nth-of-type(3) label p::before {
    font-family: 'boxicons' !important;
    content: "\\ea87";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
div[data-testid="stSidebar"] [data-testid="stMultiSelect"]:nth-of-type(4) label p::before {
    font-family: 'boxicons' !important;
    content: "\\ebcc";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
div[data-testid="stSidebar"] [data-testid="stRadio"] label p::before {
    font-family: 'boxicons' !important;
    content: "\\eed8";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
div[data-testid="stSidebar"] button p::before {
    font-family: 'boxicons' !important;
    content: "\\ebe0";
    font-size: 1.15rem;
    margin-right: 6px;
    color: #1E293B;
}
</style>
""", unsafe_allow_html=True)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
RFM_PATH   = os.path.join(BASE_DIR, "outputs", "rfm_customer_segments.csv")
RULES_PATH = os.path.join(BASE_DIR, "outputs", "market_basket_rules.csv")

# ──────────────────────────────────────────────────────────────────────────────
# TỪ ĐIỂN TÊN ĐẦY ĐỦ TIỂU BANG BRAZIL (KHÔNG VIẾT TẮT)
# ──────────────────────────────────────────────────────────────────────────────
DANH_SACH_TIEU_BANG = {
    "SP": "São Paulo",
    "RJ": "Rio de Janeiro",
    "MG": "Minas Gerais",
    "RS": "Rio Grande do Sul",
    "PR": "Paraná",
    "SC": "Santa Catarina",
    "BA": "Bahia",
    "DF": "Quận liên bang Brasília",
    "GO": "Goiás",
    "ES": "Espírito Santo",
    "PE": "Pernambuco",
    "CE": "Ceará",
    "PA": "Pará",
    "MT": "Mato Grosso",
    "MS": "Mato Grosso do Sul",
    "MA": "Maranhão",
    "AM": "Amazonas",
    "PB": "Paraíba",
    "RN": "Rio Grande do Norte",
    "AL": "Alagoas",
    "SE": "Sergipe",
    "PI": "Piauí",
    "RO": "Rondônia",
    "TO": "Tocantins",
    "AC": "Acre",
    "AP": "Amapá",
    "RR": "Roraima"
}

DANH_SACH_VUNG = {
    "Southeast": "Đông Nam",
    "South": "Nam",
    "Northeast": "Đông Bắc",
    "Midwest": "Trung Tây",
    "North": "Bắc",
}

# ──────────────────────────────────────────────────────────────────────────────
# TỪ ĐIỂN DANH MỤC SẢN PHẨM TIẾNG VIỆT HOÀN TOÀN
# ──────────────────────────────────────────────────────────────────────────────
DANH_MUC_TIENG_VIET = {
    "agro_industry_and_commerce": "Nông nghiệp, Công nghiệp & Thương mại",
    "air_conditioning": "Máy điều hòa nhiệt độ",
    "art": "Hội họa & Mỹ thuật",
    "arts_and_craftmanship": "Thủ công mỹ nghệ",
    "audio": "Thiết bị âm thanh",
    "auto": "Phụ tùng & Phụ kiện ô tô",
    "baby": "Đồ dùng cho mẹ và bé",
    "bed_bath_table": "Chăn ga gối đệm & Bàn phòng tắm",
    "books_general_interest": "Sách thường thức & Đời sống",
    "books_imported": "Sách ngoại văn nhập khẩu",
    "books_technical": "Sách chuyên ngành & Kỹ thuật",
    "cds_dvds_musicals": "Đĩa nhạc & Video ca nhạc",
    "christmas_supplies": "Đồ trang trí Giáng sinh",
    "cine_photo": "Máy ảnh & Thiết bị quay phim",
    "computers": "Máy vi tính để bàn",
    "computers_accessories": "Linh kiện & Phụ kiện máy tính",
    "consoles_games": "Máy chơi game & Trò chơi điện tử",
    "construction_tools_construction": "Dụng cụ xây dựng chuyên dụng",
    "construction_tools_lights": "Hệ thống chiếu sáng công trình",
    "construction_tools_safety": "Đồ bảo hộ lao động & An toàn",
    "cool_stuff": "Sản phẩm công nghệ độc đáo",
    "costruction_tools_garden": "Dụng cụ làm vườn",
    "costruction_tools_tools": "Dụng cụ sửa chữa cầm tay",
    "diapers_and_hygiene": "Tã bỉm & Vệ sinh trẻ em",
    "drinks": "Đồ uống & Nước giải khát",
    "dvds_blu_ray": "Đĩa phim DVD & Blu-ray",
    "electronics": "Thiết bị điện tử gia dụng",
    "fashio_female_clothing": "Thời trang nữ",
    "fashion_bags_accessories": "Túi xách & Phụ kiện thời trang",
    "fashion_childrens_clothes": "Thời trang trẻ em",
    "fashion_male_clothing": "Thời trang nam",
    "fashion_shoes": "Giày dép thời trang",
    "fashion_sport": "Thời trang thể thao",
    "fashion_underwear_beach": "Đồ lót & Đồ bơi",
    "fixed_telephony": "Điện thoại cố định",
    "flowers": "Hoa tươi & Cây cảnh",
    "food": "Thực phẩm đóng gói",
    "food_drink": "Thực phẩm & Đồ uống tổng hợp",
    "furniture_bedroom": "Nội thất phòng ngủ",
    "furniture_decor": "Nội thất & Trang trí nhà cửa",
    "furniture_living_room": "Nội thất phòng khách",
    "furniture_mattress_and_upholstery": "Đệm nệm & Ghế bọc nệm",
    "garden_tools": "Dụng cụ chăm sóc sân vườn",
    "health_beauty": "Sức khỏe & Chăm sóc sắc đẹp",
    "home_appliances": "Điện máy & Thiết bị nhà bếp",
    "home_appliances_2": "Điện gia dụng cao cấp",
    "home_comfort_2": "Tiện nghi gia đình nâng cao",
    "home_confort": "Tiện nghi & Đồ dùng êm ái trong nhà",
    "home_construction": "Vật liệu xây dựng nhà ở",
    "housewares": "Đồ gia dụng nhà bếp & Đồ dùng gia đình",
    "industry_commerce_and_business": "Thiết bị kinh doanh & Công nghiệp",
    "kitchen_dining_laundry_garden_furniture": "Bàn ghế ăn, Giặt là & Ngoài trời",
    "la_cuisine": "Dụng cụ nấu ăn cao cấp",
    "luggage_accessories": "Vali, Balo & Phụ kiện du lịch",
    "market_place": "Mặt hàng tổng hợp đa năng",
    "music": "Nhạc phẩm & Phụ kiện âm nhạc",
    "musical_instruments": "Nhạc cụ biểu diễn",
    "office_furniture": "Bàn ghế & Nội thất văn phòng",
    "party_supplies": "Phụ kiện tổ chức sự kiện & Tiệc tùng",
    "pc_gamer": "Máy tính & Phụ kiện chơi game",
    "perfumery": "Nước hoa & Dầu thơm",
    "pet_shop": "Thức ăn & Phụ kiện thú cưng",
    "portateis_cozinha_e_preparadores_de_alimentos": "Máy chế biến thực phẩm cầm tay",
    "security_and_services": "Thiết bị giám sát & Dịch vụ an ninh",
    "signaling_and_security": "Biển báo an toàn & Thiết bị an ninh",
    "small_appliances": "Thiết bị điện gia dụng cỡ nhỏ",
    "small_appliances_home_oven_and_coffee": "Lò nướng & Máy pha cà phê",
    "sports_leisure": "Thể dục, Thể thao & Dã ngoại",
    "stationery": "Văn phòng phẩm & Dụng cụ học tập",
    "tablets_printing_image": "Máy tính bảng & Thiết bị in ấn",
    "telephony": "Điện thoại di động & Phụ kiện viễn thông",
    "toys": "Đồ chơi trẻ em",
    "watches_gifts": "Đồng hồ đeo tay & Quà tặng",
    "unknown": "Danh mục chưa xác định"
}

def dich_danh_muc(ten):
    if not ten or pd.isna(ten):
        return "Danh mục chưa xác định"
    return DANH_MUC_TIENG_VIET.get(str(ten).strip().lower(), str(ten).replace("_", " ").title())

def NULL_ZERO(s):
    return s.replace(0, np.nan)


# ──────────────────────────────────────────────────────────────────────────────
# 2. XÂY DỰNG MỆNH ĐỀ ĐIỀU KIỆN LỌC (SQL)
# ──────────────────────────────────────────────────────────────────────────────
def build_where_clause(filters):
    clauses = ["1=1"]
    params = {}

    if filters.get("years"):
        placeholders = [f":yr_{i}" for i in range(len(filters["years"]))]
        clauses.append(f"d.year IN ({', '.join(placeholders)})")
        for i, val in enumerate(filters["years"]):
            params[f"yr_{i}"] = val

    if filters.get("states"):
        placeholders = [f":st_{i}" for i in range(len(filters["states"]))]
        clauses.append(f"l.customerstate IN ({', '.join(placeholders)})")
        for i, val in enumerate(filters["states"]):
            params[f"st_{i}"] = val

    if filters.get("payments"):
        placeholders = [f":pm_{i}" for i in range(len(filters["payments"]))]
        clauses.append(f"pm.paymenttype IN ({', '.join(placeholders)})")
        for i, val in enumerate(filters["payments"]):
            params[f"pm_{i}"] = val

    if filters.get("categories"):
        placeholders = [f":cat_{i}" for i in range(len(filters["categories"]))]
        clauses.append(f"COALESCE(p.categorynameen, p.categorynamept, 'unknown') IN ({', '.join(placeholders)})")
        for i, val in enumerate(filters["categories"]):
            params[f"cat_{i}"] = val

    if filters.get("delivered_only") is True:
        clauses.append("f.isdelivered = 1")
    elif filters.get("delivered_only") is False:
        clauses.append("f.isdelivered = 0")

    return " AND ".join(clauses), params


# ──────────────────────────────────────────────────────────────────────────────
# 3. TẢI DỮ LIỆU ĐỂ TẠO CÁC DANH SÁCH BỘ LỌC
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_filter_metadata():
    engine = get_engine()
    with engine.connect() as conn:
        years = [r[0] for r in conn.execute(text("SELECT DISTINCT year FROM dim_date ORDER BY year")).fetchall()]
        states = [r[0] for r in conn.execute(text("SELECT DISTINCT customerstate FROM dim_location WHERE customerstate IS NOT NULL ORDER BY customerstate")).fetchall()]
        payments = conn.execute(text("SELECT paymenttype, paymenttypevn FROM dim_payment ORDER BY paymentkey")).fetchall()
        categories = [r[0] for r in conn.execute(text("""
            SELECT DISTINCT COALESCE(categorynameen, categorynamept, 'unknown') AS cat 
            FROM dim_product 
            WHERE COALESCE(categorynameen, categorynamept, 'unknown') != 'unknown'
            ORDER BY cat
        """)).fetchall()]
    return {
        "years": years,
        "states": states,
        "payments": payments,
        "categories": categories
    }


def make_filter_key(f):
    return (
        tuple(sorted(f.get("years") or [])),
        tuple(sorted(f.get("states") or [])),
        tuple(sorted(f.get("payments") or [])),
        tuple(sorted(f.get("categories") or [])),
        f.get("delivered_only")
    )


# ──────────────────────────────────────────────────────────────────────────────
# 4. TRUY VẤN DỮ LIỆU TỰ ĐỘNG CẬP NHẬT THEO BỘ LỌC
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_filtered_kpi(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT
        COUNT(DISTINCT f.orderid)                        AS total_orders,
        COUNT(*)                                         AS total_items,
        COUNT(DISTINCT f.customerkey)                    AS total_customers,
        COUNT(DISTINCT f.productkey)                     AS total_products,
        ROUND(COALESCE(SUM(f.totalrevenue), 0)::numeric, 2)       AS total_revenue,
        ROUND(COALESCE(AVG(f.totalpaymentvalue), 0)::numeric, 2)  AS aov,
        ROUND(COALESCE(SUM(f.isdelivered)*100.0/NULLIF(COUNT(*), 0), 0)::numeric, 1) AS delivery_rate
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    LEFT JOIN dim_payment pm ON f.paymentkey = pm.paymentkey
    WHERE {where_sql}
    """
    with engine.connect() as conn:
        row = pd.read_sql_query(text(q), conn, params=params).iloc[0]
    return row

@st.cache_data(ttl=3600)
def load_filtered_monthly(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT d.yearmonth, d.year, d.month,
           COUNT(DISTINCT f.orderid)                        AS totalorders,
           COUNT(*)                                         AS totalitems,
           ROUND(COALESCE(SUM(f.totalrevenue), 0)::numeric, 2)       AS monthlyrevenue,
           ROUND(COALESCE(AVG(f.price), 0)::numeric, 2)              AS avgprice,
           ROUND(COALESCE(SUM(f.freightvalue), 0)::numeric, 2)       AS totalfreight
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    LEFT JOIN dim_payment pm ON f.paymentkey = pm.paymentkey
    WHERE {where_sql}
    GROUP BY d.yearmonth, d.year, d.month
    ORDER BY d.year, d.month
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(q), conn, params=params)
    df.columns = ["Tháng Năm", "Năm", "Tháng", "Tổng số đơn hàng", "Tổng số sản phẩm", "Doanh thu hàng tháng", "Đơn giá trung bình", "Tổng cước vận chuyển"]
    df["Doanh thu tháng trước"] = df["Doanh thu hàng tháng"].shift(1)

    # Kiểm tra tính liên tục theo tháng: chỉ tính MoM khi 2 tháng thực sự liên tiếp
    months_diff = (df["Năm"] * 12 + df["Tháng"]) - (df["Năm"].shift(1) * 12 + df["Tháng"].shift(1))
    is_consecutive = months_diff == 1

    # Loại bỏ ngoại lai cực đoan trong giai đoạn thử nghiệm (doanh thu cơ sở < 1,000 BRL)
    # Tránh trường hợp 2016-12 chỉ có 10.9 BRL -> 2017-01 tăng 1,101,718% làm bẹp toàn bộ biểu đồ
    valid_base = (df["Doanh thu tháng trước"] >= 1000) & is_consecutive

    growth = ((df["Doanh thu hàng tháng"] - df["Doanh thu tháng trước"]) / NULL_ZERO(df["Doanh thu tháng trước"]) * 100).round(2)
    df["Tốc độ tăng trưởng so với tháng trước (%)"] = growth.where(valid_base, np.nan)
    return df

@st.cache_data(ttl=3600)
def load_filtered_geo(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT l.customerstate,
           COUNT(DISTINCT f.orderid)                        AS orders,
           COUNT(DISTINCT f.customerkey)                    AS customers,
           ROUND(COALESCE(SUM(f.totalrevenue), 0)::numeric, 2)       AS revenue,
           ROUND(COALESCE(SUM(f.freightvalue), 0)::numeric, 2)       AS freight,
           ROUND(COALESCE(AVG(f.price), 0)::numeric, 2)              AS avgprice,
           SUM(f.isdelivered)                               AS delivered
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    LEFT JOIN dim_payment pm ON f.paymentkey = pm.paymentkey
    WHERE {where_sql}
    GROUP BY l.customerstate
    ORDER BY revenue DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(q), conn, params=params)
    df.columns = ["Mã tiểu bang", "Số lượng đơn hàng", "Số khách hàng", "Doanh thu", "Cước vận chuyển", "Đơn giá trung bình", "Số đơn đã giao"]
    df["Tỷ lệ giao hàng thành công (%)"] = (df["Số đơn đã giao"] / df["Số lượng đơn hàng"] * 100).round(1)
    df["Tiểu bang"] = df["Mã tiểu bang"].map(DANH_SACH_TIEU_BANG).fillna(df["Mã tiểu bang"])
    return df

@st.cache_data(ttl=3600)
def load_filtered_category(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT COALESCE(p.categorynameen, p.categorynamept, 'unknown') AS raw_cat,
           COUNT(DISTINCT f.orderid)                        AS orders,
           COUNT(*)                                         AS items,
           ROUND(COALESCE(SUM(f.totalrevenue), 0)::numeric, 2)       AS revenue,
           ROUND(COALESCE(AVG(f.price), 0)::numeric, 2)              AS avgprice
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    LEFT JOIN dim_payment pm ON f.paymentkey = pm.paymentkey
    WHERE {where_sql}
    GROUP BY COALESCE(p.categorynameen, p.categorynamept, 'unknown')
    ORDER BY revenue DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(q), conn, params=params)
    df.columns = ["Mã gốc", "Số lượng đơn hàng", "Số lượng sản phẩm", "Doanh thu", "Đơn giá trung bình"]
    df["Danh mục sản phẩm"] = df["Mã gốc"].apply(dich_danh_muc)
    return df

@st.cache_data(ttl=3600)
def load_filtered_payment(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT pm.paymenttype, pm.paymenttypevn,
           COUNT(DISTINCT f.orderid)                                  AS orders,
           ROUND(COALESCE(AVG(f.paymentinstallments), 1)::numeric, 2) AS avginstall,
           ROUND(COALESCE(SUM(f.totalpaymentvalue), 0)::numeric, 2)   AS totalpay,
           ROUND(COALESCE(AVG(f.totalpaymentvalue), 0)::numeric, 2)   AS avgordervalue
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    JOIN dim_payment pm ON f.paymentkey  = pm.paymentkey
    WHERE {where_sql}
    GROUP BY pm.paymenttype, pm.paymenttypevn
    ORDER BY orders DESC
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(q), conn, params=params)
    df.columns = ["Loại gốc", "Phương thức thanh toán", "Số lượng đơn hàng", "Số đợt trả góp trung bình", "Tổng giá trị thanh toán", "Giá trị đơn hàng trung bình"]
    return df

@st.cache_data(ttl=3600)
def load_filtered_hours(filters_tuple):
    filters = {
        "years": list(filters_tuple[0]),
        "states": list(filters_tuple[1]),
        "payments": list(filters_tuple[2]),
        "categories": list(filters_tuple[3]),
        "delivered_only": filters_tuple[4]
    }
    engine = get_engine()
    where_sql, params = build_where_clause(filters)
    q = f"""
    SELECT f.purchasehour AS hour,
           COUNT(DISTINCT f.orderid)                        AS orders,
           ROUND(COALESCE(SUM(f.totalrevenue), 0)::numeric, 2)       AS revenue
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey     = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    JOIN dim_product p  ON f.productkey  = p.productkey
    LEFT JOIN dim_payment pm ON f.paymentkey = pm.paymentkey
    WHERE {where_sql}
    GROUP BY f.purchasehour
    ORDER BY f.purchasehour
    """
    with engine.connect() as conn:
        df = pd.read_sql_query(text(q), conn, params=params)
    df.columns = ["Khung giờ", "Số lượng đơn hàng", "Doanh thu"]
    return df

@st.cache_data(ttl=600)
def load_rfm():
    if os.path.exists(RFM_PATH):
        return pd.read_csv(RFM_PATH)
    return pd.DataFrame()


# ──────────────────────────────────────────────────────────────────────────────
# CÁC HÀM TẢI DỮ LIỆU OLAP ĐA CHIỀU
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def olap_rollup(level: str):
    """Roll-up: Gộp dữ liệu từ Tháng lên Quý hoặc Năm."""
    engine = get_engine()
    if level == "Năm":
        q = """
        SELECT d.year AS _sort_year,
               d.year::text AS nam,
               COUNT(DISTINCT f.orderid) AS so_don_hang,
               COUNT(*) AS tong_san_luong,
               ROUND(SUM(f.totalrevenue)::numeric, 2) AS tong_doanh_thu
        FROM fact_sales f JOIN dim_date d ON f.datekey = d.datekey
        GROUP BY d.year ORDER BY d.year
        """
    elif level == "Quý":
        q = """
        SELECT d.year AS _sort_year,
               MIN(d.month) AS _sort_month,
               d.year::text AS nam,
               d.quartername AS quy,
               COUNT(DISTINCT f.orderid) AS so_don_hang,
               COUNT(*) AS tong_san_luong,
               ROUND(SUM(f.totalrevenue)::numeric, 2) AS tong_doanh_thu
        FROM fact_sales f JOIN dim_date d ON f.datekey = d.datekey
        GROUP BY d.year, d.quartername ORDER BY d.year, MIN(d.month)
        """
    else:  # Tháng
        q = """
        SELECT d.year AS _sort_year,
               d.month AS _sort_month,
               d.yearmonth AS thang_nam,
               COUNT(DISTINCT f.orderid) AS so_don_hang,
               COUNT(*) AS tong_san_luong,
               ROUND(SUM(f.totalrevenue)::numeric, 2) AS tong_doanh_thu
        FROM fact_sales f JOIN dim_date d ON f.datekey = d.datekey
        GROUP BY d.yearmonth, d.year, d.month ORDER BY d.year, d.month
        """
    with engine.connect() as conn:
        return pd.read_sql_query(text(q), conn)


@st.cache_data(ttl=3600)
def olap_drilldown(year: int):
    """Drill-down: Từ tổng năm → chi tiết từng tháng trong năm đó."""
    engine = get_engine()
    q = """
    SELECT d.yearmonth AS thang_nam,
           d.month AS thang,
           d.quartername AS quy,
           COUNT(DISTINCT f.orderid) AS so_don_hang,
           ROUND(SUM(f.totalrevenue)::numeric, 2) AS doanh_thu,
           ROUND(AVG(f.totalpaymentvalue)::numeric, 2) AS gia_tri_don_tb
    FROM fact_sales f JOIN dim_date d ON f.datekey = d.datekey
    WHERE d.year = :yr
    GROUP BY d.yearmonth, d.month, d.quartername
    ORDER BY d.month
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(q), conn, params={"yr": year})


@st.cache_data(ttl=3600)
def olap_slice(year: int):
    """Slice: Cắt một mặt phẳng dữ liệu — doanh thu tháng theo từng vùng (năm đã chọn)."""
    engine = get_engine()
    q = """
    SELECT d.year AS _sort_year,
           d.month AS _sort_month,
           d.yearmonth AS thang_nam,
           l.region AS vung,
           COUNT(DISTINCT f.orderid) AS so_don_hang,
           ROUND(SUM(f.totalrevenue)::numeric, 2) AS doanh_thu
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    WHERE d.year = :yr
    GROUP BY d.yearmonth, d.year, d.month, l.region
    ORDER BY d.year, d.month, l.region
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(q), conn, params={"yr": year})


@st.cache_data(ttl=3600)
def olap_dice(states: tuple, year: int):
    """Dice: Cắt khối đa chiều — lọc theo vùng (bang) VÀ năm cụ thể."""
    engine = get_engine()
    if not states:
        return pd.DataFrame()
    placeholders = ", ".join([f":s{i}" for i in range(len(states))])
    params = {f"s{i}": s for i, s in enumerate(states)}
    params["yr"] = year
    q = f"""
    SELECT d.year AS _sort_year,
           d.month AS _sort_month,
           d.yearmonth AS thang_nam,
           l.customerstate AS tieu_bang,
           l.region AS vung,
           COUNT(DISTINCT f.orderid) AS so_don_hang,
           ROUND(SUM(f.totalrevenue)::numeric, 2) AS doanh_thu,
           ROUND(AVG(f.price)::numeric, 2) AS gia_tb
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    WHERE l.customerstate IN ({placeholders}) AND d.year = :yr
    GROUP BY d.yearmonth, d.year, d.month, l.customerstate, l.region
    ORDER BY d.year, d.month, l.customerstate
    """
    with engine.connect() as conn:
        return pd.read_sql_query(text(q), conn, params=params)


@st.cache_data(ttl=3600)
def olap_pivot(states: tuple, year: int = None):
    """Pivot: Xoay ma trận — các bang thành cột, tháng thành hàng."""
    engine = get_engine()
    if not states:
        return pd.DataFrame()
    placeholders = ", ".join([f":s{i}" for i in range(len(states))])
    params = {f"s{i}": s for i, s in enumerate(states)}
    year_filter = ""
    if year:
        year_filter = "AND d.year = :yr"
        params["yr"] = year
    q = f"""
    SELECT d.yearmonth AS thang_nam,
           d.year, d.month,
           l.customerstate AS tieu_bang,
           ROUND(SUM(f.totalrevenue)::numeric, 2) AS doanh_thu
    FROM fact_sales f
    JOIN dim_date d     ON f.datekey = d.datekey
    JOIN dim_location l ON f.locationkey = l.locationkey
    WHERE l.customerstate IN ({placeholders}) {year_filter}
    GROUP BY d.yearmonth, d.year, d.month, l.customerstate
    ORDER BY d.year, d.month
    """
    with engine.connect() as conn:
        df_raw = pd.read_sql_query(text(q), conn, params=params)
    if df_raw.empty:
        return pd.DataFrame()
    df_pivot = df_raw.pivot_table(
        index="thang_nam", columns="tieu_bang", values="doanh_thu", aggfunc="sum", fill_value=0
    ).reset_index()
    # Khôi phục thứ tự thời gian sau pivot (pivot_table sort theo index alphabetically)
    order_df = df_raw[["thang_nam", "year", "month"]].drop_duplicates().sort_values(["year", "month"])
    ordered_months = order_df["thang_nam"].tolist()
    df_pivot = df_pivot.set_index("thang_nam").reindex(ordered_months).reset_index()
    df_pivot.columns.name = None
    return df_pivot


@st.cache_data(ttl=600)
def load_rules():

    if os.path.exists(RULES_PATH):
        df = pd.read_csv(RULES_PATH)
        for c in ["support", "confidence", "lift"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df
    return pd.DataFrame()


def section_header(icon_class, title):
    st.markdown(f"""
    <div style="font-size: 1.25rem; font-weight: 700; color: #1E293B; margin: 1.2rem 0 0.8rem 0; display: flex; align-items: center;">
        <i class='{icon_class}' style='font-size: 1.45rem; margin-right: 8px; color: #334155;'></i>
        <span>{title}</span>
    </div>
    """, unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 5. BỘ LỌC ĐA CHIỀU (SIDEBAR - BOXICONS ĐEN TRẮNG)
# ──────────────────────────────────────────────────────────────────────────────
meta = load_filter_metadata()

with st.sidebar:
    st.markdown("<div style='font-size:1.45rem; font-weight:800; color:#1E293B; display:flex; align-items:center;'><i class='bx bx-bar-chart-square' style='font-size:1.6rem; margin-right:8px; color:#1E293B;'></i>Phân Tích Bán Hàng</div>", unsafe_allow_html=True)
    st.markdown("<div style='color:#64748B; font-size:0.9rem; font-weight:600; margin-bottom:0.8rem;'>Hệ thống Lọc Đa Chiều</div>", unsafe_allow_html=True)
    st.divider()

    # Bộ lọc 1: Năm đặt hàng
    sel_years = st.multiselect(
        "Năm đặt hàng",
        options=meta["years"],
        default=meta["years"],
        help="Chọn một hoặc nhiều năm để phân tích xu hướng"
    )

    # Bộ lọc 2: Tiểu bang Brazil (TÊN ĐẦY ĐỦ 100%, KHÔNG KÈM MÃ VIẾT TẮT)
    state_display_map = {code: DANH_SACH_TIEU_BANG.get(code, code) for code in meta["states"]}
    state_options = sorted(list(state_display_map.keys()), key=lambda c: state_display_map[c])
    
    sel_states = st.multiselect(
        "Tiểu bang",
        options=state_options,
        format_func=lambda x: state_display_map.get(x, x),
        default=[],
        placeholder="Tất cả các tiểu bang...",
        help="Chọn một hoặc nhiều tiểu bang"
    )

    # Bộ lọc 3: Phương thức thanh toán
    pay_dict = {row[1]: row[0] for row in meta["payments"]}
    sel_pay_names = st.multiselect(
        "Phương thức thanh toán",
        options=list(pay_dict.keys()),
        default=[],
        placeholder="Tất cả hình thức...",
        help="Thẻ tín dụng, Hóa đơn tiền mặt, Phiếu mua hàng, Thẻ ghi nợ"
    )
    sel_payments = [pay_dict[name] for name in sel_pay_names]

    # Bộ lọc 4: Danh mục sản phẩm (TIẾNG VIỆT HOÀN TOÀN)
    category_display_map = {cat: dich_danh_muc(cat) for cat in meta["categories"]}
    cat_options = sorted(list(category_display_map.keys()), key=lambda c: category_display_map[c])

    sel_categories = st.multiselect(
        "Danh mục sản phẩm",
        options=cat_options,
        format_func=lambda x: category_display_map.get(x, x),
        default=[],
        placeholder="Tất cả danh mục sản phẩm...",
        help="Lọc theo các danh mục như Sức khỏe & Sắc đẹp, Chăn ga gối đệm..."
    )

    # Bộ lọc 5: Trạng thái giao hàng
    del_option = st.radio(
        "Trạng thái giao hàng",
        options=["Tất cả trạng thái", "Chỉ đơn đã giao thành công", "Đơn đang xử lý hoặc chưa giao"],
        index=0
    )
    delivered_only = True if del_option == "Chỉ đơn đã giao thành công" else (False if del_option == "Đơn đang xử lý hoặc chưa giao" else None)

    st.divider()
    if st.button("Đặt lại toàn bộ bộ lọc", use_container_width=True):
        st.rerun()

# Đóng gói bộ lọc
active_filters = {
    "years": sel_years,
    "states": sel_states,
    "payments": sel_payments,
    "categories": sel_categories,
    "delivered_only": delivered_only
}
filter_key = make_filter_key(active_filters)


# ──────────────────────────────────────────────────────────────────────────────
# 6. TIÊU ĐỀ & THANH ĐIỀU KIỆN LỌC ĐANG CHỌN
# ──────────────────────────────────────────────────────────────────────────────
st.markdown('<div class="main-title">Báo Cáo Phân Tích Kinh Doanh Thương Mại Điện Tử</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Hệ thống phân tích thông minh dựa trên dữ liệu giao dịch bán lẻ trực tuyến tại Brazil</div>', unsafe_allow_html=True)

tags = []
if active_filters["years"] and active_filters["years"] != meta["years"]:
    tags.append(f"<span class='filter-tag'><i class='bx bx-calendar'></i> Năm: {', '.join(map(str, active_filters['years']))}</span>")
if active_filters["states"]:
    state_names_full = [DANH_SACH_TIEU_BANG.get(s, s) for s in active_filters["states"]]
    tags.append(f"<span class='filter-tag'><i class='bx bx-map-pin'></i> Tiểu bang: {', '.join(state_names_full)}</span>")
if sel_pay_names:
    tags.append(f"<span class='filter-tag'><i class='bx bx-credit-card'></i> Thanh toán: {', '.join(sel_pay_names)}</span>")
if active_filters["categories"]:
    tags.append(f"<span class='filter-tag'><i class='bx bx-purchase-tag-alt'></i> {len(active_filters['categories'])} danh mục sản phẩm</span>")
if delivered_only is not None:
    tags.append(f"<span class='filter-tag'><i class='bx bxs-truck'></i> {'Đã giao thành công' if delivered_only else 'Chưa giao'}</span>")

if not tags:
    st.markdown("""
    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:10px 14px; color:#475569; font-size:0.9rem; margin-bottom:1.2rem; display:flex; align-items:center;">
        <i class='bx bx-info-circle' style='font-size:1.25rem; margin-right:8px; color:#334155;'></i>
        <span>Đang hiển thị toàn bộ dữ liệu từ năm 2016 đến 2018. Bạn có thể sử dụng các bộ lọc ở thanh bên trái để phân tích chuyên sâu.</span>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown("<b>Điều kiện lọc đang áp dụng:</b> " + " ".join(tags), unsafe_allow_html=True)


# ──────────────────────────────────────────────────────────────────────────────
# 7. CÁC PHÂN HỆ HIỂN THỊ (4 TABS - BOXICONS ĐEN TRẮNG)
# ──────────────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Chỉ Số Tổng Quan",
    "Phân Tích Địa Lý & Danh Mục",
    "Phân Khúc Khách Hàng",
    "Gợi Ý Bán Chéo Sản Phẩm",
    "Phân Tích OLAP Đa Chiều",
])


# ══════════════════════════════════════════════════════════════════════════════
# PHẦN 1: CHỈ SỐ TỔNG QUAN
# ══════════════════════════════════════════════════════════════════════════════
with tab1:
    section_header("bx bx-bar-chart-alt-2", "Các chỉ số hiệu suất kinh doanh chính")
    
    kpi = load_filtered_kpi(filter_key)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label"><i class='bx bx-package'></i> Đơn hàng</div>
            <div class="metric-value">{int(kpi.total_orders):,}</div>
            <div class="metric-sub">{int(kpi.total_items):,} sản phẩm</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        rev_val = float(kpi.total_revenue)
        rev_str = f"{rev_val/1e6:.2f}M BRL" if rev_val >= 1e6 else f"{rev_val:,.0f} BRL"
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label"><i class='bx bx-dollar-circle'></i> Doanh thu</div>
            <div class="metric-value">{rev_str}</div>
            <div class="metric-sub">{rev_val:,.0f} BRL</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label"><i class='bx bx-purchase-tag-alt'></i> Đơn giá TB</div>
            <div class="metric-value">{float(kpi.aov):.1f} BRL</div>
            <div class="metric-sub">Chi tiêu TB / đơn</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label"><i class='bx bx-user'></i> Khách hàng</div>
            <div class="metric-value">{int(kpi.total_customers):,}</div>
            <div class="metric-sub">{int(kpi.total_products):,} mặt hàng</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class="metric-card">
            <div class="metric-label"><i class='bx bxs-truck'></i> Giao thành công</div>
            <div class="metric-value">{float(kpi.delivery_rate):.1f}%</div>
            <div class="metric-sub">Tỷ lệ đơn đã giao</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("---")

    # 1. Doanh thu theo tháng
    df_monthly = load_filtered_monthly(filter_key)
    if not df_monthly.empty:
        col_l, col_r = st.columns([2, 1])
        with col_l:
            section_header("bx bx-line-chart", "Doanh thu bán hàng lẻ theo từng tháng")
            fig = px.bar(
                df_monthly, x="Tháng Năm", y="Doanh thu hàng tháng",
                labels={"Tháng Năm": "Tháng", "Doanh thu hàng tháng": "Doanh thu (Real Brazil)"},
                color="Doanh thu hàng tháng", color_continuous_scale="Blues",
                text=df_monthly["Doanh thu hàng tháng"].apply(lambda x: f"{x/1000:,.0f}K BRL" if x >= 1000 else f"{x:.0f} BRL")
            )
            fig.update_traces(
                textposition="outside",
                hovertemplate="Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>",
            )
            fig.update_layout(
                yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f"),
                height=380, margin=dict(l=40, r=20, t=30, b=40),
                showlegend=False,
                coloraxis_showscale=False
            )
            st.plotly_chart(fig, use_container_width=True)

        with col_r:
            section_header("bx bx-time-five", "Khung giờ đặt hàng trong ngày")
            df_hours = load_filtered_hours(filter_key)
            fig_h = px.bar(
                df_hours, x="Khung giờ", y="Số lượng đơn hàng",
                color="Số lượng đơn hàng", color_continuous_scale="Blues",
                labels={"Khung giờ": "Giờ đặt hàng (0 - 23h)", "Số lượng đơn hàng": "Số lượng đơn hàng"},
            )
            fig_h.update_layout(height=380, showlegend=False, margin=dict(l=20,r=20,t=30,b=20))
            st.plotly_chart(fig_h, use_container_width=True)
    else:
        st.warning("Không có dữ liệu phù hợp với điều kiện lọc hiện tại.")

    # 2. Thanh toán
    section_header("bx bx-credit-card", "Phân tích phương thức thanh toán và số đợt trả góp")
    df_pay = load_filtered_payment(filter_key)
    if not df_pay.empty:
        col_p1, col_p2 = st.columns(2)
        with col_p1:
            fig_pie = px.pie(
                df_pay, values="Số lượng đơn hàng", names="Phương thức thanh toán",
                hole=0.45, title="Tỷ trọng số lượng đơn hàng theo phương thức thanh toán",
                color_discrete_sequence=["#2563EB", "#3B82F6", "#10B981", "#F59E0B", "#8B5CF6"],
            )
            fig_pie.update_layout(height=340)
            st.plotly_chart(fig_pie, use_container_width=True)
        with col_p2:
            fig_install = px.bar(
                df_pay, x="Phương thức thanh toán", y="Số đợt trả góp trung bình",
                title="Số đợt trả góp trung bình theo từng hình thức",
                color="Số đợt trả góp trung bình", color_continuous_scale="Teal",
                labels={"Phương thức thanh toán": "Hình thức thanh toán", "Số đợt trả góp trung bình": "Đợt trả góp trung bình"},
                text=df_pay["Số đợt trả góp trung bình"].apply(lambda x: f"{x:.1f} đợt")
            )
            fig_install.update_traces(textposition="outside")
            fig_install.update_layout(height=340, showlegend=False)
            st.plotly_chart(fig_install, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PHẦN 2: ĐỊA LÝ & DANH MỤC
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    section_header("bx bx-map-alt", "Phân tích doanh thu và hiệu suất theo tiểu bang")

    df_geo = load_filtered_geo(filter_key)
    if not df_geo.empty:
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            top_n = st.slider("Số lượng tiểu bang muốn xem:", 5, min(27, len(df_geo)), min(10, len(df_geo)))
            fig_geo = px.bar(
                df_geo.head(top_n), x="Doanh thu", y="Tiểu bang",
                orientation="h", title=f"Top {top_n} tiểu bang có doanh thu cao nhất",
                color="Doanh thu", color_continuous_scale="Blues",
                labels={"Doanh thu":"Doanh thu (Real Brazil)", "Tiểu bang":"Tiểu bang"},
                text=df_geo.head(top_n)["Doanh thu"].apply(lambda x: f"{x/1000:,.0f}K BRL"),
            )
            fig_geo.update_traces(textposition="outside")
            fig_geo.update_layout(height=480, showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_geo, use_container_width=True)

        with col_g2:
            fig_del = px.bar(
                df_geo.sort_values("Tỷ lệ giao hàng thành công (%)", ascending=False).head(top_n),
                x="Tỷ lệ giao hàng thành công (%)", y="Tiểu bang",
                orientation="h",
                title=f"Tỷ lệ giao hàng thành công theo tiểu bang (%)",
                color="Tỷ lệ giao hàng thành công (%)", color_continuous_scale="Teal",
                labels={"Tỷ lệ giao hàng thành công (%)":"Tỷ lệ giao thành công (%)", "Tiểu bang":"Tiểu bang"},
                text=df_geo.sort_values("Tỷ lệ giao hàng thành công (%)", ascending=False).head(top_n)["Tỷ lệ giao hàng thành công (%)"].apply(lambda x: f"{x:.1f}%")
            )
            fig_del.update_traces(textposition="outside")
            fig_del.update_layout(height=480, showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_del, use_container_width=True)

    st.divider()
    section_header("bx bx-purchase-tag-alt", "Phân tích hiệu suất theo danh mục sản phẩm")
    df_cat = load_filtered_category(filter_key)
    if not df_cat.empty:
        top_cat = st.slider("Số danh mục sản phẩm muốn xem:", 5, min(30, len(df_cat)), min(15, len(df_cat)))
        col_c1, col_c2 = st.columns(2)
        with col_c1:
            fig_cat_rev = px.bar(
                df_cat.head(top_cat), x="Doanh thu", y="Danh mục sản phẩm",
                orientation="h", title=f"Top {top_cat} ngành hàng đóng góp doanh thu lớn nhất",
                color="Doanh thu", color_continuous_scale="Teal",
                labels={"Doanh thu":"Doanh thu (Real Brazil)", "Danh mục sản phẩm":"Danh mục sản phẩm"},
                text=df_cat.head(top_cat)["Doanh thu"].apply(lambda x: f"{x/1000:,.0f}K BRL"),
            )
            fig_cat_rev.update_traces(textposition="outside")
            fig_cat_rev.update_layout(height=480, showlegend=False, yaxis=dict(autorange="reversed"))
            st.plotly_chart(fig_cat_rev, use_container_width=True)
        with col_c2:
            df_cat_subset = df_cat.head(top_cat * 2).copy()

            fig_cat_aov = px.scatter(
                df_cat_subset, x="Số lượng đơn hàng", y="Đơn giá trung bình",
                size="Doanh thu", color="Doanh thu",
                hover_name="Danh mục sản phẩm",
                title="Tương quan giữa số lượng đơn hàng và đơn giá bình quân",
                labels={"Số lượng đơn hàng": "Số lượng đơn hàng", "Đơn giá trung bình": "Đơn giá trung bình (Real Brazil)"},
                color_continuous_scale="Blues",
            )
            fig_cat_aov.update_traces(
                hovertemplate="<b>%{hovertext}</b><br><br>Số lượng đơn hàng: <b>%{x:,.0f} đơn</b><br>Đơn giá bình quân: <b>%{y:,.2f} BRL</b><br>Tổng doanh thu: <b>%{marker.size:,.2f} BRL</b><extra></extra>"
            )
            fig_cat_aov.update_layout(
                height=480, 
                showlegend=False,
                margin=dict(l=30, r=30, t=40, b=30),
                xaxis=dict(tickformat=","),
                yaxis=dict(ticksuffix=" BRL")
            )
            st.plotly_chart(fig_cat_aov, use_container_width=True)
            st.caption("ℹ️ *Đã loại bỏ chữ trong biểu đồ để tránh đè chữ. Bạn chỉ cần rê chuột vào từng điểm bong bóng để xem đầy đủ tên danh mục và thông số.*")


# ══════════════════════════════════════════════════════════════════════════════
# PHẦN 3: PHÂN KHÚC KHÁCH HÀNG (RFM & K-MEANS)
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    section_header("bx bx-group", "Phân khúc giá trị khách hàng theo mô hình RFM và Học máy K-Means")

    df_rfm = load_rfm()
    if df_rfm.empty:
        st.warning("Chưa có dữ liệu phân khúc khách hàng.")
    else:
        # Nếu có chọn tiểu bang ở bộ lọc, đồng bộ sang tập khách hàng
        if active_filters["states"]:
            df_rfm_view = df_rfm[df_rfm["CustomerState"].isin(active_filters["states"])]
        else:
            df_rfm_view = df_rfm

        total_cust = len(df_rfm_view)
        champions  = (df_rfm_view["Segment"] == "Champions (VIP)").sum() if "Segment" in df_rfm_view.columns else 0
        avg_rec    = df_rfm_view["Recency"].mean() if "Recency" in df_rfm_view.columns else 0
        avg_mon    = df_rfm_view["Monetary"].mean() if "Monetary" in df_rfm_view.columns else 0

        k1, k2, k3, k4 = st.columns(4)
        k1.metric("Khách hàng trong phạm vi lọc", f"{total_cust:,}")
        k2.metric("Nhóm khách hàng VIP", f"{champions:,}", f"{champions/total_cust*100:.1f}%" if total_cust else "0%")
        k3.metric("Số ngày mua gần nhất bình quân", f"{avg_rec:.0f} ngày")
        k4.metric("Chi tiêu trung bình mỗi khách", f"{avg_mon:,.0f} BRL")

        if "Segment" in df_rfm_view.columns:
            # Dịch tên phân khúc sang tiếng Việt hoàn toàn
            dich_phan_khuc = {
                "Champions (VIP)": "Khách hàng VIP hàng đầu",
                "Loyal Customers (Trung thành)": "Khách hàng trung thành",
                "New / Potential Loyalists (Mới & Tiềm năng)": "Khách mới & Tiềm năng",
                "Promising (Hứa hẹn)": "Khách hàng triển vọng",
                "At Risk (Có nguy cơ rời bỏ)": "Khách hàng có nguy cơ rời bỏ",
                "Can't Lose Them (VIP sắp mất)": "Khách VIP có nguy cơ mất",
                "Hibernating / Lost (Ngủ đông / Đã mất)": "Khách hàng ngừng giao dịch",
                "Need Attention (Cần chăm sóc)": "Khách hàng cần quan tâm chăm sóc"
            }
            df_rfm_view["Tên phân khúc"] = df_rfm_view["Segment"].map(dich_phan_khuc).fillna(df_rfm_view["Segment"])

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                seg_grp = df_rfm_view.groupby("Tên phân khúc").agg(
                    Count=("CustomerUniqueID", "count") if "CustomerUniqueID" in df_rfm_view.columns else ("Recency","count"),
                    TotalRevenue=("Monetary", "sum"),
                ).reset_index().sort_values("TotalRevenue", ascending=False)
                fig_seg = px.bar(
                    seg_grp, x="Count", y="Tên phân khúc", orientation="h",
                    color="TotalRevenue", color_continuous_scale="Blues",
                    title="Số lượng khách hàng và doanh thu đóng góp theo phân khúc",
                    labels={"Count":"Số lượng khách hàng","Tên phân khúc":"Nhóm khách hàng"},
                    text=seg_grp["Count"].apply(lambda x: f"{x:,} khách"),
                )
                fig_seg.update_traces(textposition="outside")
                fig_seg.update_layout(height=450, yaxis=dict(autorange="reversed"))
                st.plotly_chart(fig_seg, use_container_width=True)

            with col_r2:
                if "Recency" in df_rfm_view.columns and "Monetary" in df_rfm_view.columns:
                    sample_size = min(4000, len(df_rfm_view))
                    fig_scatter = px.scatter(
                        df_rfm_view.sample(sample_size, random_state=42),
                        x="Recency", y="Monetary",
                        color="Tên phân khúc",
                        color_discrete_sequence=px.colors.qualitative.Bold,
                        title=f"Phân bổ khách hàng: Số ngày từ lần mua cuối vs Tổng chi tiêu",
                        labels={"Recency":"Số ngày kể từ lần mua gần nhất","Monetary":"Tổng chi tiêu (Real Brazil)"},
                        opacity=0.7,
                    )
                    fig_scatter.update_layout(height=450)
                    st.plotly_chart(fig_scatter, use_container_width=True)

        st.divider()
        section_header("bx bx-target-lock", "Kết quả phân cụm thuật toán K-Means")
        img_cols = st.columns(2)
        elbow_img = os.path.join(BASE_DIR, "outputs", "elbow_silhouette_chart.png")
        scatter_img = os.path.join(BASE_DIR, "outputs", "kmeans_clusters_scatter.png")
        if os.path.exists(elbow_img):
            img_cols[0].image(elbow_img, caption="Phương pháp Elbow & Điểm Silhouette xác định 4 cụm tối ưu", use_container_width=True)
        if os.path.exists(scatter_img):
            img_cols[1].image(scatter_img, caption="Phân bố các cụm khách hàng trên không gian đa chiều", use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PHẦN 4: GỢI Ý BÁN CHÉO (LUẬT KẾT HỢP APRIORI)
# ══════════════════════════════════════════════════════════════════════════════
with tab4:
    section_header("bx bx-cart", "Khai phá quy luật giỏ hàng và gợi ý sản phẩm mua kèm")

    df_rules = load_rules()
    if df_rules.empty:
        st.warning("Chưa có dữ liệu luật kết hợp giỏ hàng.")
    else:
        df_rules["Ngành hàng đang mua"] = df_rules["antecedents_str"].apply(lambda s: ", ".join([dich_danh_muc(x.strip()) for x in s.split(",")]))
        df_rules["Gợi ý mua kèm thêm"] = df_rules["consequents_str"].apply(lambda s: ", ".join([dich_danh_muc(x.strip()) for x in s.split(",")]))

        r1, r2, r3 = st.columns(3)
        r1.metric("Tổng số luật kết hợp tìm thấy", f"{len(df_rules):,}")
        r2.metric("Mức độ gắn kết tối đa (Hệ số Lift)", f"{df_rules['lift'].max():.2f}")
        r3.metric("Độ tin cậy tối đa", f"{df_rules['confidence'].max()*100:.1f}%")

        min_lift_sel = st.slider("Lọc theo mức độ gắn kết tối thiểu (Hệ số Lift):", 1.0, float(df_rules["lift"].max()), 1.5, step=0.2)
        df_filtered_rules = df_rules[df_rules["lift"] >= min_lift_sel].head(40)

        if not df_filtered_rules.empty:
            col_mb1, col_mb2 = st.columns([3, 2])
            with col_mb1:
                st.dataframe(
                    df_filtered_rules[["Ngành hàng đang mua", "Gợi ý mua kèm thêm", "support", "confidence", "lift"]]
                    .rename(columns={
                        "support":"Độ phổ biến (Support)",
                        "confidence":"Độ tin cậy (Confidence)",
                        "lift":"Mức độ gắn kết (Lift)",
                    })
                    .style.format({
                        "Độ phổ biến (Support)":"{:.2%}",
                        "Độ tin cậy (Confidence)":"{:.2%}",
                        "Mức độ gắn kết (Lift)":"{:.2f}"
                    }),
                    height=440,
                    use_container_width=True
                )
            with col_mb2:
                fig_scatter_rules = px.scatter(
                    df_filtered_rules, x="support", y="confidence", size="lift", color="lift",
                    color_continuous_scale="Teal",
                    title="Mối quan hệ giữa Độ phổ biến và Độ tin cậy (Kích cỡ = Lift)",
                    labels={"support":"Độ phổ biến","confidence":"Độ tin cậy","lift":"Mức độ gắn kết"},
                    hover_data=["Ngành hàng đang mua", "Gợi ý mua kèm thêm"],
                )
                fig_scatter_rules.update_layout(height=440)
                st.plotly_chart(fig_scatter_rules, use_container_width=True)

        st.divider()
        section_header("bx bx-search-alt", "Tra cứu nhanh sản phẩm mua kèm")
        search_term = st.text_input("Nhập tên ngành hàng tiếng Việt bạn muốn tìm gợi ý:", placeholder="Ví dụ: Thiết bị âm thanh, Chăn ga gối đệm, Sức khỏe & Chăm sóc sắc đẹp...")
        if search_term:
            matches = df_rules[
                df_rules["Ngành hàng đang mua"].str.contains(search_term.strip(), case=False, na=False)
            ].sort_values("lift", ascending=False).head(10)
            if not matches.empty:
                st.success(f"Đã tìm thấy {len(matches)} quy luật gợi ý bán kèm phù hợp:")
                st.dataframe(
                    matches[["Ngành hàng đang mua", "Gợi ý mua kèm thêm", "confidence", "lift"]]
                    .rename(columns={
                        "confidence":"Độ tin cậy",
                        "lift":"Mức độ gắn kết"
                    })
                    .style.format({"Độ tin cậy":"{:.2%}", "Mức độ gắn kết":"{:.2f}"}),
                    use_container_width=True,
                )
            else:
                st.info("Không tìm thấy quy luật gợi ý bán kèm nào phù hợp với ngành hàng này.")


# ══════════════════════════════════════════════════════════════════════════════
# PHẦN 5: PHÂN TÍCH TRỰC TUYẾN ĐA CHIỀU (OLAP OPERATIONS)
# ══════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("""
    <div style='font-size:1.02rem; color:#475569; margin-bottom:1.2rem; line-height:1.6;'>
        Trực quan hóa và tương tác trực tiếp với <b>5 thao tác OLAP kinh điển</b> trên khối dữ liệu bán lẻ:<br>
        <b>Roll-up (Thu gọn)</b> • <b>Drill-down (Chi tiết hóa)</b> • <b>Slice (Cắt lát đơn)</b> •
        <b>Dice (Cắt khối đa chiều)</b> • <b>Pivot (Xoay ma trận)</b>
    </div>
    """, unsafe_allow_html=True)

    # ── Chọn thao tác ──
    olap_op = st.radio(
        "Lựa chọn thao tác phân tích OLAP:",
        options=[
            "Roll-up (Thu gọn: Tháng → Quý → Năm)",
            "Drill-down (Chi tiết hóa: Năm → Tháng)",
            "Slice (Cắt lát đơn: Doanh thu theo Vùng)",
            "Dice (Cắt khối đa chiều: Tiểu bang & Năm)",
            "Pivot (Xoay ma trận: Tiểu bang theo Tháng)",
        ],
        horizontal=True,
        label_visibility="visible",
    )

    st.markdown("---")

    # ──────────────────────────────────────────────────────────────────────────
    # ROLL-UP
    # ──────────────────────────────────────────────────────────────────────────
    if olap_op.startswith("Roll-up"):
        section_header("bx bx-collapse-alt", "Thao tác ROLL-UP: Gộp dữ liệu từ cấp Tháng lên cấp Quý & Năm")
        st.markdown("""
        <div class='olap-op-card'>
          <div class='olap-op-title'><i class='bx bx-chevrons-up'></i> Roll-up (Thu gọn cấp bậc)</div>
          <div class='olap-op-desc'>Tổng hợp dữ liệu từ mức độ chi tiết nhất (Tháng) lên các mức tổng quát hơn (Quý, Năm).
          Giúp nhà quản lý nhìn bức tranh toàn cảnh dài hạn mà không bị chi phối bởi biến động vụn vặt từng kỳ.</div>
        </div>
        """, unsafe_allow_html=True)

        rollup_level = st.selectbox(
            "Chọn cấp độ tổng hợp thu gọn:",
            options=["Thu gọn theo NĂM", "Thu gọn theo QUÝ", "Xem chi tiết THÁNG"],
        )
        level_key = "Năm" if "NĂM" in rollup_level else ("Quý" if "QUÝ" in rollup_level else "Tháng")
        df_rollup = olap_rollup(level_key)

        if df_rollup.empty:
            st.info("Không có dữ liệu.")
        else:
            col_t, col_c = st.columns([1, 2])
            with col_t:
                df_table_show = df_rollup.drop(columns=[c for c in df_rollup.columns if c.startswith("_")], errors="ignore")
                rename_map = {
                    "nam": "Năm", "quy": "Quý", "thang_nam": "Tháng–Năm",
                    "so_don_hang": "Số đơn hàng", "tong_san_luong": "Sản lượng", "tong_doanh_thu": "Doanh thu (BRL)"
                }
                st.dataframe(
                    df_table_show.rename(columns=rename_map).style.format({"Doanh thu (BRL)": "{:,.2f}"}),
                    use_container_width=True, height=360
                )
            with col_c:
                if level_key == "Năm":
                    x_col, x_label = "nam", "Năm"
                    title = "Tổng Doanh Thu Theo Năm (Real Brazil)"
                    df_plot = df_rollup.sort_values("_sort_year").copy()
                elif level_key == "Quý":
                    df_plot = df_rollup.sort_values(["_sort_year", "_sort_month"]).reset_index(drop=True).copy()
                    quy_short = df_plot["quy"].str.extract(r"(Q\d)", expand=False).fillna(df_plot["quy"])
                    df_plot["nhan"] = df_plot["nam"] + " – " + quy_short
                    x_col, x_label = "nhan", "Năm – Quý"
                    title = "Tổng Doanh Thu Theo Quý (Real Brazil)"
                else:
                    x_col, x_label = "thang_nam", "Tháng–Năm"
                    title = "Doanh Thu Theo Tháng (Real Brazil)"
                    df_plot = df_rollup.sort_values(["_sort_year", "_sort_month"]).copy()

                fig_ru = px.bar(
                    df_plot, x=x_col, y="tong_doanh_thu",
                    color="tong_doanh_thu", color_continuous_scale="Blues",
                    labels={x_col: x_label, "tong_doanh_thu": "Doanh thu (Real Brazil)"},
                    title=title,
                    text=df_plot["tong_doanh_thu"].apply(
                        lambda v: f"{v/1e6:.2f}M BRL" if v >= 1e6 else f"{v/1000:,.0f}K BRL"
                    ),
                )
                fig_ru.update_traces(
                    textposition="outside",
                    hovertemplate="%{x}<br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>"
                )
                fig_ru.update_layout(
                    height=380, showlegend=False, coloraxis_showscale=False,
                    margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(tickangle=-30),
                    yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f")
                )
                st.plotly_chart(fig_ru, use_container_width=True)

    # ──────────────────────────────────────────────────────────────────────────
    # DRILL-DOWN
    # ──────────────────────────────────────────────────────────────────────────
    elif olap_op.startswith("Drill-down"):
        section_header("bx bx-expand-alt", "Thao tác DRILL-DOWN: Phóng to từng tháng trong một năm")
        st.markdown("""
        <div class='olap-op-card'>
          <div class='olap-op-title'><i class='bx bx-chevrons-down'></i> Drill-down (Chi tiết hóa)</div>
          <div class='olap-op-desc'>Từ bức tranh tổng hợp hàng năm, đi sâu vào chi tiết từng tháng để phát hiện
          mùa vụ kinh doanh, điểm đột biến và tốc độ tăng trưởng liên tiếp (MoM).</div>
        </div>
        """, unsafe_allow_html=True)

        avail_years = meta["years"]
        sel_year_dd = st.selectbox("Chọn năm để phóng to chi tiết:", options=avail_years, index=len(avail_years) - 1)
        df_dd = olap_drilldown(int(sel_year_dd))

        if not df_dd.empty:
            df_dd = df_dd.sort_values("thang").reset_index(drop=True)

            # Tính MoM chính xác: chỉ tính khi 2 tháng thực sự liên tiếp và doanh thu tháng trước >= 1,000 BRL
            # (Loại bỏ các trường hợp thử nghiệm đầu dự án 2016 gây đột biến giả tạo hàng chục nghìn %)
            df_dd["thang_prev"] = df_dd["thang"].shift(1)
            is_consecutive = (df_dd["thang"] - df_dd["thang_prev"]) == 1
            valid_base = (df_dd["doanh_thu"].shift(1) >= 1000) & is_consecutive
            raw_growth = ((df_dd["doanh_thu"] - df_dd["doanh_thu"].shift(1)) / df_dd["doanh_thu"].shift(1) * 100).round(1)
            df_dd["mom_growth"] = raw_growth.where(valid_base, np.nan)

            col_d1, col_d2 = st.columns([3, 2])
            with col_d1:
                fig_dd = px.bar(
                    df_dd, x="thang_nam", y="doanh_thu",
                    color="quy",
                    labels={"thang_nam": "Tháng", "doanh_thu": "Doanh thu (Real Brazil)", "quy": "Quý"},
                    title=f"Doanh thu từng tháng trong năm {sel_year_dd} (tô màu theo Quý)",
                    text=df_dd["doanh_thu"].apply(lambda v: f"{v/1000:,.0f}K"),
                    color_discrete_sequence=["#1E40AF", "#2563EB", "#3B82F6", "#93C5FD"],
                )
                fig_dd.update_traces(
                    textposition="outside",
                    hovertemplate="Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>"
                )
                fig_dd.update_layout(
                    height=390, margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(tickangle=-30),
                    yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f"),
                    bargap=0.15,
                )
                st.plotly_chart(fig_dd, use_container_width=True)

            with col_d2:
                df_mom_valid = df_dd.dropna(subset=["mom_growth"]).copy()
                if not df_mom_valid.empty:
                    fig_mom = px.line(
                        df_mom_valid,
                        x="thang_nam", y="mom_growth",
                        markers=True,
                        labels={"thang_nam": "Tháng", "mom_growth": "Tăng trưởng MoM (%)"},
                        title="Tốc độ tăng trưởng tháng sau so với tháng trước (%)",
                        color_discrete_sequence=["#0D9488"],
                    )
                    fig_mom.update_traces(
                        hovertemplate="Tháng: <b>%{x}</b><br>Tăng trưởng: <b>%{y:.1f}%</b><extra></extra>",
                        line=dict(width=2.5)
                    )
                    fig_mom.add_hline(y=0, line_dash="dash", line_color="#94A3B8")
                    fig_mom.update_layout(
                        height=390, margin=dict(l=20, r=20, t=40, b=60),
                        xaxis=dict(tickangle=-30),
                        yaxis=dict(title="Tăng trưởng MoM (%)", ticksuffix="%"),
                    )
                    st.plotly_chart(fig_mom, use_container_width=True)
                else:
                    st.markdown(f"""
                    <div style="background:#F8FAFC; border:1px solid #E2E8F0; border-radius:8px; padding:16px; color:#475569; font-size:0.9rem; margin-top:40px;">
                        <div style="font-weight:700; color:#1E293B; margin-bottom:6px; display:flex; align-items:center; gap:6px;">
                            <i class='bx bx-info-circle' style='font-size:1.2rem; color:#3B82F6;'></i>
                            Lưu ý về dữ liệu năm {sel_year_dd}
                        </div>
                        Giai đoạn {sel_year_dd} là thời gian bắt đầu hệ thống thử nghiệm với số lượng đơn hàng hạn chế và ngắt quãng giữa các tháng, chưa đủ điều kiện chuỗi thời gian liên tục để tính MoM. Bạn hãy chọn <b>Năm 2017</b> để xem chu kỳ tăng trưởng đầy đủ 12 tháng.
                    </div>
                    """, unsafe_allow_html=True)

            st.dataframe(
                df_dd[["thang_nam", "quy", "so_don_hang", "doanh_thu", "gia_tri_don_tb", "mom_growth"]]
                .rename(columns={
                    "thang_nam": "Tháng–Năm", "quy": "Quý",
                    "so_don_hang": "Số đơn hàng", "doanh_thu": "Doanh thu (BRL)",
                    "gia_tri_don_tb": "Giá trị đơn TB (BRL)", "mom_growth": "Tăng trưởng MoM (%)"
                })
                .style.format({
                    "Doanh thu (BRL)": "{:,.2f}",
                    "Giá trị đơn TB (BRL)": "{:,.2f}",
                    "Tăng trưởng MoM (%)": lambda v: f"{v:+.1f}%" if pd.notna(v) else "—"
                }),
                use_container_width=True, height=260,
            )

    # ──────────────────────────────────────────────────────────────────────────
    # SLICE
    # ──────────────────────────────────────────────────────────────────────────
    elif olap_op.startswith("Slice"):
        section_header("bx bx-layer", "Thao tác SLICE: Cắt một lát phẳng theo chiều Thời gian")
        st.markdown("""
        <div class='olap-op-card'>
          <div class='olap-op-title'><i class='bx bx-layer'></i> Slice (Cắt lát đơn)</div>
          <div class='olap-op-desc'>Cố định một giá trị trên một chiều phân tích (ví dụ chọn cố định 1 năm),
          sau đó quan sát toàn bộ chuyển động của các chiều còn lại (Vùng địa lý và Doanh thu tháng).</div>
        </div>
        """, unsafe_allow_html=True)

        avail_years = meta["years"]
        col_s_sel1, col_s_sel2 = st.columns([1, 1])
        with col_s_sel1:
            sel_year_sl = st.selectbox("Chọn năm (chiều Thời gian cố định):", options=avail_years, index=len(avail_years) - 1)
        with col_s_sel2:
            slice_mode = st.radio("Kiểu hiển thị biểu đồ:", ["Đường xu hướng (Line Chart)", "Cột chồng tỷ trọng (Stacked Bar)"], horizontal=True)

        df_sl = olap_slice(int(sel_year_sl))

        if not df_sl.empty:
            # Chuẩn hóa tên vùng sang tiếng Việt
            df_sl["vung_vn"] = df_sl["vung"].map(DANH_SACH_VUNG).fillna(df_sl["vung"])

            # Xây dựng ma trận hoàn chỉnh (Full Grid) để tránh đường line bị gãy hoặc nhảy cóc
            month_order_df = df_sl[["thang_nam", "_sort_year", "_sort_month"]].drop_duplicates().sort_values(["_sort_year", "_sort_month"])
            month_list = month_order_df["thang_nam"].tolist()

            pv_sl = df_sl.pivot_table(
                index="thang_nam", columns="vung_vn", values="doanh_thu", fill_value=0
            ).reindex(month_list, fill_value=0)

            df_sl_clean = pv_sl.reset_index().melt(
                id_vars="thang_nam", var_name="vung_vn", value_name="doanh_thu"
            )

            color_map = {
                "Đông Nam": "#1E40AF",
                "Nam": "#2563EB",
                "Đông Bắc": "#0D9488",
                "Trung Tây": "#F59E0B",
                "Bắc": "#7C3AED",
            }

            col_s1, col_s2 = st.columns([3, 2])
            with col_s1:
                if "Đường" in slice_mode:
                    fig_sl = px.line(
                        df_sl_clean, x="thang_nam", y="doanh_thu", color="vung_vn",
                        markers=True,
                        labels={"thang_nam": "Tháng", "doanh_thu": "Doanh thu (Real Brazil)", "vung_vn": "Vùng kinh tế"},
                        title=f"Doanh thu theo tháng & vùng địa lý — Lát cắt năm {sel_year_sl}",
                        category_orders={"thang_nam": month_list},
                        color_discrete_map=color_map,
                    )
                    fig_sl.update_traces(
                        hovertemplate="Vùng: <b>%{data.name}</b><br>Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>",
                        line=dict(width=2.5)
                    )
                else:
                    fig_sl = px.bar(
                        df_sl_clean, x="thang_nam", y="doanh_thu", color="vung_vn",
                        labels={"thang_nam": "Tháng", "doanh_thu": "Doanh thu (Real Brazil)", "vung_vn": "Vùng kinh tế"},
                        title=f"Cơ cấu doanh thu theo tháng & vùng — Lát cắt năm {sel_year_sl}",
                        category_orders={"thang_nam": month_list},
                        color_discrete_map=color_map,
                        barmode="stack"
                    )
                    fig_sl.update_traces(
                        hovertemplate="Vùng: <b>%{data.name}</b><br>Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>"
                    )

                fig_sl.update_layout(
                    height=410, margin=dict(l=20, r=20, t=40, b=60),
                    xaxis=dict(tickangle=-30),
                    yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f"),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                st.plotly_chart(fig_sl, use_container_width=True)

            with col_s2:
                region_total = df_sl.groupby("vung_vn")["doanh_thu"].sum().reset_index().sort_values("doanh_thu", ascending=False)
                fig_pie_sl = px.pie(
                    region_total, values="doanh_thu", names="vung_vn", hole=0.45,
                    title=f"Tỷ trọng doanh thu theo vùng năm {sel_year_sl}",
                    color="vung_vn", color_discrete_map=color_map,
                )
                fig_pie_sl.update_traces(
                    hovertemplate="Vùng: <b>%{label}</b><br>Doanh thu: <b>%{value:,.2f} BRL</b><br>Tỷ trọng: <b>%{percent}</b><extra></extra>"
                )
                fig_pie_sl.update_layout(height=410, margin=dict(l=20, r=20, t=40, b=20))
                st.plotly_chart(fig_pie_sl, use_container_width=True)

            st.markdown(f"""
            <div style='color:#64748B; font-size:0.86rem; margin-top:4px; display:flex; align-items:center; gap:6px;'>
                <i class='bx bx-info-circle' style='font-size:1.1rem; color:#2563EB;'></i>
                Lát cắt cố định: <b>Năm = {sel_year_sl}</b> — Khảo sát trên <b>{df_sl['vung_vn'].nunique()}</b> vùng kinh tế trong suốt <b>{len(month_list)}</b> tháng hoạt động.
            </div>
            """, unsafe_allow_html=True)

    # ──────────────────────────────────────────────────────────────────────────
    # DICE
    # ──────────────────────────────────────────────────────────────────────────
    elif olap_op.startswith("Dice"):
        section_header("bx bx-cube-alt", "Thao tác DICE: Cắt khối đa chiều (Tiểu bang & Năm)")
        st.markdown("""
        <div class='olap-op-card'>
          <div class='olap-op-title'><i class='bx bx-cube-alt'></i> Dice (Cắt khối đa chiều)</div>
          <div class='olap-op-desc'>Thu hẹp phạm vi đồng thời trên <b>nhiều chiều dữ liệu</b> (kết hợp lọc cả Năm và một nhóm Tiểu bang cụ thể).
          Tạo thành một khối con độc lập (sub-cube) để đối chiếu trực tiếp giữa các thị trường mục tiêu.</div>
        </div>
        """, unsafe_allow_html=True)

        avail_years = meta["years"]
        col_dc1, col_dc2 = st.columns(2)
        with col_dc1:
            sel_year_dc = st.selectbox("Chiều Thời gian — chọn năm:", options=avail_years, index=len(avail_years) - 1)
        with col_dc2:
            top_states_default = meta["states"][:5] if len(meta["states"]) >= 5 else meta["states"]
            sel_states_dc = st.multiselect(
                "Chiều Địa lý — chọn các tiểu bang muốn so sánh:",
                options=meta["states"],
                default=top_states_default,
                format_func=lambda x: DANH_SACH_TIEU_BANG.get(x, x),
                placeholder="Chọn ít nhất 2 tiểu bang...",
            )

        if len(sel_states_dc) < 1:
            st.info("Vui lòng chọn ít nhất 1 tiểu bang để tiến hành phân tích Dice.")
        else:
            df_dc = olap_dice(tuple(sel_states_dc), int(sel_year_dc))
            if df_dc.empty:
                st.warning("Không có dữ liệu phù hợp với điều kiện đã chọn.")
            else:
                df_dc["ten_tieu_bang"] = df_dc["tieu_bang"].map(DANH_SACH_TIEU_BANG).fillna(df_dc["tieu_bang"])

                # Xây dựng Full Grid đảm bảo không bị khuyết tháng gây gãy nét vẽ
                month_order_dc = df_dc[["thang_nam", "_sort_year", "_sort_month"]].drop_duplicates().sort_values(["_sort_year", "_sort_month"])
                month_list_dc = month_order_dc["thang_nam"].tolist()

                pv_dc = df_dc.pivot_table(
                    index="thang_nam", columns="ten_tieu_bang", values="doanh_thu", fill_value=0
                ).reindex(month_list_dc, fill_value=0)

                df_dc_clean = pv_dc.reset_index().melt(
                    id_vars="thang_nam", var_name="ten_tieu_bang", value_name="doanh_thu"
                )

                col_dc_c1, col_dc_c2 = st.columns([3, 2])
                with col_dc_c1:
                    fig_dc = px.line(
                        df_dc_clean, x="thang_nam", y="doanh_thu", color="ten_tieu_bang",
                        markers=True,
                        labels={"thang_nam": "Tháng", "doanh_thu": "Doanh thu (Real Brazil)", "ten_tieu_bang": "Tiểu bang"},
                        title=f"Doanh thu theo tháng — Khối con: {len(sel_states_dc)} bang × Năm {sel_year_dc}",
                        category_orders={"thang_nam": month_list_dc},
                    )
                    fig_dc.update_traces(
                        hovertemplate="Bang: <b>%{data.name}</b><br>Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>",
                        line=dict(width=2.5)
                    )
                    fig_dc.update_layout(
                        height=420, margin=dict(l=20, r=20, t=40, b=60),
                        xaxis=dict(tickangle=-30),
                        yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_dc, use_container_width=True)

                with col_dc_c2:
                    state_agg = df_dc.groupby("ten_tieu_bang").agg(
                        tong_doanh_thu=("doanh_thu", "sum"),
                        tong_don=("so_don_hang", "sum"),
                    ).reset_index().sort_values("tong_doanh_thu", ascending=True)
                    fig_dc_bar = px.bar(
                        state_agg, x="tong_doanh_thu", y="ten_tieu_bang",
                        orientation="h", color="tong_doanh_thu", color_continuous_scale="Blues",
                        labels={"tong_doanh_thu": "Tổng doanh thu (Real Brazil)", "ten_tieu_bang": "Tiểu bang"},
                        title=f"Tổng doanh thu năm {sel_year_dc} theo bang",
                        text=state_agg["tong_doanh_thu"].apply(lambda v: f"{v/1000:,.0f}K"),
                    )
                    fig_dc_bar.update_traces(
                        textposition="outside",
                        hovertemplate="Bang: <b>%{y}</b><br>Doanh thu: <b>%{x:,.2f} BRL</b><extra></extra>"
                    )
                    fig_dc_bar.update_layout(
                        height=420, showlegend=False, coloraxis_showscale=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    st.plotly_chart(fig_dc_bar, use_container_width=True)

                st.markdown(f"""
                <div style='color:#64748B; font-size:0.86rem; margin-top:4px; display:flex; align-items:center; gap:6px;'>
                    <i class='bx bx-info-circle' style='font-size:1.1rem; color:#2563EB;'></i>
                    Khối con được xác định bởi: <b>Năm = {sel_year_dc}</b> và <b>{len(sel_states_dc)} tiểu bang</b> ({', '.join(sel_states_dc)}).
                </div>
                """, unsafe_allow_html=True)

                st.dataframe(
                    df_dc[["thang_nam", "tieu_bang", "ten_tieu_bang", "vung", "so_don_hang", "doanh_thu", "gia_tb"]]
                    .rename(columns={
                        "thang_nam": "Tháng", "tieu_bang": "Mã bang", "ten_tieu_bang": "Tiểu bang",
                        "vung": "Vùng", "so_don_hang": "Số đơn", "doanh_thu": "Doanh thu (BRL)", "gia_tb": "Giá TB (BRL)"
                    })
                    .style.format({"Doanh thu (BRL)": "{:,.2f}", "Giá TB (BRL)": "{:,.2f}"}),
                    use_container_width=True, height=280,
                )

    # ──────────────────────────────────────────────────────────────────────────
    # PIVOT
    # ──────────────────────────────────────────────────────────────────────────
    else:
        section_header("bx bx-sync", "Thao tác PIVOT: Xoay ma trận so sánh các tiểu bang theo tháng")
        st.markdown("""
        <div class='olap-op-card'>
          <div class='olap-op-title'><i class='bx bx-sync'></i> Pivot (Xoay ma trận)</div>
          <div class='olap-op-desc'>Hoán đổi các chiều trong ma trận: biến <b>Tiểu bang</b> thành các cột và <b>Tháng</b> thành các hàng.
          Cho phép quan sát đồng thời diễn biến doanh thu giữa nhiều bang trên cùng một mặt phẳng bảng số liệu hoặc bản đồ nhiệt.</div>
        </div>
        """, unsafe_allow_html=True)

        col_pv_s1, col_pv_s2 = st.columns([1, 2])
        with col_pv_s1:
            sel_year_pv = st.selectbox(
                "Phạm vi thời gian:",
                options=["Toàn bộ thời gian (2016 – 2018)", 2017, 2018, 2016],
                index=0
            )
            year_arg = None if "Toàn bộ" in str(sel_year_pv) else int(sel_year_pv)

        with col_pv_s2:
            top_states_pv = meta["states"][:5] if len(meta["states"]) >= 5 else meta["states"]
            sel_states_pv = st.multiselect(
                "Chọn các tiểu bang để đưa vào ma trận (tối đa 8 bang):",
                options=meta["states"],
                default=top_states_pv,
                format_func=lambda x: DANH_SACH_TIEU_BANG.get(x, x),
                max_selections=8,
            )

        if not sel_states_pv:
            st.info("Vui lòng chọn ít nhất 1 tiểu bang.")
        else:
            df_pv = olap_pivot(tuple(sel_states_pv), year=year_arg)
            if df_pv.empty:
                st.warning("Không có dữ liệu.")
            else:
                state_cols = [c for c in df_pv.columns if c != "thang_nam"]

                col_pv1, col_pv2 = st.columns([2, 3])
                with col_pv1:
                    st.markdown("<b>Ma trận số liệu Pivot — Doanh thu (Real Brazil)</b>", unsafe_allow_html=True)
                    # Đổi tên cột sang tên đầy đủ
                    df_pv_display = df_pv.copy()
                    display_col_map = {c: DANH_SACH_TIEU_BANG.get(c, c) for c in state_cols}
                    df_pv_display = df_pv_display.rename(columns=display_col_map)
                    styled = df_pv_display.set_index("thang_nam").style.format("{:,.0f}").background_gradient(
                        cmap="Blues", axis=None
                    )
                    st.dataframe(styled, use_container_width=True, height=430)

                with col_pv2:
                    df_pv_melt = df_pv.melt(
                        id_vars="thang_nam", value_vars=state_cols,
                        var_name="Tiểu bang", value_name="Doanh thu (Real Brazil)"
                    )
                    df_pv_melt["Tên tiểu bang"] = df_pv_melt["Tiểu bang"].map(DANH_SACH_TIEU_BANG).fillna(df_pv_melt["Tiểu bang"])
                    month_order = df_pv["thang_nam"].tolist()

                    fig_pv = px.line(
                        df_pv_melt, x="thang_nam", y="Doanh thu (Real Brazil)", color="Tên tiểu bang",
                        markers=True,
                        labels={"thang_nam": "Tháng–Năm"},
                        title="Diễn biến doanh thu theo tháng — Pivot Chart",
                        category_orders={"thang_nam": month_order},
                    )
                    fig_pv.update_traces(
                        hovertemplate="Bang: <b>%{data.name}</b><br>Tháng: <b>%{x}</b><br>Doanh thu: <b>%{y:,.2f} BRL</b><extra></extra>",
                        line=dict(width=2.5)
                    )
                    fig_pv.update_layout(
                        height=430, margin=dict(l=20, r=20, t=40, b=60),
                        xaxis=dict(tickangle=-30),
                        yaxis=dict(title="Doanh thu (Real Brazil)", tickformat=",.0f"),
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig_pv, use_container_width=True)

                # Heatmap
                st.markdown("<b>Bản đồ nhiệt ma trận (Heatmap Pivot)</b>", unsafe_allow_html=True)
                df_heat = df_pv.set_index("thang_nam")[state_cols]
                df_heat.columns = [DANH_SACH_TIEU_BANG.get(c, c) for c in df_heat.columns]
                fig_heat = go.Figure(data=go.Heatmap(
                    z=df_heat.values,
                    x=df_heat.columns.tolist(),
                    y=df_heat.index.tolist(),
                    colorscale="Blues",
                    hovertemplate="Tháng: <b>%{y}</b><br>Bang: <b>%{x}</b><br>Doanh thu: <b>%{z:,.0f} BRL</b><extra></extra>",
                    zmin=0,
                ))
                fig_heat.update_layout(
                    height=max(360, len(df_heat) * 24),
                    margin=dict(l=20, r=20, t=20, b=40),
                    xaxis_title="Tiểu bang",
                    yaxis=dict(title="Tháng–Năm", autorange="reversed", tickfont=dict(size=10)),
                )
                st.plotly_chart(fig_heat, use_container_width=True)


