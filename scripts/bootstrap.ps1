# Copy .env.example to .env and bring up the full on-premise stack
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot\..

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host "Created .env from .env.example — change default passwords before production use."
}

Write-Host "Building and starting Iran Carbon Black platform..."
docker compose up -d --build

Write-Host ""
Write-Host "Gateway:     http://localhost:8080/health"
Write-Host "Auth docs:   http://localhost:8001/docs"
Write-Host "Grafana:     http://localhost:3000"
Write-Host "MinIO:       http://localhost:9001"
Write-Host "Prometheus:  http://localhost:9090"
Write-Host ""
Write-Host "Default admin user (change immediately): admin / Admin@ChangeMe1"
