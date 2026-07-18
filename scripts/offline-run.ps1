# Run dashboard + backend fully offline (no internet / no CDN / no npm registry).
# Prerequisites: offline/dashboard built via .\scripts\offline-save.ps1
#                Docker images already local (or offline/docker-images.tar)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

$dash = "offline\dashboard\index.html"
if (-not (Test-Path $dash)) {
    Write-Host "[ICB] offline/dashboard missing. Building it now..." -ForegroundColor Yellow
    & "$PSScriptRoot\offline-save.ps1"
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$gatewayPort = "18080"
if (Test-Path .env) {
    $m = Select-String -Path .env -Pattern '^\s*API_GATEWAY_PORT\s*=\s*(\d+)' | Select-Object -First 1
    if ($m) { $gatewayPort = $m.Matches[0].Groups[1].Value }
} elseif (Test-Path "offline\manifest.json") {
    try {
        $man = Get-Content "offline\manifest.json" -Raw | ConvertFrom-Json
        if ($man.gateway_port) { $gatewayPort = [string]$man.gateway_port }
    } catch {}
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    (Get-Content .env) -replace 'API_GATEWAY_PORT=\d+', "API_GATEWAY_PORT=$gatewayPort" | Set-Content .env
}

# Docker engine
try {
    docker info 1>$null 2>$null
    if ($LASTEXITCODE -ne 0) { throw "docker not ready" }
} catch {
    Write-Host "[ICB] Docker Desktop is not running. Start it, then re-run." -ForegroundColor Red
    exit 1
}

# Load archived images if present and stack images missing
$tar = "offline\docker-images.tar"
$haveAuth = docker images -q iran-carbon-black-auth:latest
if (-not $haveAuth -and (Test-Path $tar)) {
    Write-Host "[ICB] Loading Docker images from offline/docker-images.tar ..."
    docker load -i $tar
}

Write-Host "[ICB] Starting backend offline (compose --pull never)..."
$prev = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose up -d --pull never | Out-Host
$composeCode = $LASTEXITCODE
$ErrorActionPreference = $prev
if ($composeCode -ne 0) {
    Write-Host "[ICB] compose up failed. If images are missing, run online once:" -ForegroundColor Yellow
    Write-Host "  docker compose build"
    Write-Host "  .\scripts\offline-save.ps1 -SaveDocker"
    exit $composeCode
}

$healthUrl = "http://127.0.0.1:$gatewayPort/health"
Write-Host "[ICB] Waiting for $healthUrl ..."
$ok = $false
for ($i = 1; $i -le 90; $i++) {
    try {
        $res = Invoke-WebRequest -Uri $healthUrl -UseBasicParsing -TimeoutSec 3
        if ($res.StatusCode -eq 200) { $ok = $true; break }
    } catch {}
    Start-Sleep -Seconds 2
}
if (-not $ok) {
    Write-Host "[ICB] Gateway not healthy yet — dashboard will still start; APIs may lag." -ForegroundColor Yellow
} else {
    Write-Host "[ICB] Backend ready." -ForegroundColor Green
}

# Stop any previous offline static server on 5173
Get-NetTCPConnection -LocalPort 5173 -ErrorAction SilentlyContinue |
    ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }

Write-Host ""
Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  OFFLINE DASHBOARD"
Write-Host "  UI + API proxy : http://127.0.0.1:5173"
Write-Host "  Gateway        : http://127.0.0.1:$gatewayPort"
Write-Host "  (also serves Docker SPA on gateway / )"
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

node "$PSScriptRoot\offline-static-server.mjs" $gatewayPort 5173
