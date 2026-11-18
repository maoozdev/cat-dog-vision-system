# PawSense: Cat vs Dog Vision System

A full-stack web app that classifies a photo as **Cat**, **Dog** or **Neither / Unknown**.
You can upload an image or take one with the live camera. Your predictions are saved to a
personal history.

| Layer | Technology |
|---|---|
| Model | PyTorch + torchvision, **MobileNetV3-Small** (transfer learning), 3 classes |
| Backend | FastAPI, SQLAlchemy 2, Alembic, PostgreSQL 17, JWT + Argon2 |
| Frontend | React 19 + TypeScript + Vite, React Router, Axios |
| Deployment | Docker Compose, Caddy (reverse proxy + automatic HTTPS) |

---

## 1. Architecture

```
 Browser ──HTTPS──► Caddy (frontend container)
                     ├── /          static React app
                     ├── /docs      FastAPI interactive API docs
                     └── /api/*  ─► FastAPI (backend container) ──► PostgreSQL (db container)
                                     │  model loaded ONCE at startup from models/cat_dog_model.pth
                                     └─ images saved to the "uploads" volume (DB stores only the path)
```

**How one prediction flows:**
1. You log in. The backend returns a 15-minute **access token** (JWT, kept only in JS memory)
   and sets a 7-day **refresh token** in an `HttpOnly; Secure; SameSite=Lax` cookie. The
   database stores only a SHA-256 hash of the refresh token.
2. React sends `POST /api/predict` (multipart) with `Authorization: Bearer <token>`.
3. The backend checks the upload:
   - at most 5 MB
   - really a JPEG/PNG/WEBP (it checks the file content, not the name)
   - not corrupted
   - not a "decompression bomb" (a small file that expands to an enormous image)
4. It re-encodes the image as JPEG, which strips EXIF data such as GPS location, and saves it.
5. It runs the model and stores a row in `predictions`.
6. It returns the label, the confidence and all three probabilities. If the top probability is below the
   **confidence threshold**, the answer becomes "other" (Neither / Unknown) with `low_confidence: true`.
7. When the access token expires, the frontend silently calls `/api/auth/refresh`. The
   refresh token is **rotated** on every use. Reusing an old one revokes all of that user's sessions
   (theft detection).

---

## 2. Model results (real, measured)

| | |
|---|---|
| Data | Oxford-IIIT Pets (cats, dogs) + COCO val2017 with every cat/dog image removed ("other") |
| Cleaning | 0 corrupted, 32 duplicates removed (perceptual hash, **before** splitting) |
| Split | 2,361 images per class, 70 / 15 / 15 → 4,959 train / 1,062 val / 1,062 test |
| Training | 3 epochs head-only (lr 1e-3) + 8 epochs fine-tuning the last 4 blocks (lr 1e-4), Adam, CrossEntropyLoss, **13.3 min on a 4-thread CPU** |
| Best checkpoint | epoch 6, validation accuracy 98.49% |
| Threshold | **0.52**, tuned on the **validation** set (best macro-F1) |
| **Test accuracy** | **97.55%** with threshold (97.83% plain argmax), macro F1 0.9755 |

| class | precision | recall | F1 |
|---|---|---|---|
| cat | 0.9801 | 0.9746 | 0.9773 |
| dog | 0.9745 | 0.9718 | 0.9731 |
| other | 0.9720 | 0.9802 | 0.9761 |

The full report and plots are in [training/outputs/](training/outputs/):
- [evaluation_report.md](training/outputs/evaluation_report.md)
- `confusion_matrix.png`
- `training_curves.png`
- `history.csv`

**Limitation:** these numbers measure photos like the training data. The "other" class is
COCO scenes, so drawings, cartoons and very unusual photos may do worse.

The checkpoint `models/cat_dog_model.pth` (5.9 MB) also stores:
- `model_version`, `class_names` and `confidence_threshold`
- `image_size` 224 and `resize_size` 256
- the ImageNet `normalization` values

The backend reads its preprocessing settings from this file.

---

## 3. Quick start with Docker (recommended)

**Requirements:** Docker Desktop running, and the trained model at `models/cat_dog_model.pth`.
If you don't have the model, see section 5.

```powershell
Copy-Item .env.example .env
# Edit .env: set POSTGRES_PASSWORD (also inside DATABASE_URL) and JWT_SECRET. Generate a secret with:
python -c "import secrets; print(secrets.token_urlsafe(48))"

docker compose up -d --build      # first build: ~5 min (downloads CPU PyTorch)
docker compose ps                 # wait for backend "healthy"
```

Open **https://localhost**. The browser warns once, because Caddy uses its own local
certificate authority (CA). Click *Advanced → Continue*. Plain http://localhost redirects to HTTPS.

| URL | What |
|---|---|
| https://localhost | the app |
| https://localhost/docs | interactive API documentation (Swagger UI) |
| https://localhost/api/health | health check |

Useful commands:
```powershell
docker compose logs -f backend    # structured JSON logs
docker compose restart backend    # e.g. after replacing models/cat_dog_model.pth
docker compose down               # stop; data stays in volumes
docker compose down -v            # stop AND delete database, uploads and certificates
```

### Use it from your phone on the same Wi-Fi (HTTPS needed for the camera)

1. Find your PC's IP: `ipconfig`, e.g. `192.168.18.109`.
2. In `.env`, set `SITE_ADDRESS=192.168.18.109`. Then run `docker compose up -d`.
3. Allow inbound TCP 443 in Windows Firewall (run as admin):
   `New-NetFirewallRule -DisplayName "PawSense HTTPS" -Direction Inbound -Protocol TCP -LocalPort 443 -Action Allow`
4. On the phone, open `https://192.168.18.109` and accept the certificate warning.

> This phone setup has not been tested on a real device yet.

---

## 4. Local development (without Docker for the app)

```powershell
docker compose up -d db                                  # only PostgreSQL (port 5433 on your PC)

# Backend: terminal 1
cd backend
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
alembic upgrade head                                     # create/update tables
uvicorn app.main:app --reload                            # http://127.0.0.1:8000/docs

# Frontend: terminal 2
cd frontend
npm ci
npm run dev                                              # http://localhost:5173
```
Vite forwards `/api/*` to `127.0.0.1:8000` (see [vite.config.ts](frontend/vite.config.ts)).
The browser therefore sees a single origin, so cookies work without CORS.

---

## 5. Reproduce the dataset and model

```powershell
python -m venv training\.venv; .\training\.venv\Scripts\Activate.ps1
pip install -r training\requirements.txt
python training\download_data.py   # ~1.8 GB into training/raw/
python training\preprocess.py      # clean, dedupe, balance, split -> training/dataset/
python training\train.py           # ~13 min on CPU -> models/cat_dog_model.pth
python training\evaluate.py        # threshold on val, metrics on test -> training/outputs/
```
Results can differ by a fraction of a percent between runs, because CPU threads change the order of
floating-point operations.

---

## 6. API reference

All endpoints are under `/api` behind Caddy, or at the root on `127.0.0.1:8000` in development.
Errors always look like `{"detail": "..."}`. Every response has an `X-Request-ID` header.

| Method | Path | Auth | Description |
|---|---|---|---|
| POST | `/auth/register` | – | `{email, password}` → **201** user. Password: ≥ 8 characters, with a letter and a number. **409** if the email exists. |
| POST | `/auth/login` | – | `{email, password}` → `{access_token, token_type, expires_in, user}` and sets the refresh cookie. **401** if wrong. |
| POST | `/auth/refresh` | cookie | → new access token and a rotated cookie. **401** if expired, revoked or reused. |
| POST | `/auth/logout` | cookie | Revokes the session and clears the cookie → **204** |
| GET | `/auth/me` | Bearer | The current user |
| POST | `/predict` | Bearer | multipart field `file` (JPEG/PNG/WEBP, ≤ 5 MB) → prediction. **400** corrupted, **413** too large, **415** wrong type |
| GET | `/predictions?page=1&page_size=10` | Bearer | Your history, newest first: `{items, total, page, page_size, pages}`. `page_size` ≤ 100 |
| GET | `/predictions/{id}/image` | Bearer | The stored image (owner only; others get **404**) |
| GET | `/health` | – | `{status, database, model_loaded, model_version}`. **503** if degraded |

**Rate limits** (per minute, **429** with a `Retry-After` header):
- login and register: 10 per IP
- refresh: 60 per IP
- predict: 30 per user

Example `POST /predict` response:
```json
{
  "id": "9e2c…", "predicted_label": "cat", "confidence": 0.999944,
  "probabilities": {"cat": 0.999944, "dog": 0.000054, "other": 0.000002},
  "model_version": "1.0.0", "created_at": "2026-11-16T12:06:58Z",
  "image_url": "/predictions/9e2c…/image", "low_confidence": false, "threshold": 0.52
}
```

Example with curl (development):
```powershell
curl.exe -X POST http://127.0.0.1:8000/auth/login -H "Content-Type: application/json" -d "{\"email\":\"you@example.com\",\"password\":\"secret123\"}"
curl.exe -X POST http://127.0.0.1:8000/predict -H "Authorization: Bearer <access_token>" -F "file=@cat.jpg"
```

---

## 7. Database

The schema is managed by Alembic ([backend/alembic/versions/](backend/alembic/versions/)). The
backend container runs `alembic upgrade head` automatically on start.

| Table | Columns |
|---|---|
| `users` | id (UUID), email (unique), password_hash (Argon2id), created_at |
| `sessions` | id, user_id, refresh_token_hash (SHA-256, unique), created_at, expires_at, revoked_at, user_agent, ip |
| `predictions` | id, user_id, image_path, predicted_label, confidence, probabilities (JSONB), model_version, created_at |

After changing a model in `backend/app/models/`, run:
```powershell
alembic revision --autogenerate -m "describe change"   # review the generated file!
alembic upgrade head
```

---

## 8. Tests

| Suite | Command | What it covers | Result |
|---|---|---|---|
| Backend (pytest) | `cd backend; python -m pytest -q` | auth flows, token rotation and reuse detection, rate limits, upload validation, 15 real held-out photos, pagination, privacy, production secret check | **29 passed** |
| Browser end-to-end (Playwright) | `.\e2e\.venv\Scripts\python.exe e2e\run_e2e.py` | 17 real-browser steps: register and login, file picker, drag and drop, **live camera (fake webcam)**, history pagination, reload keeps session, profile, mobile layout, logout | **17/17 passed** on the Vite dev server **and** on the Docker HTTPS stack |

Run the e2e suite against Docker with `$env:E2E_BASE_URL='https://localhost'` first.
Screenshots are saved to [e2e/screenshots/](e2e/screenshots/).

E2E setup, once:
```powershell
python -m venv e2e\.venv
.\e2e\.venv\Scripts\pip install -r e2e\requirements.txt
.\e2e\.venv\Scripts\python -m playwright install chromium
```

---

## 9. Deploying to the cloud with real HTTPS

> These steps have **not been run** on a real cloud server yet.

1. Rent a Linux VM with at least 2 GB RAM (e.g. Ubuntu 24.04) and install Docker Engine plus the Compose plugin.
2. Point a domain at it: add a DNS **A record**, e.g. `cats.example.com` → the server's IP.
3. Open ports **80 and 443** in the provider's firewall. Let's Encrypt needs port 80 to verify the domain.
4. Copy the project to the server, including `models/cat_dog_model.pth`. The datasets and `.venv` folders aren't needed.
5. Create `.env` from `.env.example`:
   - set strong secrets
   - set `SITE_ADDRESS=cats.example.com`
6. Security hardening: in `docker-compose.yml`, **delete the `ports:` section of `db`**.
7. Run `docker compose up -d --build`. Caddy gets a **real Let's Encrypt certificate automatically** and renews it.
8. Back up the database regularly:
   `docker compose exec db pg_dump -U catdog catdog > backup.sql`.
   Also back up the `uploads` volume.

**Why HTTPS matters here:**
- Browsers only allow `getUserMedia` (the camera) on secure pages, meaning `https://` or `localhost`.
- The refresh cookie is marked `Secure`, so the browser only sends it over HTTPS.
- If `COOKIE_SECURE=true` and `JWT_SECRET` is weak or the default, the backend **refuses to start**.

---

## 10. Demo script (about 5 minutes)

1. `docker compose up -d` → open https://localhost → **Register**.
2. **Upload tab:** drag in a cat photo → **Predict**. You'll see "Cat", the confidence, and three probability bars.
3. Upload a non-animal photo (a street or food) → "Neither / Unknown".
4. **Live camera:** click Start camera and allow access. Point it at a pet, or at a pet photo on your phone. Click Capture, then Predict.
   On a phone, use "Switch camera" for front/back.
5. **History:** thumbnails and pagination. **Profile:** account information and total.
6. Reload the page and notice you stay logged in. Then **Log out**.
7. Open https://localhost/docs to show the API, and `training/outputs/` to show the evaluation.

---

## 11. Troubleshooting

| Symptom | Cause / fix |
|---|---|
| `bind: ... port 5432` when starting db | Another PostgreSQL uses 5432. This project uses **5433** on the PC (`POSTGRES_HOST_PORT`). |
| Backend or Alembic hangs connecting to the DB | On Windows, `localhost` tries IPv6 first and Docker never answers. Use `127.0.0.1` in `DATABASE_URL`. |
| `npm ci` fails in Docker with "Missing: @emnapi…" | The lock file was created on Windows. Regenerate it in Linux: `docker run --rm -v "${PWD}\frontend:/app" -w /app node:24-alpine npm install --package-lock-only` |
| `.env` values ignored | The file was saved with a BOM by PowerShell 5.1 `Set-Content -Encoding utf8`. Save it as UTF-8 **without** BOM. |
| Camera: "needs a secure page" | Use https:// (Docker/Caddy) or http://localhost. Plain http on a LAN IP won't work. |
| `Activate.ps1 cannot be loaded` | Run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| Backend exits with "JWT_SECRET is missing or too short" | Set a random JWT_SECRET of 32+ characters in `.env`. |

---

## 12. Project structure

```
├── training/        download_data.py, preprocess.py, train.py, evaluate.py, outputs/ (reports)
├── models/          cat_dog_model.pth (weights + metadata)
├── backend/         FastAPI app (app/: config, database, models, schemas, routers, services, ml, utils),
│                    alembic/ migrations, tests/, Dockerfile
├── frontend/        React app (src/: pages, components, services, context, hooks, utils),
│                    Caddyfile, Dockerfile
├── e2e/             Playwright browser tests + screenshots
├── docker-compose.yml, .env.example, .gitignore, README.md
```
