# Guide to running the dashboard offline in VS Code / Cursor
# (without internet, with a live connection to the local Backend)

## Recommended offline method (saved)

The dashboard is saved as a **static bundle** in `offline/dashboard` (local font, no CDN).

### Save once (even on a system with internet)

```powershell
cd "c:\Users\asus\Documents\companies\ithub\AI\products\clones\iran carbon black\Iran-carbon-black"
.\scripts\offline-save.ps1
# optional — full archive of Docker images for air-gapped transfer:
.\scripts\offline-save.ps1 -SaveDocker
```

### Every run without internet

```powershell
.\scripts\offline-run.ps1
```

Then open: **http://127.0.0.1:5173**

| Component | Description |
|:---|:---|
| `offline/dashboard` | Ready SPA (HTML/JS/CSS/font) |
| `scripts/offline-static-server.mjs` | Local server with no npm dependency |
| `docker compose --pull never` | Backend only from local images |
| `/api` proxy | to gateway `18080` |

In VS Code: Task **`ICB: Offline run (no internet)`**

---

## General idea (development with Vite)

| Layer | Address | Role |
|:---|:---|:---|
| Vite dashboard | http://127.0.0.1:5173 | Live UI with Hot Reload |
| API proxy | `/api/*` from Vite | Forwarded to the local gateway |
| Backend | http://127.0.0.1:18080 | Docker Compose (if 8080 is free you can use that one) |

> **Note:** On many Windows systems port `8080` is occupied. The project default is `API_GATEWAY_PORT=18080`.

### If you see `ERR_CONNECTION_REFUSED`

It means that port is not up or the address is wrong:

1. Vite dashboard: only **http://127.0.0.1:5173** (not 8080)
2. Bring up the Backend separately: `.\scripts\dev-backend.ps1`
3. If the Docker image is incomplete (online once):
   `docker pull python:3.11-slim`  
   `docker compose build`  
   `docker compose up -d`

The internet is needed only for the **first time** (downloading Docker images and `npm install`). After that everything works on localhost. Fonts are inside `web/public/fonts` and there is no CDN.

---

## One-time prerequisites (online)

1. Install and start **Docker Desktop**.
2. In the project root:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose pull
docker compose build
cd web
npm install
cd ..
```

3. (Optional) sample data:

```powershell
python scripts/seed_synthetic.py
```

After this step you can disconnect the internet.

---

## Method 1 — with VS Code / Cursor (recommended)

### A) Combined Task

1. Open the project folder in VS Code.
2. `Ctrl+Shift+P` → **Tasks: Run Task**
3. Select: **`ICB: Live dashboard (backend + Vite)`**
4. Wait until the Backend ready and Vite Local messages appear.
5. Open the browser at: **http://127.0.0.1:5173**

Or from the **Terminal → Run Build Task** menu (`Ctrl+Shift+B`) the same default Task runs.

### B) Debugging with the browser inside VS Code

1. **Run and Debug** panel (`Ctrl+Shift+D`)
2. Configuration **`ICB: Open dashboard (Edge)`** or **Chrome**
3. Green ▶ key or `F5`

The Backend + Vite come up and the dashboard opens in the debug browser. `/api` requests go live to Docker.

### C) Simple Browser inside the editor

```
Ctrl+Shift+P → Simple Browser: Show
→ http://127.0.0.1:5173
```

---

## Method 2 — PowerShell only

```powershell
.\scripts\dev-dashboard.ps1
```

This script:

1. Checks Docker
2. Runs `docker compose up -d`
3. Waits for `http://127.0.0.1:8080/health` to become healthy
4. Runs `npm run dev` in the `web` folder

Stopping the Backend:

```powershell
docker compose stop
```

---

## Checking the API connection

In the browser DevTools → Network these should be `200`:

- `GET /api/v1/finance/dashboard`
- `GET /api/v1/ops/status`
- `GET /api/v1/maturity/dashboard`

Quick test in PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:5173/api/v1/ops/status
```

If Vite is up, the second path goes through the **Vite proxy** (the same real path of the dashboard).

---

## Troubleshooting

| Problem | Action |
|:---|:---|
| Docker Desktop is not running | Open Docker until it turns green |
| Gateway timeout | `docker compose ps` and `docker compose logs gateway` |
| Dashboard has empty data / error | The Backend is not up yet; run the script again |
| Port 5173 is occupied | Close the previous Vite process or `Stop-Process -Name node` |
| Port 8080 is occupied | `docker compose down` then up again |
| Strange Persian font | The files `web/public/fonts/*.woff2` must exist |

---

## Alternative mode: gateway only (without Vite)

If you bring up the full Compose stack with the Docker dashboard:

```powershell
.\scripts\bootstrap.ps1
```

The dashboard is served at **http://127.0.0.1:8080** (production build). For UI development with Hot Reload, the Vite method on `:5173` is better.
