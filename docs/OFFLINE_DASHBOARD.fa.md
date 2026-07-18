# راهنمای اجرای آفلاین داشبورد در VS Code / Cursor
# (بدون اینترنت، با اتصال زنده به Backend محلی)

## ایده کلی

| لایه | آدرس | نقش |
|:---|:---|:---|
| داشبورد Vite | http://127.0.0.1:5173 | UI زنده با Hot Reload |
| پروکسی API | `/api/*` از Vite | به گیت‌وی محلی فوروارد می‌شود |
| Backend | http://127.0.0.1:18080 | Docker Compose (اگر ۸۰۸۰ آزاد باشد می‌توانید همان را بگذارید) |

> **توجه:** روی بسیاری از ویندوزها پورت `8080` اشغال است. پیش‌فرض پروژه `API_GATEWAY_PORT=18080` است.

### اگر `ERR_CONNECTION_REFUSED` دیدید

یعنی آن پورت بالا نیست یا آدرس اشتباه است:

1. داشبورد Vite: فقط **http://127.0.0.1:5173** (نه ۸۰۸۰)
2. Backend را جداگانه بالا بیاورید: `.\scripts\dev-backend.ps1`
3. اگر Docker ایمیج ناقص است (آنلاین یک‌بار):  
   `docker pull python:3.11-slim`  
   `docker compose build`  
   `docker compose up -d`

اینترنت فقط برای **اولین بار** لازم است (دانلود ایمیج Docker و `npm install`). بعد از آن همه‌چیز روی localhost کار می‌کند. فونت‌ها داخل `web/public/fonts` هستند و CDN ندارند.

---

## پیش‌نیاز یک‌باره (آنلاین)

1. **Docker Desktop** را نصب و روشن کنید.
2. در ریشه پروژه:

```powershell
Copy-Item .env.example .env -ErrorAction SilentlyContinue
docker compose pull
docker compose build
cd web
npm install
cd ..
```

3. (اختیاری) داده نمونه:

```powershell
python scripts/seed_synthetic.py
```

بعد از این مرحله می‌توانید اینترنت را قطع کنید.

---

## روش ۱ — با VS Code / Cursor (پیشنهادی)

### الف) Task ترکیبی

1. پوشه پروژه را در VS Code باز کنید.
2. `Ctrl+Shift+P` → **Tasks: Run Task**
3. انتخاب کنید: **`ICB: Live dashboard (backend + Vite)`**
4. صبر کنید تا پیام Backend ready و Vite Local ظاهر شود.
5. مرورگر را باز کنید روی: **http://127.0.0.1:5173**

یا از منوی **Terminal → Run Build Task** (`Ctrl+Shift+B`) همان Task پیش‌فرض اجرا می‌شود.

### ب) دیباگ با مرورگر داخل VS Code

1. پنل **Run and Debug** (`Ctrl+Shift+D`)
2. پیکربندی **`ICB: Open dashboard (Edge)`** یا **Chrome**
3. کلید سبز ▶ یا `F5`

Backend + Vite بالا می‌آید و داشبورد در مرورگر دیباگ باز می‌شود. درخواست‌های `/api` به‌صورت زنده به Docker می‌روند.

### ج) Simple Browser داخل ادیتور

```
Ctrl+Shift+P → Simple Browser: Show
→ http://127.0.0.1:5173
```

---

## روش ۲ — فقط PowerShell

```powershell
.\scripts\dev-dashboard.ps1
```

این اسکریپت:

1. Docker را چک می‌کند
2. `docker compose up -d` می‌زند
3. منتظر سالم شدن `http://127.0.0.1:8080/health` می‌ماند
4. `npm run dev` را در پوشه `web` اجرا می‌کند

توقف Backend:

```powershell
docker compose stop
```

---

## بررسی اتصال به API

در مرورگر DevTools → Network باید این‌ها `200` باشند:

- `GET /api/v1/finance/dashboard`
- `GET /api/v1/ops/status`
- `GET /api/v1/maturity/dashboard`

تست سریع در PowerShell:

```powershell
Invoke-RestMethod http://127.0.0.1:8080/health
Invoke-RestMethod http://127.0.0.1:5173/api/v1/ops/status
```

اگر Vite بالا باشد، مسیر دوم از **پروکسی Vite** می‌گذرد (همان مسیر واقعی داشبورد).

---

## عیب‌یابی

| مشکل | کار |
|:---|:---|
| Docker Desktop is not running | Docker را باز کنید تا سبز شود |
| Gateway timeout | `docker compose ps` و `docker compose logs gateway` |
| داشبورد داده خالی / خطا | Backend هنوز بالا نیامده؛ اسکریپت را دوباره بزنید |
| پورت 5173 اشغال | پروسس قبلی Vite را ببندید یا `Stop-Process -Name node` |
| پورت 8080 اشغال | `docker compose down` سپس دوباره up |
| فونت فارسی عجیب | فایل‌های `web/public/fonts/*.woff2` باید موجود باشند |

---

## حالت جایگزین: فقط از گیت‌وی (بدون Vite)

اگر استک کامل Compose را با داشبورد Docker بالا بیاورید:

```powershell
.\scripts\bootstrap.ps1
```

داشبورد روی **http://127.0.0.1:8080** سرو می‌شود (بیلد production). برای توسعه UI با Hot Reload همان روش Vite روی `:5173` بهتر است.
