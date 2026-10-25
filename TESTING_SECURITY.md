# FindBack 2.0 — Testing & Security Specification

**Document Version:** 1.0.0-draft  
**Target Audience:** First-Year B.Tech Engineering Project Team, Faculty Mentors, and Reviewers  
**Document Status:** Proposed Specification (No Application Code Has Been Written Yet)  

> [!NOTE]
> This document defines the testing strategy, test fixtures, security invariants, privacy verification procedures, and acceptance criteria for FindBack 2.0. All tests described herein are **planned tests**. In accordance with project engineering rules, no test may be described as "passed" or "verified" until test scripts are implemented, executed against real code, and their execution logs recorded.

---

## 1. Testing Strategy

### 1.1 Strategy Overview
FindBack 2.0 is built by a first-year student engineering team learning Python, Flask, and relational databases. The testing strategy is designed to be rigorous, educational, and feasible without requiring complex testing microservices, Selenium clusters, or end-to-end browser automation suites.

Testing is organized into seven interconnected levels:

```
┌────────────────────────────────────────────────────────────────────────┐
│                   FindBack 2.0 Testing Pyramid                         │
├────────────────────────────────────────────────────────────────────────┤
│ Level 7: Manual Desk & Handover Acceptance (Desk verification audit)   │
│ Level 6: Accessibility (a11y) & Usability Checks (Keyboard, Contrast)  │
│ Level 5: Security & Vulnerability Tests (SQLi, XSS, CSRF, Oracles)    │
│ Level 4: Privacy Boundary Tests (Zero Public Leakage, DOM assertions) │
│ Level 3: Route & Controller Integration Tests (Flask Test Client)      │
│ Level 2: Subsystem Tests (Deterministic Matcher, RBAC, Handover Token) │
│ Level 1: Unit Tests (Database constraints, helpers, utilities)         │
└────────────────────────────────────────────────────────────────────────┘
```

1. **Unit Testing (Level 1):** Focuses on standalone functions, database connection helpers (`db.py`), allowlist check logic, and schema constraints. Runs entirely in-memory with zero network overhead.
2. **Subsystem Logic Testing (Level 2):** Evaluates core application algorithms in isolation: the deterministic scoring engine (`matcher.py`), point breakdown generator (`explainer.py`), password hashing verification, and single-use token lifecycle.
3. **Route & Controller Integration Testing (Level 3):** Uses Flask’s built-in test client (`app.test_client()`) to simulate HTTP GET and POST requests, checking status codes, redirects, template rendering, and database state transitions.
4. **Privacy Boundary Testing (Level 4):** Automated security assertions verifying that no private electronics record, student contact detail, tracking code, or ownership clue ever enters the public view, public API payload, or rendered HTML DOM.
5. **Security & Vulnerability Testing (Level 5):** Systematic checks for common web vulnerabilities, including SQL injection, cross-site scripting (XSS), cross-site request forgery (CSRF), credential harvesting defense, and session tampering.
6. **Accessibility & Usability Testing (Level 6):** Validates semantic HTML, keyboard focus indicators, screen reader accessibility attributes, responsive breakpoints, and contrast compliance.
7. **Manual Acceptance & Scenario Testing (Level 7):** Human-executed end-to-end workflows simulating campus scenarios (ordinary item report, confidential electronics report, matching trigger, admin review, and supervised desk handover).

### 1.2 Core Testing Principles
* **Planned vs. Executed:** Every test in this document is a planned specification. Stating "the test passes" requires empirical evidence: running `pytest -v`, inspecting the output, and recording the exit code.
* **Structured Assertions Over Simple String Matching:** Tests must assert against structured response objects, database records, and targeted DOM nodes. Searching raw HTML for the absence of a column name string is insufficient because it does not prove the underlying data was excluded from the template context or JSON serialization.
* **Fail Loudly and Early:** Tests should fail with clear, descriptive assertion messages so that beginner developers can instantly diagnose the root cause.
* **Shared Accountability:** While Member 4 is the Testing Lead, every team member must run and understand the tests associated with their components before opening a pull request.

---

## 2. Test Environment & Fixture Management

### 2.1 Runtime & Compatibility Verification
The development environment operates on **Python 3.15**. Before any package is installed or used in tests, its compatibility must be verified against official PyPI classifiers and release notes.

1. **Virtual Environment Isolation:** All tests run inside an isolated virtual environment (`.venv/`), activated prior to invoking `pytest`.
2. **Deterministic Dependency Pinning:** Dependencies are pinned strictly in `requirements.txt` (e.g., `flask==3.1.x`, `pytest==8.x.x`). No unpinned or floating package specifications are permitted.
3. **Standard Library Utilization:** Where possible, standard library modules are prioritized (`sqlite3`, `secrets`, `hashlib`, `datetime`, `re`) to minimize external package conflicts.

### 2.2 Isolated Test Database Fixture
Tests must **never** run against the development database (`findback.db`). Using a shared database creates test interdependencies, dirty state, and false test passes.

Instead, tests utilize Pytest fixtures defined in `tests/conftest.py`:

```python
# Conceptual Pytest Fixture Blueprint (tests/conftest.py)
import os
import pytest
import sqlite3
from app import create_app
from database.db import init_db_schema

@pytest.fixture
def app():
    """Create and configure a clean Flask application instance for testing."""
    os.environ['SECRET_KEY'] = 'test-secret-key-32-characters-minimum-for-testing'
    os.environ['DATABASE'] = ':memory:'  # Fast in-memory SQLite database
    
    app = create_app({
        'TESTING': True,
        'DATABASE': ':memory:',
        'WTF_CSRF_ENABLED': False  # Explicitly disabled only where route logic is isolated
    })
    
    with app.app_context():
        # Initialize full schema in memory
        init_db_schema()
        yield app

@pytest.fixture
def client(app):
    """A test client for sending HTTP requests to the application."""
    return app.test_client()

@pytest.fixture
def db_conn(app):
    """Direct database connection to inspect test state."""
    with app.app_context():
        conn = sqlite3.connect(':memory:')
        conn.row_factory = sqlite3.Row
        yield conn
        conn.close()
```

### 2.3 Safe Synthetic Test Data
Real student data, actual student email addresses, real phone numbers, or active passwords must **never** be used in test fixtures or seed scripts.

Test fixtures must use structured synthetic datasets:
* **Fictitious Names & Identifiers:** `Student Alice (ID: 9901)`, `Officer Sharma (Admin ID: 1)`.
* **Standardized Synthetic Emails:** `test.student@campus.local`, `admin.custody@campus.local`.
* **Simulated Campus Locations:** `Central Library Floor 2`, `Science Block Lab 302`, `Main Cafeteria West Wing`.
* **Distinct Test Electronics:**
  * Device A: Smartphone, Apple iPhone 13, Midnight Blue, lost Oct 20.
  * Device B: Smartphone, Apple iPhone 13, Midnight Blue, found Oct 21.
  * Device C: Laptop, Lenovo ThinkPad T14, Black, found Oct 22.

---

## 3. Privacy Boundary & Zero-Leakage Verification

### 3.1 The Confidentiality Invariant
High-value electronics reports (`private_electronics`) and all associated records (student contact info, ownership clues, tracking codes, match leads, and internal admin notes) must **never** appear in public route responses, rendered public HTML, search feeds, or client-side assets.

```
┌────────────────────────────────────────────────────────────────────────┐
│                      Public vs. Private Route Map                      │
├──────────────────────────────────┬─────────────────────────────────────┤
│ Public Routes (Zero Leakage)     │ Protected Routes (Auth Required)    │
├──────────────────────────────────┼─────────────────────────────────────┤
│ GET /                            │ GET /admin/leads                    │
│ GET /report                      │ GET /admin/disputes                 │
│ GET /report/ordinary             │ GET /admin/handover                 │
│ POST /report/ordinary            │ POST /admin/leads/<id>/status       │
│ GET /report/electronics          │ POST /admin/leads/<id>/approve      │
│ POST /report/electronics         │ POST /admin/handover                │
│ GET /status                      │ GET /admin/logout                   │
└──────────────────────────────────┴─────────────────────────────────────┘
```

### 3.2 Two-Tier Privacy Assertions
To prevent data leakage, privacy tests must evaluate two distinct layers:

1. **Tier 1: Data-Layer / Context Projections:**
   * Assert that queries serving `/` execute explicit `SELECT` statements covering only: `id`, `category`, `description`, `campus_location`, `date_discovered`, `status`.
   * Assert that `SELECT *` is never executed against `ordinary_items` or `private_electronics` in public route handlers.
   * Assert that the Jinja2 template context dictionary passed to `render_template()` contains no reference to `private_electronics` records.
2. **Tier 2: Rendered Payload / DOM Assertions:**
   * Assert that the HTTP response body returned to an unauthenticated client contains zero matching substrings for:
     * Any private tracking code (e.g., `TRK-`).
     * Any student phone number or contact email submitted to the private electronics form.
     * Any private ownership clue (e.g., "dog wallpaper", "cracked back glass").
     * Any database column name from `private_electronics` (e.g., `distinctive_clues`, `reporter_contact`).
   * Assert that no HTML `data-*` attribute or hidden `<input type="hidden">` embeds private report details in public templates.

### 3.3 Leakage Defense on Error Pages & Direct Access Attempts
* **Error Page Sanitization:** Sending an invalid request, requesting an unapproved category, or triggering a 404/500 handler must render sanitized templates (`errors/400.html`, `404.html`, `500.html`). Tests assert that error templates contain no database error messages, stack traces, table names, or raw SQL queries.
* **Direct URL Enumeration Defense:** Sending a GET request to `/report/electronics/1` or `/item/electronics/1` must return HTTP 404 or redirect. Tests assert that unauthenticated probing cannot extract private records by ID.

---

## 4. Authentication, Authorization & Session Security

### 4.1 Individual Admin Accounts & Password Hashing
* **No Shared Credentials:** Every administrator has a distinct row in `admin_users` with an individual username, full name, and role.
* **Modern Password Hashing:** Passwords must be hashed using `werkzeug.security.generate_password_hash` with PBKDF2/SHA-256 and verified with `check_password_hash`.
* **Testing Assertions:**
  * Verify that `admin_users.password_hash` never equals the plain-text password.
  * Verify that two identical passwords generate different hashes due to cryptographic salt.
  * Verify that an invalid password fails verification with a timing-resistant check.

### 4.2 Understanding Flask Sessions: Signed Cookies vs. Server Storage
A critical educational point for first-year engineers:
* **Flask Signed Cookies Are Signed, NOT Confidential:** By default, Flask serializes the `session` dictionary into a base64-encoded string stored in a client-side HTTP cookie, signed with `SECRET_KEY`.
* **The Implication:** Anyone can decode the cookie in browser developer tools and read its contents. The signature only proves the user did not modify the cookie; it does not hide what is inside.
* **Strict Session Invariant:** **Never store passwords, password hashes, student contact details, report descriptions, or private ownership clues in the session cookie.** The session must store only minimal, non-sensitive identifiers (e.g., `user_id`: 1, `role`: 'admin').
* **Confirmed Architectural Choice (DEC-07):** Option A (Flask Built-in Signed Cookie Session with Strict Dynamic Database Re-verification).
  * The signed cookie stores **strictly `admin_user_id`**.
  * Roles, permissions, and active status are never stored in or trusted from the cookie.
  * On every protected request, `@admin_required` queries SQLite to re-verify account existence and `is_active == 1`.
  * Inactive or deleted accounts have access revoked immediately on the next request.
  * Session-bound CSRF protection with constant-time `hmac.compare_digest` validation is enforced on state-changing actions.
  * Verified by 20 automated tests in `tests/test_auth.py`.

### 4.3 Enforced Server-Side Access Control (RBAC)
* **Rejection of Security by Obscurity:** Hiding an "Admin Portal" link or disabling a button in HTML provides **zero** protection. Any user can type `/admin/leads` directly into the address bar.
* **The `@admin_required` Decorator:** Must intercept all incoming requests to `/admin/*`, check the active session, verify administrator privileges against the database, and redirect unauthenticated requests to `/admin/login` (or return HTTP 403 for API calls).
* **Testing Assertions:**
  * Request `/admin/leads` with no session $\rightarrow$ HTTP 302 redirect to `/admin/login`.
  * Request `/admin/leads` with an expired session $\rightarrow$ HTTP 302 redirect to `/admin/login`.
  * Request `/admin/leads` with an active admin session $\rightarrow$ HTTP 200.
  * Confirm that visiting `/admin/logout` calls `session.clear()`, invalidates the cookie, and prevents subsequent access without re-authenticating.

### 4.4 Cross-Site Request Forgery (CSRF) Protection
* All state-changing administrative actions (updating lead review status, approving a match, logging a handover) must use HTTP POST and require a valid CSRF token.
* Testing asserts that a POST request to `/admin/leads/<id>/status` lacking a valid CSRF token is rejected with HTTP 400.
* The specific CSRF implementation approach (manual session token vs. extension) will be settled during Phase 7 per DEC-07 and team agreement.

---

## 5. Input Validation, Database Safety & Injection Defense

### 5.1 Parameterized SQL Queries (SQL Injection Defense)
SQL injection occurs when untrusted user input is directly concatenated or formatted into a SQL query string.

* **Mandatory Rule:** All SQL queries must use SQLite `?` placeholders:
  ```python
  # CORRECT: Parameterized query (safe against SQLi)
  cursor.execute("SELECT * FROM ordinary_items WHERE category = ?", [category])

  # PROHIBITED: String formatting (CRITICAL VULNERABILITY)
  cursor.execute(f"SELECT * FROM ordinary_items WHERE category = '{category}'")
  ```
* **Testing Assertions:**
  * Pass classic SQL injection payloads into every input field (`' OR '1'='1`, `'; DROP TABLE ordinary_items; --`, `UNION SELECT ...`).
  * Assert that the query treats the payload strictly as literal data, returning expected results or validation errors without altering query structure or triggering SQLite syntax exceptions.

### 5.2 Category Allowlist Enforcement
The public feed is strictly limited to 7 approved ordinary categories:
1. `Water Bottles & Mugs`
2. `Notebooks, Binders & Textbooks`
3. `Umbrellas`
4. `Eyeglasses & Sunglasses`
5. `Non-Electronic Stationery`
6. `Outerwear, Jackets & Scarves`
7. `General Bags & Backpacks (Non-Electronic)`

* **Testing Assertions:**
  * Submitting an ordinary report with category `"Water Bottles & Mugs"` $\rightarrow$ HTTP 302/200 (Success).
  * Submitting an ordinary report with category `"Smartphone"` $\rightarrow$ HTTP 400 (Bad Request).
  * Submitting an ordinary report with category `"Laptop"` $\rightarrow$ HTTP 400 (Bad Request).
  * Submitting an ordinary report with an empty or arbitrary string $\rightarrow$ HTTP 400 (Bad Request).
  * Submitting directly via `curl` or Postman bypassing the HTML `<select>` $\rightarrow$ Rejected server-side with HTTP 400.

### 5.3 Prohibited Credential Defense (Heuristic Limitations)
Under project safety guidelines, the platform must never collect, store, or accept device unlock PINs, passwords, biometric credentials, or recovery keys.

> [!WARNING]
> **Heuristic Limitations Notice:** Keyword checks, regex patterns, or automated scans **cannot reliably detect every possible PIN, password, or recovery phrase**. A user could submit a PIN as obscure text (e.g., "my code is four twos"). Therefore, regex checks are treated as a best-effort defense-in-depth layer, **not an infallible security guarantee**. The primary protection is clear, prominent UI microcopy warning users never to provide credentials, accompanied by server-side sanity checks.

* **Testing Assertions:**
  * Submit a report with `"PIN: 1234"` or `"password is secret"` $\rightarrow$ Caught by heuristic validator, rejected with HTTP 400.
  * Document the limitation in test logs: passing this test demonstrates the heuristic catches common patterns, not that it provides a foolproof barrier.

### 5.4 Cross-Site Scripting (XSS) Defense
* Jinja2 auto-escaping is enabled by default across all templates.
* **Testing Assertions:**
  * Submit an item description containing `<script>alert('XSS')</script>` or `<img src=x onerror=alert(1)>`.
  * Render the public feed or admin review page.
  * Assert that the rendered HTML contains `&lt;script&gt;` rather than executable `<script>` tags, and that the browser does not execute the script.
  * Verify that no template applies the `| safe` filter to user-supplied text.

---

## 6. Tracking-Code Safety & Anti-Oracle Design

### 6.1 Cryptographic Unpredictability
When a user submits a confidential electronics report, the system issues a private `tracking_code` used to check status on `/status`.

* **Generation Standard:** The code must be generated using Python’s standard-library `secrets` module (e.g., `secrets.token_urlsafe(32)` or formatted token with high entropy). Short, sequential, or predictable IDs (e.g., `TRK-001`, `TRK-002`) are strictly prohibited.
* **Testing Assertions:**
  * Generate 1,000 consecutive tracking codes in a unit test.
  * Assert that all 1,000 codes are unique.
  * Assert that entropy is sufficient and no sequential patterns exist.

### 6.2 Tracking Code is a Credential, Not Proof of Ownership
The tracking code functions strictly as a lookup credential allowing the submitter to view their report's progress. It **never proves that the holder owns the lost device**. Physical verification by staff at the desk is always required.

### 6.3 Anti-Oracle Status Endpoint Design
If a status lookup endpoint returns different error messages for "code does not exist" versus "code exists but no match yet", an attacker can use the endpoint as an **oracle** to brute-force and discover valid tracking codes.

* **Uniform Response Rule:** Submitting an invalid, unknown, or non-matching tracking code to `GET /status` must return a generic, uniform status message:
  > *"Status not available for this tracking code. Please verify the code you entered."*
* **Testing Assertions:**
  * Request `/status?tracking_code=VALID_CODE` $\rightarrow$ Returns structured status label (`Submitted`, `Searching for Match`, etc.).
  * Request `/status?tracking_code=INVALID_CODE` $\rightarrow$ Returns HTTP 200 with uniform generic message.
  * Request `/status?tracking_code=MALFORMED_INPUT` $\rightarrow$ Returns HTTP 200 with identical generic message.
  * Assert that the response never states "Tracking code not found in database."
  * Assert that valid status responses **never return** student contact details, distinctive clues, or matching candidate information.

### 6.4 Brute-Force & Rate-Limiting Protection
Because tracking codes protect private status, the system must evaluate proportionate defenses against automated guessing (e.g., rate-limiting lookups per IP address or introducing delay after repeated failures). This requirement is documented as a pre-deployment check in Section 11.

---

## 7. Matching Engine, Dispute Handling & Transaction Safety

### 7.1 Deterministic Matching Scoring
The matching engine (`matching/matcher.py`) computes similarity based on explicit additive rules.

* **Score as Lead Invariant:** An automated match score is **strictly an investigative lead for staff review, never definitive legal proof of ownership**.
* **Device Type Gate (Mandatory Invariant):** If `lost_report['device_type'] != found_report['device_type']`, the algorithm must immediately halt, assign a score of **0**, and produce no lead.
* **Provisional Scoring Weights (DEC-12):** Device Type (30 pts), Brand (25 pts), Color (15 pts), Location (15 pts), Time Plausibility (15 pts). Provisional notification threshold: 85 pts.
* **Testing Assertions:**
  * Identical reports (Smartphone, Apple, Blue, Library, within 24h) $\rightarrow$ Score: 100.
  * Incompatible types (Smartphone vs. Laptop) $\rightarrow$ Score: 0, `match_possible: False`.
  * Partial match (Smartphone vs. Smartphone, different brand) $\rightarrow$ Intermediate score.
  * Determinism check: Call `compute_score(reportA, reportB)` 100 times $\rightarrow$ Output is identical every time.

### 7.2 Explainable JSON Breakdown
Every evaluated match lead must produce a structured JSON breakdown (`score_breakdown_json`) showing exact points awarded per factor. Tests assert that the JSON breakdown parses correctly and that the sum of factor points equals `match_score`.

### 7.3 Competing-Claim Detection (Item-Level Conflict)
A competing-claim situation arises when the **same physical item** is claimed by multiple parties:
* Example: Two different students submit lost reports matching the same found iPhone.

* **Dispute Protocol:**
  * When a new match lead is generated for a `private_electronics` record that already has an active lead, both leads and the underlying item records must be flagged with `review_status = 'disputed'`.
  * The system must immediately freeze automated progression.
* **Transaction Safety:**
  * Detecting competing claims and updating multiple database rows must execute inside a single SQLite transaction (`BEGIN TRANSACTION` ... `COMMIT`).
  * If any step fails, the entire transaction is rolled back (`ROLLBACK`) so that records are never left in an inconsistent state.
* **Testing Assertions:**
  * Seed one found iPhone and two matching lost iPhone reports.
  * Trigger matching $\rightarrow$ Assert both match lead rows have `review_status = 'disputed'`.
  * Assert that attempting to approve either lead or generate a handover token is rejected by the backend.

---

## 8. Supervised Handover Protocol & Audit Security

### 8.1 Single-Use Handover Token Lifecycle
Handover of high-value electronics occurs exclusively at an authorized campus desk under staff supervision.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        Handover Token Lifecycle                        │
├────────────────────────────────────────────────────────────────────────┤
│ 1. Admin reviews non-secret clues & evidence $\rightarrow$ Approves Handover   │
│ 2. Server generates random token via `secrets.token_urlsafe(8)`        │
│ 3. Server computes SHA-256 hash $\rightarrow$ Stores in `handover_logs`        │
│ 4. Token expires in 30 minutes (`token_expires_at = now() + 30 min`)    │
│ 5. Staff conducts in-person physical check at desk                     │
│ 6. Staff submits token in `/admin/handover`                            │
│ 7. Server checks: hash matches, not expired, `token_used_at IS NULL`   │
│ 8. Server sets `token_used_at = now()`, marks item `resolved`          │
└────────────────────────────────────────────────────────────────────────┘
```

### 8.2 Safe Verification Invariants
* **No Credential Demand:** Staff must **never** ask a claimant for their device unlock PIN, password, or biometric credentials. Verification relies on non-secret visual clues (case, stickers, scratches, lock-screen wallpaper description) and student ID inspection.
* **Token Does Not Prove Ownership:** The handover verification token confirms that the *administrative procedure* was completed at the desk; it does not constitute proof of ownership.
* **Hashed Storage:** The raw token is displayed on screen to staff once. Only `hashlib.sha256(token.encode()).hexdigest()` is stored in the database.
* **Testing Assertions:**
  * Verify token generation produces an unguessable string.
  * Verify `handover_logs.token_hash` stores the SHA-256 hash, not the plain token.
  * Verify submitting a valid token marks `token_used_at` with a timestamp and resolves the item.
  * Verify submitting an expired token is rejected.
  * Verify submitting an already-used token is rejected (single-use enforcement).
  * Verify an item marked `disputed` cannot generate or redeem a handover token.

### 8.3 Operational Limitations of SQLite Audit Logs
While `handover_logs` is managed as an append-oriented table at the application layer (no UPDATE or DELETE routes exist), SQLite is a single local file on disk. It does not provide cryptographic or hardware-level write-once-read-many (WORM) immutability against anyone with direct operating system access to `findback.db`. This operational boundary is documented as a known prototype limitation.

---

## 9. User Interface, Responsiveness & Accessibility Testing

### 9.1 Semantic Structure & Landmark Verification
* All pages must include standard HTML5 semantic elements: `<header>`, `<nav>`, `<main>`, `<section>`, and `<footer>`.
* Headings must follow a strict sequential hierarchy (`<h1>` $\rightarrow$ `<h2>` $\rightarrow$ `<h3>`) without skipping levels.
* Form inputs must be linked to `<label>` elements via matching `for` and `id` attributes.

### 9.2 Keyboard Navigation & Focus Visibility
* **Tab Order:** A user must be able to navigate all links, form controls, buttons, and close actions using `Tab` and `Shift + Tab` in a logical reading order.
* **Focus Indicators:** Interactive elements must display a high-contrast focus ring (`:focus-visible` with `outline: 3px solid var(--color-border-focus)`). Tests verify that `outline: none` is never applied without a visible replacement.
* **Actionable Keys:** Buttons and dialogs must respond to `Enter` and `Space`. Modals must close on `Escape`.

### 9.3 Responsive Breakpoints & Mobile Usability
Manual and layout tests must verify rendering across three standard viewports:
* **Mobile Viewport (320px – 640px):** Single-column layout; full-width buttons ($44\text{px}$ minimum touch targets); navigation collapses to hamburger menu; zero horizontal scrolling.
* **Tablet Viewport (640px – 1024px):** 2-column card grid; responsive tables with horizontal scroll wrappers where necessary.
* **Desktop Viewport (> 1024px):** 3-4 column grid; full side-by-side lead review comparison tables.

### 9.4 Contrast & Color-Blind Safety
* Body text against background must achieve a contrast ratio of at least $4.5:1$ (WCAG AA).
* Large headings ($>18\text{pt}$ or bold $>14\text{pt}$) must achieve at least $3:1$.
* Status information must never be conveyed by color alone. Every badge must combine a color accent with an explicit text label (e.g., Red background + text `"Disputed"`).

---

## 10. Comprehensive Master Test Matrix

The following matrix documents all planned test cases. Every test has a unique ID, clear preconditions, execution method, expected outcome, and priority:
* **P0 (Critical):** Core security, privacy, and data isolation tests. Must pass before any release.
* **P1 (High):** Core functional workflows, matching logic, and role-based access controls.
* **P2 (Medium):** Accessibility, responsive styling, and input edge cases.

| Test ID | Category | Purpose / Description | Preconditions & Steps | Expected Result & Structured Assertion | Type | Priority |
| :--- | :--- | :--- | :--- | :--- | :---: | :---: |
| **TEST-PRIV-01** | Privacy | Verify public feed never returns private electronics | Seed `ordinary_items` and `private_electronics`. Send `GET /`. | HTTP 200. Assert response data contains only ordinary fields; 0 records, clues, or contacts from `private_electronics` present in context or DOM. | Automated | **P0** |
| **TEST-PRIV-02** | Privacy | Verify direct URL probing of private reports is blocked | Send unauthenticated `GET /report/electronics/1`. | HTTP 404 or redirect. Assert no private attributes or SQL errors in response body. | Automated | **P0** |
| **TEST-PRIV-03** | Privacy | Anti-oracle verification on status lookup | Send `GET /status?tracking_code=NON_EXISTENT_CODE`. | HTTP 200. Returns generic "Status not available" message. Assert message does not confirm or deny database existence. | Automated | **P0** |
| **TEST-PRIV-04** | Privacy | Zero data leakage in error responses | Send malformed request triggering 400, 404, or 500 error handlers. | Appropriate error template rendered. Assert response body contains zero column names, database exceptions, or stack traces. | Automated | **P0** |
| **TEST-PRIV-05** | Privacy | Contact details excluded from ordinary public cards | Seed ordinary item with contact email. Send `GET /`. | HTTP 200. Assert rendered card contains category, location, date, status, but `contact_email` is strictly absent. | Automated | **P0** |
| **TEST-AUTH-01** | Auth / RBAC | Block unauthenticated access to admin dashboard | Send `GET /admin/leads` with no session cookie. | HTTP 302 redirect to `/admin/login`. Assert protected page content is not rendered. | Automated | **P0** |
| **TEST-AUTH-02** | Auth / RBAC | Successful admin login with valid credentials | Post valid credentials to `/admin/login`. | HTTP 302 redirect to `/admin/leads`. Session cookie set. Password verified via `check_password_hash`. | Automated | **P1** |
| **TEST-AUTH-03** | Auth / RBAC | Reject invalid admin credentials generically | Post invalid password to `/admin/login`. | HTTP 200 (login page re-rendered). Generic "Invalid credentials" error shown. No session set. | Automated | **P1** |
| **TEST-AUTH-04** | Auth / RBAC | Verify session cookie payload contains zero secrets | Authenticate admin; decode base64 session cookie payload. | Assert cookie contains only minimal IDs (`user_id`, `role`). Zero passwords, hashes, contact info, or clues. | Automated | **P0** |
| **TEST-AUTH-05** | Auth / RBAC | Admin logout clears session | Log in, then send `GET /admin/logout`. | Session cleared (`session.clear()`). Subsequent `GET /admin/leads` redirects to login. | Automated | **P1** |
| **TEST-AUTH-06** | Auth / RBAC | CSRF protection on administrative POST actions | Send POST to `/admin/leads/1/status` without CSRF token. | HTTP 400 Bad Request. Action rejected. Lead status unchanged. | Automated | **P0** |
| **TEST-INP-01** | Input Safety | Parameterized SQL query injection defense | Submit `' OR '1'='1` in search and category fields. | Treated as literal search string. Zero syntax errors; database records unaltered. | Automated | **P0** |
| **TEST-INP-02** | Input Safety | Enforce ordinary category allowlist | Submit ordinary report with category `"Smartphone"`. | HTTP 400 Bad Request. Validation error returned. Record not inserted into database. | Automated | **P0** |
| **TEST-INP-03** | Input Safety | XSS script tags escaped in template rendering | Submit `<script>alert('xss')</script>` in description. | Rendered HTML contains `&lt;script&gt;` entities. Zero unescaped script execution. | Automated | **P0** |
| **TEST-INP-04** | Input Safety | Credential heuristic rejects obvious PIN/password | Submit `"PIN: 4921"` in distinctive clues field. | HTTP 400 Bad Request. Warning displayed explaining passwords must not be entered. | Automated | **P1** |
| **TEST-MTCH-01** | Matching | Incompatible device types produce zero score | Pass `phone` report and `laptop` report to matcher. | Return `total_score: 0`, `match_possible: False`. Zero points awarded across other factors. | Automated | **P0** |
| **TEST-MTCH-02** | Matching | Deterministic scoring reproducibility | Execute `compute_score(itemA, itemB)` 100 times. | Output score and JSON breakdown are identical on every single execution. | Automated | **P1** |
| **TEST-MTCH-03** | Matching | Explainable score breakdown generation | Compute score for matching candidate pair. | Returns structured dictionary with factors (type, brand, color, location, time) summing to total score. | Automated | **P1** |
| **TEST-MTCH-04** | Matching | Competing claims trigger automatic dispute flag | Two lost reports match same found device. | Both match leads flagged `review_status = 'disputed'`. Database update wrapped in SQLite transaction. | Automated | **P0** |
| **TEST-HND-01** | Handover | Expired handover token rejected | Submit token where `now() > token_expires_at`. | Request rejected. Handover not marked completed; item remains open. | Automated | **P0** |
| **TEST-HND-02** | Handover | Reused handover token rejected (Single-use) | Submit token where `token_used_at IS NOT NULL`. | Request rejected with HTTP 400 Single-Use Violation. Item status unaltered. | Automated | **P0** |
| **TEST-HND-03** | Handover | Disputed item blocks token generation | Attempt to approve lead with `review_status = 'disputed'`. | Action blocked. No handover token generated until dispute is cleared by admin. | Automated | **P0** |
| **TEST-HND-04** | Handover | Token stored as SHA-256 hash | Generate handover token for approved lead. | `handover_logs.token_hash` contains 64-char hex string; raw token not stored in database. | Automated | **P0** |
| **TEST-HND-05** | Handover / RBAC | Tiered RBAC: desk_staff blocked from status update & approval | Authenticate as `desk_staff`; POST to `/admin/leads/<id>/status` or `/approve`. | HTTP 403 Forbidden. Restricted actions enforce server-side role check. | Automated | **P0** |
| **TEST-HND-06** | Handover / Dispute | Dismissing competing claim unfreezes remaining lead | Admin dismisses invalid claim in conflict group. | Remaining lead and underlying item automatically unfrozen to `investigating` / `lead_identified`. | Automated | **P0** |
| **TEST-HND-07** | Handover | Disputed item blocks token redemption | Attempt to redeem valid token for item subsequently flagged disputed. | Redemption blocked with HTTP 400. Dispute freeze enforced at redemption point. | Automated | **P0** |
| **TEST-HND-08** | Handover | Concurrent / race condition redemption prevented | Two concurrent requests submit identical valid token. | Atomic compare-and-swap allows exactly one redemption; second request fails safely. | Automated | **P0** |
| **TEST-HND-09** | Handover | Atomic transaction rollback on failure | Trigger database failure during handover resolution. | Transaction rolls back; `token_used_at` remains NULL; item status unchanged. | Automated | **P0** |
| **TEST-HND-10** | Handover / CSRF | CSRF token enforced on review actions | POST to approve, status, or handover without valid CSRF token. | HTTP 400 Bad Request. Missing or tampered CSRF tokens rejected. | Automated | **P0** |
| **TEST-A11Y-01** | Accessibility | Keyboard tab navigation across all interactive items | Navigate entire page using `Tab` and `Shift + Tab`. | Every button, link, and input receives high-contrast focus ring in logical sequence. | Manual | **P1** |
| **TEST-A11Y-02** | Accessibility | Form controls explicitly labeled | Inspect all form controls in public and admin forms. | Every `<input>`, `<select>`, `<textarea>` has corresponding `<label for="...">`. | Automated | **P1** |
| **TEST-A11Y-03** | Accessibility | High contrast ratios across UI text | Measure contrast with a11y color checker. | Body text $\ge 4.5:1$; headings $\ge 3.0:1$. | Manual | **P2** |
| **TEST-RESP-01** | Layout | Responsive mobile viewport rendering | Render application at 375px viewport width. | Zero horizontal overflow scrollbars; touch targets $\ge 44\text{px} \times 44\text{px}$; readable 16px text. | Manual | **P1** |
| **TEST-MAN-01** | Acceptance | Full ordinary item reporting and discovery flow | User reports found water bottle; searcher finds on board. | Item appears on board with approved fields; search filters item correctly. | Manual | **P1** |
| **TEST-MAN-02** | Acceptance | Full confidential electronics match and handover flow | Submit lost phone; submit found phone; admin reviews lead; desk completes handover. | Tracking code issued; lead generated in admin queue; desk conducts physical check; token resolves item. | Manual | **P0** |

---

## 11. Pre-Demonstration Release Checklist & Verification Gates

Before the first-year engineering team can declare the FindBack 2.0 MVP ready for presentation and evaluation, every item on this checklist must be verified with documented evidence:

### Gate 1: Code & Environment Cleanliness
* [ ] **Python Compatibility Confirmed:** Python 3.15 compatibility for Flask and pytest verified via PyPI classifiers.
* [ ] **Clean Virtual Environment:** Application installs and runs cleanly from `requirements.txt` inside `.venv/`.
* [ ] **No Committed Secrets:** Repository history inspected via `git log -p` confirming zero `SECRET_KEY`, passwords, or `.env` files are tracked.
* [ ] **Database File Ignored:** `findback.db` is present in `.gitignore` and not tracked in Git.

### Gate 2: Automated Test Execution & Empirical Evidence
* [ ] **Test Suite Actually Executed:** `pytest tests/ -v` executed with actual output logged in project records.
* [ ] **100% of P0 Tests Passing:** All P0 privacy, security, allowlist, and access control tests pass without exception.
* [ ] **Zero Public Leakage Verified:** `test_privacy.py` passes, verifying both JSON response payloads and rendered HTML templates.
* [ ] **Deterministic Scoring Tested:** Unit tests confirm matching function is 100% deterministic and incompatible device types yield 0 points.

### Gate 3: Security & Privacy Invariants
* [ ] **Parameterized Queries Everywhere:** Codebase searched; zero occurrences of `f"SELECT..."` or string concatenation in SQL queries.
* [ ] **Prohibited Data Defense Active:** Warning banners visible in UI; backend rejects obvious credential patterns.
* [ ] **Session Cookie Safety Inspected:** Browser developer tools used to inspect session cookie; verified that cookie payload contains zero sensitive data.
* [ ] **Server-Side RBAC Enforced:** Unauthenticated requests to `/admin/*` confirmed to redirect or return HTTP 403; confirmed that hiding UI buttons is not the only protection.
* [ ] **Anti-Oracle Status Check:** Status lookup verified to return uniform generic message for unknown tracking codes.

### Gate 4: Documented Scope Boundaries & Untested Cases
* [ ] **Explicit Exclusions Maintained:** Photo uploads, Google Gemini API, campus SSO, and automated SMS/email remain excluded from the codebase.
* [ ] **Known Prototype Limitations Recorded:**
  * Heuristic credential checks cannot detect every possible password variation.
  * SQLite audit logs are append-only at the application layer but not physically immutable on the host filesystem.
  * Rate-limiting is evaluated as a pre-deployment requirement but full IP throttling may be simulated in local prototyping.
* [ ] **Open Decisions Preserved:** All 6 open decisions (`DEC-07` through `DEC-12`) documented as pending team/mentor alignment rather than invented.

---

## 12. Beginner Explanations: Why These Security Controls Matter

To help first-year engineering students understand and present these security concepts during evaluations, each major control is explained in plain language below:

### 1. Why Parameterized SQL Queries Matter (SQL Injection)
* *The Threat:* If you write `query = "SELECT * FROM users WHERE name = '" + user_input + "'"` and someone types `' OR '1'='1`, the database reads their input as code instead of data. This allows attackers to bypass logins or delete tables.
* *The Defense:* Parameterized queries (`?` placeholders) tell SQLite: *"Treat this value strictly as text, never as instructions."* Even if someone enters SQL commands, SQLite treats them as plain characters.

### 2. Why Signed Cookies Are Not Confidential
* *The Threat:* Beginners often assume that because a cookie is "signed by Flask," nobody can read it. In reality, Flask signed cookies are only encoded with base64—anyone can paste the cookie into a decoder and read every word inside.
* *The Defense:* The cryptographic signature only detects if someone *altered* the cookie. It does not *encrypt* or hide the contents. Therefore, we never put passwords, student contact info, or private clues in session cookies.

### 3. Why Hiding Buttons Is Not Security (Security by Obscurity)
* *The Threat:* Hiding an "Admin" link in the menu with CSS (`display: none`) does not stop an attacker. Anyone can open their browser and type `http://127.0.0.1:5000/admin/leads` directly into the address bar.
* *The Defense:* True access control happens on the server. The `@admin_required` Python decorator checks the user's session before running the route. If they are not logged in, the server immediately turns them away.

### 4. Why We Never Ask for Device Passwords or PINs
* *The Threat:* Asking a student for their phone unlock PIN creates enormous security risks. If that PIN is stored, anyone who sees the database could access the student's personal accounts, bank apps, and private photos.
* *The Defense:* Campus staff verify ownership using non-secret physical clues (case color, stickers, lockscreen photo description). During in-person handover, the student unlocks their own device with their own finger without telling staff the PIN.

### 5. Why Match Scores Are Leads, Not Proof
* *The Threat:* An automated algorithm might see that two phones are both "Black Apple iPhone 13s found in the Library" and give a 90% score. However, there might be dozens of black iPhone 13s on campus!
* *The Defense:* An algorithm only highlights similarities. A high score is an investigative lead telling staff *"Take a look at this pair."* Only human verification of distinctive clues and student ID establishes rightful ownership.

### 6. Why Anti-Oracle Status Responses Are Necessary
* *The Threat:* If a website says *"Code TRK-123 is valid"* for real reports and *"Code TRK-999 does not exist"* for wrong ones, a hacker can write a script that tests thousands of random codes until it finds ones that exist.
* *The Defense:* An anti-oracle response returns the exact same generic message for any code that doesn't produce an active result. The system never reveals whether or not a record exists in the database.

---

## 13. Preservation of Open Architectural Decisions

This testing specification respects and preserves the unresolved decisions recorded in [`DECISIONS.md`](file:///c:/Users/omwor/Documents/findback/DECISIONS.md). No institutional assumptions or unauthorized choices have been made:

* **DEC-07 (Admin Session Mechanism):** Confirmed. Option A (Flask signed cookie) storing strictly `admin_user_id` with dynamic SQLite database re-verification on every protected request. Verified in `tests/test_auth.py`.
* **DEC-08 (Admin Account Provisioning):** Open. Tests assume an administrative account exists in `admin_users` created via safe configuration, pending final selection between seed script and CLI prompt.
* **DEC-09 (Student Identity Verification):** Open. Form validation tests accommodate general email plus desk ID inspection vs. strict campus domain regex.
* **DEC-10 (Physical Handover Desk Location):** Open. UI and manual acceptance tests use neutral placeholder `"Central Campus Lost & Found Custody Desk"`.
* **DEC-11 (Data Retention & Archiving):** Open. Test fixtures do not enforce a specific retention period until confirmed by mentors.
* **DEC-12 (Scoring Factor Weights):** Proposed. Unit tests evaluate the provisional weights (30/25/15/15/15; benchmark 85) while explicitly noting they represent unvalidated hypotheses awaiting empirical calibration.
