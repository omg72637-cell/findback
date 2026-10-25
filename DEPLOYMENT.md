# FindBack 2.0 — Production Deployment & Cloud Hosting Guide

This guide provides a beginner-friendly, step-by-step procedure to deploy FindBack 2.0 to a public HTTPS URL using **free, persistent cloud infrastructure**.

---

## 1. Hosting & Storage Architecture

| Component | Provider & Tier | Persistence & Limits | Cost |
| :--- | :--- | :--- | :--- |
| **Web Service (Flask + Gunicorn)** | **Render** (Free / Hobby Web Service) | Ephemeral disk (wiped on restart/spin-down); 512 MB RAM, 0.1 CPU; 750 free hours/mo; spins down after 15 min inactivity; wakes on HTTP request (~50s cold start). | **$0/mo** |
| **Persistent Database** | **Neon** (Serverless PostgreSQL Free Tier) | **Permanent storage** (1 GB storage; does NOT expire after 30 days, unlike Render Postgres); auto-suspends when idle; wakes in ~300ms on connection. | **$0/mo** |

> [!WARNING]
> **Why Not Render's Built-In Free PostgreSQL?**
> Render's free PostgreSQL databases **strictly expire and are permanently deleted after 30 days**. Render web service containers also have an **ephemeral filesystem** that wipes local files (including SQLite `.db` files) every time the app restarts, redeploys, or spins down. Using **Neon Free PostgreSQL** ensures your college project data persists permanently at zero cost.

---

## 2. Prerequisites

1. Your GitHub repository with the latest code pushed: `https://github.com/omg72637-cell/findback`
2. A free account on [Neon](https://neon.tech) (sign up with GitHub).
3. A free account on [Render](https://render.com) (sign up with GitHub).

---

## 3. Step-by-Step Deployment Procedure

### Step 1: Create Your Free Persistent Database on Neon
1. Log in to [Neon Console](https://console.neon.tech).
2. Click **Create Project**.
3. Name your project: `findback-db` (Region: choose nearest, e.g. US East or Europe).
4. On the project dashboard, locate the **Connection Details** box.
5. Ensure the dropdown is set to **`psql`** or **`Postgres`**, and copy the connection string. It will look like:
   ```text
   postgresql://neondb_owner:npg_RANDOM_PASSWORD@ep-example-host.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```
   *(Keep this string handy for Step 2; you will provide it as `DATABASE_URL` in Render).*

---

### Step 2: Deploy the Web Service on Render

#### Option A: One-Click Blueprint Deployment (Recommended)
Because this repository contains [`render.yaml`](render.yaml), you can deploy automatically:
1. Log in to [Render Dashboard](https://dashboard.render.com).
2. Click **New +** &rarr; **Blueprint**.
3. Connect your GitHub repository: `omg72637-cell/findback`.
4. Render will read `render.yaml` and prompt you for the un-synced environment variables:
   - `DATABASE_URL`: Paste your Neon connection string from Step 1.
   - `INITIAL_ADMIN_PASSWORD`: Choose a strong initial administrator password.
   - `INITIAL_DESK_STAFF_PASSWORD`: Choose a strong initial desk officer password.
5. Click **Apply**. Render will automatically build and deploy your service.

#### Option B: Manual Web Service Setup
If creating the service manually:
1. Click **New +** &rarr; **Web Service**.
2. Select **Build and deploy from a Git repository** and choose `omg72637-cell/findback`.
3. Configure the service settings:
   - **Name:** `findback`
   - **Region:** Same general region as your Neon database.
   - **Branch:** `main`
   - **Runtime:** `Python`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:**
     ```bash
     python database/init_db.py && gunicorn "app:create_app()" --bind 0.0.0.0:$PORT --workers 2 --threads 2
     ```
   - **Instance Type:** `Free`
4. Expand **Advanced** and set:
   - **Health Check Path:** `/healthz`
5. In the **Environment Variables** section, add:

| Key | Value | Description |
| :--- | :--- | :--- |
| `FLASK_ENV` | `production` | Enables production cookie flags (`Secure`, `HttpOnly`, `SameSite=Lax`). |
| `PYTHON_VERSION` | `3.12.8` | Ensures Render builds with a modern, fully-supported Python runtime. |
| `SECRET_KEY` | *(Generate a 32-byte hex key)* | `python -c "import secrets; print(secrets.token_hex(32))"` |
| `DATABASE_URL` | *(Your Neon Postgres URI)* | `postgresql://user:pass@ep-host.neon.tech/neondb?sslmode=require` |
| `INITIAL_ADMIN_PASSWORD` | *(Your secure admin password)* | Required by `init_db.py` to create the initial `admin` account. |
| `INITIAL_DESK_STAFF_PASSWORD` | *(Your secure desk staff password)*| Required by `init_db.py` to create the initial `desk_staff` account. |

6. Click **Create Web Service**.

---

## 4. How the Repeatable Deployment Works

1. **Build Phase:**
   Render runs `pip install -r requirements.txt` to install `Flask`, `Werkzeug`, `Gunicorn`, and `psycopg2-binary`.
2. **Pre-Start Initialization:**
   Before Gunicorn workers spawn, `python database/init_db.py` executes:
   - Executes `database/schema_pg.sql` (`CREATE TABLE IF NOT EXISTS`) to establish all tables and constraints.
   - Checks if `admin` or `desk_staff` accounts exist. If absent, it hashes the passwords provided in `INITIAL_ADMIN_PASSWORD` and `INITIAL_DESK_STAFF_PASSWORD` and inserts the records.
   - If accounts already exist, it preserves them untouched without altering passwords.
   - Checks if ordinary items exist. If empty, seeds initial demonstration ordinary items.
3. **Application Serving:**
   Gunicorn binds to `0.0.0.0:$PORT` using the Flask application factory `"app:create_app()"`.
   - `ProxyFix` middleware correctly handles Render's upstream HTTPS headers.
   - Session cookies are strictly `HttpOnly`, `SameSite=Lax`, and `Secure`.
   - Reverse proxy health checks monitor `/healthz`.

---

## 5. Post-Deployment Verification Checklist

Once your Render dashboard shows **Live**:

- [ ] **Health Check:** Navigate to `https://<your-service>.onrender.com/healthz`. Expected response: `{"status": "ok"}`.
- [ ] **Public Feed:** Navigate to `https://<your-service>.onrender.com/`. Verify ordinary items appear on the public feed.
- [ ] **Report Submission (Workflow A):** Submit a new ordinary item (e.g. lost water bottle). Verify it appears on the public board.
- [ ] **Confidential Submission (Workflow B):** Submit a private electronics report (e.g. lost iPhone). Verify a private tracking code (`TRK-...`) is issued and that the report **never** appears on the public feed.
- [ ] **Status Stepper:** Navigate to `/status` and check your tracking code. Verify progress status loads without leaking internal evidence.
- [ ] **Admin Authentication:** Navigate to `/admin/login`. Sign in using `admin` and your `INITIAL_ADMIN_PASSWORD`.
- [ ] **Database Persistence Test:** In Render dashboard, click **Manual Deploy &rarr; Restart Service**. After the service restarts, navigate to the public board and verify your newly reported items and accounts remain intact.

---

## 6. Troubleshooting Common Issues

| Symptom | Cause | Solution |
| :--- | :--- | :--- |
| **First page load takes ~50 seconds** | Render Free Tier spins down after 15 min of inactivity. | Normal behavior on free tier; subsequent requests respond instantly. |
| **Build fails with `psycopg2` error** | Outdated Python version without binary wheels. | Ensure `PYTHON_VERSION=3.12.8` is set in Render environment variables. |
| **App crashes on startup with `SECRET_KEY not set`** | Missing environment variable. | Add `SECRET_KEY` in Render Environment tab. |
| **App crashes with `Missing required environment variable INITIAL_ADMIN_PASSWORD`** | Initial passwords not set for fresh database. | Set `INITIAL_ADMIN_PASSWORD` and `INITIAL_DESK_STAFF_PASSWORD` in Render dashboard. |
| **Database connection error / SSL required** | Missing `?sslmode=require` in Postgres URI. | Ensure your `DATABASE_URL` ends with `?sslmode=require`. |
