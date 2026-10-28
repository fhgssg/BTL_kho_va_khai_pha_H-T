"""Nạp catalog DummyJSON và hợp nhất vào chiều sản phẩm dùng chung."""

import os
import re
import unicodedata

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCT_CATALOG_CSV = os.path.join(BASE_DIR, "outputs", "products_catalog.csv")

PRODUCT_CATALOG_COLUMN_MAP = {
    "ProductID": "product_id",
    "Title": "title",
    "Description": "description",
    "Category": "category",
    "Price": "price",
    "DiscountPercentage": "discount_percentage",
    "Rating": "rating",
    "Stock": "stock",
    "Brand": "brand",
    "SKU": "sku",
    "Weight": "weight",
    "WarrantyInformation": "warranty_information",
    "ShippingInformation": "shipping_information",
    "AvailabilityStatus": "availability_status",
    "MinimumOrderQuantity": "minimum_order_quantity",
    "CreatedAt": "created_at",
    "UpdatedAt": "updated_at",
    "Barcode": "barcode",
}

UNIFIED_PRODUCT_COLUMNS = [
    "ProductKey",
    "StockCode",
    "Description",
    "UnitPrice_Standard",
    "SourceSystem",
    "APIProductID",
    "CatalogTitle",
    "Category",
    "CategorySource",
    "CatalogPrice",
    "CatalogDiscountPercentage",
    "CatalogRating",
    "CatalogStock",
    "Brand",
    "CatalogMatchMethod",
]

CATALOG_CATEGORY_LABELS = {
    "beauty": "Làm đẹp",
    "fragrances": "Nước hoa",
    "furniture": "Nội thất",
    "groceries": "Thực phẩm",
    "home-decoration": "Trang trí nhà",
    "kitchen-accessories": "Dụng cụ nhà bếp",
    "laptops": "Máy tính xách tay",
    "mens-shirts": "Áo nam",
    "mens-shoes": "Giày nam",
    "mens-watches": "Đồng hồ nam",
    "mobile-accessories": "Phụ kiện điện thoại",
    "motorcycle": "Xe máy",
    "skin-care": "Chăm sóc da",
    "smartphones": "Điện thoại",
    "sports-accessories": "Phụ kiện thể thao",
    "sunglasses": "Kính mát",
    "tablets": "Máy tính bảng",
    "tops": "Áo",
    "vehicle": "Xe cộ",
    "womens-bags": "Túi xách nữ",
    "womens-dresses": "Váy nữ",
    "womens-jewellery": "Trang sức nữ",
    "womens-shoes": "Giày nữ",
    "womens-watches": "Đồng hồ nữ",
}

RETAIL_CATEGORY_RULES = (
    (("lipstick", "mascara", "perfume", "fragrance", "cosmetic", "nail"), "Làm đẹp"),
    (("bag", "handbag", "purse", "rucksack", "tote"), "Túi xách"),
    (("mug", "cup", "bowl", "plate", "cutlery", "teapot", "tea", "coffee", "cake", "jar", "kitchen"), "Dụng cụ nhà bếp"),
    (("jumper", "shirt", "dress", "hat", "scarf", "sock", "apron", "glove"), "Thời trang"),
    (("card", "wrap", "paper", "notebook", "pencil", "pen", "sticker"), "Văn phòng phẩm"),
    (("clock", "watch"), "Đồng hồ và đồng hồ treo tường"),
    (("frame", "mirror"), "Khung ảnh và gương"),
    (("toy", "doll", "game"), "Đồ chơi"),
    (
        (
            "heart", "candle", "lantern", "holder", "light", "wreath", "christmas",
            "decoration", "hanging", "ornament", "doormat", "cushion", "vase",
            "tlight", "garland", "bauble",
        ),
        "Trang trí nhà",
    ),
    (("cabinet", "table", "chair", "drawer", "shelf", "stool"), "Nội thất"),
    (("towel", "soap", "bottle", "basket"), "Đồ gia dụng"),
)

DEFAULT_RETAIL_CATEGORY = "Quà tặng khác"
CATEGORY_FROM_CATALOG = "Danh mục DummyJSON"
CATEGORY_FROM_KEYWORD = "Luật từ khóa bán lẻ"
TOKEN_JACCARD_THRESHOLD = 0.85


def _normalize_product_name(value):
    normalized = unicodedata.normalize("NFKC", str(value)).casefold().strip()
    return " ".join(re.sub(r"[^\w]+", " ", normalized).split())


def _tokenize(value):
    return {token for token in _normalize_product_name(value).split() if token}


def _token_jaccard(left, right):
    if not left or not right:
        return 0.0
    intersection = len(left & right)
    union = len(left | right)
    return intersection / union if union else 0.0


def catalog_category_label(raw_category):
    if raw_category is None or (isinstance(raw_category, float) and pd.isna(raw_category)):
        return None
    key = str(raw_category).strip().casefold()
    return CATALOG_CATEGORY_LABELS.get(key, str(raw_category).replace("-", " ").strip().title())


def classify_retail_category(description):
    tokens = _tokenize(description)
    joined = " ".join(sorted(tokens))
    for keywords, label in RETAIL_CATEGORY_RULES:
        if any(keyword in tokens or keyword in joined for keyword in keywords):
            return label
    return DEFAULT_RETAIL_CATEGORY


def read_product_catalog(csv_path=PRODUCT_CATALOG_CSV):
    if not os.path.exists(csv_path):
        return None

    dataframe = pd.read_csv(csv_path, dtype={"SKU": str, "Barcode": str})
    missing_columns = set(PRODUCT_CATALOG_COLUMN_MAP) - set(dataframe.columns)
    if missing_columns:
        raise ValueError(
            "Product catalog CSV is missing required columns: "
            + ", ".join(sorted(missing_columns))
        )

    dataframe = dataframe.rename(columns=PRODUCT_CATALOG_COLUMN_MAP)
    dataframe["product_id"] = pd.to_numeric(dataframe["product_id"], errors="coerce")
    if dataframe["product_id"].isna().any() or dataframe["product_id"].duplicated().any():
        raise ValueError("Product catalog contains missing or duplicate product IDs.")

    for column in ("price", "discount_percentage", "rating", "stock", "weight", "minimum_order_quantity"):
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
    if dataframe[["title", "category", "price", "stock"]].isna().any().any():
        raise ValueError("Product catalog contains missing required values.")
    if (dataframe["price"] < 0).any() or (dataframe["stock"] < 0).any():
        raise ValueError("Product catalog contains negative prices or stock values.")

    dataframe["sku"] = dataframe["sku"].astype(str).str.strip()
    dataframe["barcode"] = dataframe["barcode"].astype(str).str.strip()
    dataframe["category_label"] = dataframe["category"].map(catalog_category_label)
    return dataframe


def _unique_lookup(series):
    counts = series[series.notna() & (series.astype(str).str.strip() != "")].value_counts()
    return {
        key: index
        for index, key in series.items()
        if key in counts.index and counts[key] == 1
    }


def _apply_catalog_fields(target, row, method):
    target.update({
        "SourceSystem": "Online Retail + DummyJSON",
        "APIProductID": int(row["product_id"]),
        "CatalogTitle": row["title"],
        "Category": row["category_label"],
        "CategorySource": CATEGORY_FROM_CATALOG,
        "CatalogPrice": row["price"],
        "CatalogDiscountPercentage": row["discount_percentage"],
        "CatalogRating": row["rating"],
        "CatalogStock": int(row["stock"]),
        "Brand": row["brand"],
        "CatalogMatchMethod": method,
    })


def build_unified_product_dimension(retail_products, product_catalog=None):
    """Hợp nhất hai nguồn: nối bản ghi khi khóa tin cậy, gán danh mục cho toàn bộ sản phẩm."""
    retail = retail_products.copy()
    retail["StockCode"] = retail["StockCode"].astype(str)
    retail["Description"] = retail["Description"].astype(str).str.slice(0, 255)
    retail["_match_name"] = retail["Description"].map(_normalize_product_name)
    retail["_tokens"] = retail["Description"].map(_tokenize)
    catalog = product_catalog.copy() if product_catalog is not None else pd.DataFrame()
    if not catalog.empty:
        catalog.columns = [str(column).strip() for column in catalog.columns]
        catalog = catalog.rename(columns={column: column.lower() for column in catalog.columns})
        if "category_label" not in catalog.columns:
            catalog["category_label"] = catalog["category"].map(catalog_category_label)
        for column in ("sku", "barcode"):
            if column not in catalog.columns:
                catalog[column] = ""
            catalog[column] = (
                catalog[column].astype(str).str.strip().replace({"nan": "", "None": "", "<NA>": ""})
            )
        catalog["_match_name"] = catalog["title"].map(_normalize_product_name)
        catalog["_tokens"] = catalog["title"].map(_tokenize)

    records = []
    retail_by_index = {}
    for index, row in retail.iterrows():
        retail_record = {
            "ProductKey": len(records) + 1,
            "StockCode": row["StockCode"],
            "Description": row["Description"],
            "UnitPrice_Standard": round(float(row["UnitPrice_Standard"]), 2),
            "SourceSystem": "Online Retail",
            "APIProductID": None,
            "CatalogTitle": None,
            "Category": classify_retail_category(row["Description"]),
            "CategorySource": CATEGORY_FROM_KEYWORD,
            "CatalogPrice": None,
            "CatalogDiscountPercentage": None,
            "CatalogRating": None,
            "CatalogStock": None,
            "Brand": None,
            "CatalogMatchMethod": None,
        }
        records.append(retail_record)
        retail_by_index[index] = retail_record

    matched_catalog_ids = set()
    matched_count = 0
    if not catalog.empty:
        retail_sku_lookup = _unique_lookup(retail["StockCode"])
        retail_name_lookup = _unique_lookup(retail["_match_name"])
        catalog_sku_lookup = _unique_lookup(catalog["sku"])
        catalog_barcode_lookup = _unique_lookup(catalog["barcode"])
        catalog_name_lookup = _unique_lookup(catalog["_match_name"])

        def try_match(catalog_index, retail_index, method):
            nonlocal matched_count
            catalog_id = int(catalog.loc[catalog_index, "product_id"])
            target = retail_by_index[retail_index]
            if catalog_id in matched_catalog_ids or target["APIProductID"] is not None:
                return False
            _apply_catalog_fields(target, catalog.loc[catalog_index], method)
            matched_catalog_ids.add(catalog_id)
            matched_count += 1
            return True

        for catalog_index, row in catalog.iterrows():
            sku = str(row["sku"]).strip()
            barcode = str(row["barcode"]).strip()
            if sku and sku in catalog_sku_lookup and sku in retail_sku_lookup:
                try_match(catalog_index, retail_sku_lookup[sku], "sku_chinh_xac")
            elif barcode and barcode in catalog_barcode_lookup and barcode in retail_sku_lookup:
                try_match(catalog_index, retail_sku_lookup[barcode], "ma_vach_chinh_xac")
            elif row["_match_name"] in catalog_name_lookup and row["_match_name"] in retail_name_lookup:
                try_match(
                    catalog_index,
                    retail_name_lookup[row["_match_name"]],
                    "ten_chuan_hoa_chinh_xac",
                )

        unmatched_catalog = [
            index for index, row in catalog.iterrows()
            if int(row["product_id"]) not in matched_catalog_ids
        ]
        unmatched_retail = [
            index for index, record in retail_by_index.items()
            if record["APIProductID"] is None
        ]
        used_retail = set()
        jaccard_candidates = []
        for catalog_index in unmatched_catalog:
            catalog_tokens = catalog.loc[catalog_index, "_tokens"]
            best_retail = None
            best_score = TOKEN_JACCARD_THRESHOLD
            ties = 0
            for retail_index in unmatched_retail:
                if retail_index in used_retail:
                    continue
                score = _token_jaccard(catalog_tokens, retail.loc[retail_index, "_tokens"])
                if score > best_score:
                    best_score = score
                    best_retail = retail_index
                    ties = 1
                elif score == best_score and best_retail is not None:
                    ties += 1
            if best_retail is not None and ties == 1:
                jaccard_candidates.append((catalog_index, best_retail, best_score))

        retail_best = {}
        for catalog_index, retail_index, score in jaccard_candidates:
            previous = retail_best.get(retail_index)
            if previous is None or score > previous[1]:
                retail_best[retail_index] = (catalog_index, score)

        for retail_index, (catalog_index, _score) in retail_best.items():
            if try_match(catalog_index, retail_index, "giao_token_duy_nhat"):
                used_retail.add(retail_index)

        for _, row in catalog.iterrows():
            if int(row["product_id"]) in matched_catalog_ids:
                continue
            records.append({
                "ProductKey": len(records) + 1,
                "StockCode": None,
                "Description": str(row["title"])[:255],
                "UnitPrice_Standard": None,
                "SourceSystem": "DummyJSON",
                "APIProductID": int(row["product_id"]),
                "CatalogTitle": row["title"],
                "Category": row["category_label"],
                "CategorySource": CATEGORY_FROM_CATALOG,
                "CatalogPrice": row["price"],
                "CatalogDiscountPercentage": row["discount_percentage"],
                "CatalogRating": row["rating"],
                "CatalogStock": int(row["stock"]),
                "Brand": row["brand"],
                "CatalogMatchMethod": None,
            })

    dimension = pd.DataFrame(records, columns=UNIFIED_PRODUCT_COLUMNS)
    for column in ("ProductKey", "CatalogStock"):
        dimension[column] = pd.to_numeric(dimension[column], errors="raise").astype("Int64")
    dimension["APIProductID"] = pd.to_numeric(
        dimension["APIProductID"], errors="coerce"
    ).astype("Int64")
    for column in (
        "UnitPrice_Standard",
        "CatalogPrice",
        "CatalogDiscountPercentage",
        "CatalogRating",
    ):
        dimension[column] = pd.to_numeric(dimension[column], errors="coerce").astype("Float64")

    stats = {
        "retail_products": len(retail),
        "catalog_products": len(catalog),
        "matched_products": matched_count,
        "catalog_only_products": len(catalog) - matched_count,
        "retail_only_products": len(retail) - matched_count,
        "categorized_products": int(dimension["Category"].notna().sum()),
    }
    return dimension, stats
