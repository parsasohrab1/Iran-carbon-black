# Offline dashboard package

This folder is produced by `scripts/offline-save.ps1` and is designed to run **without internet**.

| Path | Purpose |
|:---|:---|
| `dashboard/` | Static SPA (HTML/JS/CSS + self-hosted fonts) |
| `manifest.json` | Ports and metadata |
| `docker-images.tar` | Optional air-gap Docker archive (`-SaveDocker`) |

## Run offline

```powershell
.\scripts\offline-run.ps1
```

Open http://127.0.0.1:5173

No Google Fonts / CDN. API calls go to the local Docker gateway.
