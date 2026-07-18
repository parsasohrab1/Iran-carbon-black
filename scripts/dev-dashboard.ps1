# One-shot: bring backend + Vite dashboard for live local (offline-capable) development.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

& "$PSScriptRoot\dev-backend.ps1"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Push-Location web
try {
    if (-not (Test-Path "node_modules")) {
        Write-Host "[ICB] Installing npm dependencies (needs network the first time only)..."
        npm install
        if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    }
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "  Dashboard:  http://127.0.0.1:5173"
    Write-Host "  API proxy:  /api  ->  http://127.0.0.1:8080"
    Write-Host "  Gateway:    http://127.0.0.1:8080"
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    npm run dev
} finally {
    Pop-Location
}
