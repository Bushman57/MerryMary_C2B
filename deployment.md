## Deployment Guide – Render (Backend) & Vercel (Frontend)

This project is split into:

- **Backend**: Flask API + Neon Postgres in `backend/`
- **Frontend**: Vue 3 + Vite UI in `frontend/`

We deploy:

- Backend to **Render**
- Frontend to **Vercel**

---

## 1. Prerequisites

- Neon Postgres database (connection string available).
- Accounts on:
  - Render (`https://render.com`)
  - Vercel (`https://vercel.com`)
- Code pushed to a Git provider (GitHub/GitLab/Bitbucket).

---

## 2. Backend – Flask API on Render

### 2.1. Backend entrypoint

Backend entrypoint is `backend/app.py`:

```58:60:backend/app.py
if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
```

`create_app` configures CORS, database, blueprints and health check.

### 2.2. Requirements

All dependencies are listed in:

```1:25:backend/requirements.txt
blinker==1.9.0
...
Flask==3.0.0
Flask-Cors==4.0.0
Flask-SQLAlchemy==3.1.1
gunicorn==21.2.0
psycopg2-binary==2.9.11
...
```

No extra packages are required for Render.

### 2.3. Create Web Service on Render

1. In Render, click **New → Web Service**.
2. Connect the repository containing `transaction_history/`.
3. Configure:

- **Root Directory**: the repo root (where `backend/` lives).
- **Environment**: Python 3.x.
- **Build Command**:

  ```bash
  cd backend && pip install -r requirements.txt
  ```

- **Start Command**:

  ```bash
  cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 1 "app:create_app()"
  ```

  Use a single worker unless you need more processes for CPU-bound load (each worker repeats cold boot cost). Optional: add `--threads 2` for extra I/O concurrency without a second worker.

4. Set **Environment Variables** (Render dashboard → Settings → Environment):

- `FLASK_ENV=production`
- `DATABASE_URL=<your Neon connection string>`
- Any other config used by `backend/config.py` (e.g. `SECRET_KEY`, `MAX_UPLOAD_SIZE_MB`, etc.).
- **Schema / cold boot:** Production skips `db.create_all()` on startup (faster cold starts). Create or migrate tables with [`backend/migrate_direct.py`](backend/migrate_direct.py), [`backend/migrate.py`](backend/migrate.py), or [`backend/scripts/dedupe_transaction_url.py`](backend/scripts/dedupe_transaction_url.py) as documented in the README. To force SQLAlchemy `create_all()` on boot (e.g. empty greenfield DB), set `ENABLE_DB_CREATE_ALL=true` once, then remove it.
- **Firebase Admin (required for auth in production)**  
  - **Recommended (Render secret file):** In the Render dashboard add a **Secret File** with your Firebase service account JSON (from Firebase Console → Project settings → Service accounts → Generate new private key). Files are mounted under **`/etc/secrets/`** using the filename you choose (e.g. `/etc/secrets/firebase_service_account.json`). Set:  
    - `FIREBASE_CREDENTIALS_PATH=/etc/secrets/firebase_service_account.json`  
  - **Alternative:** `FIREBASE_CREDENTIALS_JSON` — paste the same JSON as a **single line**.  
  - **Alternative:** `GOOGLE_APPLICATION_CREDENTIALS` — absolute path to the JSON file (common locally).  
  - Optional: `ALLOWED_FIREBASE_UIDS` — comma-separated Firebase Auth **UIDs** (preferred; leave unset to allow any signed-in user, or use `ALLOWED_EMAILS` if UIDs are not set).
  - Optional: `ALLOWED_EMAILS` — comma-separated emails (used only when `ALLOWED_FIREBASE_UIDS` is empty).  
  - Do **not** set `FIREBASE_AUTH_DISABLED` in production.

5. Click **Create Web Service** and wait for deployment.

Render will provide a URL like:

- `https://your-backend.onrender.com`

The API base used by the frontend will be:

- `https://your-backend.onrender.com/api`

### 2.4. Quick health check

Verify the backend is healthy:

- `GET https://your-backend.onrender.com/api/health`  
  should return:
  - `{"status": "ok"}` with HTTP 200.

### 2.5. Firebase + Google Sign-In

1. In [Firebase Console](https://console.firebase.google.com), create or select a project.
2. **Authentication** → Sign-in method → enable **Google**.
3. **Authentication** → Settings → Authorized domains: add your Vercel domain (and `localhost` for dev).
4. Add a **Web** app under Project settings; copy the config values into Vercel env vars (see §3.3).
5. **Project settings → Service accounts** → generate a private key JSON. On Render, upload it as a **Secret File** and set `FIREBASE_CREDENTIALS_PATH=/etc/secrets/<your_filename>.json`, or paste the minified JSON into `FIREBASE_CREDENTIALS_JSON`.

Protected API routes (`/api/upload`, `/api/transactions`, `/api/statements`, etc.) require a valid Firebase ID token:

- Header: `Authorization: Bearer <id_token>`  
- The Vue app attaches this automatically after Google Sign-In.

Public route (no token): `GET /api/health`.  
Profile check (requires token): `GET /api/me`.

---

## 3. Frontend – Vue + Vite on Vercel

The frontend lives in `frontend/` and uses `VITE_API_BASE_URL`:

```3:10:frontend/src/utils/api.js
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000/api'
```

### 3.1. Create Vercel project

1. In Vercel, click **New Project**.
2. Import the same repository.
3. When prompted for **Root Directory**, select `frontend`.
4. Framework preset: **Vue**.
5. Build settings:
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`

### 3.2. Configure API base URL on Vercel

In the Vercel project:

1. Go to **Settings → Environment Variables**.
2. Add:
   - **Name**: `VITE_API_BASE_URL`
   - **Value**: `https://your-backend.onrender.com/api`
   - **Environment**: Production (and Preview if desired).
3. Redeploy or trigger a new deployment.

After deployment, the frontend will call the Render backend via:

- `POST /upload` → `https://your-backend.onrender.com/api/upload`
- `GET /statements/<statement_id>` → `https://your-backend.onrender.com/api/statements/<statement_id>`
- `GET /transactions` for analytics, with query parameters.

### 3.3. Firebase client env vars (Vercel)

Add these in **Settings → Environment Variables** (same environments as `VITE_API_BASE_URL`):

| Name | Source |
|------|--------|
| `VITE_FIREBASE_API_KEY` | Firebase Web app config |
| `VITE_FIREBASE_AUTH_DOMAIN` | Firebase Web app config |
| `VITE_FIREBASE_PROJECT_ID` | Firebase Web app config |
| `VITE_FIREBASE_APP_ID` | Firebase Web app config |
| `VITE_FIREBASE_MESSAGING_SENDER_ID` | Firebase Web app config (if shown) |

Redeploy after adding variables so Vite embeds them at build time.

---

## 4. Behavior in Production

### 4.1. Load_statement tab

- User uploads a PDF statement.
- Frontend sends file to:
  - `POST https://your-backend.onrender.com/api/upload`
- Backend:
  - Parses the PDF.
  - Stores all transactions into Neon.
  - Returns JSON with `statement_id`, `rows_updated`, `transaction_count`, and a sample of transactions.
- Frontend:
  - Fetches all rows for that `statement_id` using:
    - `GET https://your-backend.onrender.com/api/statements/<statement_id>?page=1&limit=500`
  - Displays them in the main table.

### 4.2. Analytics tab

- User navigates to **Analytics** tab.
- Sets:
  - `Start Date` and `End Date` (date widgets).
  - `Phone Number` filter.
  - Optional sort field and order.
- Clicks **Apply filters**.
- Frontend calls:

  ```text
  GET https://your-backend.onrender.com/api/transactions
      ?phone=<phone>
      &start_date=<YYYY-MM-DD>
      &end_date=<YYYY-MM-DD>
      &sort_by=<value_date|credit>
      &sort_order=<asc|desc>
      &page=1
      &limit=500
  ```

- Backend filters by phone and date range, sorts, and returns matching rows.
- Analytics view shows:
  - **Value Date**, **Credit (In)**, **Phone Number** columns.
  - **Total Credit (In)** (sum of credit amounts) at the top.

---

## 5. Local Development vs Production

### 5.1. Local development

Backend (from `backend/`):

```bash
flask run  # or python app.py
# http://localhost:5000/api/...
```

Frontend (from `frontend/`):

```bash
npm install
npm run dev  # http://localhost:5173
```

`frontend/vite.config.js` proxies `/api` locally:

```6:14:frontend/vite.config.js
server: {
  port: 5173,
  host: '0.0.0.0',
  proxy: {
    '/api': {
      target: 'http://localhost:5000',
      changeOrigin: true
    }
  }
}
```

So locally you do **not** need `VITE_API_BASE_URL`; `/api` is forwarded directly to Flask.

### 5.2. Production

- Frontend uses `VITE_API_BASE_URL` to reach the backend on Render.
- All uploads and analytics traffic go:
  - Browser → Vercel frontend → Render backend → Neon DB.

---

## 6. Deployment Checklist

1. **Backend on Render**
   - [ ] `backend/app.py` exposes `create_app()` and binds to `0.0.0.0`.
   - [ ] `backend/requirements.txt` includes `gunicorn`, `Flask`, `Flask-Cors`, `Flask-SQLAlchemy`, `psycopg2-binary`.
   - [ ] Render Web Service configured with:
     - Build: `cd backend && pip install -r requirements.txt`
     - Start: `cd backend && gunicorn --bind 0.0.0.0:$PORT --workers 1 "app:create_app()"`
   - [ ] Env vars set: `DATABASE_URL`, `FLASK_ENV`, `SECRET_KEY`, etc.
   - [ ] `GET /api/health` works on the Render URL.

2. **Frontend on Vercel**
   - [ ] Project root set to `frontend/`.
   - [ ] Build command `npm run build`, output dir `dist`.
   - [ ] Env var `VITE_API_BASE_URL=https://your-backend.onrender.com/api`.
   - [ ] App loads at the Vercel URL.

3. **End-to-end verification**
   - [ ] Upload `Statement_test.pdf` on **Load_statement** tab; stored count matches Neon and table shows all rows.
   - [ ] Use **Analytics** tab with start date, end date, and phone filters; results and total credit look correct.

