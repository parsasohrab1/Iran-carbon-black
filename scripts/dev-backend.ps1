# Start (or reuse) the local Docker backend and wait until the API gateway is healthy.
# Designed for offline/on-prem use after images have been pulled once.

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "[ICB] Created .env from .env.example"
}

$dockerOk = $false
try {
    docker info 1>$null 2>$null
    if ($LASTEXITCODE -eq 0) { $dockerOk = $true }
} catch {
    $dockerOk = $false
}

if (-not $dockerOk) {
    Write-Host ""
    Write-Host "[ICB] Docker Desktop is not running." -ForegroundColor Red
    Write-Host "1) Open Docker Desktop and wait until it says Running."
    Write-Host "2) Re-run this task / script."
    Write-Host ""
    exit 1
}

Write-Host "[ICB] Starting backend stack (docker compose up -d)..."
docker compose up -d
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ICB] docker compose failed. If images are missing, run once while online:" -ForegroundColor Yellow
    Write-Host "      docker compose pull"
    Write-Host "      docker compose build"
    exit $LASTEXITCODE
}

$healthPort = "18080"
if (Test-Path .env) {
    $m = Select-String -Path .env -Pattern '^\s*API_GATEWAY_PORT\s*=\s*(\d+)' | Select-Object -First 1
    if ($m) { $healthPort = $m.Matches[0].Groups[1].Value }
}
$healthUrl = "http://127.0.0.1:$healthPort/health"
$maxAttempts = 90
Write-Host "[ICB] Waiting for gateway $healthUrl ..."

for ($i = 1; $i -le $maxAttempts; $i++) {
    try {
        $res = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
        if ($res.StatusCode -eq 200) {
            Write-Host "[ICB] Backend ready. Gateway: http://127.0.0.1:$healthPort" -ForegroundColor Green
            Write-Host "[ICB] Dashboard (Vite): http://127.0.0.1:5173"
            exit 0
        }
    } catch {
        # keep waiting
    }
    Start-Sleep -Seconds 2
    Write-Host "  attempt $i/$maxAttempts ..."
}

Write-Host "[ICB] Gateway did not become healthy in time. Check: docker compose ps" -ForegroundColor Red
exit 1
