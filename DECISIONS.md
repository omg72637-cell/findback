# FindBack 2.0 — Architecture & Project Decision Records (DECISIONS.md)

**Document Version:** 1.0.0-draft  
**Target Audience:** First-Year Engineering Project Team, Faculty Mentors, and Reviewers  
**Document Status:** Living Record of Confirmed, Proposed, and Open Decisions  

---

## 1. Project Constraints & Confirmed Scope

The core architecture and project boundaries for FindBack 2.0 have been established across [GEMINI.md](file:///c:/Users/omwor/Documents/findback/GEMINI.md), [PRD.md](file:///c:/Users/omwor/Documents/findback/PRD.md), and [ARCHITECTURE.md](file:///c:/Users/omwor/Documents/findback/ARCHITECTURE.md). The following constraints represent confirmed baseline requirements for the project:

1. **Dual-Workflow Architecture:**
   * **Public Ordinary Items:** Ordinary, low-risk items (water bottles, notebooks, umbrellas, eyeglasses, stationery, outerwear, and non-electronic bags) may be browsed and searched publicly, but only when their category is on an explicit, hardcoded allowlist.
   * **Private High-Value Electronics:** Lost and found reports for electronics (smartphones, laptops, tablets, earbuds, chargers, smartwatches) are strictly confidential and must **never** appear in public listings, search indexes, or public API responses.
2. **Minimalist, Beginner-Friendly Tech Stack:**
   * **Frontend:** Vanilla HTML5, CSS3, and JavaScript. No external frontend frameworks (React, Vue) or Node.js package build tools (npm, Webpack, Vite) are used.
   * **Backend:** Python 3 with the lightweight Flask micro-framework.
   * **Database:** SQLite local single-file database (`findback.db`), pre-installed with Python.
3. **Explainable Deterministic Matching:**
   * Similarity between lost and found electronics is computed using a rule-based, deterministic Python scoring algorithm.
   * An automated score serves strictly as an investigative lead for campus staff, **never as proof of ownership**.
4. **Explicitly Deferred Features (Post-MVP):**
   * **Photo / Image Uploads:** Deferred to avoid multipart upload vulnerabilities, file storage overhead, and complexity for first-year students.
   * **Google Gemini Multimodal API:** Deferred until the deterministic matching engine is fully built, calibrated, and tested.
   * **Campus Single Sign-On (SSO / OAuth / LDAP):** Deferred to avoid external infrastructure dependencies during local prototyping.
   * **Automated External Notifications (SMS / Email):** Deferred to avoid third-party API dependencies (Twilio, SendGrid); communication is mediated by campus desk staff.

---

## 2. Decision Register

The following register tracks the state of architectural decisions. Statuses are defined as:
* **Confirmed:** Formally agreed upon in existing project documentation.
* **Proposed:** Recommended design requiring discussion and sign-off by the student team.
* **Open:** Unresolved requirement or institutional variable that must be decided before implementation.
* **Deferred:** Intentionally excluded from the current MVP milestone.

| Decision ID | Topic | Current Position | Status | Reason & Context | What Must Be Decided / Verified |
| :--- | :--- | :--- | :---: | :--- | :--- |
| **DEC-01** | Technology Stack | Vanilla HTML/CSS/JS + Python Flask + SQLite | **Confirmed** | Minimizes beginner tooling friction; no build pipelines required; easy to understand and present. | Ensure local Python environment and Flask run cleanly across all team machines. |
| **DEC-02** | Dual-Workflow Separation | Separate tables: `ordinary_items` (public) and `private_electronics` (confidential) | **Confirmed** | Protects student privacy and prevents opportunistic theft of expensive gadgets. | Implement and test zero-leakage query projections in all public routes. |
| **DEC-03** | Ordinary Category Allowlist | Strict 7-category hardcoded allowlist for public submissions | **Confirmed** | Prevents high-value or dangerous items from slipping onto the public campus board. | Validate that backend rejects non-allowlisted categories with HTTP 400. |
| **DEC-04** | Matching Engine Paradigm | Pure Python deterministic additive scoring | **Confirmed** | Transparent, reproducible, and explainable without cloud dependencies or black-box heuristics. | Formulate and verify unit test fixtures covering scoring factors. |
| **DEC-05** | Credential Harvesting Prohibition | Strict ban on requesting device PINs, passwords, pattern locks, or biometrics | **Confirmed** | Essential safety guardrail to protect students from account and device compromise. | Implement form regex and backend validators to catch prohibited credential keywords. |
| **DEC-06** | Access Control Model | Server-side role-based authorization via custom `@admin_required` decorator | **Confirmed** | Security-by-obscurity (hiding URLs or UI buttons) is unsafe and rejected. | Ensure every `/admin/*` route redirects or returns HTTP 401/403 for unauthorized requests. |
| **DEC-07** | Admin Session Mechanism | Flask signed-cookie session storing strictly `admin_user_id` (dynamic DB re-verification) | **Confirmed** | Cookie stores ONLY non-sensitive `admin_user_id`. Every protected request queries SQLite to re-verify existence, `is_active == 1`, and role, providing immediate revocation on account deactivation. | Confirmed and verified with 20 automated tests in Phase 7 (`test_auth.py`). Session-bound CSRF and secure cookie flags enforced. |
| **DEC-08** | Admin Account Provisioning | Scripted initialization via `database/init_db.py` using environment variables | **Open** | Needs a secure, repeatable way to create the initial admin account without hardcoding credentials. | Agree on initial admin credentials loading mechanism (`.env` vs CLI setup script). |
| **DEC-09** | Student Identity Verification | Standard email + physical Student ID check at the desk vs. campus email domain restriction | **Open** | Balances ease of reporting for students against identity authenticity. | Team must decide if `@campus.edu` email format validation is required. |
| **DEC-10** | Physical Handover Desk Location | Centralized campus location (e.g., Campus Security Office, Student Union Helpdesk, Library Desk) | **Open** | Handover copy in UI templates must specify an accurate campus drop-off point. | Determine the designated physical handover desk label to use in mock UI views. |
| **DEC-11** | Data Retention & Archiving | Retention timeline for resolved records (e.g., 30 days vs. semester end) | **Open** | Minimizes long-term storage of student contact details and descriptive clues. | Agree on an archival policy and document whether records are soft-deleted or purged. |
| **DEC-12** | Matching Factor Weights & Threshold | Provisional weights (Type: 30, Brand: 25, Color: 15, Location: 15, Time: 15; Benchmark: 85) | **Proposed** | Weighted model provides a working baseline but has not yet been calibrated against test data. | Calibrate weights and notification threshold using simulated test datasets. |
| **DEC-13** | Photo Uploads | Excluded from MVP | **Deferred** | Avoids file upload vulnerabilities, storage bloat, and multipart form complexity in Phase 1. | Revisit in Phase 2 after core text-based matching is proven. |
| **DEC-14** | Google Gemini Multimodal API | Excluded from MVP | **Deferred** | Rule-based baseline must be thoroughly tested before AI integrations are introduced. | Revisit in Phase 3 as an optional experimental module. |

---

## 3. Authentication and Sessions

Administrative functionality (inspecting private electronics reports, reviewing match leads, adjudicating disputes, and logging handovers) requires secure administrator authentication.

### 3.1 Understanding Flask Sessions (Signed Cookies vs. Database Sessions)
For a first-year engineering team, understanding the difference between client-side signed cookies and true server-side sessions is essential:

* **What a Signed Cookie Is:** By default, Flask stores session data in an HTTP cookie on the user's browser, signed with a cryptographic key (`SECRET_KEY`). The signature ensures that if the user alters the cookie, Flask detects the tampering and rejects it.
* **The "Signed $\ne$ Encrypted" Rule:** A signed cookie is **not secret**. It is base64-encoded and can be unpacked and read by anyone using browser developer tools.
* **Strict Cookie Invariant:** **Never store passwords, password hashes, student contact details, report descriptions, or private ownership clues in session cookies.** A session cookie must only contain non-sensitive identifiers (e.g., `user_id`: 1, `role`: 'admin').

### 3.2 Comparison of Candidate Session Approaches

| Dimension | Option A: Flask Built-in Signed Cookie Session | Option B: Database-Backed SQLite Session Table |
| :--- | :--- | :--- |
| **How It Works** | Session dictionary serialized and signed into a browser cookie. Server verifies signature on incoming requests. | Server creates a random 32-byte token stored in an SQLite `admin_sessions` table. Cookie contains only the token. |
| **Implementation Complexity** | **Low:** Native to Flask; zero additional tables or database queries per request. | **Medium:** Requires an additional SQL table, query on every request, and periodic expiry cleanup. |
| **Session Revocation** | **Mitigated in DEC-07:** By storing strictly `admin_user_id` and re-verifying `is_active` against SQLite on every protected request, account deactivation takes effect immediately without rotating `SECRET_KEY`. | **Strong:** Immediate revocation. Logging out deletes the database row, instantly invalidating the session. |
| **Dependency Overhead** | None (pure standard Flask). | None (uses existing SQLite connection). |
| **Recommended Verdict** | **Confirmed (DEC-07):** Approved and implemented. Stores ONLY non-sensitive `admin_user_id`. Dynamic DB verification on every request. | **Alternative:** Preserved as viable future extension if multi-device active session lists are required. |

> [!NOTE]
> **DEC-07 Resolution (Confirmed):**
> The project team approved Option A with the mandatory architectural constraint that the signed session cookie contains **strictly `admin_user_id`**. Roles, permissions, and active status are never stored in or trusted from cookie payloads. On every protected request, `@admin_required` queries SQLite to verify account existence and `is_active == 1`. Inactive or deleted accounts have access revoked immediately on the next request. State-changing admin actions enforce session-bound CSRF protection (`auth/csrf.py`) using `hmac.compare_digest`.

### 3.3 Universal Security Controls for Admin Sessions
Regardless of the session mechanism selected:
1. **Password Hashing:** Passwords must be hashed using `werkzeug.security.generate_password_hash` with PBKDF2/SHA-256. Raw passwords must never enter the database.
2. **Secure Cookie Settings:** `SESSION_COOKIE_HTTPONLY = True`, `SESSION_COOKIE_SAMESITE = 'Lax'`, `SESSION_COOKIE_SECURE = True` in production.
3. **Session Timeout:** Sessions must expire automatically after 60 minutes of inactivity.
4. **Explicit Logout:** Visiting `/admin/logout` must clear all session variables and clear the cookie.
5. **CSRF Protection:** State-changing POST requests (e.g., updating dispute statuses) must validate a CSRF token.

---

## 4. Identity, Handover, and Retention

The following institutional and operational questions must be reviewed by the team before writing deployment configurations. **No institutional policies (e.g., specific VIT Pune campus rules) are assumed or invented.**

### 4.1 Administrator Account Provisioning
* **Unresolved Question:** How should the initial administrator account be created?
* **Options Under Consideration:**
  * *Option 1 (Recommended for Prototype):* A dedicated database initialization script (`database/init_db.py`) that creates a default seed admin (e.g., `admin_user`) using credentials defined in `.env`.
  * *Option 2:* A command-line utility (e.g., `python create_admin.py`) that interactively prompts for username and password.
* **Status:** Open for team decision.

### 4.2 Student Identity Verification
* **Unresolved Question:** How should the application verify that a claimant is a bona fide student?
* **Options Under Consideration:**
  * *Option 1:* Restrict the reporter contact email field to a validated institutional email format (e.g., requiring `@campus.edu` or institutional domain).
  * *Option 2:* Allow any valid email address for contact, but mandate that physical Student ID cards must be inspected in person by staff before completing any handover.
* **Status:** Open for team decision.

### 4.3 Physical Handover Desk Arrangement
* **Unresolved Question:** What physical campus facility should be designated as the custody and handover hub in UI microcopy?
* **Options Under Consideration:**
  * Generic Campus Central Lost & Found Desk.
  * Campus Security Office.
  * Central Student Union Helpdesk.
  * Main Library Circulation Desk.
* **Status:** Open for team decision. (UI copy will use a neutral placeholder until confirmed).

### 4.4 Data Retention and Archiving Policy
* **Unresolved Question:** What is the lifecycle of resolved or inactive lost/found reports?
* **Options Under Consideration:**
  * *Option 1:* Retain records indefinitely with status `resolved` for historical project demonstration.
  * *Option 2 (Privacy-Preserving):* Automatically anonymize or purge student contact details (`reporter_contact`) 30 days after item handover is logged.
* **Status:** Open for team decision.

---

## 5. Matching and Dispute Handling

### 5.1 Provisional Scoring Model
The matching algorithm uses a deterministic, additive point model (0–100 total points):
* **Device Type Compatibility (30 pts):** **Mandatory prerequisite.** If device types are incompatible (e.g., `phone` vs. `laptop`), the algorithm immediately halts, sets the score to **0**, and produces no lead.
* **Brand & Manufacturer (25 pts):** Exact case-insensitive match on normalized brand strings.
* **Primary Color (15 pts):** Normalized color keyword matching.
* **Campus Location Proximity (15 pts):** Same building/zone receives 15 pts; neighboring zone receives 5 pts.
* **Time Plausibility Window (15 pts):** Decaying points if found within 0–48 hours of loss date; 0 points if item was found before it was reported lost.

> [!NOTE]
> The weights and the proposed 85% notification threshold are **provisional design benchmarks**. The team makes no claims regarding algorithm accuracy, precision, or recall until empirical test fixtures are executed.

### 5.2 Dispute Freeze Protocol
* **Investigative Lead Only:** An automated match score is strictly an investigative lead for staff; it **never proves ownership**.
* **Competing Claims Invariant:** If two or more lost reports match the same found item (or vice versa), the system **freezes automatic progression**. The affected reports are flagged with `status = 'disputed'`, disabling handover token generation until an authorized administrator conducts a human review.

---

## 6. Security and Privacy Invariants

The following security invariants are non-negotiable architectural rules that must be preserved across all implementations:

1. **Prohibited Credential Collection:**
   * Under no circumstances may any form, endpoint, or database table request, accept, or store device unlock PINs, passwords, lock-screen pattern combinations, biometric data (fingerprint/Face ID), or account recovery codes.
2. **Zero Public Data Leakage:**
   * Public routes (`/`, `/api/ordinary`) must strictly project approved ordinary item fields only.
   * Private electronics reports, student contact details, private ownership clues, administrator credentials (`password_hash`), and application session secrets must **never** be rendered in public HTML templates or exposed in public API responses.
3. **No Security by Obscurity:**
   * Administrative routes (`/admin/*`) must be defended by server-side authentication and role checks. Simply hiding links or buttons in UI templates is explicitly rejected as an access control method.
4. **Parameterized SQL Queries:**
   * All database interactions must use parameterized queries (`?` syntax in Python `sqlite3`). String formatting, concatenation, or interpolation in SQL queries is strictly forbidden to prevent SQL injection.
5. **Non-Accusatory Fraud Policy:**
   * Algorithmic heuristics or image checks must never automatically accuse a user of fraud or lock student accounts. Suspicious cases default to neutral in-person staff inquiry.

---

## 7. Approval History

This log tracks formal decisions made by the project team. Where a decision remains proposed or open, approval details are left blank pending team alignment.

| Decision ID | Decision Title | Decision-Maker / Team | Date Approved | Rationale |
| :--- | :--- | :--- | :---: | :--- |
| **DEC-01** | Stack Selection (HTML/CSS/JS + Flask + SQLite) | Engineering Team | 2026-10-24 | Optimal for first-year learning, zero build overhead, simple local execution. |
| **DEC-02** | Dual-Workflow Architecture | Engineering Team | 2026-10-24 | Prevents public exposure of expensive electronics while keeping ordinary items accessible. |
| **DEC-03** | Ordinary Category Allowlist | Engineering Team | 2026-10-24 | Guarantees that high-value electronics cannot be mistakenly listed on public boards. |
| **DEC-04** | Deterministic Matching Engine Baseline | Engineering Team | 2026-10-24 | Transparent, fully explainable, and testable without cloud dependencies. |
| **DEC-05** | Credential Harvesting Ban | Engineering Team | 2026-10-24 | Mandatory privacy and security guardrail to protect student device credentials. |
| **DEC-06** | Server-Side Access Control | Engineering Team | 2026-10-24 | Rejects security-by-obscurity; ensures administrative endpoints are protected at the server. |
| **DEC-07** | Admin Session Architecture | *(Pending Team Review)* | — | Under evaluation (Option A Signed Cookie vs. Option B SQLite Sessions). |
| **DEC-08** | Admin Account Provisioning | *(Pending Team Review)* | — | Mechanism for creating the first admin account is under discussion. |
| **DEC-09** | Student Identity Verification | *(Pending Team Review)* | — | Evaluation of `@campus.edu` enforcement vs. in-person ID inspection. |
| **DEC-10** | Handover Desk Facility Location | *(Pending Team Review)* | — | Specific physical campus desk location pending confirmation. |
| **DEC-11** | Data Retention & Archiving Policy | *(Pending Team Review)* | — | Archival schedule and PII anonymization timeline pending discussion. |
| **DEC-12** | Factor Weights & Lead Calibration | *(Pending Team Review)* | — | Provisional weights require empirical test calibration. |
| **DEC-13** | Deferral of Photo Uploads | Engineering Team | 2026-10-24 | Eliminates multipart form security risks and file storage bloat in initial MVP. |
| **DEC-14** | Deferral of Gemini Multimodal AI | Engineering Team | 2026-10-24 | Rule-based engine must be validated first before optional AI extensions are explored. |

---

## 8. Next Review Checklist

Before beginning application code development (Phase 1), the four-member team should meet and resolve the following items:

* [ ] **Item 1 (Session Strategy):** Formally approve either Option A (Flask signed cookie session) or Option B (database-backed SQLite session table) for `auth/session.py`.
* [ ] **Item 2 (Admin Seed):** Decide whether initial admin credentials will be generated via a pre-set seed in `database/init_db.py` reading from `.env` or via an interactive CLI script.
* [ ] **Item 3 (Student Identity):** Decide whether form validation should reject non-institutional email formats or rely on in-person campus ID card checks at the desk.
* [ ] **Item 4 (Physical Desk Label):** Agree on the text label to use for the physical campus handover location in user-facing templates.
* [ ] **Item 5 (Data Lifecycle):** Confirm whether resolved records should be permanently stored or have their contact PII anonymized after 30 days.
* [ ] **Item 6 (Test Fixtures):** Agree on the synthetic test dataset pairs to create for calibrating the deterministic matching engine.
