# FindBack 2.0 — Implementation Plan

**Document Version:** 1.0.0-draft  
**Target Audience:** First-Year B.Tech Engineering Project Team, Faculty Mentors, and Reviewers  
**Document Status:** Proposed Roadmap (No Application Code Has Been Written Yet)  

> [!NOTE]
> This document plans implementation steps for a project that is currently at the documentation stage. No application source code, database files, or configuration scripts exist yet. All phases describe future work.

---

## 1. Implementation Principles

The following principles must be respected by every team member throughout the project:

1. **Build Small, Learn First:** Start with the smallest working version of each feature before adding complexity. A single Flask route that prints "Hello, FindBack!" is more valuable than half-finished but complex code.
2. **Explain Before Implementing:** Before any team member writes a piece of code, they must be able to explain in plain language what the code does and why it is needed.
3. **Implement → Run → Test → Review → Document:** No feature is considered complete until it can be demonstrated running locally, tested with real inputs, and peer-reviewed by at least one other team member.
4. **Test Actually Means Run:** Saying "tests pass" requires that automated test commands have actually been executed, their results have been read, and those results are recorded. A test described in this document is a planned test, not a passing test.
5. **No Unnecessary Dependencies:** Do not add Python packages or external services without first checking their compatibility with the project environment and getting team agreement. The project uses Python 3.15 (installed locally); package compatibility with this version must be verified before installing anything.
6. **Privacy and Safety Are Non-Negotiable:** Every code change must be checked to ensure it cannot leak private electronics reports, contact details, or ownership clues through public routes, error pages, or session cookies.
7. **One Decision at a Time:** Unresolved decisions from `DECISIONS.md` (e.g., session strategy, handover desk location) must be settled through team discussion, not silently implemented by one person.

---

## 2. Phased Roadmap

Each phase follows a structured pattern: **Goal → Prerequisites → Tasks → Expected Files → Test → Completion Criteria → Common Beginner Mistakes.**

Phases are ordered by dependency. Implementation must not begin on a later phase while a gate of an earlier phase remains open.

---

### Phase 0: Review Requirements and Settle Open Decisions

**Goal:** Every team member reads and understands the four planning documents and the team resolves the open decisions from `DECISIONS.md` (DEC-07 through DEC-12) before writing a single line of application code.

**Prerequisites:** All four planning documents must be read by every team member.

**Tasks:**
1. Read `GEMINI.md`, `PRD.md`, `ARCHITECTURE.md`, and `DECISIONS.md` individually.
2. Meet as a team and discuss each document section by section.
3. Formally resolve these open decisions together:
   - **DEC-07:** Choose either Option A (Flask signed-cookie session) or Option B (SQLite-backed session table) for admin authentication.
   - **DEC-08:** Agree on how the first admin account will be created (seed script vs. interactive CLI tool).
   - **DEC-09:** Decide whether the submission form requires a validated campus email format.
   - **DEC-10:** Agree on the label for the physical handover desk location that will appear in UI templates.
   - **DEC-11:** Agree on a data-retention period for resolved and inactive records.
   - **DEC-12:** Accept the provisional scoring weights as a starting point and agree to calibrate with test data.
4. Update `DECISIONS.md` to record each decision and the date it was made (edit of `DECISIONS.md` only; no application files).

**Expected Files Updated (Documentation Only):**
* `DECISIONS.md` (updated status fields, decision-maker names, and dates)

**Test:**
* No automated test. Completion is verified by: every team member can explain the dual-workflow architecture, the privacy boundary, the provisional matching algorithm, and the admin auth design without referring to the documents.

**Completion Criteria:**
* All six open decisions (DEC-07 through DEC-12) recorded as `Confirmed` or `Proposed` in `DECISIONS.md`.
* Each team member can explain the system's purpose in a two-minute informal presentation.
* Team roles (see Section 3) have been assigned.

**Common Beginner Mistake:**
> Skipping this phase to "get to the coding faster." Unresolved design decisions create contradictory code later and waste more time than a focused planning session.

---

### Phase 1: Inspect the Repository and Confirm the Runtime Environment

**Goal:** Confirm that every team member can access the repository, that Git is working, and that Python 3 runs correctly on all development machines. No application files are created yet.

**Prerequisites:** Phase 0 complete. Git installed on all machines.

> [!IMPORTANT]
> Python 3.15 is installed in the current project environment. Before installing Flask or any other package, the team **must** verify that each package officially lists Python 3.15 as a supported version. Check the package's release history and classifiers on PyPI — do not rely on the package page existing or a recent release date alone. If a required package does not yet support Python 3.15, the team must **pause** and agree together on a supported Python version to use, then reconfigure the virtual environment accordingly. Do not force installation or attempt workarounds without documented team approval.

**Tasks:**
1. Clone or pull the repository on each team member's machine.
2. Verify Python 3 is available: run `python --version` or `python3 --version` and record the exact output.
3. Verify that `pip` (Python's package installer) is available: run `pip --version`.
4. Check that `python3 -c "import sqlite3; print(sqlite3.sqlite_version)"` produces a SQLite version number. SQLite is part of the Python standard library and should not require installation.
5. Look up Flask's latest version on PyPI and confirm it **explicitly lists Python 3.15 as a supported version** in the release classifiers or release notes. Record this finding, including the version number checked and the date. If Flask does not yet list Python 3.15 as supported, the team must stop and agree on a supported Python version before proceeding.
6. Look up `pytest`'s latest version on PyPI and confirm Python 3.15 support using the same method. Record this finding. If `pytest` does not support Python 3.15, the team must stop and agree on a supported Python version before proceeding.
7. Create a local Python virtual environment using `python -m venv .venv` and activate it.
8. Note: `.venv/` is already listed in `.gitignore` and must not be committed.
9. Inspect the current repository root: list `README.md`, `GEMINI.md`, `PRD.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `IMPLEMENTATION_PLAN.md`, and `.gitignore`.

**Expected Files (Unchanged):** No new application files. Existing planning documents only.

**Test (Manual Verification):**
* Every team member records in a shared chat or log: `python3 --version`, `sqlite3` version string, and Flask/pytest PyPI compatibility finding.

**Completion Criteria:**
* All four team members have confirmed their Python version locally.
* Flask and pytest compatibility with the installed Python version has been verified from official PyPI release classifiers or release notes (not assumed), and the finding is recorded. If either package does not support the installed Python version, the team has agreed on and documented a resolution before proceeding.
* Virtual environment creation succeeds on at least one machine.

**Common Beginner Mistake:**
> Installing packages globally (without a virtual environment) causes version conflicts between projects and makes it impossible to reproduce the project environment on another machine.

---

### Phase 2: Create the Smallest Flask Application and Verify It Runs Locally

**Goal:** Create only the minimal skeleton Flask application — a single file that starts a web server and returns a text response — and confirm it runs locally. This is not the complete application; it is a working foundation to build on.

**Prerequisites:** Phase 1 complete. Flask verified as compatible and installed inside `.venv`.

**Tasks:**
1. Activate the virtual environment on each machine (`source .venv/bin/activate` on macOS/Linux; `.venv\Scripts\activate` on Windows).
2. Install Flask inside the virtual environment: `pip install flask`. Record the exact version installed.
3. Create `requirements.txt` listing `flask` and `pytest` with their installed version pins. (For example: `flask==3.x.x`.)
4. Create `app.py` at the repository root containing only:
   - A Flask application instance.
   - A single route (`/`) that returns a simple HTML string: `"FindBack 2.0 — running."`.
   - A `if __name__ == '__main__': app.run(debug=True)` guard.
5. Create `config.py` with `SECRET_KEY` loaded from an environment variable using `os.environ.get('SECRET_KEY')`. **Do not provide a fallback value.** If `SECRET_KEY` is `None` or an empty string, the application must refuse to start — raise a `RuntimeError` with a clear message such as `"SECRET_KEY environment variable is not set. Set it before starting the application."`. Before running the app, create a local `.env` file (listed in `.gitignore` and never committed) that sets a development key of at least 32 random characters. You can generate one with `python -c "import secrets; print(secrets.token_hex(32))"`. The `.env` file is for local development only; a separately configured secret must be used in any other environment.
6. Run the application locally: `python app.py`. Verify the browser shows the expected response at `http://127.0.0.1:5000/`.
7. Create the folder layout described in `ARCHITECTURE.md` Section 2 — **empty folders and `__init__.py` placeholder files only**. Do not write any logic yet.

**Expected New Files:**
```text
app.py
config.py
requirements.txt
database/__init__.py
auth/__init__.py
matching/__init__.py
static/css/style.css       (empty placeholder)
static/js/main.js          (empty placeholder)
templates/base.html        (minimal HTML5 boilerplate only)
templates/errors/400.html  (minimal template only)
templates/errors/403.html
templates/errors/404.html
templates/errors/500.html
tests/__init__.py
tests/conftest.py
```

**Test:**
* **Manual test:** Visit `http://127.0.0.1:5000/` in a browser and confirm the text `"FindBack 2.0 — running."` appears.
* **Automated test (to be run now):** Write one test in `tests/conftest.py` using Flask's built-in test client that sends a GET request to `/` and asserts the response status is 200. Run `pytest` and record the result.

**Completion Criteria:**
* `python app.py` starts without error on at least one machine.
* `pytest` runs the skeleton test and it passes (result confirmed, not assumed).
* `requirements.txt` contains Flask and pytest with pinned versions.
* No hardcoded secrets in `app.py` or `config.py`.
* All team members can start the server on their own machines.

**Common Beginner Mistake:**
> Hardcoding `SECRET_KEY = 'my-secret'` directly in `app.py` or using a silent fallback like `os.environ.get('SECRET_KEY', 'dev-only-insecure-key')`. Either way the insecure value ends up in Git. Always load the key exclusively from an environment variable and make the application refuse to start if the variable is missing or empty.

---

### Phase 3: Build the Initial SQLite Schema and Safe Database Access

**Goal:** Define the five database tables (from `ARCHITECTURE.md` Section 4) in a SQL schema file, write a database connection helper, and a script to create and seed the database. No Flask routes are connected yet.

**Prerequisites:** Phase 2 complete. Folder structure created.

**Tasks:**
1. Write `database/schema.sql` containing `CREATE TABLE IF NOT EXISTS` statements for all five tables:
   - `ordinary_items`
   - `private_electronics`
   - `match_leads`
   - `admin_users` (stores only `password_hash`, never raw passwords)
   - `handover_logs`
   - Apply `PRAGMA foreign_keys = ON;` at the top.
   - Apply `CHECK` constraints for `category` (must be in allowlist) and `report_type` (`lost` or `found`).
2. Write `database/db.py` with helper functions:
   - `get_db()` — opens a SQLite connection with `row_factory = sqlite3.Row` so query results behave like dictionaries.
   - `close_db()` — closes the connection.
   - `query_db(sql, args, one)` — executes parameterized queries using `?` placeholders only. String interpolation in SQL is prohibited.
3. Write `database/init_db.py`:
   - Reads `schema.sql` and executes all statements.
   - Creates a seed admin account using credentials loaded from environment variables or a local `.env` file (not hardcoded). The password is hashed with `werkzeug.security.generate_password_hash` before insertion.
   - Inserts a small set of test ordinary items and sample electronics entries to support later testing.
4. Run `python database/init_db.py` and confirm `findback.db` is created. Verify its tables exist using Python's `sqlite3` module interactively.
5. Add `findback.db` to `.gitignore`. Database files must never be committed to version control.

**Expected New Files:**
```text
database/schema.sql
database/db.py
database/init_db.py
```

**Test (to be run now, not assumed):**
* Write `tests/test_db.py` with the following tests and run `pytest`:
  - Schema creation: running `init_db.py` creates all five tables without error.
  - Allowlist constraint: inserting an `ordinary_items` row with category `"Smartphone"` raises a SQLite `IntegrityError`.
  - `report_type` constraint: inserting a row with an invalid `report_type` raises an error.
  - Foreign key enforcement: inserting a `match_leads` row referencing a non-existent `private_electronics` ID raises an error.
  - Parameterized safety: the `query_db` function must accept only parameterized queries; document that raw SQL with user inputs is not implemented anywhere.

**Completion Criteria:**
* `pytest tests/test_db.py` passes — confirmed by running and reading the output.
* `findback.db` exists locally and contains all five tables.
* `findback.db` is listed in `.gitignore`.
* Password hash (not plaintext password) is stored in `admin_users`.

**Common Beginner Mistake:**
> Writing SQL as `f"SELECT * FROM {table}"` or `"SELECT * WHERE name = '" + name + "'"`. This is SQL injection. Always use `?` placeholders: `"SELECT * WHERE name = ?"`, `[name]`.

---

### Phase 4: Build Public Ordinary-Item Reporting and Allowlisted Listing Views

**Goal:** Build the public-facing pages: the home feed, the ordinary-item report form, and the category search/filter. Enforce the allowlist. Expose only approved fields in responses.

**Prerequisites:** Phase 3 complete. Database helper functions working and tested.

**Tasks:**
1. In `app.py`, add Flask routes:
   - `GET /` — queries `ordinary_items` using **explicit column projection** (never `SELECT *`) and renders `templates/index.html`.
   - `GET /report` — renders `templates/report_choice.html` explaining both workflows.
   - `GET /report/ordinary` — renders the empty ordinary-item form.
   - `POST /report/ordinary` — validates category against the hardcoded allowlist in Python (server-side), then inserts the record. Returns HTTP 400 with an error message if the category is not on the allowlist.
2. Write the Jinja2 templates:
   - `templates/index.html` — extends `base.html`; displays item cards showing only: category, description, campus location, date, and status. No email or contact field rendered.
   - `templates/report_choice.html` — explains the two workflows; includes a prominent banner about confidential electronics reports.
   - `templates/report_ordinary.html` — form with a strict category `<select>` dropdown (server-side allowlist enforced on POST, not just in HTML).
3. Apply Jinja2 auto-escaping. Do not disable it. This prevents XSS attacks.
4. Add a simple client-side validator in `static/js/main.js` that shows a helpful warning if the user selects an empty category before submitting. This is a UI convenience only; the server-side check is the authoritative guard.

**Expected New Files / Modified Files:**
```text
app.py                            (add routes)
templates/index.html              (public feed)
templates/report_choice.html      (workflow selector)
templates/report_ordinary.html    (ordinary-item form)
static/css/style.css              (basic responsive layout)
static/js/main.js                 (client-side hint only)
```

**Test (to be run now):**
* Write `tests/test_routes.py` and run `pytest`:
  - Submit ordinary form with an approved category → HTTP 302 redirect to `/` (or HTTP 200 if re-rendered). Record result.
  - Submit ordinary form with category `"Smartphone"` → HTTP 400. Record result.
  - Submit ordinary form with an empty category → HTTP 400. Record result.
  - GET `/` response must not expose `contact_email` in the rendered HTML. Assert this against the structured response data, not only by searching for the string `"contact_email"` in the HTML (a column name being absent from rendered HTML does not guarantee the underlying data is not accessible). Record result.
  - GET `/` — send a request without any session and assert that the JSON-serializable form of the response data contains no field names or values from `private_electronics`. Record result.

**Completion Criteria:**
* All five route tests pass — results recorded.
* Public feed page renders only approved fields.
* Team member (Member 1, frontend role) can demonstrate the pages in a browser.
* All team members understand how the allowlist check works in Python.

**Common Beginner Mistake:**
> Relying entirely on the HTML `<select>` to restrict categories. A user can bypass client-side controls by modifying the form with browser developer tools. The server must always re-validate the submitted category.

---

### Phase 5: Build Private Electronics Reporting and Privacy-Isolation Tests

**Goal:** Add the confidential electronics submission form and its backend route. Implement and verify that private reports are completely isolated from all public views, API responses, and error pages.

**Prerequisites:** Phase 4 complete and its tests passing.

**Tasks:**
1. Add routes in `app.py`:
   - `GET /report/electronics` — renders the confidential form.
   - `POST /report/electronics` — validates inputs server-side (device type must be from the allowed list). The form includes a prominent warning that device PINs, passwords, and recovery codes must never be entered; if the submitted text contains obvious patterns that resemble credentials (e.g., a field labelled "PIN" or a value that looks like a numeric PIN), the server rejects the request with HTTP 400. **Important limitation:** keyword or pattern detection is a heuristic, not a reliable filter. It cannot catch all forms of credential input. The server must also never store any value it recognises as a likely credential, and the team must document that heuristic detection is best-effort only, not a security guarantee. Generates a `tracking_code` using `secrets.token_urlsafe(32)` (or a longer value). This code is a **private status-lookup credential** — it lets the submitter check their report's status. It is not proof of ownership and must be treated as confidential: it must not be logged, displayed in error messages, or exposed to any other party. Inserts the record into `private_electronics` and shows the tracking code to the submitter exactly once.
   - `GET /status` — accepts a `tracking_code` parameter and returns only the item's current status label (`Submitted`, `Searching for Match`, `Under Staff Review`, `Ready for Desk Handover`, `Resolved`). Returns nothing else — no contact details, no distinctive clues, no match information. If the code is not found or does not match any record, return only a generic message (e.g., `"Status not available."`) **without confirming whether or not a record with that code exists.** This prevents an attacker from using the endpoint to probe whether random codes are valid.
2. Write `templates/report_electronics.html`:
   - Includes a prominent alert box: *"Do not enter your device PIN, password, or recovery code. These are never needed and must never be shared."*
   - Form fields: device type (restricted dropdown), brand, primary color, campus location, date found/lost, and safe distinctive clues (wallpaper description, case color, stickers).
3. Write `templates/status_lookup.html`.
4. Review every route in `app.py`: confirm there is no code path from any public route (`/`, `/report/*`, `/status`) to the `private_electronics` table.

**Expected New / Modified Files:**
```text
app.py                               (add electronics routes)
templates/report_electronics.html    (confidential form)
templates/status_lookup.html         (status lookup page)
```

**Test (to be run now):**
* Write `tests/test_privacy.py` and run `pytest`. Record all results:
  - GET `/` (unauthenticated) → response body and any response headers contain zero values from `private_electronics`. Assert against structured response data, not only by string-searching the HTML for column names. Record result.
  - Attempt to access a private electronics record directly (e.g., by guessing its URL) without a valid admin session → HTTP 404 or HTTP 403. The error page must not reveal any private data, column names, or database details. Record result.
  - POST to `/report/electronics` with a clearly credential-like input (e.g., `"PIN: 1234"` in the clues field) → HTTP 400. Record result. Note: this test confirms the heuristic rejects obvious patterns, not that it catches all possible credential inputs — document this limitation in the test record.
  - GET `/status` with a valid tracking code → returns only status label; assert that `reporter_contact`, `distinctive_clues`, and any other private field are absent from the structured response (not just absent from rendered HTML). Record result.
  - GET `/status` with an invalid or unknown tracking code → returns only a generic message without confirming whether a record exists for that code. Record result.
  - GET on any route that does not exist → custom 404 template renders; assert no database column names, stack traces, or private data appear in the response body or headers. Record result.
  - Attempt to access `/admin/leads` without a valid session → HTTP 302 to login. Confirm the response body contains no private electronics data. Record result.

**Completion Criteria:**
* All seven privacy tests pass — results recorded.
* No private electronics data appears in any public view, error page, or unauthorized response under any tested condition.
* Team member (Member 2, backend role) can explain the privacy isolation approach to the group.

**Common Beginner Mistake:**
> Writing a search feature that searches both `ordinary_items` and `private_electronics` with the same query. Always keep these tables in completely separate query paths.

---

### Phase 6: Implement and Test Deterministic Matching and Competing-Claim Handling

**Goal:** Implement the deterministic scoring algorithm in `matching/matcher.py`, the breakdown generator in `matching/explainer.py`, and the dispute-freeze protocol.

**Prerequisites:** Phase 5 complete and its tests passing. Team has agreed on provisional factor weights (DEC-12).

**Tasks:**
1. Write `matching/matcher.py`:
   - `compute_score(lost_report, found_report) -> dict`: takes two report dictionaries and returns a score dictionary.
   - **Device Type Gate (mandatory first check):** If `lost_report['device_type'] != found_report['device_type']`, immediately return `{"total_score": 0, "match_possible": False}`. No lead is created.
   - If device types match, compute additive score across remaining factors (brand, color, location, time window) using the provisional weights from `DECISIONS.md` DEC-12.
   - The function must be deterministic: given the same inputs, it must always return the exact same outputs.
2. Write `matching/explainer.py`:
   - `generate_breakdown(lost_report, found_report, score_dict) -> dict`: generates a structured Python dictionary explaining which factor earned which points and why.
3. Write a matching trigger in `database/db.py` or a background function called after a new electronics report is inserted:
   - Queries all open reports of the opposite type.
   - For each candidate pair, calls `compute_score`.
   - If the score meets the provisional notification threshold, inserts a row into `match_leads` with the score and the serialized breakdown (stored as a JSON string in `score_breakdown_json`).
4. Implement competing-claim freeze:
   - A competing claim exists at the **item level**: the same `private_electronics` record (a single lost or found report) appears in more than one `match_leads` row with `review_status` other than `dismissed`.
   - Before inserting a new lead: check whether the involved `private_electronics` record already appears in an active lead. If it does, mark both the new lead and the existing lead as `disputed`. Both updates and the new insert must be wrapped in a single SQLite transaction (`BEGIN`/`COMMIT`) so that no lead is left in an inconsistent state if the process is interrupted.
   - No handover token may be generated for any lead with `review_status = 'disputed'`.
   - **Match scores are investigative leads, not proof of ownership.** A high score means the pair is worth a human review, not that a claim is confirmed. Record this principle as a comment in `matcher.py`.

**Expected New / Modified Files:**
```text
matching/matcher.py
matching/explainer.py
database/db.py       (matching trigger helper)
```

**Test (to be run now):**
* Write `tests/test_matcher.py` and run `pytest`. Record all results:
  - Identical inputs (phone vs. phone, same brand, color, location, within 24 hours) → score = 100. Record result.
  - Incompatible device types (phone vs. laptop) → `match_possible = False`, `total_score = 0`. Record result.
  - Partial match (correct device type and brand, different color, different location) → intermediate score. Record result.
  - Same inputs called twice → identical score and breakdown (determinism test). Record result.
  - Two competing lost reports for the same found item → both leads marked `disputed` in database. Record result.
  - Disputed item → no handover token can be generated (function returns an error or guard value). Record result.

> [!IMPORTANT]
> The provisional 85% benchmark is an unvalidated hypothesis. Do not label any specific score as "proven accurate" after these tests. Record the actual scores produced for each test case and keep them for future calibration.

**Completion Criteria:**
* All six matching tests pass — results recorded.
* Member 4 (matching/testing role) can explain each scoring factor and why it contributes to the score.
* The team has a log of actual score outputs from test cases to compare against the 85% benchmark.

---

### Phase 7: Implement Individual Administrator Authentication and Authorisation

**Goal:** Implement the admin login, logout, and `@admin_required` server-side decorator. Block unauthorized access to all `/admin/*` routes. Do not implement this phase until the session strategy (DEC-07) and account provisioning approach (DEC-08) are confirmed.

**Prerequisites:** Phase 6 complete. DEC-07 (session approach) and DEC-08 (account provisioning) formally confirmed. Phase 3 seed script creates a valid hashed admin account.

**Tasks:**
1. Write `auth/session.py`:
   - `@admin_required` decorator: checks that `session['user_id']` exists and that the corresponding user in `admin_users` has an admin role. If not, redirect to `/admin/login` (or return HTTP 403 for API requests).

   > [!WARNING]
   > **Flask's signed cookie is signed, not confidential.** The session cookie's payload is base64-encoded and can be decoded by anyone who can read the cookie — only the signature prevents tampering. **Do not store passwords, password hashes, sensitive clues, reporter contact details, or any private report data in the session cookie.** Signing and obscuring values are not substitutes for keeping sensitive data server-side. Hiding admin links from the navigation bar provides no access control; only the server-side `@admin_required` check matters.

   - Implement the session approach agreed upon in DEC-07:
     - **If Option A:** Store only `user_id` (integer) and `role` (string) in Flask's signed cookie session. Set `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, and `PERMANENT_SESSION_LIFETIME = timedelta(minutes=60)` in `config.py`.
     - **If Option B:** Generate a `secrets.token_hex(32)` session token, store it in an `admin_sessions` table, and keep only the token in the cookie.
2. Write `auth/routes.py`:
   - `GET /admin/login` — renders login form.
   - `POST /admin/login` — fetches `password_hash` from `admin_users` and verifies it with `werkzeug.security.check_password_hash`. On success, set session variables. On failure, return the login page with a generic "invalid credentials" message (never say "wrong password" vs "wrong username" specifically).
   - `GET /admin/logout` — calls `session.clear()` and redirects to `/`.
3. Write `templates/admin/login.html` with CSRF protection on the form and error display.

   > [!IMPORTANT]
   > **The CSRF implementation approach must be agreed upon before any state-changing form is coded.** The team must choose a minimal, understandable method — for example, a manually generated hidden token stored in the session and compared on each POST — and record this choice in `DECISIONS.md` before Phase 7 begins. If a third-party library is considered, the team must verify it is compatible with the installed Python version and obtain documented agreement before installing it. Do not assume any library is available.
4. Apply `@admin_required` to every route in `/admin/*`.

**Expected New / Modified Files:**
```text
auth/routes.py
auth/session.py
config.py               (secure cookie settings added)
templates/admin/login.html
app.py                  (register auth blueprint)
```

**Test (to be run now):**
* Write `tests/test_auth.py` and run `pytest`. Record all results:
  - GET `/admin/leads` without session → redirected to `/admin/login` (HTTP 302). Record result.
  - POST `/admin/login` with correct credentials → session set; redirect to `/admin/leads`. Record result.
  - POST `/admin/login` with wrong credentials → login page returned; no session variable set. Record result.
  - After login, GET `/admin/leads` → HTTP 200. Record result.
  - After logout, GET `/admin/leads` → redirected to `/admin/login`. Record result.
  - Direct URL access to `/admin/leads` without session cookie → rejected. Record result.
  - Inspect the session cookie after login (decode the base64 payload) and confirm it contains **only** `user_id` and `role` — no password hashes, no contact details, no private clues, no sensitive report data. Record result.

**Completion Criteria:**
* All six auth tests pass — results recorded.
* Member 3 (database/auth role) can explain how `werkzeug.security` hashing works.
* Admin portal is inaccessible without a valid authenticated session, verified by test results.
* No password hash, student contact, or private clue is stored in or readable from the session cookie.

**Common Beginner Mistake:**
> Hiding the admin link from the navigation bar and assuming that prevents access. Any user can type `http://127.0.0.1:5000/admin/leads` directly. Only a server-side check inside the route handler (the `@admin_required` decorator) provides real protection.

---

### Phase 8: Implement Authorized Review Dashboard and Safe Handover Records

**Goal:** Build the admin lead review queue, the dispute adjudication view, and the supervised handover token workflow.

**Prerequisites:** Phase 7 complete and all auth tests passing. DEC-10 (handover desk label) confirmed.

**Tasks:**
1. Write Flask routes (all decorated with `@admin_required`):
   - `GET /admin/leads` — queries `match_leads` joined with `private_electronics` fields (restricted to admin only). Renders a side-by-side comparison of lost vs. found clue descriptions and score breakdowns.
   - `POST /admin/leads/<id>/status` — updates `review_status` for a lead (`investigating`, `disputed`, `dismissed`). Validates the CSRF token using the approach agreed upon in Phase 7.
   - `POST /admin/leads/<id>/approve` — changes `review_status` to `approved`, generates an expiring single-use handover token (see below).
   - `GET /admin/handover` — renders the handover token entry screen.
   - `POST /admin/handover` — verifies the submitted token: checks the SHA-256 hash matches, that `token_expires_at` is in the future, and that `token_used_at IS NULL`. If all checks pass, marks `token_used_at = now()`, updates item status to `resolved`, and logs `admin_id` and timestamp.
2. Handover token generation:
   - Use `secrets.token_urlsafe(8)` to generate a short token.
   - Store `hashlib.sha256(token.encode()).hexdigest()` in `handover_logs.token_hash`. Never store the raw token in the database.
   - Set `token_expires_at` to 30 minutes from now.
   - Display the raw token only once (on the admin screen at the moment of generation).
3. Write templates:
   - `templates/admin/leads.html` — shows match lead queue, score badge, and clue comparison. Displays `Disputed` status prominently. Never exposes raw `reporter_contact` values in HTML attributes or data attributes.
   - `templates/admin/disputes.html` — dispute review view.
   - `templates/admin/handover.html` — token entry and confirmation screen.

**Expected New / Modified Files:**
```text
app.py                          (admin review, dispute, and handover routes added)
matching/service.py             (token generation, hashing, dispute adjudication helpers)
templates/admin/leads.html      (side-by-side review dashboard)
templates/admin/disputes.html   (conflict adjudication view)
templates/admin/handover.html   (custody desk protocol and token redemption)
templates/admin/token_issued.html (one-time token issuance receipt)
templates/base.html             (updated staff navigation)
templates/admin/dashboard.html  (updated overview cards)
tests/test_handover.py          (19 dedicated automated tests)
```

**Test Execution Results (Phase 8 Verified):**
* Executed `pytest tests/test_handover.py -v`: **19 passed, 0 failed in 6.58s**.
* Executed full test suite `pytest -v`: **79 passed, 0 failed in 14.28s**.
  - Authorized staff (`admin` and `desk_staff`) can access review queues and handover desk.
  - Unauthenticated requests redirect to `/admin/login`.
  - Tiered RBAC: `desk_staff` attempting `status` update or `approve` receives HTTP 403 Forbidden.
  - Server allowlist rejects arbitrary statuses with HTTP 400.
  - Disputed leads and items strictly locked from token generation and redemption.
  - Dismissing invalid competing claim cleanly unfreezes remaining valid candidate.
  - Single-use token is unpredictable; only SHA-256 hash stored in database.
  - Expired tokens (>30 minutes) and previously consumed tokens rejected with HTTP 400.
  - Double redemption / race conditions prevented by atomic compare-and-swap.
  - Failed transactions roll back atomically.
  - Missing or tampered CSRF tokens blocked with HTTP 400.
  - Audit trail in `handover_logs` captures required events without raw tokens or credentials.
  - Error responses do not leak SQL, secrets, private clues, or stack traces.

**Completion Criteria:**
* All 19 Phase 8 tests pass — results verified and recorded.
* Handover token is never stored in plain text in SQLite, confirmed by inspection of `handover_logs`.
* `Disputed` leads cannot produce or redeem a handover token, confirmed by automated tests.
* Full test suite regression check confirms 79 passing tests across Phases 1–8.

---

### Phase 9: Security, Usability, Accessibility, and Regression Checks

**Goal:** Run a structured review of the complete application against all privacy, security, and usability requirements before the final demonstration.

**Prerequisites:** Phases 3 through 8 complete, all phase test gates passed.

**Tasks:**

**Security Checklist (Every Item Checked and Empirically Recorded):**
1. `test_privacy.py` — Ran full privacy suite (17 passed). Confirmed zero private electronics data leaks through any public route or error page (400, 403, 404, 500 templates).
2. SQL injection check — Automated AST analysis across all `.py` files confirmed 100% parameterized query usage (`?` placeholders). Zero string concatenations, f-strings, or `.format()` calls found in database queries.
3. Secret check — Verified via `git log -p` and `git diff HEAD`. Confirmed zero secrets, `.env` files, or passwords in Git history (only initial 2-line `README.md` tracked).
4. Session cookie inspection — Confirmed DEC-07 compliance: Flask signed-cookie session contains strictly `admin_user_id`. Roles and status are dynamically verified against SQLite on every protected request.
5. XSS check — Automated scan of all HTML templates confirmed zero usages of `| safe` filter. Jinja2 automatic HTML escaping is preserved on all user inputs.

**Usability & Accessibility Checklist:**
1. Every form has explicit `<label for="...">` tags and clear, high-contrast validation error messages (`role="alert"`).
2. The site is navigable with keyboard-only controls. Added WCAG-compliant skip-to-content link (`.skip-link`) pointing to `<main id="main-content">`.
3. Responsive design tested: navigation links use `flex-wrap: wrap`, comparison grids collapse cleanly on mobile (`.lead-col-lost`), and audit tables use horizontal overflow scrolling.

**Regression & Integration Test:**
* Created `tests/test_integration.py` with 5 end-to-end user journeys (ordinary item workflow, confidential electronics matching & handover lifecycle, competing-claim dispute freeze & unfreezing, anti-oracle defenses, and accessibility compliance).
* Run `pytest -v` across entire `tests/` directory: **84 passed, 0 failed in 21.75s**.

**Completion Criteria:**
* All security checklist items recorded and resolved.
* `pytest` passes all 84 tests (79 existing + 5 new integration tests). Full output recorded.
* No hardcoded secrets visible in repository.

---

### Phase 10: Demonstration, Documentation, and Final Review

**Goal:** Prepare a working demonstration suitable for a project presentation and ensure all documentation accurately reflects the implemented system.

**Prerequisites:** Phase 9 complete and all checks recorded.

**Tasks:**
1. **Write or complete `README.md`:** The current `README.md` at the repository root is a placeholder with only two lines. Phase 10 replaces it with a complete setup guide. Write it from scratch so that a person who was not on the team can set up and run the project without asking for help. Include: project description, prerequisites, how to clone the repository, how to create and activate the virtual environment, how to install dependencies with `pip install -r requirements.txt`, how to create the `.env` file and set `SECRET_KEY`, how to run `python database/init_db.py` to create the database, and how to start the server with `python app.py`.
2. **Update planning documents:** If any implementation detail changed from what was originally proposed, record those changes in `DECISIONS.md` with a date and rationale. Do not change what the documents say a feature does — change the document to match what was actually built.
3. **Prepare a demonstration script** (a plain text or markdown walkthrough that each team member can use to guide a live demo):
   - Ordinary-item submission → appears on public board.
   - Attempt to submit an electronics item to the public form → rejected.
   - Confidential electronics submission → tracking code received.
   - Matching engine computes score → lead appears in admin queue.
   - Admin reviews lead, inspects score breakdown.
   - Admin approves handover → expiring token generated.
   - Token submitted → handover recorded, item resolved.
4. **Final peer walk-through:** Every team member (not just the one who wrote the code) demonstrates one complete user workflow in the browser while explaining what each part does.

**Completion Status & Criteria:**
* `README.md` completely rewritten from a 2-line placeholder into a full, self-contained project quick-start and setup guide.
* `DEMO_SCRIPT.md` created with a timed 7–10 minute rehearsable walkthrough, 10 detailed presentation steps, script cards, and fallback procedures.
* `USER_GUIDE.md` created with complete operational instructions for students and staff.
* `SETUP_AND_TESTING.md` created with developer setup, test suite execution guide, pre-flight demo checklist, and production cloud deployment guidelines.
* `PRESENTATION_NOTES.md` created with problem statement, system architecture, innovation, 4-person work division, limitations, and 10 faculty Q&As.
* DEC-08 through DEC-12 preserved as unresolved institutional decisions.
* Complete test suite verified: **84 passed, 0 failed in 19.47s**.

---

## 3. Four-Person Work Division

Team roles are defined by primary ownership, not exclusive access. Every team member must be able to explain every part of the system.

| Role | Primary Owner | Core Deliverables |
| :--- | :--- | :--- |
| **Member 1: Frontend / UI** | — | HTML templates (`base.html`, public pages, admin pages), CSS styling, client-side JS hints, keyboard accessibility, responsive layout. |
| **Member 2: Flask Routes & Workflows** | — | `app.py` routes, form handling, request validation, Jinja2 template rendering, error handlers, blueprint registration. |
| **Member 3: Database & Authentication** | — | `database/schema.sql`, `database/db.py`, `database/init_db.py`, `auth/routes.py`, `auth/session.py`, password hashing, session cookie configuration, CSRF tokens. |
| **Member 4: Matching Engine & Testing** | — | `matching/matcher.py`, `matching/explainer.py`, all test files (`tests/`), score calibration records, privacy and security test suites. |

### Shared Integration Checkpoints
At the end of Phases 4, 6, 8, and 10, the full team must meet and run the complete test suite together. Any failure is a shared responsibility, not the responsibility of only one team member.

### Cross-Learning Requirement
* Member 1 must be able to read and explain a Flask route.
* Member 2 must be able to explain a Jinja2 template loop.
* Member 3 must be able to trace a database query through `db.py`.
* Member 4 must be able to explain the allowlist validation logic.

No team member may present work at the final demonstration without being able to answer a question about any other member's component.

---

## 4. Git Workflow

**Rules for using Git in this project:**

> [!CAUTION]
> Never commit or push `.env` files, `findback.db`, or any file containing real credentials. These are listed in `.gitignore`. Before every commit, run `git status` and read the output carefully to confirm which files you are adding.

1. **Feature Branches:** For each phase or significant task, create a branch named descriptively (e.g., `phase-3-database-schema`, `phase-4-public-feed`). Never commit directly to `main` until the feature is reviewed by at least one other team member.
2. **Small, Focused Commits:** Each commit should represent one logical change. A commit message should complete the sentence "This commit ___." (e.g., "adds allowlist validation to ordinary-item POST route").
3. **Review Diffs Before Committing:** Run `git diff --staged` before committing to read every line you are adding. This habit catches accidentally staged secrets, debug prints, or unfinished code.
4. **Pull Before Working:** Start every work session with `git pull origin main` (or your branch name) to get the latest changes from teammates.
5. **Resolve Conflicts Carefully:** When a merge conflict appears, read both versions of the conflicting code before choosing which to keep. Never blindly accept "theirs" or "ours".
6. **No Remote Changes:** This plan does not authorize changing the Git remote URL, creating new remotes, or altering GitHub repository settings.

---

## 5. Testing Strategy

All tests described below are **planned**. A test is only considered to have run when a team member has executed the test command, read the output, and recorded the number of passing and failing tests.

| Test Category | What It Checks | When It Runs | Files |
| :--- | :--- | :--- | :--- |
| **Unit: Database** | Table creation, constraints, foreign keys, parameterized query safety | End of Phase 3 | `tests/test_db.py` |
| **Unit: Matching** | Scoring factors, device-type gate, determinism, competing-claim freeze | End of Phase 6 | `tests/test_matcher.py` |
| **Integration: Routes** | Public form submission, allowlist rejection, rendering | End of Phase 4 | `tests/test_routes.py` |
| **Privacy Leakage** | Public views, API responses, error pages never return private electronics data | End of Phase 5 and again in Phase 9 | `tests/test_privacy.py` |
| **Authorization (RBAC)** | Unauthenticated access to admin routes is blocked server-side | End of Phase 7 | `tests/test_auth.py` |
| **Handover Validation** | Token expiry, single-use enforcement, dispute freeze on handover | End of Phase 8 | `tests/test_auth.py` (extended) |
| **Regression** | All previous tests still pass after each new phase | End of Phase 9 and Phase 10 | `pytest` (full suite) |

---

## 6. Definition of Done

A phase is considered **complete** only when **all** of the following are true:

1. **Code runs without error** on at least one team member's machine.
2. **Tests have actually been executed:** The `pytest` command was run, the output was read, and the result (number passed / failed) was recorded in a shared log or team notes.
3. **Privacy constraints remain satisfied:** Confirmed by running `tests/test_privacy.py` after any change that touches routes or templates.
4. **Peer review:** At least one team member who did not write the code for this phase has read the diff, asked questions, and approved the changes.
5. **Team understanding:** Every team member can describe what this phase adds to the system, without referring to the implementation plan.
6. **No unapproved decisions:** If implementing the phase required making a design choice not covered in `DECISIONS.md`, that choice must be recorded in `DECISIONS.md` before the phase is marked done.

---

## 7. Risks and Dependencies

### 7.1 Python Version Compatibility Risk

> [!WARNING]
> The project environment currently has **Python 3.15** installed. Python 3.15 was released in 2025 and is a recent version. Some third-party packages (including Flask extensions and testing plugins) may not yet have stable releases compatible with Python 3.15. Before installing any package, the team must:
> 1. Check the package's release history on PyPI.
> 2. Confirm the package lists Python 3.15 as a supported version.
> 3. Install in a virtual environment (`.venv`), not globally.
> 4. Record the exact installed version in `requirements.txt`.

If a package is not yet compatible with Python 3.15, the team must either use a compatible older version, find an alternative, or report the blocker to a mentor.

### 7.2 Unresolved Decisions (from `DECISIONS.md`)

These decisions must be resolved during Phase 0 before implementation begins:

| Decision ID | Topic | Blocking Which Phase |
| :--- | :--- | :--- |
| **DEC-07** | Admin Session Mechanism (Option A or B) | Phase 7 |
| **DEC-08** | Admin Account Provisioning Mechanism | Phase 3 |
| **DEC-09** | Student Identity Verification Approach | Phase 5 |
| **DEC-10** | Physical Handover Desk Location Label | Phase 8 |
| **DEC-11** | Data Retention and Archiving Policy | Phase 8 |
| **DEC-12** | Scoring Factor Weights | Phase 6 |

This plan does not silently resolve any of these open decisions. Each must be formally agreed upon by the team.

### 7.3 Scope Freeze
The following features remain **out of scope** for all phases in this plan:
* Photo / image uploads
* Google Gemini API integration
* Campus Single Sign-On (SSO)
* Automated email or SMS notifications

Adding any of these would require a formal scope change approved by the team and documented in `DECISIONS.md`.

---

## 8. Scope Boundaries

The following table summarizes what this implementation plan authorizes and what it does not:

| Authorized Activity | Not Authorized |
| :--- | :--- |
| Creating and editing application files in phases 2–10 | Editing `PRD.md`, `ARCHITECTURE.md`, `DECISIONS.md`, or `GEMINI.md` (except to record resolved decisions) |
| Installing `flask` and `pytest` inside `.venv` | Installing packages globally or without checking Python 3.15 compatibility first |
| Creating `findback.db` locally | Committing `findback.db` to Git |
| Creating `.env` locally for `SECRET_KEY` | Committing `.env` to Git |
| Writing and running tests with `pytest` | Claiming tests pass without running them |
| Photo uploads | (Deferred to a future phase outside this plan) |
| Gemini API integration | (Deferred; rule-based matching must be validated first) |
| Campus SSO / OAuth | (Deferred; outside scope of local prototype) |
| Automated email / SMS | (Deferred; communication mediated by campus desk staff) |
