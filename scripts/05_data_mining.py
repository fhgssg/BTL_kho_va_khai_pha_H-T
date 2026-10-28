"""
File: 05_data_mining.py
Mô tả: Giai đoạn 5 - Khai phá dữ liệu chuyên sâu (Data Mining & Machine Learning)
       cho bộ dữ liệu Olist Brazilian E-Commerce:
       1. Phân khúc khách hàng RFM (Rule-based) & Phân cụm K-Means Clustering.
       2. Phân tích giỏ hàng (Market Basket Analysis) với thuật toán Apriori.
       Nguồn dữ liệu: PostgreSQL DWH (fact_sales, dim_customer, dim_product)
"""

import os
import sys
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from mlxtend.frequent_patterns import apriori, association_rules
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
from dwh_connection import get_engine

OUTPUTS_DIR = os.path.join(BASE_DIR, "outputs")


# ==============================================================================
# PHẦN 1: PHÂN KHÚC KHÁCH HÀNG RFM (RECENCY - FREQUENCY - MONETARY)
# ==============================================================================
def rfm_segmentation_and_clustering(conn, output_csv):
    print("\n" + "=" * 70)
    print("PHẦN 1: MÔ HÌNH PHÂN KHÚC KHÁCH HÀNG RFM & PHÂN CỤM K-MEANS — OLIST")
    print("=" * 70)

    # 1. Trích xuất dữ liệu giao dịch từ Fact_Sales (Olist)
    # Mỗi customer_unique_id là 1 khách hàng; độ hạt Olist: 1 order ≠ 1 invoice
    query = """
    SELECT
        c.CustomerUniqueID,
        c.CustomerCode,
        c.CustomerState,
        f.OrderID,
        f.PurchaseTimestamp,
        f.TotalRevenue
    FROM fact_sales f
    JOIN dim_customer c ON f.CustomerKey = c.CustomerKey
    """
    df_sales = pd.read_sql_query(text(query), conn)
    df_sales.columns = [
        "CustomerUniqueID", "CustomerCode", "CustomerState",
        "OrderID", "PurchaseTimestamp", "TotalRevenue",
    ]
    df_sales["PurchaseTimestamp"] = pd.to_datetime(df_sales["PurchaseTimestamp"])

    # 2. Snapshot Date
    snapshot_date = df_sales["PurchaseTimestamp"].max() + pd.Timedelta(days=1)
    print(f"- Ngày mốc phân tích (Snapshot Date): {snapshot_date.strftime('%Y-%m-%d')}")
    print(f"- Tổng số giao dịch phân tích: {len(df_sales):,} dòng")
    print(f"- Tổng số khách hàng duy nhất: {df_sales['CustomerUniqueID'].nunique():,}")

    # 3. Tính 3 chỉ số R, F, M
    # Olist: đa số khách chỉ mua 1 lần → Frequency theo số OrderID duy nhất
    rfm = df_sales.groupby("CustomerUniqueID").agg(
        CustomerState=("CustomerState", "first"),
        CustomerCode=("CustomerCode", "first"),
        LastPurchaseDate=("PurchaseTimestamp", "max"),
        Frequency=("OrderID", "nunique"),        # Số đơn hàng duy nhất
        Monetary=("TotalRevenue", "sum"),         # Tổng doanh thu BRL
    ).reset_index()

    rfm["Recency"]  = (snapshot_date - rfm["LastPurchaseDate"]).dt.days
    rfm["Monetary"] = rfm["Monetary"].round(2)

    print("\nThống kê mô tả chỉ số RFM:")
    print(rfm[["Recency", "Frequency", "Monetary"]].describe().round(2))

    # 4. Chấm điểm ngũ vị phân (Quantiles 1 - 5)
    rfm["R_Score"] = pd.qcut(rfm["Recency"], q=5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F_Score"] = pd.qcut(rfm["Frequency"].rank(method="first"), q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M_Score"] = pd.qcut(rfm["Monetary"].rank(method="first"),  q=5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["RFM_Group"] = rfm["R_Score"].astype(str) + rfm["F_Score"].astype(str) + rfm["M_Score"].astype(str)
    rfm["RFM_Score"] = rfm["R_Score"] + rfm["F_Score"] + rfm["M_Score"]

    # 5. Phân nhóm theo nghiệp vụ (Rule-Based)
    def assign_rfm_segment(row):
        r, f, m = row["R_Score"], row["F_Score"], row["M_Score"]
        if r >= 4 and f >= 4 and m >= 4:
            return "Champions (VIP)"
        elif r >= 3 and f >= 3 and m >= 3:
            return "Loyal Customers (Trung thành)"
        elif r >= 4 and f <= 2:
            return "New / Potential Loyalists (Mới & Tiềm năng)"
        elif r >= 3 and f <= 3:
            return "Promising (Hứa hẹn)"
        elif r == 2 and f >= 3:
            return "At Risk (Có nguy cơ rời bỏ)"
        elif r == 1 and f >= 4:
            return "Can't Lose Them (VIP sắp mất)"
        elif r <= 2 and f <= 2:
            return "Hibernating / Lost (Ngủ đông / Đã mất)"
        else:
            return "Need Attention (Cần chăm sóc)"

    rfm["Segment"] = rfm.apply(assign_rfm_segment, axis=1)

    print("\nPhân bổ số lượng khách hàng theo từng phân khúc RFM:")
    segment_summary = rfm.groupby("Segment").agg(
        CustomerCount=("CustomerUniqueID", "count"),
        AvgRecency=("Recency", "mean"),
        AvgFrequency=("Frequency", "mean"),
        AvgMonetary=("Monetary", "mean"),
        TotalRevenue=("Monetary", "sum"),
    ).round(2).sort_values("TotalRevenue", ascending=False)
    segment_summary["CustomerShare_Pct"] = (segment_summary["CustomerCount"] / len(rfm) * 100).round(2)
    segment_summary["RevenueShare_Pct"]  = (segment_summary["TotalRevenue"] / rfm["Monetary"].sum() * 100).round(2)
    print(segment_summary[[
        "CustomerCount", "CustomerShare_Pct", "TotalRevenue",
        "RevenueShare_Pct", "AvgRecency", "AvgFrequency", "AvgMonetary",
    ]])

    # 6. K-Means Clustering
    print("\nTiến hành gom cụm không giám sát K-Means Clustering...")
    rfm_values = rfm[["Recency", "Frequency", "Monetary"]].clip(lower=0).to_numpy()
    train_indices, test_indices = train_test_split(
        np.arange(len(rfm_values)), test_size=0.2, random_state=42
    )
    rfm_log    = np.log1p(rfm_values)
    log_scaler = StandardScaler().fit(rfm_log[train_indices])
    rfm_scaled = log_scaler.transform(rfm_log)
    train_scaled = rfm_scaled[train_indices]
    test_scaled  = rfm_scaled[test_indices]

    # Để tính toán nhanh chóng trên 94k dòng (tránh O(N^2) silhouette trên 75k dòng), lấy sample 10k để tính Silhouette
    eval_sample_size = min(10000, len(train_scaled))
    np.random.seed(42)
    sample_train_idx = np.random.choice(len(train_scaled), eval_sample_size, replace=False)
    sample_test_idx = np.random.choice(len(test_scaled), min(5000, len(test_scaled)), replace=False)

    k_range               = range(2, 9)
    wcss_values           = []
    train_silhouette_values = []
    evaluation_rows       = []
    print(f"\n  {'k':>3} | {'Train Inertia':>16} | {'Train Silhouette (Sample)':>26} | {'Test Silhouette (Sample)':>25}")
    print("  " + "-" * 80)
    for k in k_range:
        km = KMeans(n_clusters=k, random_state=42, n_init=5)
        train_labels = km.fit_predict(train_scaled)
        test_labels  = km.predict(test_scaled)
        wcss        = km.inertia_
        train_sil   = silhouette_score(train_scaled[sample_train_idx], train_labels[sample_train_idx])
        test_sil    = silhouette_score(test_scaled[sample_test_idx],  test_labels[sample_test_idx])
        wcss_values.append(wcss)
        train_silhouette_values.append(train_sil)
        evaluation_rows.append({
            "Model": "KMeans_log1p", "K": k,
            "Train_Silhouette": train_sil, "Test_Silhouette": test_sil,
        })
        print(f"  {k:>3} | {wcss:>16,.2f} | {train_sil:>26.4f} | {test_sil:>25.4f}")

    # Baseline: raw RFM không log
    raw_scaler       = StandardScaler().fit(rfm_values[train_indices])
    raw_train_scaled = raw_scaler.transform(rfm_values[train_indices])
    raw_test_scaled  = raw_scaler.transform(rfm_values[test_indices])
    baseline         = KMeans(n_clusters=2, random_state=42, n_init=5).fit(raw_train_scaled)
    evaluation_rows.append({
        "Model": "Baseline_KMeans_raw_RFM", "K": 2,
        "Train_Silhouette": silhouette_score(train_scaled[sample_train_idx], baseline.labels_[sample_train_idx]),
        "Test_Silhouette":  silhouette_score(test_scaled[sample_test_idx],  baseline.predict(raw_test_scaled)[sample_test_idx]),
    })
    eval_path = os.path.join(OUTPUTS_DIR, "kmeans_holdout_evaluation.csv")
    pd.DataFrame(evaluation_rows).to_csv(eval_path, index=False)
    print(f"\n  → Đã lưu kết quả holdout: '{eval_path}'")

    # Chọn K=4 theo mục tiêu nghiệp vụ 4 nhóm khách hàng
    best_k = 4
    k4_idx = best_k - k_range.start
    selected_train_sil = train_silhouette_values[k4_idx]
    selected_test_sil  = next(r["Test_Silhouette"] for r in evaluation_rows
                               if r["Model"] == "KMeans_log1p" and r["K"] == best_k)
    rfm_scaled_final   = StandardScaler().fit_transform(rfm_log)

    print(f"\n  [SO SÁNH BASELINE vs MÔ HÌNH ĐỀ XUẤT]")
    print(f"  + Baseline (K-Means Raw RFM, k=2): Train Silhouette = {evaluation_rows[-1]['Train_Silhouette']:.4f}")
    print(f"  + Đề xuất (K-Means Log-RFM, k={best_k}): Train Silhouette = {selected_train_sil:.4f}, "
          f"Test Silhouette = {selected_test_sil:.4f}")

    # Biểu đồ Elbow & Silhouette
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    ax1.plot(list(k_range), wcss_values, "bo-", linewidth=2, markersize=8)
    ax1.axvline(x=best_k, color="red", linestyle="--", alpha=0.7, label=f"k = {best_k}")
    ax1.set_xlabel("Số cụm (k)"); ax1.set_ylabel("WCSS (Inertia)")
    ax1.set_title("Elbow Method — K-Means log-RFM (Olist)", fontweight="bold")
    ax1.legend(); ax1.grid(True, alpha=0.3)

    ax2.plot(list(k_range), train_silhouette_values, "gs-", linewidth=2, markersize=8)
    ax2.axvline(x=best_k, color="red", linestyle="--", alpha=0.7, label=f"k = {best_k}")
    ax2.set_xlabel("Số cụm (k)"); ax2.set_ylabel("Silhouette Score")
    ax2.set_title("Silhouette — Chọn K tối ưu (Olist)", fontweight="bold")
    ax2.legend(); ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    elbow_path = os.path.join(OUTPUTS_DIR, "elbow_silhouette_chart.png")
    plt.savefig(elbow_path, dpi=150, bbox_inches="tight"); plt.close()
    print(f"\n  📊 Biểu đồ Elbow & Silhouette → '{elbow_path}'")

    # Áp dụng K-Means k=best_k
    kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
    rfm["KMeans_Cluster"] = kmeans.fit_predict(rfm_scaled_final)

    cluster_monetary = rfm.groupby("KMeans_Cluster")["Monetary"].mean().sort_values()
    cluster_rank     = {c: i for i, c in enumerate(cluster_monetary.index)}
    value_names      = {2: ["Lower Value", "Higher Value"],
                        3: ["Low Value", "Moderate Value", "High Value"],
                        4: ["Low Value", "Moderate Value", "High Value", "Super VIP"]
                        }.get(best_k, [f"Tier {i+1}" for i in range(best_k)])
    cluster_labels   = {r: f"Cluster {r+1} - {n}" for r, n in enumerate(value_names)}
    rfm["KMeans_Label"] = rfm["KMeans_Cluster"].map(cluster_rank).map(cluster_labels)

    # Scatter plot phân bố cụm
    fig2, ax3 = plt.subplots(figsize=(10, 7))
    colors = ["#3498db", "#2ecc71", "#f39c12", "#e74c3c"]
    for cid in sorted(rfm["KMeans_Cluster"].unique()):
        mask  = rfm["KMeans_Cluster"] == cid
        rank  = cluster_rank.get(cid, cid)
        label = cluster_labels.get(rank, f"Cluster {cid}")
        color = colors[rank] if rank < len(colors) else "#95a5a6"
        ax3.scatter(
            np.log1p(rfm.loc[mask, "Frequency"]),
            np.log1p(rfm.loc[mask, "Monetary"].clip(lower=0)),
            c=color, label=label, alpha=0.6, s=30,
            edgecolors="white", linewidth=0.3,
        )
    ax3.set_xlabel("log(1 + Frequency)"); ax3.set_ylabel("log(1 + Monetary) [BRL]")
    ax3.set_title(f"Phân bố cụm K-Means (k={best_k}) — Olist Customers", fontweight="bold")
    ax3.legend(title="Cụm khách hàng", fontsize=9); ax3.grid(True, alpha=0.3)
    plt.tight_layout()
    scatter_path = os.path.join(OUTPUTS_DIR, "kmeans_clusters_scatter.png")
    plt.savefig(scatter_path, dpi=150, bbox_inches="tight"); plt.close()
    print(f"  📊 Biểu đồ phân bố cụm K-Means → '{scatter_path}'")

    # Kiểm tra độ ổn định cụm (dùng sample 10k để tính Silhouette nhanh)
    print(f"\n  Kiểm tra độ ổn định cụm (Stability Test, k={best_k}, 5 seeds):")
    sample_full_idx = np.random.choice(len(rfm_scaled_final), min(10000, len(rfm_scaled_final)), replace=False)
    stability_labels = []
    for seed in [0, 7, 42, 123, 2024]:
        km_s   = KMeans(n_clusters=best_k, random_state=seed, n_init=5)
        lbl    = km_s.fit_predict(rfm_scaled_final)
        sil    = silhouette_score(rfm_scaled_final[sample_full_idx], lbl[sample_full_idx])
        print(f"    Seed {seed:>5}: Silhouette = {sil:.4f}")
        stability_labels.append(lbl)

    from scipy.optimize import linear_sum_assignment
    ref = stability_labels[0]
    agreements = []
    for other in stability_labels[1:]:
        cnt = np.zeros((best_k, best_k), dtype=int)
        for a, b in zip(ref, other):
            cnt[a, b] += 1
        ri, ci   = linear_sum_assignment(-cnt)
        agreements.append(sum(cnt[r, c] for r, c in zip(ri, ci)) / len(ref))
    avg_agree = np.mean(agreements)
    print(f"  → Tỷ lệ đồng thuận trung bình: {avg_agree:.2%} "
          f"({'✅ Ổn định' if avg_agree >= 0.90 else '⚠️ Kém ổn định'})")

    rfm.to_csv(output_csv, index=False)
    print(f"\n→ Đã lưu kết quả phân khúc RFM → '{output_csv}'")
    return rfm


# ==============================================================================
# PHẦN 2: PHÂN TÍCH GIỎ HÀNG — MARKET BASKET ANALYSIS (APRIORI)
# Lưu ý Olist: Mỗi order thường chỉ chứa 1 sản phẩm → tỷ lệ multi-item thấp hơn.
# Cần min_support thấp (0.005) để tìm đủ luật có ý nghĩa.
# ==============================================================================
def market_basket_analysis(conn, output_csv, min_support=0.005, min_lift=1.2):
    print("\n" + "=" * 70)
    print("PHẦN 2: PHÂN TÍCH GIỎ HÀNG (MARKET BASKET ANALYSIS - APRIORI) — OLIST")
    print("=" * 70)

    # Trích xuất giao dịch: OrderID × CategoryNameEN (dùng category thay vì product_id đơn lẻ)
    # Olist: số lượng sản phẩm trùng lặp trong 1 order rất thấp → MBA ở cấp category
    query = """
    SELECT
        f.OrderID,
        COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown') AS Category
    FROM fact_sales f
    JOIN dim_product p ON f.ProductKey = p.ProductKey
    WHERE COALESCE(p.CategoryNameEN, p.CategoryNamePT, 'unknown') != 'unknown'
    """
    df_items = pd.read_sql_query(text(query), conn)
    df_items.columns = ["OrderID", "Category"]
    print(f"- Số dòng items phân tích: {len(df_items):,}")

    # Lọc đơn có >= 2 category
    order_cat_counts  = df_items.groupby("OrderID")["Category"].nunique()
    valid_orders      = order_cat_counts[order_cat_counts >= 2].index
    df_filtered       = df_items[df_items["OrderID"].isin(valid_orders)]
    print(f"- Số đơn có ≥ 2 category: {len(valid_orders):,} đơn ({len(valid_orders)/len(order_cat_counts)*100:.1f}%)")

    if len(valid_orders) < 100:
        print("  ⚠️  Quá ít đơn multi-category. Thực hiện MBA trên toàn bộ đơn (single + multi).")
        df_filtered = df_items

    # Xây dựng Transaction Matrix
    print("  → Đang xây dựng ma trận giỏ hàng One-Hot Transaction Matrix...")
    basket = (
        df_filtered.groupby(["OrderID", "Category"])["Category"]
        .count().unstack().fillna(0).reset_index().set_index("OrderID")
    )
    basket_sets = (basket > 0)
    print(f"     + Ma trận: {basket_sets.shape[0]:,} đơn hàng × {basket_sets.shape[1]:,} category")

    # Chạy Apriori
    print(f"  → Chạy Apriori (min_support={min_support}, {min_support*100:.1f}%)...")
    try:
        frequent_itemsets = apriori(basket_sets, min_support=min_support, use_colnames=True)
        frequent_itemsets["length"] = frequent_itemsets["itemsets"].apply(len)
        print(f"     + Tìm thấy {len(frequent_itemsets):,} tập category phổ biến")

        if len(frequent_itemsets) == 0:
            print("  ⚠️  Không tìm thấy tập phổ biến. Giảm min_support và thử lại.")
            return pd.DataFrame()

        rules = association_rules(frequent_itemsets, metric="lift", min_threshold=min_lift)
        rules["antecedents_str"] = rules["antecedents"].apply(lambda x: ", ".join(sorted(list(x))))
        rules["consequents_str"] = rules["consequents"].apply(lambda x: ", ".join(sorted(list(x))))
        rules = rules.sort_values(["lift", "confidence"], ascending=[False, False])

        print(f"\n→ Đã khai phá {len(rules):,} luật kết hợp có ý nghĩa kinh doanh!")
        print("\nTOP 10 LUẬT KẾT HỢP GỢI Ý BÁN CHÉO MẠNH NHẤT (HIGHEST LIFT):")
        print("-" * 70)
        for i, (_, row) in enumerate(rules.head(10).iterrows()):
            print(f"Luật {i+1}:")
            print(f"  - Nếu mua danh mục: [{row['antecedents_str']}]")
            print(f"  - Gợi ý mua thêm  : [{row['consequents_str']}]")
            print(f"  - Support: {row['support']*100:.2f}% | Confidence: {row['confidence']*100:.2f}% | Lift: {row['lift']:.2f}")
            print()

        rules_save = rules[[
            "antecedents_str", "consequents_str",
            "antecedent support", "consequent support",
            "support", "confidence", "lift", "leverage", "conviction",
        ]]
        rules_save.to_csv(output_csv, index=False)
        print(f"→ Đã lưu {len(rules):,} luật kết hợp → '{output_csv}'")
        return rules

    except Exception as e:
        print(f"  ❌ Lỗi MBA: {e}")
        return pd.DataFrame()


# ==============================================================================
# HÀM CHÍNH ĐIỀU PHỐI
# ==============================================================================
def run_data_mining():
    os.makedirs(OUTPUTS_DIR, exist_ok=True)
    rfm_output    = os.path.join(OUTPUTS_DIR, "rfm_customer_segments.csv")
    basket_output = os.path.join(OUTPUTS_DIR, "market_basket_rules.csv")

    engine = get_engine()
    with engine.connect() as conn:
        rfm_segmentation_and_clustering(conn, rfm_output)
        market_basket_analysis(conn, basket_output, min_support=0.005, min_lift=1.2)

    print("\n" + "=" * 70)
    print("✅ HOÀN THÀNH GIAI ĐOẠN 5: KHAI PHÁ DỮ LIỆU & MACHINE LEARNING — OLIST!")
    print("=" * 70)


if __name__ == "__main__":
    run_data_mining()
