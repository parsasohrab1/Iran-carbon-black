# Build & persist an offline-capable dashboard package (run once while online / images present).
# Creates:
#   offline/dashboard/     → static SPA (fonts + JS/CSS, no CDN)
#   offline/manifest.json  → ports & checksums
# Optional:
#   offline/docker-images.tar → docker save of stack images (large)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$offlineRoot = Join-Path (Get-Location) "offline"
$dashOut = Join-Path $offlineRoot "dashboard"
New-Item -ItemType Directory -Force -Path $dashOut | Out-Null

# Gateway port
$gatewayPort = "18080"
if (Test-Path .env) {
    $m = Select-String -Path .env -Pattern '^\s*API_GATEWAY_PORT\s*=\s*(\d+)' | Select-Object -First 1
    if ($m) { $gatewayPort = $m.Matches[0].Groups[1].Value }
}

Write-Host "[ICB] Building offline static dashboard..." -ForegroundColor Cyan
Push-Location web
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "[ICB] npm install (needs network once)..."
        npm install --prefer-offline --no-audit --no-fund
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
} finally {
    Pop-Location
}

if (-not (Test-Path "web\dist\index.html")) {
    Write-Host "[ICB] Build failed: web/dist/index.html missing" -ForegroundColor Red
    exit 1
}

Write-Host "[ICB] Copying dist → offline/dashboard ..."
if (Test-Path $dashOut) { Remove-Item -Recurse -Force $dashOut }
Copy-Item -Recurse "web\dist" $dashOut

# Ensure fonts landed (Vite copies public/)
$font = Join-Path $dashOut "fonts\Vazirmatn-Variable.woff2"
if (-not (Test-Path $font)) {
    Write-Host "[ICB] Copying fonts from web/public/fonts ..."
    New-Item -ItemType Directory -Force -Path (Join-Path $dashOut "fonts") | Out-Null
    Copy-Item "web\public\fonts\*" (Join-Path $dashOut "fonts") -Force
}

$manifest = @{
    created_at     = (Get-Date).ToString("o")
    gateway_port   = $gatewayPort
    dashboard_url  = "http://127.0.0.1:5173"
    gateway_url    = "http://127.0.0.1:$gatewayPort"
    static_root    = "offline/dashboard"
    fonts          = @("Vazirmatn-Variable.woff2", "Syne-700.woff2", "Syne-800.woff2")
    offline_run    = ".\scripts\offline-run.ps1"
    notes          = "No CDN. Static SPA + local Docker API. Internet not required after this save."
}
$manifest | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 (Join-Path $offlineRoot "manifest.json")

# Optional docker image archive
$saveDocker = $env:ICB_SAVE_DOCKER_IMAGES
if ($saveDocker -eq "1" -or $args -contains "-SaveDocker") {
    Write-Host "[ICB] Saving Docker images to offline/docker-images.tar (this can take a while)..."
    $images = @(
        docker images --format "{{.Repository}}:{{.Tag}}" |
            Where-Object { $_ -match "iran-carbon-black-|timescale/timescaledb:latest-pg16|redis:7-alpine|minio/minio:|eclipse-mosquitto:2|prom/prometheus:v2.54.1|grafana/grafana:11.2.0|nginx:1.27-alpine|python:3.11-slim|minio/mc:" }
    )
    if ($images.Count -eq 0) {
        Write-Host "[ICB] No images found. Run docker compose build first." -ForegroundColor Yellow
    } else {
        $tar = Join-Path $offlineRoot "docker-images.tar"
        docker save -o $tar @images
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[ICB] Saved $($images.Count) images → offline/docker-images.tar" -ForegroundColor Green
        }
    }
}

# Rebuild dashboard container so gateway serves the same UI offline
Write-Host "[ICB] Rebuilding dashboard Docker image (local only)..."
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose build --pull=false dashboard | Out-Host
$buildCode = $LASTEXITCODE
docker compose up -d --no-deps --pull never dashboard gateway | Out-Host
$upCode = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($buildCode -ne 0) {
    Write-Host "[ICB] Warning: dashboard image rebuild returned $buildCode (static package is still saved)." -ForegroundColor Yellow
}
if ($upCode -ne 0) {
    Write-Host "[ICB] Warning: could not refresh dashboard/gateway containers ($upCode)." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host " Offline package ready"
Write-Host "  Static UI : offline/dashboard"
Write-Host "  Run       : .\scripts\offline-run.ps1"
Write-Host "  URL       : http://127.0.0.1:5173"
Write-Host "  Gateway   : http://127.0.0.1:$gatewayPort"
Write-Host "============================================" -ForegroundColor Green
Write-Host "Tip: for a full air-gap image dump, re-run with -SaveDocker"
