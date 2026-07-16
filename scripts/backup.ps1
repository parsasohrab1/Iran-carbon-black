# Offline backup for Iran Carbon Black platform
# Targets: RPO ≤ 1 hour (hourly backups), RTO ≤ 2 hours (documented restore drill)

param(
    [string]$BackupRoot = ".\backups",
    [string]$ComposeProject = "iran-carbon-black"
)

$ErrorActionPreference = "Stop"
$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$dest = Join-Path $BackupRoot $timestamp
New-Item -ItemType Directory -Force -Path $dest | Out-Null

Write-Host "Starting backup to $dest"

# PostgreSQL dump (TimescaleDB compatible plain SQL)
docker compose exec -T postgres pg_dump -U $env:POSTGRES_USER -d $env:POSTGRES_DB --format=custom -f /tmp/icb.dump
docker compose cp postgres:/tmp/icb.dump (Join-Path $dest "postgres.dump")

# MinIO mirror via mc in temporary container (best-effort)
try {
    docker compose run --rm --entrypoint /bin/sh minio-init -c @"
      mc alias set local http://minio:9000 `$MINIO_ROOT_USER `$MINIO_ROOT_PASSWORD;
      mkdir -p /tmp/minio-backup;
      mc mirror --overwrite local/`$MINIO_BUCKET_RAW /tmp/minio-backup/raw || true;
      mc mirror --overwrite local/`$MINIO_BUCKET_CURATED /tmp/minio-backup/curated || true;
      mc mirror --overwrite local/`$MINIO_BUCKET_MODELS /tmp/minio-backup/models || true;
      tar -czf /tmp/minio-backup.tgz -C /tmp/minio-backup .;
      echo done;
"@
} catch {
    Write-Warning "MinIO mirror step skipped/failed: $_"
}

# Capture compose config snapshot for recovery
docker compose config > (Join-Path $dest "compose-config.yml")
Copy-Item .env (Join-Path $dest "env.snapshot") -ErrorAction SilentlyContinue

# Manifest
$size = (Get-ChildItem $dest -Recurse -File | Measure-Object Length -Sum).Sum
$manifest = @{
    started = $timestamp
    path = (Resolve-Path $dest).Path
    size_bytes = $size
    components = @("postgres", "compose-config", "env")
    rpo_seconds = 3600
    rto_seconds = 7200
} | ConvertTo-Json
Set-Content -Path (Join-Path $dest "manifest.json") -Value $manifest

# Report to ops service if available
try {
    $body = @{
        status = "success"
        backup_path = (Resolve-Path $dest).Path
        size_bytes = $size
        components = @{ postgres = $true; config = $true }
    } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "http://localhost:8011/api/v1/ops/backups/report" -ContentType "application/json" -Body $body | Out-Null
} catch {
    Write-Warning "Could not report backup to ops service (stack may be down)."
}

# Retention: keep last 48 hourly backups (~2 days) for RPO headroom
Get-ChildItem $BackupRoot -Directory |
    Sort-Object Name -Descending |
    Select-Object -Skip 48 |
    ForEach-Object { Remove-Item $_.FullName -Recurse -Force }

Write-Host "Backup complete: $dest ($size bytes)"
