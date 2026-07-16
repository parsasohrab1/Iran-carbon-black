# Restore PostgreSQL from a backup folder produced by backup.ps1
# RTO target ≤ 2 hours — practice this drill quarterly.

param(
    [Parameter(Mandatory = $true)]
    [string]$BackupDir
)

$ErrorActionPreference = "Stop"
$dump = Join-Path $BackupDir "postgres.dump"
if (-not (Test-Path $dump)) {
    throw "postgres.dump not found in $BackupDir"
}

Write-Host "WARNING: This will overwrite database '$env:POSTGRES_DB'."
Write-Host "Restoring from $dump ..."

docker compose cp $dump postgres:/tmp/icb-restore.dump
docker compose exec -T postgres pg_restore -U $env:POSTGRES_USER -d $env:POSTGRES_DB --clean --if-exists /tmp/icb-restore.dump

Write-Host "Restore finished. Validate with: python scripts\phase4_smoke.py"
Write-Host "Record actual restore duration against RTO ≤ 7200 seconds."
