"""
Script 07: Tích Hợp API Thương Mại Điện Tử (E-Commerce Product Catalog API Enrichment)
=====================================================================================
GIAI ĐOẠN 1 – Trích xuất dữ liệu danh mục, sản phẩm, đánh giá từ DummyJSON E-Commerce API
GIAI ĐOẠN 2 – Làm giàu dữ liệu sản phẩm (Data Enrichment) cho Kho dữ liệu bán lẻ
GIAI ĐOẠN 3 – Lưu snapshot thô (raw JSON) và bảng đối soát cho Lakehouse & BI Dashboard

Nguồn API: https://dummyjson.com/products (RESTful E-Commerce Catalog API – Miễn phí, không cần key)
"""

import os
import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

import json
from datetime import datetime
import urllib.request
import urllib.parse
import pandas as pd

BASE_URL = "https://dummyjson.com/products"
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")
RAW_SNAPSHOT = os.path.join(RAW_DIR, "ecommerce_products_raw.json")
CATALOG_CSV = os.path.join(OUTPUTS_DIR, "ecommerce_product_catalog.csv")
BENCHMARK_CSV = os.path.join(OUTPUTS_DIR, "ecommerce_category_benchmarks.csv")

os.makedirs(RAW_DIR, exist_ok=True)
os.makedirs(OUTPUTS_DIR, exist_ok=True)

CATEGORY_MAP_VN = {
    "beauty": "Làm đẹp & Mỹ phẩm",
    "fragrances": "Nước hoa & Tinh dầu",
    "furniture": "Nội thất gia đình",
    "groceries": "Thực phẩm & Bách hóa",
    "home-decoration": "Trang trí nhà cửa",
    "kitchen-accessories": "Dụng cụ nhà bếp & Bàn ăn",
    "laptops": "Máy tính & Công nghệ",
    "mens-shirts": "Thời trang nam",
    "mens-shoes": "Giày dép nam",
    "mens-watches": "Đồng hồ nam",
    "mobile-accessories": "Phụ kiện điện thoại",
    "motorcycle": "Phụ tùng xe máy",
    "skin-care": "Chăm sóc da",
    "smartphones": "Điện thoại thông minh",
    "sports-accessories": "Phụ kiện thể thao",
    "sunglasses": "Kính mắt thời trang",
    "tablets": "Máy tính bảng",
    "tops": "Áo thời trang",
    "vehicle": "Phương tiện vận tải",
    "womens-bags": "Túi xách nữ",
    "womens-dresses": "Váy đầm nữ",
    "womens-jewellery": "Trang sức nữ",
    "womens-shoes": "Giày dép nữ",
    "womens-watches": "Đồng hồ nữ",
}

def fetch_ecommerce_api() -> pd.DataFrame:
    print("\n" + "=" * 65)
    print("  GIAI ĐOẠN 1: KẾT NỐI & TRÍCH XUẤT DỮ LIỆU TỪ E-COMMERCE API")
    print("=" * 65)

    extracted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    url = f"{BASE_URL}?limit=194"
    print(f"📡 Đang kết nối tới E-Commerce REST API: {url}...")

    raw_data = None
    is_fallback = False

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw_data = json.loads(resp.read().decode("utf-8"))
        products = raw_data.get("products", [])
        print(f"✅ Kết nối thành công! Đã trích xuất {len(products)} mặt hàng thương mại điện tử.")
    except Exception as e:
        is_fallback = True
        print(f"⚠️ Không thể kết nối API trực tiếp ({e}). Sử dụng tập dữ liệu dự phòng chuẩn...")
        # Tạo fallback data phong phú
        products = [
            {"id": 1, "title": "Bình cắm hoa thủy tinh phong cách cổ điển", "category": "home-decoration", "price": 14.99, "rating": 4.65, "stock": 45, "brand": "HomeDecor", "availabilityStatus": "In Stock", "shippingInformation": "Giao hàng từ 2-4 ngày làm việc"},
            {"id": 2, "title": "Bộ dao thớt đa năng inox 304", "category": "kitchen-accessories", "price": 29.50, "rating": 4.82, "stock": 80, "brand": "KitchenPro", "availabilityStatus": "In Stock", "shippingInformation": "Giao hàng từ 1-2 ngày làm việc"},
            {"id": 3, "title": "Đèn ngủ hình thỏ con cảm ứng", "category": "home-decoration", "price": 12.00, "rating": 4.70, "stock": 25, "brand": "KidsLight", "availabilityStatus": "Low Stock", "shippingInformation": "Giao hàng từ 3-5 ngày làm việc"},
            {"id": 4, "title": "Khay bánh kem 3 tầng phong cách hoàng gia", "category": "kitchen-accessories", "price": 25.00, "rating": 4.90, "stock": 60, "brand": "Regency", "availabilityStatus": "In Stock", "shippingInformation": "Giao hàng từ 2-4 ngày làm việc"},
            {"id": 5, "title": "Túi cói dã ngoại vintage", "category": "womens-bags", "price": 18.20, "rating": 4.45, "stock": 30, "brand": "VintageLife", "availabilityStatus": "In Stock", "shippingInformation": "Giao hàng từ 2-4 ngày làm việc"},
            {"id": 6, "title": "Hộp thiếc đựng bánh quy quà tặng", "category": "groceries", "price": 8.50, "rating": 4.30, "stock": 100, "brand": "PantrySweet", "availabilityStatus": "In Stock", "shippingInformation": "Giao hàng từ 1-3 ngày làm việc"},
        ]
        raw_data = {"products": products, "total": len(products)}

    # Lưu snapshot thô
    snapshot_payload = {
        "metadata": {
            "api_name": "DummyJSON E-Commerce Products API",
            "extracted_at": extracted_at,
            "endpoint": url,
            "status": "FALLBACK" if is_fallback else "LIVE_API_SUCCESS",
            "is_fallback": is_fallback,
            "total_items": len(products)
        },
        "payload": raw_data
    }
    with open(RAW_SNAPSHOT, "w", encoding="utf-8") as f:
        json.dump(snapshot_payload, f, ensure_ascii=False, indent=2)
    print(f"💾 Đã lưu bản snapshot thô vào: '{RAW_SNAPSHOT}'")

    # Chuyển đổi thành DataFrame
    rows = []
    for p in products:
        cat_slug = p.get("category", "other")
        rows.append({
            "product_id": p.get("id"),
            "product_name": p.get("title"),
            "category_slug": cat_slug,
            "category_vn": CATEGORY_MAP_VN.get(cat_slug, cat_slug.capitalize()),
            "price_usd": p.get("price", 0.0),
            "rating": p.get("rating", 0.0),
            "stock_quantity": p.get("stock", 0),
            "brand": p.get("brand", "Generic"),
            "availability_status": p.get("availabilityStatus", "In Stock"),
            "shipping_info": p.get("shippingInformation", "Giao trong 2-4 ngày"),
            "return_policy": p.get("returnPolicy", "Đổi trả trong 30 ngày"),
            "minimum_order_qty": p.get("minimumOrderQuantity", 1),
            "extracted_at": extracted_at
        })

    df_catalog = pd.DataFrame(rows)
    df_catalog.to_csv(CATALOG_CSV, index=False, encoding="utf-8")
    print(f"💾 Đã lưu danh mục sản phẩm E-Commerce vào: '{CATALOG_CSV}' ({len(df_catalog)} dòng)")

    # ── GIAI ĐOẠN 2: TỔNG HỢP BENCHMARKS THEO NGÀNH HÀNG ───────────────────────
    print("\n" + "=" * 65)
    print("  GIAI ĐOẠN 2: TỔNG HỢP CHỈ SỐ NGÀNH HÀNG THƯƠNG MẠI ĐIỆN TỬ")
    print("=" * 65)

    category_benchmarks = df_catalog.groupby(["category_slug", "category_vn"]).agg(
        so_san_pham=("product_id", "count"),
        gia_trung_binh_usd=("price_usd", "mean"),
        diem_danh_gia_sao=("rating", "mean"),
        ton_kho_trung_binh=("stock_quantity", "mean"),
    ).reset_index().round(2)

    category_benchmarks = category_benchmarks.sort_values(by="so_san_pham", ascending=False)
    category_benchmarks.to_csv(BENCHMARK_CSV, index=False, encoding="utf-8")
    print(f"💾 Đã lưu bảng chuẩn hóa ngành hàng vào: '{BENCHMARK_CSV}'")
    print(category_benchmarks.head(8).to_string(index=False))

    return df_catalog

if __name__ == "__main__":
    fetch_ecommerce_api()
