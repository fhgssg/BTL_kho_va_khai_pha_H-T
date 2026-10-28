"""
Tải và kiểm tra catalog sản phẩm DummyJSON.

Catalog được hợp nhất vào Dim_Product cùng nguồn giao dịch Online Retail:
nối bản ghi khi có khóa tin cậy, gán danh mục phân tích dùng chung, rồi mới
chạy OLAP và dashboard.
"""

import json
import os
from datetime import datetime, timezone

import pandas as pd
import requests

BASE_URL = "https://dummyjson.com/products"
PAGE_SIZE = 100
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
RAW_SNAPSHOT = os.path.join(RAW_DIR, "products_raw.json")
OUTPUT_CSV = os.path.join(BASE_DIR, "outputs", "products_catalog.csv")

PRODUCT_FIELDS = (
    "id",
    "title",
    "description",
    "category",
    "price",
    "discountPercentage",
    "rating",
    "stock",
    "brand",
    "sku",
    "weight",
    "warrantyInformation",
    "shippingInformation",
    "availabilityStatus",
    "minimumOrderQuantity",
)

CSV_COLUMNS = (
    "ProductID",
    "Title",
    "Description",
    "Category",
    "Price",
    "DiscountPercentage",
    "Rating",
    "Stock",
    "Brand",
    "SKU",
    "Weight",
    "WarrantyInformation",
    "ShippingInformation",
    "AvailabilityStatus",
    "MinimumOrderQuantity",
    "CreatedAt",
    "UpdatedAt",
    "Barcode",
)


def fetch_and_validate() -> tuple[pd.DataFrame, dict]:
    """Fetch every page and validate the product records before saving."""
    extracted_at = datetime.now(timezone.utc).isoformat()
    products = []
    total = None
    skip = 0

    while total is None or skip < total:
        response = requests.get(
            BASE_URL,
            params={"limit": PAGE_SIZE, "skip": skip},
            timeout=20,
        )
        response.raise_for_status()
        page = response.json()

        page_products = page.get("products")
        page_total = page.get("total")
        if (
            not isinstance(page_products, list)
            or not isinstance(page_total, int)
            or page.get("skip") != skip
        ):
            raise ValueError("DummyJSON response is missing a products list or total count.")
        if total is None:
            total = page_total
        elif page_total != total:
            raise ValueError("DummyJSON total changed while the catalog was being fetched.")
        if not page_products and skip < total:
            raise ValueError(f"DummyJSON returned an empty page before all records were fetched (skip={skip}).")

        products.extend(page_products)
        skip += len(page_products)

    if not products or len(products) != total:
        raise ValueError(f"Expected {total} products from DummyJSON, received {len(products)}.")

    product_ids = []
    records = []
    for product in products:
        missing_fields = [field for field in ("id", "title", "category", "price", "stock") if field not in product]
        if missing_fields:
            raise ValueError(f"DummyJSON product is missing required fields: {', '.join(missing_fields)}")
        product_ids.append(product["id"])
        meta = product.get("meta") or {}
        records.append({
            "ProductID": product["id"],
            "Title": product["title"],
            "Description": product.get("description"),
            "Category": product["category"],
            "Price": product["price"],
            "DiscountPercentage": product.get("discountPercentage"),
            "Rating": product.get("rating"),
            "Stock": product["stock"],
            "Brand": product.get("brand"),
            "SKU": product.get("sku"),
            "Weight": product.get("weight"),
            "WarrantyInformation": product.get("warrantyInformation"),
            "ShippingInformation": product.get("shippingInformation"),
            "AvailabilityStatus": product.get("availabilityStatus"),
            "MinimumOrderQuantity": product.get("minimumOrderQuantity"),
            "CreatedAt": meta.get("createdAt"),
            "UpdatedAt": meta.get("updatedAt"),
            "Barcode": meta.get("barcode"),
        })

    if len(set(product_ids)) != len(product_ids):
        raise ValueError("DummyJSON returned duplicate product IDs.")

    dataframe = pd.DataFrame.from_records(records, columns=CSV_COLUMNS)
    if dataframe[["ProductID", "Title", "Category", "Price", "Stock"]].isna().any().any():
        raise ValueError("DummyJSON catalog has missing required values.")
    for column in ("ProductID", "Price", "Stock"):
        dataframe[column] = pd.to_numeric(dataframe[column], errors="coerce")
    if dataframe[["ProductID", "Price", "Stock"]].isna().any().any():
        raise ValueError("DummyJSON catalog contains non-numeric product IDs, prices, or stock values.")
    if (dataframe["Price"] < 0).any():
        raise ValueError("DummyJSON catalog contains a negative product price.")
    if (dataframe["Stock"] < 0).any():
        raise ValueError("DummyJSON catalog contains a negative stock value.")
    ratings = pd.to_numeric(dataframe["Rating"], errors="coerce").dropna()
    if not ratings.between(0, 5).all():
        raise ValueError("DummyJSON catalog contains a rating outside the expected 0–5 range.")

    snapshot = {
        "metadata": {
            "extracted_at": extracted_at,
            "endpoint": BASE_URL,
            "status": "SUCCESS",
            "record_count": len(records),
            "fields": list(PRODUCT_FIELDS) + ["meta.createdAt", "meta.updatedAt", "meta.barcode"],
            "note": "Catalog được hợp nhất vào Dim_Product; chỉ nối bản ghi khi SKU, mã vạch hoặc tên khớp tin cậy.",
        },
        "products": [
            {field: product.get(field) for field in PRODUCT_FIELDS}
            | {
                "meta": {
                    key: (product.get("meta") or {}).get(key)
                    for key in ("createdAt", "updatedAt", "barcode")
                }
            }
            for product in products
        ],
    }
    return dataframe, snapshot


def main() -> None:
    dataframe, snapshot = fetch_and_validate()
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(os.path.dirname(OUTPUT_CSV), exist_ok=True)

    with open(RAW_SNAPSHOT, "w", encoding="utf-8") as snapshot_file:
        json.dump(snapshot, snapshot_file, ensure_ascii=False, indent=2)
    dataframe.to_csv(OUTPUT_CSV, index=False)
    print(f"Fetched and validated {len(dataframe):,} DummyJSON products.")
    print(f"Raw snapshot: {RAW_SNAPSHOT}")
    print(f"Catalog CSV: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
