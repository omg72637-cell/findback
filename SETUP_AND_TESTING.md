# FindBack 2.0 — Local Setup, Testing & Demonstration Runbook

## 1. System Requirements & Prerequisites

To run FindBack 2.0 locally, ensure you have:
* **Operating System:** Windows 10/11, macOS, or Linux.
* **Python Version:** Python 3.10 to 3.15 (standard CPython release).
* **Database:** SQLite 3 (included natively with standard Python distributions).
* **Version Control:** Git 2.25+ installed.
* **Web Browser:** Any modern evergreen web browser (Chrome, Firefox, Safari, Edge).

---

## 2. Step-by-Step Local Installation

### Step 1: Clone the Repository
Open Command Prompt (Windows) or Terminal (macOS/Linux) and clone the repository:
```bash
git clone https://github.com/omg72637-cell/findback.git
cd findback
```

### Step 2: Create & Activate Virtual Environment
Always install project dependencies in an isolated virtual environment:

**On Windows:**
```cmd
python -m venv .venv
.\.venv\Scripts\activate
```

**On macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 3: Install Required Dependencies
FindBack 2.0 uses a deliberately lean dependency footprint (zero heavy frameworks):
```bash
pip install -r requirements.txt
```

*Installed Packages in `requirements.txt`:*
- `Flask==3.1.3` (Core web framework)
- `Werkzeug==3.1.9` (WSGI utilities, password hashing, and HTTP helpers)
- `pytest==9.1.1` (Automated testing harness)

### Step 4: Configure Local Environment Variables
Copy the template configuration file:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On Windows (Command Prompt):**
```cmd
copy .env.example .env
```

**On macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` and configure your local settings. You can generate a cryptographically strong 32-byte secret key using Python:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Configure your `.env` file with placeholders replaced by your own local values:
```ini
# FindBack 2.0 Local Environment Configuration
SECRET_KEY=paste-your-generated-64-character-hex-key-here
FLASK_ENV=development
INITIAL_ADMIN_PASSWORD=choose-a-strong-initial-admin-password
INITIAL_DESK_STAFF_PASSWORD=choose-a-strong-initial-desk-staff-password
```

> [!NOTE]
> **How Environment Variables are Loaded:**
> FindBack provides a zero-dependency `.env` reader in `config.py` and `database/init_db.py` to parse key-value pairs if a local `.env` exists. However, Python standard library does not natively inject `.env` files into operating system environment variables. In PowerShell, you can also define environment variables directly in your current session:
> ```powershell
> $env:SECRET_KEY = "paste-your-generated-64-character-hex-key-here"
> $env:FLASK_ENV = "development"
> $env:INITIAL_ADMIN_PASSWORD = "choose-a-strong-initial-admin-password"
> $env:INITIAL_DESK_STAFF_PASSWORD = "choose-a-strong-initial-desk-staff-password"
> ```

*(Note: In accordance with security standards, `.env` and `findback.db` are strictly ignored by `.gitignore` and must never be committed to Git).*

### Step 5: Initialize Schema & Seed Synthetic Demonstration Data
Run the database initialization script:
```bash
python database/init_db.py
```

*What this script does:*
1. Enables SQLite foreign key enforcement (`PRAGMA foreign_keys = ON;`).
2. Creates the schema tables (`admin_users`, `ordinary_items`, `private_electronics`, `match_leads`, `handover_logs`).
3. Verifies that `INITIAL_ADMIN_PASSWORD` and `INITIAL_DESK_STAFF_PASSWORD` are present in the environment (raising a clear `ValueError` if either is missing) and securely hashes them using Werkzeug before inserting the accounts.
4. Seeds two demonstration accounts: `admin` (Role: `admin`) and `desk_staff` (Role: `desk_staff`).
5. Seeds four fictitious ordinary items (water bottle, umbrella, reading glasses, notebook) for immediate public feed browsing.
6. Preserves existing accounts and passwords without changes if re-run against an already initialized database.

> [!TIP]
> **Teammate Database Isolation:**
> When collaborating or verifying locally, each developer can initialize their own separate database without touching another instance:
> ```powershell
> # Option A: Pass custom path as argument
> python database/init_db.py teammate.db
>
> # Option B: Set DATABASE environment variable
> $env:DATABASE = "teammate.db"
> python database/init_db.py
> ```

### Step 6: Start the Local Development Server
Launch the Flask development server:
```bash
python app.py
```

You should see:
```text
 * Serving Flask app 'app'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 3. Automated Testing Guide

FindBack 2.0 includes a comprehensive, test-driven validation suite with **88 passing automated tests** covering database constraints, deterministic matching, role-based authorization, single-use token lifecycles, and zero-leakage privacy boundaries.

### 3.1 Running the Full Test Suite
To run all 88 automated tests with verbose output:
```bash
pytest -v
```
*Expected Result:* **`88 passed in ~17s`** (0 failures).

### 3.2 Running Focused Test Categories
You can run specific test modules depending on what you are reviewing:

| Test Target | Command | What It Verifies |
| :--- | :--- | :--- |
| **End-to-End Integration** | `pytest tests/test_integration.py -v` | Complete user journeys: ordinary flow, confidential electronics matching, dispute adjudication, token handover, and WCAG accessibility. |
| **Privacy & Zero-Leakage** | `pytest tests/test_privacy.py -v` | Anti-oracle status lookup, zero-leakage of private electronics in public views, prohibited credential defenses. |
| **Handover & Token Lifecycle** | `pytest tests/test_handover.py -v` | Single-use token hash storage, 30-min expiry, dispute locking, compare-and-swap race condition prevention. |
| **Staff Authentication & RBAC** | `pytest tests/test_auth.py -v` | Password hashing, signed-cookie sessions, CSRF token enforcement, open redirect defenses, role permissions. |
| **Deterministic Matching Engine** | `pytest tests/test_matcher.py -v` | Factor weights, device compatibility gate, score calibration, dispute detection. |
| **Database Schema & Constraints** | `pytest tests/test_db.py -v` | Foreign key cascades, category allowlists, parameterized query safety, and initial password environment variable requirements. |
| **Public Feed Routes** | `pytest tests/test_routes.py -v` | Allowlist enforcement on ordinary submissions, contact email exclusion. |

---

## 4. Demonstration Runbook & Pre-Flight Checks

Follow these steps before presenting live to faculty:

### 4.1 Reset to Clean Demonstration State
If previous demo runs left test records in your local database:
```cmd
python database/init_db.py
```
*(If you need a completely blank slate, you may delete the local `findback.db` file and re-run `python database/init_db.py`).*

### 4.2 Demonstration Accounts Available
The local seed script generates two safe, fictitious demonstration accounts:
- **Security Administrator Account:** Username `admin` (Role: `admin` — full privileges: review, adjudicate disputes, approve leads, issue tokens).
- **Custody Desk Officer Account:** Username `desk_staff` (Role: `desk_staff` — restricted privileges: queue inspection, custody desk token redemption; approval actions return HTTP 403 Forbidden).

*(Initial passwords must be set via `INITIAL_ADMIN_PASSWORD` and `INITIAL_DESK_STAFF_PASSWORD` in `.env` or the environment; hardcoded fallback passwords are prohibited).*

### 4.3 Pre-Calculated Demonstration Scenarios

#### Scenario A: High-Scoring Match (Success Path)
* **Report 1 (Lost):** Phone &bull; Apple &bull; iPhone 13 &bull; Midnight Blue &bull; Library 2nd Floor &bull; Clue: *"Clear case with small owl decal"*
* **Report 2 (Found):** Phone &bull; Apple &bull; iPhone 13 &bull; Midnight Blue &bull; Library 2nd Floor &bull; Clue: *"Clear case with small owl sticker on corner"*
* **Result:** Total score = **85.0%** &rarr; Lead created in `/admin/leads` &rarr; Approved by Admin &rarr; Token issued &rarr; Redeemed at desk.

#### Scenario B: Incompatible Device Gate (Rejection Path)
* **Report 1 (Lost):** Laptop &bull; Apple &bull; MacBook Air &bull; Silver &bull; Library 2nd Floor
* **Report 2 (Found):** Tablet &bull; Apple &bull; iPad Pro &bull; Silver &bull; Library 2nd Floor
* **Result:** Device gate fails &rarr; Score = **0.0%** &rarr; Zero leads created.

#### Scenario C: Competing Claim Dispute (Freeze Path)
* **Found Report:** Phone &bull; Samsung &bull; Galaxy S22 &bull; Black &bull; Lab 101
* **Claimant 1 (Lost):** Phone &bull; Samsung &bull; Galaxy S22 &bull; Black &bull; Lab 101 &bull; Clue: *"Blue bumper case with dog sticker"*
* **Claimant 2 (Lost):** Phone &bull; Samsung &bull; Galaxy S22 &bull; Black &bull; Lab 101 &bull; Clue: *"Plain black case with cracked screen protector"*
* **Result:** Dispute detected &rarr; Both leads and items flagged `disputed` &rarr; Handover frozen &rarr; Admin adjudicates on `/admin/disputes`.

---

## 5. Production Deployment Guide (Render / Cloud Hosting)

> [!IMPORTANT]
> The local development setup described above uses Flask's built-in development server (`python app.py`), which is single-threaded and not designed for production traffic. A production deployment requires the following specific steps:

### 5.1 Add Production WSGI Server
Add `gunicorn` to `requirements.txt`:
```text
flask==3.1.3
gunicorn==23.0.0
pytest==9.1.1
werkzeug==3.1.9
```

### 5.2 Configure Environment Variables in Cloud Dashboard
Set the following environment variables in your cloud provider's web service dashboard (e.g. Render, Railway):
- `FLASK_ENV=production` &rarr; Automatically activates `SESSION_COOKIE_SECURE=True` in `config.py`, requiring HTTPS.
- `SECRET_KEY` &rarr; Set to a cryptographically secure 64-character hex string.
- `INITIAL_ADMIN_PASSWORD` &rarr; Set a strong, unique password for the administrator account.
- `INITIAL_DESK_STAFF_PASSWORD` &rarr; Set a strong, unique password for the desk staff account.

### 5.3 Build & Start Commands
On cloud platforms with ephemeral filesystems (like Render free tier), the start command must initialize the SQLite database before binding Gunicorn:
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `python database/init_db.py && gunicorn "app:create_app()"`

### 5.4 Pre-Deployment Git Verification
Before pushing to production, verify with `git status` that `.env` and `findback.db` remain untracked and that zero credentials are committed to version control.
