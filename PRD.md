# FindBack 2.0 — Product Requirements Document (PRD)

**Document Version:** 1.0.0-draft  
**Target Audience:** First-Year Engineering Project Team, Faculty Reviewers, and Mentors  
**Status:** Approved for Implementation Planning  

---

## 1. Project Overview & Problem Statement

### 1.1 Context
In a bustling campus environment, hundreds of personal items are misplaced every semester across lecture halls, libraries, cafeterias, labs, and athletic facilities. Existing campus lost-and-found operations often rely on fragmented physical lost-and-found boxes, informal social media posts, or unmoderated public bulletin boards.

### 1.2 The Problem
Traditional lost-and-found approaches suffer from two fundamental design flaws:
1. **Public Exposure of High-Value Electronics:** Posting detailed photos, brand names, and serial numbers of lost smartphones, laptops, or tablets on public boards exposes student privacy and enables opportunistic theft or fraudulent claims. Bad actors can easily claim an item by reciting details visible in the public post.
2. **Neglect of Ordinary Everyday Items:** Lower-risk, low-value items (such as water bottles, notebooks, umbrellas, and eyewear) accumulate in physical boxes and are rarely claimed because there is no searchable, centralized, and accessible public record.

### 1.3 The FindBack 2.0 Solution
FindBack 2.0 is a web-based campus lost-and-found application engineered around a **dual-workflow architecture**:
* **Public Workflow for Ordinary Items:** Lower-risk everyday items on an explicit category allowlist are publicly searchable to make claiming frictionless.
* **Private Workflow for High-Value Electronics:** Electronics reports are strictly confidential, never published publicly, and processed exclusively through an internal, deterministic matching engine and supervised administrative review.

---

## 2. Project Goals & Measurable Success Criteria

### 2.1 Project Goals
* **Educational Feasibility:** Implement a clean, modular, and maintainable software architecture using vanilla HTML, CSS, JavaScript, Python with Flask, and SQLite that is understandable and presentable by first-year engineering students.
* **Privacy by Design:** Enforce zero-leakage boundaries ensuring that confidential electronics reports, personal contact details, and ownership clues are never accessible via public routes.
* **Explainable Matching:** Develop an explainable, deterministic scoring engine that provides transparent point breakdowns for why two reports may match.
* **Supervised Safety:** Facilitate safe handovers mediated by authorized campus personnel, eliminating dangerous or unverified direct student meetups.

### 2.2 Measurable Success Criteria
* **Zero Data Leakage:** 100% of automated privacy-boundary test cases pass, verifying that public pages, public API responses, error messages, and unauthorized requests never leak private electronics reports, claimant clues, or student contact info, testing both backend responses and visible UI views.
* **Strict Category Enforcement:** 100% of submissions to the public feed are verified against the explicit ordinary-item allowlist.
* **Prohibited Data Defense:** Zero forms or API endpoints collect or accept device unlock PINs, passwords, biometric credentials, or account recovery codes.
* **Deterministic Matching Performance Target:** Matching scores and explanation breakdowns have a performance target of under 100ms when measured under documented local test conditions with test fixtures of at least 200 items. Correctness and privacy isolation take strict priority over this performance target.
* **Empirical Threshold Validation:** The proposed matching lead notification threshold (tentatively set at 85%) is treated as an unvalidated design hypothesis; actual scoring accuracy and precision will be measured empirically against test fixtures before claims of reliability are made.

---

## 3. Target Users & Their Roles

| User Role | Description | Key Permissions & Responsibilities |
| :--- | :--- | :--- |
| **Student / Campus Finder** | Any campus member who discovers an item on campus. | • Submit public found reports for approved ordinary items.<br>• Submit confidential found reports for electronics.<br>• Hand over found items to an authorized campus desk. |
| **Student / Campus Searcher** | Any campus member searching for a lost possession. | • Browse and search public listings for ordinary items.<br>• Submit confidential lost reports for electronics.<br>• Provide safe ownership clues for verification.<br>• Receive status updates on confidential inquiries. |
| **Authorized Campus Administrator** | Designated campus staff (e.g., Campus Security, Student Helpdesk, Library Desk). | • Authenticate via individual admin accounts with role-based checks.<br>• Inspect matching leads and score breakdowns for electronics.<br>• Review and adjudicate conflicting or suspicious claims.<br>• Supervise physical handovers and log resolution tokens. |

---

## 4. The Two Core Workflows

```
┌────────────────────────────────────────────────────────────────────────┐
│                        FindBack 2.0 Report Entry                       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                  Item Classification & Allowlist Check
                                    │
           ┌────────────────────────┴────────────────────────┐
           ▼                                                 ▼
┌───────────────────────────────┐         ┌───────────────────────────────┐
│     Ordinary Items Flow       │         │    High-Value Electronics     │
│   (Strict Category Allowlist) │         │     (Confidential Flow)       │
├───────────────────────────────┤         ├───────────────────────────────┤
│ • Water Bottles               │         │ • Smartphones & Tablets       │
│ • Notebooks & Textbooks       │         │ • Laptops & Notebook PCs      │
│ • Umbrellas                   │         │ • Earbuds & Headphones        │
│ • Eyeglasses & Sunglasses     │         │ • Smartwatches & Chargers     │
│ • Clothing, Coats & Bags      │         │                               │
├───────────────────────────────┤         ├───────────────────────────────┤
│ Storage: `ordinary_items`     │         │ Storage: `private_electronics`│
│ Public Board: Visible         │         │ Public Board: NEVER VISIBLE   │
│ Discovery: Public Search      │         │ Discovery: Matching Engine    │
│ Handover: Direct / Desk Check │         │ Handover: Authorized Desk Only│
└───────────────────────────────┘         └───────────────────────────────┘
```

### 4.1 Workflow A: Ordinary / Lower-Risk Items (Public)
1. **Explicit Category Allowlist:** Only items matching approved low-risk categories may be entered into the public board:
   * Water bottles & mugs
   * Notebooks, binders, and textbooks
   * Umbrellas
   * Eyeglasses & sunglasses
   * Non-electronic stationary
   * Outerwear, jackets, scarves, and general tote bags
2. **Publicly Exposed Fields (Approved Only):**
   * Item Category
   * Public General Description (e.g., "Blue stainless-steel thermos")
   * General Campus Location Found/Lost (e.g., "Science Complex, 2nd floor")
   * Date/Time Discovered
   * Item Status (`Available`, `Claim Pending`, `Resolved`)
3. **Excluded from Public Listing:** Student personal phone numbers, physical home addresses, and private identification numbers are never rendered on the public board.

### 4.2 Workflow B: High-Value Electronics (Confidential & Private)
1. **Target Items:** Smartphones, laptops, tablets, smartwatches, wireless earbuds, premium headphones, and portable chargers.
2. **Strict Confidentiality Invariant:**
   * High-value electronics reports are saved exclusively in private tables.
   * Public browsing pages, public search endpoints, and public JSON feeds must **never** return private electronics records.
   * Contact details, private clues, and serial numbers are strictly restricted to authenticated administrators.
3. **Processing Pipeline:**
   * Private Report Ingestion $\rightarrow$ Background Deterministic Matcher $\rightarrow$ Lead Generation with Explainable Breakdown $\rightarrow$ Queued for Authorized Admin Review $\rightarrow$ Supervised In-Person Handover.

---

## 5. MVP Functional Requirements

### 5.1 Ordinary Items Module (Public)
* **FR-01 (Category Validation):** The backend must validate all ordinary submissions against the hardcoded category allowlist, rejecting unapproved categories with clear error feedback.
* **FR-02 (Public Listing Feed):** Provide a responsive, paginated or clean card view of active ordinary items displaying approved fields only.
* **FR-03 (Search & Filter):** Allow users to filter ordinary listings by category, location, and keywords.
* **FR-04 (Ordinary Item Claim Request):** Allow a claimant to submit a claim inquiry with a contact method and simple verifying description without exposing personal details publicly.

### 5.2 Confidential Electronics Module (Private)
* **FR-05 (Confidential Submission):** Provide a dedicated form for lost and found electronics capturing structured attributes (device type, brand, model family, primary color, campus location, date/time) and private ownership clues.
* **FR-06 (Prohibited Data Guardrail):** The form and backend validator must explicitly reject inputs attempting to provide device unlock PINs, passwords, biometric credentials, or account recovery codes, displaying a prominent warning.
* **FR-07 (Deterministic Matching Engine):** Automatically compute match scores (0–100) between open lost and found electronics reports based on weighted attribute similarity (Device Type, Brand, Color, Location, Time Window).
* **FR-08 (Explainable Breakdown Generator):** For every evaluated match pair, the system must generate a human-readable JSON breakdown explaining exactly how many points were earned per attribute.

### 5.3 Administrative & Security Module
* **FR-09 (Individual Admin Accounts & Auth Selection):** Admins must authenticate using individual username/password credentials with secure password hashing (`werkzeug.security`). Shared passphrases are strictly prohibited. Before implementation, the team must choose and document a suitable authentication and session-management approach.
* **FR-10 (Enforced Role-Based Access Control):** Administrative endpoints (`/admin/*`) and actions must enforce server-side session and role-based access checks; unauthenticated or unauthorized requests must be rejected (e.g., HTTP 401/403) or redirected. Access control must never rely on security through obscurity (such as simply hiding admin URLs or UI buttons).
* **FR-11 (Match Lead Review Queue):** Admins can view prioritized match leads, compare lost vs. found clues side-by-side, inspect the explainable scoring breakdown, and update the status (`Under Investigation`, `Dispute Flagged`, `Approved for Handover`, `Dismissed`).
* **FR-12 (No Automatic Contact Disclosure):** The system must not automatically email or disclose claimant contact details upon scoring a match; contact sharing or notification requires authorized administrative mediation.
* **FR-13 (Supervised Handover Token):** Upon approving a handover, the system must generate a one-time verification token and log the completing admin ID, timestamp, and final resolution.

---

## 6. Explicitly Excluded Features & Future Enhancements

To keep the MVP feasible and robust for a first-year engineering team learning Python, the following features are **explicitly excluded** from the MVP:

| Excluded Feature | Reason for Deferral | Proposed Future Phase |
| :--- | :--- | :--- |
| **Photo / Image Uploads** | Eliminates multipart form complexity, image file security vulnerabilities, and local media storage overhead during initial prototype. | Phase 2 (Media Handling) |
| **Google Gemini Multimodal API** | The project rules mandate that explainable rule-based matching must be fully implemented, calibrated, and tested first. | Phase 3 (AI Assistance) |
| **Campus Single Sign-On (SSO / OAuth / LDAP)** | Requires enterprise infrastructure integration out of scope for local prototype. | Future Release |
| **Automated Email / SMS Notifications** | Avoids external SMTP/Twilio API dependencies and credentials management during local development. | Phase 2 (Notifications) |
| **Direct Peer-to-Peer Student Chat** | Direct unmoderated student meetups for high-value electronics present physical safety risks. | Rejected by Design |
| **AI-Based Automated Fraud Accusation** | Image heuristics or algorithmic detectors are not infallible; automated banning is unethical and prohibited. | Rejected by Design |

---

## 7. Privacy, Safety & Security Requirements

### 7.1 Data Minimization
* Collect only the minimum descriptive and contact attributes necessary to establish a lead.
* Avoid collecting government ID numbers, personal home addresses, or full birthdates.

### 7.2 Zero Public Leakage Boundary
* Database queries for public views must strictly target the `ordinary_items` table and select only approved public columns.
* Private electronics tables must have zero public API, error message, or template bindings.
* Public pages, public API responses, error messages, and unauthorized requests must never expose private electronics reports, ownership clues, claimant evidence, or personal contact details.
* Automated testing must verify both the visible UI views and the underlying backend data responses to ensure complete isolation.

### 7.3 Prohibited Data Requests
* Form fields must never ask for, and instructions must clearly prohibit, submitting:
  * Device unlock PINs, passwords, or pattern combinations.
  * Apple ID, Google Account, or iCloud credentials.
  * Two-factor authentication (2FA) codes or recovery keys.
  * Biometric credentials (e.g., fingerprint or Face ID descriptions).

### 7.4 Secret Protection
* Application secret keys and database paths must be loaded via environment variables or a separate `config.py` file.
* No API keys, credentials, or private configuration values may be committed to Git.

### 7.5 Injection & Input Security
* All database interactions must use SQLite parameterized queries (`?` placeholders) to prevent SQL injection.
* All user inputs rendered in HTML templates must be escaped (default Jinja2 auto-escaping enabled) to prevent Cross-Site Scripting (XSS).

---

## 8. Ownership Verification, Matching Leads, Disputes & Supervised Handover

### 8.1 Permissible Ownership Clues
To prove ownership of high-value electronics without compromising security, claimants may only provide non-invasive visual clues:
* Description of lock screen wallpaper image (e.g., "Photo of a golden retriever with a red collar").
* Brand, color, and physical material of protective case.
* Specific stickers, decals, or superficial scratches on the device chassis.
* Specific peripheral accessories attached (e.g., braided lanyard, specific headphone tip color).

### 8.2 Lead Interpretation & Scoring Thresholds
* **Investigative Lead Only:** An automated match score is strictly a lead for human review, never definitive legal proof of ownership.
* **Unvalidated 85% Threshold:** The 85% threshold is a provisional baseline. The system will flag scores $\ge 85$ as "High Confidence Leads" and scores between $60$ and $84$ as "Moderate Leads" for admin inspection. Accuracy claims will remain unstated until empirical unit tests validate scoring distributions.

### 8.3 Dispute & Conflict Resolution
* **Multiple Claimant Dispute:** If two or more students submit lost reports matching the same found device, the system automatically flags the item with a `Disputed` badge and locks it from handover until an administrator conducts an in-person review.
* **Suspicious Reports:** Any report exhibiting inconsistent dates, contradictory clues, or conflicting descriptions is flagged for administrative inquiry.
* **Non-Accusatory Policy:** Algorithmic heuristics must never label a user as fraudulent. Suspicious items are routed to neutral human inspection.

### 8.4 Supervised Handover Procedure
1. Authorized administrator contacts both parties through recorded campus contact channels.
2. The item is held at a designated campus lost-and-found desk.
3. The claimant attends the desk in person and provides physical proof (e.g., unlocking the device with their fingerprint/PIN in front of staff, without disclosing the PIN to staff).
4. Staff enters a one-time verification token in the admin portal to mark the item `Resolved` and logs the record.

---

## 9. User-Facing Pages & Expected Behaviour

| Page / Route | Template Name | Target User | Expected Functional Behaviour |
| :--- | :--- | :--- | :--- |
| **`/` (Home / Public Feed)** | `index.html` | All Campus | Displays allowlisted ordinary items; search bar; category filter pills; prominent banner guiding electronics losers/finders to confidential forms. |
| **`/report` (Report Selector)** | `report_item.html` | All Campus | Explains the two distinct workflows; allows the user to select either an Ordinary Item report or a Confidential Electronics report. |
| **`/report/ordinary`** | `report_ordinary.html` | Finders / Losers | Form with strict category dropdown (allowlist only), item description, location, date, and contact email. |
| **`/report/electronics`** | `report_electronics.html`| Finders / Losers | Confidential form capturing device attributes, safe ownership clues, and private contact info. Displays prohibited data warnings. |
| **`/status` (Inquiry Lookup)**| `status_lookup.html` | Student Searcher | Allows a student to enter their private Report ID and view public status (`Submitted`, `Searching for Match`, `Under Staff Review`, `Ready for Desk Handover`). |
| **`/admin/login`** | `admin_login.html` | Campus Staff | Individual admin credential login form with CSRF protection and error messaging for invalid attempts. |
| **`/admin/leads`** | `admin_leads.html` | Campus Staff | Protected dashboard displaying match leads, score breakdowns, clue comparisons, and dispute flags. |
| **`/admin/handover`** | `admin_handover.html` | Campus Staff | Desk verification interface to log claimant verification, generate completion token, and mark case resolved. |

---

## 10. Non-Functional Requirements

### 10.1 Usability & Accessibility
* **Beginner-Friendly Layout:** Minimalist, semantic HTML5 structure with responsive, high-contrast CSS styling.
* **Clear Microcopy:** Form fields must have clear instructions, especially clarifying what details to provide and what sensitive details to omit.
* **Keyboard Navigation:** All interactive elements (buttons, form inputs, links) must be navigable using standard keyboard inputs.

### 10.2 Maintainability & Simplicity
* **Lean Architecture:** Pure Python 3 standard library + Flask + SQLite. No heavy node build chains, Webpack, or external database engines.
* **Readable Codebase:** Every module, class, and function must have descriptive docstrings written in simple language suitable for first-year engineering students.
* **Separation of Concerns:** Clear demarcation between routing (`app.py`), database queries (`database/db.py`), and matching algorithms (`matching/matcher.py`).

### 10.3 Performance & Reliability
* **Response Time Target:** Local page renders and API responses have a performance target of under 100 milliseconds to be measured under documented local test conditions, rather than a guaranteed result. System correctness, robust validation, and privacy isolation take strict priority over this performance target.
* **Zero Crash Invariants:** Database locks and missing fields must be caught gracefully and return user-friendly error pages rather than unhandled 500 exceptions.

---

## 11. Proposed Acceptance Criteria & Testable Conditions

To achieve verifiable completion, the MVP must satisfy the following testable conditions:

* **[ ] Acceptance Test 1 (Ordinary Allowlist Validation):** Submitting an ordinary item with an unapproved category (e.g., "Smartphone" or "Jewelry") is rejected by the backend with an HTTP 400 status.
* **[ ] Acceptance Test 2 (Zero Public Leakage & Boundary Testing):** Automated tests verify that across public pages, public API endpoints, error handlers (e.g., 404, 500), and unauthorized requests, 0 records or attributes from `private_electronics` (including ownership clues and personal contact details) are ever leaked. Both backend responses and visible rendered UI templates must be verified.
* **[ ] Acceptance Test 3 (Prohibited Credential Defense):** Submitting a confidential electronics report containing PIN or password keywords triggers a client-side warning and backend validation failure.
* **[ ] Acceptance Test 4 (Deterministic Scoring Unit Test):** The matching function executed on identical input pairs yields the exact same numerical score and breakdown every time.
* **[ ] Acceptance Test 5 (Enforced Role-Based Access Control):** Accessing `/admin/*` routes without an active, authenticated admin session rejects or redirects the request. Tests must confirm that hiding buttons/links is not treated as access control and that direct URL requests are blocked at the backend.
* **[ ] Acceptance Test 6 (Dispute Lock):** When an item is marked `Disputed`, the handover completion button is disabled until the dispute status is explicitly cleared by an admin.
* **[ ] Acceptance Test 7 (Verification Token Generation):** Completing a handover logs an entry in `handover_logs` with a unique verification token and timestamp.

---

## 12. Assumptions, Limitations & Open Decisions

### 12.1 Assumptions
1. The application will initially run in a local development environment (localhost) on SQLite for demonstration and evaluation purposes.
2. The initial campus deployment model assumes a single centralized campus desk or security office handles physical verification and custody.
3. Test datasets of simulated lost and found reports will be generated to calibrate and demonstrate the matching engine.

### 12.2 Limitations
1. No native mobile application; the platform will operate as a responsive mobile-friendly web application.
2. No automated external messaging (SMS or email dispatch) in the MVP; communication is mediated by the desk admin.
3. No automated physical item storage tracking (e.g., shelf/bin warehouse barcode management) in this release.

### 12.3 Open Decisions & Questions Needing Team / Mentor Alignment

* **Open Question 1 (Physical Handover Desk Location):** Which specific campus office should be designated in the UI copy as the physical custody desk (e.g., Campus Security Office, Central Student Union Helpdesk, or Main Library Circulation Desk)?
* **Open Question 2 (Admin Auth & Session Strategy):** Which specific authentication and session-management mechanism should the team document and implement (e.g., Flask-Login, secure HMAC-signed cookie sessions, or lightweight session tokens)?
* **Open Question 3 (Claimant Verification Method):** Should student searchers be required to provide a verified campus email format (`@campus.edu`), or will a general email address plus Student ID card inspection at the desk suffice?
* **Open Question 4 (Data Retention Policy):** How long should resolved or unclaimed records remain in the database before archiving or anonymization (e.g., 30 days vs. end of academic semester)?
* **Open Question 5 (Score Weight Calibration):** What exact weights should be assigned to physical attributes (Brand vs. Color vs. Location vs. Time Window) once initial empirical test fixtures are executed?
