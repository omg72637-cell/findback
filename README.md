# FindBack 2.0 — Campus Lost & Found Custody System

FindBack 2.0 is an educational engineering design prototype for campus lost-and-found management built using **Python, Flask, SQLite, and vanilla HTML5/CSS3/JavaScript**.

It solves opportunistic theft and privacy violations on university campuses through a **dual-workflow architecture**:
1. **Workflow A (Ordinary Items):** Everyday low-risk items (bottles, umbrellas, notebooks) are listed on an open, searchable public board.
2. **Workflow B (High-Value Electronics):** High-value devices (smartphones, laptops, earbuds) are **strictly confidential**. They never appear publicly and are processed exclusively via a deterministic matching engine, dispute locking, and single-use handover tokens.

---

## 1. Quick Start Guide (Run Locally in 5 Minutes)

### Prerequisites
- Python 3.10 to 3.15 installed
- Git installed
- SQLite 3 (built into standard Python)

### Step 1: Clone the Repository
```bash
git clone https://github.com/omg72637-cell/findback.git
cd findback
```

### Step 2: Create & Activate Virtual Environment
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

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Configure Local Environment (`.env`)
Copy the example environment template:

**Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**Windows (Command Prompt):**
```cmd
copy .env.example .env
```

**macOS / Linux:**
```bash
cp .env.example .env
```

Generate a secure 32-byte secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Configure your `.env` file with the generated key and your chosen initial staff passwords:
```ini
SECRET_KEY=paste-your-generated-key-here
FLASK_ENV=development
INITIAL_ADMIN_PASSWORD=choose-a-strong-initial-admin-password
INITIAL_DESK_STAFF_PASSWORD=choose-a-strong-initial-desk-staff-password
```

> [!NOTE]
> **Environment Variable Loading:**
> FindBack includes a zero-dependency `.env` reader that parses `.env` if present. However, standard Python does not natively inject `.env` files into operating system environment variables. If you prefer or are running scripts in PowerShell without a `.env` file, you can set environment variables directly in the active session:
> ```powershell
> $env:SECRET_KEY = "paste-your-generated-key-here"
> $env:FLASK_ENV = "development"
> $env:INITIAL_ADMIN_PASSWORD = "choose-a-strong-initial-admin-password"
> $env:INITIAL_DESK_STAFF_PASSWORD = "choose-a-strong-initial-desk-staff-password"
> ```

### Step 5: Initialize Database & Seed Demonstration Data
```bash
python database/init_db.py
```
This initializes the SQLite schema, creates staff accounts (`admin` and `desk_staff`) using the passwords specified in your environment, and seeds fictitious ordinary items.
- Both `INITIAL_ADMIN_PASSWORD` and `INITIAL_DESK_STAFF_PASSWORD` are required when creating accounts; the script halts with a helpful error if either is missing.
- Passwords are immediately hashed with Werkzeug scrypt/pbkdf2 and stored securely.
- If accounts already exist in the database, running `init_db.py` preserves them and will never alter existing passwords.

*(Teammate Database Isolation: A teammate cloning the repository can initialize their own separate database file by passing a path argument: `python database/init_db.py teammate.db`, or by setting `$env:DATABASE = "teammate.db"`).*

### Step 6: Start the Server
```bash
python app.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 2. Running Automated Tests

FindBack 2.0 maintains an empirically verified, test-driven validation suite with **88 passing tests** across 8 test modules:

```bash
pytest -v
```

*Expected execution result:* **`88 passed in ~17s`** (0 failures).

---

## 3. Project Documentation Directory

| Document | Purpose |
| :--- | :--- |
| **[`DEMO_SCRIPT.md`](file:///C:/Users/omwor/Documents/findback/DEMO_SCRIPT.md)** | Timed (7–10 minute) step-by-step live demonstration script with talking points and jury fallbacks. |
| **[`USER_GUIDE.md`](file:///C:/Users/omwor/Documents/findback/USER_GUIDE.md)** | End-user and staff operational manual (Workflow A, Workflow B, Status Stepper, Custody Desk). |
| **[`SETUP_AND_TESTING.md`](file:///C:/Users/omwor/Documents/findback/SETUP_AND_TESTING.md)** | Detailed developer setup, test suite details, demonstration reset runbook, and production deployment notes. |
| **[`PRESENTATION_NOTES.md`](file:///C:/Users/omwor/Documents/findback/PRESENTATION_NOTES.md)** | College EDI presentation notes, architecture diagrams, work division, limitations, and faculty Q&A. |
| **[`ARCHITECTURE.md`](file:///C:/Users/omwor/Documents/findback/ARCHITECTURE.md)** | Technical specification, data model, security boundaries, and scoring math. |
| **[`DECISIONS.md`](file:///C:/Users/omwor/Documents/findback/DECISIONS.md)** | Approved architectural decision records (DEC-01 to DEC-07) and deferred future scope (DEC-08 to DEC-12). |

---

## 4. Key Security Invariants

- **Zero Public Electronics Exposure:** High-value devices never appear in public feeds or HTML responses.
- **Prohibited Credential Protection:** Form heuristics block device unlock PINs, passwords, and biometrics.
- **Explainable Scoring:** Rule-based matching with transparent mathematical factor breakdown; match scores are investigative leads, not legal proof.
- **Dispute Freezing:** Competing claims lock handover tokens until an administrator adjudicates the conflict.
- **Cryptographic Token Lifecycle:** Handover tokens expire after 30 minutes, are single-use, and stored strictly as SHA-256 hashes in SQLite. Plaintext tokens are displayed only once.
- **100% Parameterized SQL:** Zero string concatenations or formatting in SQL statements.
