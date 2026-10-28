param(
    [switch]$SkipSuperset,
    [switch]$SkipDashboard,
    [switch]$SkipProductCatalog,
    [switch]$ValidateOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$RequirementsPath = Join-Path $ProjectRoot "requirements.txt"
$DataPath = Join-Path $ProjectRoot "data\raw\olist_orders_dataset.csv"
$VenvPath = Join-Path $ProjectRoot ".venv"
$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$RequirementsMarker = Join-Path $VenvPath ".requirements-sha256"

function Invoke-ExternalCommand {
    param(
        [Parameter(Mandatory = $true)][string]$Executable,
        [Parameter(Mandatory = $true)][string[]]$Arguments,
        [Parameter(Mandatory = $true)][string]$Description
    )

    Write-Host "`n>>> $Description" -ForegroundColor Cyan
    & $Executable @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description thất bại (exit code $LASTEXITCODE). Đã dừng quy trình."
    }
}

function Test-TcpPort {
    param([int]$Port)

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $pending = $client.BeginConnect("127.0.0.1", $Port, $null, $null)
        if (-not $pending.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($pending)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Wait-ContainerHealthy {
    param(
        [Parameter(Mandatory = $true)][string]$ContainerName,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $state = & docker inspect --format "{{.State.Status}}" $ContainerName 2>$null
        if ($LASTEXITCODE -eq 0) {
            $state = ([string]$state).Trim()
            if ($state -eq "running") {
                $health = & docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerName 2>$null
                if ($LASTEXITCODE -eq 0 -and (([string]$health).Trim() -eq "healthy" -or ([string]$health).Trim() -eq "none")) {
                    Write-Host "  $ContainerName sẵn sàng." -ForegroundColor Green
                    return
                }
                if ($LASTEXITCODE -eq 0 -and ([string]$health).Trim() -eq "unhealthy") {
                    throw "Container $ContainerName ở trạng thái unhealthy. Kiểm tra bằng: docker compose logs $ContainerName"
                }
            }
            elseif ($state -eq "exited" -or $state -eq "dead") {
                throw "Container $ContainerName đã dừng. Kiểm tra bằng: docker compose logs $ContainerName"
            }
        }
        Start-Sleep -Seconds 3
    }

    throw "Hết thời gian chờ container $ContainerName sẵn sàng sau $TimeoutSeconds giây."
}

function Wait-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Url,
        [Parameter(Mandatory = $true)][string]$Description,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($response.StatusCode -eq 200) {
                Write-Host "  $Description sẵn sàng: $Url" -ForegroundColor Green
                return
            }
        }
        catch {
            Start-Sleep -Seconds 3
        }
    }

    throw "$Description chưa phản hồi tại $Url sau $TimeoutSeconds giây."
}

Push-Location $ProjectRoot
try {
    Write-Host "=== Khởi chạy dự án Retail DWH ===" -ForegroundColor Green

    if (-not (Test-Path $RequirementsPath)) {
        throw "Không tìm thấy requirements.txt trong thư mục dự án."
    }
    if (-not (Test-Path $DataPath)) {
        throw "Thiếu dữ liệu nguồn Olist: data\raw\olist_orders_dataset.csv. Hãy tải đủ 6 file CSV từ Kaggle Brazilian E-Commerce rồi chạy lại."
    }

    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if ($null -eq $dockerCommand) {
        throw "Không tìm thấy Docker. Hãy cài Docker Desktop, mở Docker Desktop rồi chạy lại."
    }
    & docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        throw "Docker chưa chạy hoặc chưa sẵn sàng. Hãy mở Docker Desktop, đợi khởi động xong rồi chạy lại."
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -eq $pythonCommand) {
        $pythonCommand = Get-Command py -ErrorAction SilentlyContinue
    }
    if ($null -eq $pythonCommand) {
        throw "Không tìm thấy Python. Hãy cài Python 3.10 trở lên và thêm vào PATH."
    }

    if (-not (Test-Path $VenvPython)) {
        if ($pythonCommand.Name -eq "py.exe" -or $pythonCommand.Name -eq "py") {
            Invoke-ExternalCommand $pythonCommand.Source @("-3", "-m", "venv", $VenvPath) "Tạo môi trường Python"
        }
        else {
            Invoke-ExternalCommand $pythonCommand.Source @("-m", "venv", $VenvPath) "Tạo môi trường Python"
        }
    }

    Invoke-ExternalCommand $VenvPython @("-c", "import sys; print('Python', sys.version.split()[0]); raise SystemExit(0 if sys.version_info >= (3, 10) else 'Python 3.10 trở lên là bắt buộc')") "Kiểm tra phiên bản Python"

    $requirementsHash = (Get-FileHash -Path $RequirementsPath -Algorithm SHA256).Hash
    $installedHash = ""
    if (Test-Path $RequirementsMarker) {
        $installedHash = (Get-Content -Path $RequirementsMarker -Raw).Trim()
    }
    if ($requirementsHash -ne $installedHash) {
        Invoke-ExternalCommand $VenvPython @("-m", "pip", "install", "-r", $RequirementsPath) "Cài đặt/cập nhật thư viện Python"
        Set-Content -Path $RequirementsMarker -Value $requirementsHash -NoNewline
    }
    else {
        Write-Host "Thư viện Python đã khớp requirements.txt; bỏ qua cài đặt." -ForegroundColor Green
    }

    if ($ValidateOnly) {
        Write-Host "`nKiểm tra trước thành công. Chưa khởi động container hoặc chạy ETL." -ForegroundColor Green
        return
    }

    if ($SkipSuperset) {
        Invoke-ExternalCommand "docker" @("compose", "up", "-d", "minio", "minio-init", "postgres") "Khởi động MinIO và PostgreSQL"
    }
    else {
        Invoke-ExternalCommand "docker" @("compose", "up", "-d", "--build") "Khởi động MinIO, PostgreSQL và Superset"
    }

    Wait-ContainerHealthy "dwh_minio"
    Wait-ContainerHealthy "dwh_postgres"

    $initDeadline = (Get-Date).AddSeconds(60)
    $initFinished = $false
    while ((Get-Date) -lt $initDeadline) {
        $initState = & docker inspect --format "{{.State.Status}}" dwh_minio_init 2>$null
        if ($LASTEXITCODE -eq 0 -and ([string]$initState).Trim() -eq "exited") {
            $initCode = & docker inspect --format "{{.State.ExitCode}}" dwh_minio_init 2>$null
            if ($LASTEXITCODE -ne 0 -or ([string]$initCode).Trim() -ne "0") {
                throw "Khởi tạo bucket MinIO thất bại. Kiểm tra bằng: docker compose logs minio-init"
            }
            $initFinished = $true
            break
        }
        Start-Sleep -Seconds 2
    }
    if (-not $initFinished) {
        throw "Container minio-init chưa hoàn tất. Kiểm tra bằng: docker compose logs minio-init"
    }
    Write-Host "  Các bucket MinIO đã khởi tạo." -ForegroundColor Green

    if (-not $SkipSuperset) {
        Wait-HttpEndpoint "http://localhost:8088/health" "Superset" 180
    }

    if (-not $SkipProductCatalog) {
        try {
            Invoke-ExternalCommand $VenvPython @("scripts\07_api_enrichment.py") "Tải danh mục sản phẩm DummyJSON"
        }
        catch {
            Write-Warning "Không cập nhật được catalog DummyJSON; vẫn tiếp tục ETL giao dịch. Catalog đã lưu trước đó (nếu có) sẽ được dùng: $_"
        }
    }
    Invoke-ExternalCommand $VenvPython @("scripts\06_lakehouse_minio_postgres_etl.py") "Chạy ETL MinIO → PostgreSQL"
    Invoke-ExternalCommand $VenvPython @("scripts\03b_dwh_test_reconciliation.py") "Kiểm thử và đối soát DWH"
    Invoke-ExternalCommand $VenvPython @("scripts\04_run_olap_queries.py") "Chạy các truy vấn OLAP"
    Invoke-ExternalCommand $VenvPython @("scripts\05_data_mining.py") "Chạy RFM, K-Means và phân tích giỏ hàng"

    if (-not $SkipDashboard) {
        if (Test-TcpPort 8501) {
            try {
                $dashboardHealth = Invoke-WebRequest -Uri "http://localhost:8501/_stcore/health" -UseBasicParsing -TimeoutSec 5
                if ($dashboardHealth.StatusCode -ne 200) {
                    throw "Cổng 8501 đang được dùng bởi tiến trình khác."
                }
                Write-Host "Streamlit đã chạy tại http://localhost:8501." -ForegroundColor Green
            }
            catch {
                throw "Cổng 8501 đang được dùng nhưng không phản hồi như Streamlit. Hãy đóng tiến trình đang dùng cổng này rồi chạy lại."
            }
        }
        else {
            $stdoutLog = Join-Path $env:TEMP "retail-streamlit-$PID.out.log"
            $stderrLog = Join-Path $env:TEMP "retail-streamlit-$PID.err.log"
            $streamlit = Start-Process -FilePath $VenvPython `
                -ArgumentList @("-m", "streamlit", "run", "app.py", "--server.headless=true") `
                -WorkingDirectory $ProjectRoot `
                -RedirectStandardOutput $stdoutLog `
                -RedirectStandardError $stderrLog `
                -WindowStyle Hidden `
                -PassThru

            try {
                Wait-HttpEndpoint "http://localhost:8501/_stcore/health" "Streamlit" 45
            }
            catch {
                if (-not $streamlit.HasExited) {
                    Stop-Process -Id $streamlit.Id
                }
                Write-Host "Streamlit stdout: $stdoutLog"
                Write-Host "Streamlit stderr: $stderrLog"
                throw
            }
        }
    }

    Write-Host "`n=== Hoàn tất ===" -ForegroundColor Green
    Write-Host "MinIO Console: http://localhost:9001"
    Write-Host "PostgreSQL:    localhost:5432"
    if (-not $SkipSuperset) {
        Write-Host "Superset:      http://localhost:8088"
    }
    if (-not $SkipDashboard) {
        Write-Host "Streamlit:     http://localhost:8501"
    }
    Write-Host "Lưu ý: ETL sẽ nạp lại (TRUNCATE rồi load) các bảng DWH; Docker volumes không bị xóa."
}
finally {
    Pop-Location
}
