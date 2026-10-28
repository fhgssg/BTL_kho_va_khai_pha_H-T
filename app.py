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
    df["Tốc độ tăng trưởng so với tháng trước (%)"] = ((df["Doanh thu hàng tháng"] - df["Doanh thu tháng trước"]) / NULL_ZERO(df["Doanh thu tháng trước"]) * 100).round(2)
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
tab1, tab2, tab3, tab4 = st.tabs([
    "Chỉ Số Tổng Quan",
    "Phân Tích Địa Lý & Danh Mục",
    "Phân Khúc Khách Hàng",
    "Gợi Ý Bán Chéo Sản Phẩm"
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
            section_header("bx bx-line-chart", "Doanh thu theo tháng và tốc độ tăng trưởng")
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=df_monthly["Tháng Năm"], y=df_monthly["Doanh thu hàng tháng"],
                name="Doanh thu (Real Brazil)", marker_color="#2563EB", opacity=0.85,
            ))
            fig.add_trace(go.Scatter(
                x=df_monthly["Tháng Năm"], y=df_monthly["Tốc độ tăng trưởng so với tháng trước (%)"],
                name="Tăng trưởng so với tháng trước (%)", yaxis="y2", mode="lines+markers",
                line=dict(color="#10B981", width=2.5),
            ))
            fig.update_layout(
                yaxis=dict(title="Doanh thu (Real Brazil)"),
                yaxis2=dict(title="Tốc độ tăng trưởng (%)", overlaying="y", side="right", showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                height=380, margin=dict(l=40, r=40, t=30, b=40),
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
            fig_cat_aov = px.scatter(
                df_cat.head(top_cat * 2), x="Số lượng đơn hàng", y="Đơn giá trung bình",
                size="Doanh thu", color="Doanh thu",
                hover_name="Danh mục sản phẩm", text="Danh mục sản phẩm",
                title="Tương quan giữa số lượng đơn hàng và đơn giá bình quân",
                labels={"Số lượng đơn hàng":"Số lượng đơn hàng","Đơn giá trung bình":"Đơn giá trung bình (Real Brazil)"},
                color_continuous_scale="Blues",
            )
            fig_cat_aov.update_traces(textposition="top center", textfont_size=9)
            fig_cat_aov.update_layout(height=480, showlegend=False)
            st.plotly_chart(fig_cat_aov, use_container_width=True)


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
