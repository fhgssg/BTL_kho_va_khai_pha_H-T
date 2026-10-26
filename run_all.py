"""
================================================================================
SCRIPT ĐIỀU PHỐI KHỞI CHẠY DỰ ÁN 1 LỆNH (ONE-COMMAND MASTER RUNNER)
Dự án: Online Retail Data Lakehouse, DWH & Analytics
================================================================================
Chỉ cần chạy:
    python run_all.py

Hoặc trên Windows:
    run.bat
    .\run.ps1
================================================================================
"""

import os
import sys
import time
import socket
import argparse
import subprocess
import webbrowser

# Thiết lập UTF-8 cho Windows console và các subprocess
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def print_banner():
    banner = """
================================================================================
  🛍️  ONLINE RETAIL DATA LAKEHOUSE & ANALYTICS PIPELINE
      Hồ Dữ Liệu MinIO -> PostgreSQL DWH -> OLAP & Mining -> Streamlit
================================================================================
    """
    print(banner)


def run_step(step_name, command, check_error=True):
    print(f"\n{'='*80}")
    print(f"  👉 [THỰC THI] {step_name}")
    print(f"     Lệnh: {' '.join(command) if isinstance(command, list) else command}")
    print(f"{'='*80}\n")
    start_time = time.time()
    
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    ret = subprocess.run(command, cwd=BASE_DIR, env=env)
    elapsed = time.time() - start_time
    
    if ret.returncode != 0:
        print(f"\n❌ [LỖI] Bước '{step_name}' thất bại (Mã lỗi: {ret.returncode}) sau {elapsed:.1f}s!")
        if check_error:
            sys.exit(ret.returncode)
        return False
    
    print(f"\n✅ [HOÀN THÀNH] {step_name} thành công trong {elapsed:.1f} giây.")
    return True


def check_port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def wait_for_services(timeout=30):
    print("\n⏳ Đang kiểm tra trạng thái khởi động của MinIO (9000) và PostgreSQL (5432)...")
    start = time.time()
    pg_ready = False
    minio_ready = False
    
    while time.time() - start < timeout:
        if not pg_ready and check_port_open("localhost", 5432):
            pg_ready = True
            print("   ✅ PostgreSQL DWH (localhost:5432) đã sẵn sàng kết nối!")
        if not minio_ready and check_port_open("localhost", 9000):
            minio_ready = True
            print("   ✅ MinIO S3 API (localhost:9000) đã sẵn sàng kết nối!")
            
        if pg_ready and minio_ready:
            print("🎉 Toàn bộ hạ tầng Docker Container đã sẵn sàng hoạt động!\n")
            return True
        time.sleep(1.5)
        
    if not (pg_ready and minio_ready):
        print("⚠️ Cảnh báo: Một số dịch vụ Docker chưa phản hồi cổng trong thời gian chờ.")
    return False


def check_docker_installed():
    try:
        ret = subprocess.run(["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return ret.returncode == 0
    except FileNotFoundError:
        return False


def main():
    parser = argparse.ArgumentParser(description="Chạy tự động toàn bộ đồ án Online Retail Lakehouse.")
    parser.add_argument("--sqlite", action="store_true", help="Chạy luồng cục bộ SQLite (không dùng Docker)")
    parser.add_argument("--skip-etl", action="store_true", help="Bỏ qua bước ETL nếu dữ liệu đã được nạp")
    parser.add_argument("--only-dashboard", action="store_true", help="Chỉ mở Streamlit Dashboard")
    args = parser.parse_args()

    print_banner()
    py = sys.executable

    # Nếu chỉ muốn chạy dashboard
    if args.only_dashboard:
        print("🚀 Khởi chạy Streamlit Dashboard...")
        subprocess.run([py, "-m", "streamlit", "run", "app.py"], cwd=BASE_DIR)
        return

    # Luồng SQLite (không cần Docker)
    if args.sqlite:
        print("\n⚙️  CHẾ ĐỘ DỰ PHÒNG: SỬ DỤNG SQLITE (LOCAL)...")
        os.environ["DWH_DATABASE_URL"] = "sqlite:///database/retail_dwh.db"
        
        if not args.skip_etl:
            run_step("1. Làm sạch dữ liệu (EDA & Cleaning)", [py, "scripts/01_eda_and_cleaning.py"])
            run_step("2. Nạp dữ liệu vào SQLite DWH", [py, "scripts/03_etl_pipeline.py"])
        
        run_step("3. Chạy các truy vấn OLAP", [py, "scripts/04_run_olap_queries.py"])
        run_step("4. Khai phá dữ liệu (RFM & Apriori)", [py, "scripts/05_data_mining.py"])
        
        print("\n" + "="*80)
        print("🎉 HOÀN THÀNH TOÀN BỘ PIPELINE SQLITE! Đang mở Streamlit Dashboard...")
        print("="*80)
        subprocess.run([py, "-m", "streamlit", "run", "app.py"], cwd=BASE_DIR)
        return

    # Luồng chính: DATA LAKEHOUSE (MinIO + PostgreSQL)
    print("🚀 CHẾ ĐỘ CHÍNH: MODERN DATA LAKEHOUSE (MinIO S3 + PostgreSQL DWH)")
    
    if not check_docker_installed():
        print("\n❌ LỖI: Docker Desktop chưa được bật hoặc chưa cài đặt trên máy!")
        print("   -> Bạn có thể khởi động Docker Desktop rồi chạy lại lệnh.")
        print("   -> Hoặc nếu không muốn dùng Docker, hãy chạy chế độ SQLite: python run_all.py --sqlite\n")
        sys.exit(1)

    # Bước 1: Bật Docker Container
    run_step("Bước 1: Khởi động MinIO và PostgreSQL qua Docker Compose", 
             ["docker", "compose", "up", "-d", "minio", "postgres"])
    wait_for_services(timeout=30)

    # Bước 2: Tích hợp API Thương Mại Điện Tử (DummyJSON E-Commerce REST API)
    if not args.skip_etl:
        run_step("Bước 2: Trích xuất danh mục và đánh giá từ E-Commerce REST API", 
                 [py, "scripts/07_api_enrichment.py"])

        # Bước 3: Đường ống Lakehouse ETL
        run_step("Bước 3: Đường ống Lakehouse (MinIO raw -> staging -> curated -> PostgreSQL)", 
                 [py, "scripts/06_lakehouse_minio_postgres_etl.py"])

    # Bước 4: Kiểm thử và đối soát kho dữ liệu
    run_step("Bước 4: Kiểm thử chất lượng & đối soát dữ liệu (Reconciliation 25 Test Cases)", 
             [py, "scripts/03b_dwh_test_reconciliation.py"])

    # Bước 5: Chạy các truy vấn phân tích đa chiều OLAP
    run_step("Bước 5: Báo cáo phân tích kinh doanh đa chiều OLAP", 
             [py, "scripts/04_run_olap_queries.py"])

    # Bước 6: Khai phá dữ liệu (RFM + K-Means + Apriori)
    run_step("Bước 6: Khai phá dữ liệu Machine Learning (RFM & Market Basket)", 
             [py, "scripts/05_data_mining.py"])

    # Bước 7: Mở Streamlit Dashboard
    print("\n" + "="*80)
    print("🎉 TOÀN BỘ QUÁ TRÌNH THỰC THI HOÀN TẤT THÀNH CÔNG 100%!")
    print("   👉 MinIO Console:      http://localhost:9001 (User: minioadmin / Pass: minioadmin123)")
    print("   👉 PostgreSQL DWH:     localhost:5432 (User: dataeng / Pass: dataeng123 / DB: dwh)")
    print("   👉 Streamlit Dashboard: http://localhost:8501")
    print("="*80 + "\n")
    
    subprocess.run([py, "-m", "streamlit", "run", "app.py"], cwd=BASE_DIR)


if __name__ == "__main__":
    main()
