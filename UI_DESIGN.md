# FindBack 2.0 — User Interface & User Experience Design Specification

**Document Version:** 1.0.0-draft  
**Target Audience:** First-Year B.Tech Engineering Project Team, Faculty Mentors, and Reviewers  
**Document Status:** Proposed UI/UX Specification (No Application Code Has Been Written Yet)  

> [!NOTE]
> This document specifies the visual architecture, component library, page layouts, interactive states, and user experience for FindBack 2.0. In adherence to project guidelines, all designs are tailored for execution using **semantic HTML5, vanilla CSS3, lightweight JavaScript, and Flask Jinja2 templates**. No complex JavaScript frameworks (React, Vue) or CSS preprocessors are required.

---

## 1. Design System & Visual Foundation

### 1.1 Design Philosophy & Educational Goals
FindBack 2.0 must deliver a trustworthy, clear, and modern experience for campus students and administrators while remaining accessible to a first-year student engineering team learning web development.

1. **Clarity Over Complexity:** Interfaces must make the dual-workflow distinction obvious at a single glance. Ordinary public items and private confidential reports must never be confused.
2. **Privacy by Presentation:** The UI must reinforce privacy visually. Confidential areas must visually signal safety and encryption, reassuring students that their expensive gadgets are protected.
3. **Zero External CSS/JS Dependencies:** Built entirely with native browser capabilities: CSS Grid, Flexbox, CSS Custom Properties (variables), and standard DOM APIs. No node build steps, CDN dependencies, or external runtime libraries.
4. **Accessible to All Students:** Compliant with WCAG 2.1 AA standards, ensuring high contrast, clean typography, keyboard navigation, and clear error signposting.

---

### 1.2 Color Palette & Semantic Tokens
The design utilizes a clean, academic palette combining a commanding navy primary, crisp teal accents, and purposeful status colors. The two workflows are delineated by distinct brand accents:
* **Public Ordinary Items Flow:** Fresh Emerald / Teal (open, accessible, community-oriented).
* **Confidential Electronics Flow:** Deep Indigo / Slate (secure, confidential, protected).

All color tokens are declared via CSS Custom Properties in `:root`:

```css
:root {
  /* Brand Core Colors */
  --color-primary: #1E293B;         /* Slate Navy - Core header, primary text */
  --color-primary-dark: #0F172A;    /* Deep Midnight - Contrast accents */
  --color-primary-light: #334155;   /* Slate Medium - Subheadings, borders */
  
  /* Workflow Accents */
  --color-workflow-public: #0D9488;       /* Teal - Public ordinary items */
  --color-workflow-public-bg: #F0FDFA;    /* Soft Mint - Public backgrounds */
  --color-workflow-private: #4F46E5;      /* Indigo - Confidential electronics */
  --color-workflow-private-bg: #EEF2FF;   /* Soft Lavender - Private backgrounds */

  /* Neutral Surface & Background Colors */
  --color-bg-body: #F8FAFC;         /* Light Canvas - App body background */
  --color-surface-white: #FFFFFF;   /* Pure White - Cards, modals, containers */
  --color-surface-alt: #F1F5F9;     /* Light Gray - Secondary boxes, card footers */
  --color-border: #E2E8F0;          /* Subtle Gray - Card borders, dividers */
  --color-border-focus: #3B82F6;    /* Royal Blue - Active input focus ring */

  /* Typography Colors */
  --color-text-main: #0F172A;       /* High contrast body text */
  --color-text-muted: #64748B;      /* Medium gray - Timestamps, hints, captions */
  --color-text-inverse: #FFFFFF;    /* White text on dark buttons / badges */

  /* Status & Feedback Tokens */
  --color-success: #16A34A;         /* Green - Resolved, verified, exact match */
  --color-success-bg: #DCFCE7;      /* Light Green - Success alerts, match badges */
  --color-warning: #D97706;         /* Amber - Pending review, moderate lead */
  --color-warning-bg: #FEF3C7;      /* Soft Amber - Warnings, attention alerts */
  --color-danger: #DC2626;          /* Crimson - Dispute flagged, error states */
  --color-danger-bg: #FEE2E2;       /* Soft Red - Prohibited input, dispute alerts */
  --color-info: #0284C7;            /* Blue - Information banners, guide notes */
  --color-info-bg: #E0F2FE;         /* Soft Blue - Info containers */

  /* Elevation & Shadows */
  --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
  --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
  --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);
  
  /* Radii & Transitions */
  --radius-sm: 4px;
  --radius-md: 8px;
  --radius-lg: 12px;
  --radius-full: 9999px;
  --transition-fast: 150ms ease-in-out;
  --transition-base: 250ms ease-in-out;
}
```

---

### 1.3 Typography System
The typography hierarchy uses a native, high-performance system font stack. This eliminates layout shifts, external font download lag, and offline rendering failures during local demonstration.

```css
:root {
  --font-family-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
  --font-family-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;

  /* Font Scales */
  --font-size-xs: 0.75rem;    /* 12px - Footnotes, micro-badges */
  --font-size-sm: 0.875rem;   /* 14px - Helper text, table cells, metadata */
  --font-size-base: 1.0rem;   /* 16px - Body copy, input fields */
  --font-size-lg: 1.125rem;   /* 18px - Card titles, button text */
  --font-size-xl: 1.25rem;    /* 20px - Section headers */
  --font-size-2xl: 1.5rem;    /* 24px - Sub-headings, module headers */
  --font-size-3xl: 1.875rem;  /* 30px - Page titles */
  --font-size-4xl: 2.25rem;   /* 36px - Hero titles */

  /* Line Heights */
  --line-height-tight: 1.25;
  --line-height-normal: 1.5;
  --line-height-relaxed: 1.625;
}
```

---

### 1.4 Spacing & Layout Architecture
All layout spacing is derived from a standard **8-point grid** ($4\text{px}, 8\text{px}, 16\text{px}, 24\text{px}, 32\text{px}, 48\text{px}, 64\text{px}$).

| Spacing Token | Value | Recommended Usage |
| :--- | :--- | :--- |
| `--space-1` | `4px` | Fine adjustments, inline badge padding, border widths |
| `--space-2` | `8px` | Gap between icon and label, tight button padding |
| `--space-3` | `12px` | Input field vertical padding, compact card gaps |
| `--space-4` | `16px` | Standard padding for form fields, cards, card grids |
| `--space-6` | `24px` | Card internal padding, desktop component gaps |
| `--space-8` | `32px` | Section margins, container top/bottom gutters |
| `--space-12`| `48px` | Major section vertical breaks, hero banners |
| `--space-16`| `64px` | Page hero gutters, footer separation |

#### Layout Containers
* **Main Content Max-Width:** `1200px` (centered via `margin: 0 auto; padding: 0 16px;`).
* **Form Container Max-Width:** `680px` (centered for optimal single-column readability and form focus).
* **Admin Dashboard Container:** `1400px` (to comfortably render side-by-side match comparison tables).

---

### 1.5 Reusable Component Library
The frontend is composed of simple, reusable semantic HTML blocks styled with modular utility classes.

#### 1. Button Components (`.btn`)
* `.btn`: Base styles with `padding: 10px 18px;`, `border-radius: var(--radius-md);`, font-weight 600, accessible focus rings, and cursor pointer.
* `.btn-primary`: Background `--color-primary`, text white. For default primary actions.
* `.btn-public`: Background `--color-workflow-public`, text white. For ordinary reporting.
* `.btn-private`: Background `--color-workflow-private`, text white. For confidential electronics reporting.
* `.btn-secondary`: Background `--color-surface-white`, border `1px solid var(--color-border)`, text `--color-text-main`.
* `.btn-danger`: Background `--color-danger`, text white. For dispute actions, rejections.
* `.btn:focus-visible`: High-contrast `outline: 3px solid var(--color-border-focus); outline-offset: 2px;`.

#### 2. Badge & Pill Components (`.badge`, `.pill`)
* `.badge`: Small inline status indicator (`padding: 4px 8px; font-size: var(--font-size-xs); font-weight: 700; border-radius: var(--radius-full);`).
* `.badge-success`: Green text and background (`Available`, `Verified`, `Exact Match`).
* `.badge-warning`: Amber text and background (`Under Review`, `Pending`).
* `.badge-danger`: Red text and background (`Disputed`, `Rejected`).
* `.badge-private`: Indigo badge indicating `Confidential / Internal`.
* `.badge-score`: Distinct numerical match score display (e.g., `85% Lead`).
* `.pill-filter`: Clickable category filter chips on the public listings page (`padding: 6px 14px; border: 1px solid var(--color-border); border-radius: var(--radius-full); cursor: pointer;`).

#### 3. Card Containers (`.card`)
* Standard card with white background, subtle border, rounded corners, and soft shadow:
  ```html
  <article class="card">
    <header class="card-header"> ... </header>
    <div class="card-body"> ... </div>
    <footer class="card-footer"> ... </footer>
  </article>
  ```

#### 4. Alert & Callout Banners (`.alert`)
* `.alert`: Full-width or container-width feedback box with left border accent (`border-left: 4px solid ...; padding: 16px; border-radius: var(--radius-md);`).
* `.alert-danger`: Prominently used on the electronics form for **Prohibited Credential Warnings** (PINs, passwords, pattern locks).
* `.alert-info`: Explanatory campus guidelines and privacy invariants.

---

### 1.6 Accessibility (a11y) Standards
To ensure the application is accessible to all students and staff:
1. **WCAG 2.1 AA Contrast:** All text elements achieve at least a $4.5:1$ contrast ratio against their background ($3:1$ for large headings).
2. **Focus Indicators:** Interactive elements (`a`, `button`, `input`, `select`, `textarea`) provide an unmissable `:focus-visible` ring. Focus outline is never set to `none` without a prominent replacement.
3. **Semantic HTML5:** All pages use `<header>`, `<nav>`, `<main>`, `<section>`, `<article>`, and `<footer>` landmarks. Headings follow a strict hierarchy (`h1` $\rightarrow$ `h2` $\rightarrow$ `h3`) with no skipped levels.
4. **Form Labels:** Every `<input>`, `<select>`, and `<textarea>` has an explicitly associated `<label for="...">`. Descriptive helper text is linked using `aria-describedby`.
5. **Screen Reader Affordances:** Modals and dynamic status containers include `role="dialog"`, `aria-modal="true"`, or `role="status"` / `aria-live="polite"` where status changes occur.

---

## 2. Core Workflow Separation & Privacy Architecture in UI

The most vital architectural invariant of FindBack 2.0 is the **complete separation between public ordinary listings and private electronics reports**. The UI must make this separation immediately evident.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                                 FindBack 2.0 Campus Hub                                │
├───────────────────────────────────────────┬────────────────────────────────────────────┤
│       WORKFLOW A: PUBLIC ORDINARY ITEMS   │     WORKFLOW B: PRIVATE ELECTRONICS        │
├───────────────────────────────────────────┼────────────────────────────────────────────┤
│ • Accent Theme: Teal (#0D9488)            │ • Accent Theme: Indigo (#4F46E5)           │
│ • Audience: Public Campus Community       │ • Audience: Individual Submitter & Admins  │
│ • Items: Bottles, umbrellas, notebooks    │ • Items: Phones, laptops, tablets, earbuds │
│ • Listing Status: Openly searchable       │ • Listing Status: NEVER LISTED PUBLICLY    │
│ • Verification: Physical inspection       │ • Verification: Deterministic match lead,  │
│   at designated campus desk               │   safe non-secret clues, desk review       │
└───────────────────────────────────────────┴────────────────────────────────────────────┘
```

### 2.1 Visual Delineation Rules
1. **Never Mix in Search:** The search input on the public home page must explicitly state: *"Search public ordinary items (bottles, umbrellas, books)..."*. It must never imply or query electronics.
2. **Prominent Workflow Selector:** The `/report` route acts as a clear fork in the road (`report_choice.html`), presenting two distinct, high-contrast visual cards before any form is shown.
3. **Electronics Form Privacy Shield:** The electronics report page features a dark indigo header with a prominent shield/lock icon, titled: *"Confidential Electronics Report — Strictly Private"*.
4. **Permanent Prohibited Data Warning:** The electronics form embeds an unmistakable warning box at the very top and above sensitive clue fields:
   > ⚠️ **DO NOT ENTER UNLOCK PINS, PASSWORDS, OR BIOMETRICS.**  
   > Campus staff will never ask for your device password or PIN. Reports containing passwords or PINs are rejected automatically.

---

### 2.2 Privacy & Zero-Leakage UI Invariants
The frontend is engineered to guarantee zero data leakage:
* **No Private Fields in Public DOM:** Under no circumstances are private electronics fields, student phone numbers, email addresses, or ownership clues rendered in public HTML templates or embedded in HTML `data-*` attributes.
* **Strict Server-Side Projection:** Jinja2 templates for the public feed only receive objects containing approved fields: `id`, `category`, `description`, `campus_location`, `date_discovered`, `status`.
* **Private Tracking Code Isolation:** When a user submits an electronics report, their generated `tracking_code` is displayed in a dedicated receipt view or modal **once**. The tracking code is never visible in public query views or listed anywhere on the site.
* **No UI-Only Security:** Hiding an admin link or button with `display: none` is **not** an access control mechanism. All administrative UI elements reflect server-side authentication state; direct URL navigation to `/admin/*` without an authorized session results in HTTP 302 redirect or HTTP 403 error.

---

## 3. Page-by-Page Layouts & Wireframe Blueprints

### 3.1 Global Shell & Navigation (`templates/base.html`)
The global master layout wraps every page with a consistent header, flash message container, and footer.

#### Desktop & Mobile Navigation Bar
* **Left:** Brand Logo `[FindBack 2.0]` with campus badge.
* **Center (Desktop):** Links to `[Browse Ordinary Items]`, `[Report Item]`, `[Check Status]`.
* **Right:** 
  * Unauthenticated: `[Admin Portal]` link (neutral, discreet link in footer or subtle nav item).
  * Authenticated Admin: `[Admin Queue]`, `[Handover Desk]`, `[Logged in as: admin_name]`, `[Logout]`.
* **Mobile:** Responsive hamburger toggle menu displaying the same primary navigation links.

#### Flash Message Container
* Dynamic Jinja block rendering session alert messages (`info`, `success`, `warning`, `danger`) with close buttons.

#### Global Footer
* Campus custody desk information, educational project disclaimer (VIT Pune first-year engineering demo), link to `/admin/login`.

---

### 3.2 Landing Page & Public Feed (`templates/index.html`)

```
+------------------------------------------------------------------------------------+
|  FindBack 2.0  [Browse Ordinary]  [Report Item]  [Check Status]    [Admin Login]   |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  [HERO BANNER]                                                                     |
|  Find What Was Lost. Protect What Matters.                                         |
|  The campus lost-and-found with dedicated privacy for your valuable belongings.    |
|                                                                                    |
|  +-------------------------------------+   +-------------------------------------+ |
|  | [Teal Card]                         |   | [Indigo Card]                       | |
|  | Found or Lost an Ordinary Item?     |   | Lost an Electronic Device?          | |
|  | Water bottles, umbrellas, notebooks |   | Phones, laptops, tablets, earbuds   | |
|  | [Browse Public Items]  [Report Item]|   | [Submit Confidential Report]        | |
|  +-------------------------------------+   +-------------------------------------+ |
|                                                                                    |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  PUBLIC ORDINARY ITEMS FEED                                                        |
|  [Search input: "Search ordinary items by keyword or location..."] [Search Button]  |
|                                                                                    |
|  Filter by Category:                                                               |
|  [ All (14) ] [ Bottles & Mugs ] [ Notebooks & Books ] [ Umbrellas ]               |
|  [ Eyeglasses ] [ Stationery ] [ Outerwear ] [ General Bags ]                      |
|                                                                                    |
|  +------------------------+ +------------------------+ +------------------------+  |
|  | Water Bottles & Mugs   | | Umbrellas              | | Eyeglasses             |  |
|  | Stainless Steel Flask  | | Black Compact Umbrella | | Wire-frame Reading     |  |
|  | Loc: Central Library   | | Loc: Science Block C   | | Loc: Cafeteria Main    |  |
|  | Date: Oct 23, 2026     | | Date: Oct 22, 2026     | | Date: Oct 20, 2026     |  |
|  | Status: [ Available ]  | | Status: [ Available ]  | | Status: [ Claimed ]    |  |
|  | [Inquire at Desk]      | | [Inquire at Desk]      | | [Resolved]             |  |
|  +------------------------+ +------------------------+ +------------------------+  |
|                                                                                    |
+------------------------------------------------------------------------------------+
|  Footer: FindBack 2.0 Campus Lost & Found Hub | First-Year Engineering Project     |
+------------------------------------------------------------------------------------+
```

#### Key Layout Elements
1. **Dual Action Banners:** Clear choice right in the hero section directing high-value electronics away from the public feed.
2. **Search & Filter Controls:** Real-time or GET-based form with category pill toggles.
3. **Item Cards:** Rendered using CSS Grid (`grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));`).
4. **Ordinary Item Claim Modal/Trigger:** Clicking `[Inquire at Desk]` opens a lightweight dialog explaining the physical pickup location and required verification steps (e.g., student ID).

---

### 3.3 Workflow Selector Page (`templates/report_choice.html`)

When a user clicks "Report Item", they arrive at this structured decision gateway to ensure they select the appropriate workflow.

```
+------------------------------------------------------------------------------------+
|                       What type of item are you reporting?                         |
|           Select the category below to ensure proper privacy and handling          |
+------------------------------------------------------------------------------------+
|                                                                                    |
|   +------------------------------------+  +------------------------------------+   |
|   | WORKFLOW A: ORDINARY ITEM          |  | WORKFLOW B: HIGH-VALUE ELECTRONICS |   |
|   | [Teal Header with Open Box Icon]   |  | [Indigo Header with Shield Icon]   |   |
|   |                                    |  |                                    |   |
|   | Suitable for:                      |  | Strictly for:                      |   |
|   | • Water bottles, tumblers & mugs   |  | • Smartphones & cellphones         |   |
|   | • Notebooks, binders & textbooks   |  | • Laptops & tablet computers       |   |
|   | • Umbrellas & rain gear            |  | • Wireless earbuds & headphones    |   |
|   | • Eyeglasses & sunglasses          |  | • Smartwatches & fitness trackers  |   |
|   | • Coats, jackets & tote bags       |  | • Power adapters & chargers        |   |
|   |                                    |  |                                    |   |
|   | Privacy Level: PUBLIC              |  | Privacy Level: CONFIDENTIAL        |   |
|   | Item will appear on the public     |  | Item details NEVER appear publicly.|   |
|   | board for easy discovery.          |  | Processed via private matcher.     |   |
|   |                                    |  |                                    |   |
|   | [Continue to Ordinary Form ->]     |  | [Continue to Private Form ->]      |   |
|   +------------------------------------+  +------------------------------------+   |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

---

### 3.4 Ordinary Item Submission Form (`templates/report_ordinary.html`)
A focused, accessible form constrained strictly to the hardcoded allowlist.

#### Form Structure & Fields
1. **Report Type Selection:** Segmented control radio buttons: `[ (•) I Found This Item ]` / `[ ( ) I Lost This Item ]`.
2. **Category Selection (`<select>`):**
   * Pre-filled exclusively with the 7 allowlisted categories.
   * Prominently includes helper text: *"Looking for phones or laptops? [Click here for Confidential Electronics Reporting]"*.
3. **Item Description (`<textarea>`):** Placeholder: *"e.g., 750ml blue Hydro Flask with small dent on bottom rim"*.
4. **Campus Location Found/Lost (`<input text>`):** Placeholder: *"e.g., Central Library, 2nd Floor Reading Hall"*.
5. **Date Discovered (`<input type="date">`):** Defaults to current date.
6. **Reporter Contact Email (`<input type="email">`):**
   * Explanatory microcopy: *"Your email is used only by campus desk staff to coordinate handover. It will NEVER be published on the public listing."*
7. **Submit Button:** `[ Publish to Ordinary Items Board ]`.

---

### 3.5 Confidential Electronics Report Form (`templates/report_electronics.html`)
The confidential submission form includes explicit safety alerts, structured device attributes, and safe clue capture.

```
+------------------------------------------------------------------------------------+
|  [SHIELD ICON] Confidential Electronics Report (Strictly Private)                 |
|  Details entered here are NEVER visible on public listings.                        |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  +------------------------------------------------------------------------------+  |
|  |  ⚠️ SECURITY WARNING: NEVER SUBMIT PASSWORDS OR PINs                         |  |
|  |  Do NOT enter device unlock PINs, passwords, pattern locks, or recovery      |  |
|  |  codes. Campus staff will NEVER ask for your password. Submissions with     |  |
|  |  passwords are automatically blocked by the security filter.                 |  |
|  +------------------------------------------------------------------------------+  |
|                                                                                    |
|  Report Type:  (•) I Lost This Device    ( ) I Found This Device                   |
|                                                                                    |
|  1. Device Identification                                                          |
|     Device Type: [ Select: Smartphone / Laptop / Tablet / Earbuds / Charger v ]    |
|     Brand / Make: [ e.g., Apple, Samsung, Lenovo, Dell, Sony                 ]    |
|     Model Family: [ e.g., iPhone 13, Galaxy S22, ThinkPad T14 (optional)     ]    |
|     Primary Color: [ e.g., Space Gray, Midnight Blue, Silver, Black          ]    |
|                                                                                    |
|  2. Incident Details                                                               |
|     Campus Location: [ e.g., Main Auditorium, Row F / CS Lab 302             ]    |
|     Date Lost / Found: [ YYYY-MM-DD ]                                              |
|                                                                                    |
|  3. Safe Ownership Clues (Non-Secret Physical Clues Only)                          |
|     +---------------------------------------------------------------------------+  |
|     | Clues must be non-secret visual traits staff can verify without unlocking.|  |
|     | Examples: Case color, stickers, lockscreen wallpaper description,         |  |
|     | superficial scratches, attached accessories.                              |  |
|     +---------------------------------------------------------------------------+  |
|     Distinctive Clues Description:                                                 |
|     [ Textarea: e.g., Clear silicon case with a yellow smiley sticker on the    ]  |
|     [ back; lock screen photo shows a golden retriever dog.                     ]  |
|                                                                                    |
|  4. Your Contact Details                                                           |
|     Campus Email or Phone: [ student@campus.edu or +91-98XXXXXXXX             ]    |
|     (Kept strictly confidential; accessed only by authorized desk staff)           |
|                                                                                    |
|  [ Submit Confidential Report ]                                                    |
+------------------------------------------------------------------------------------+
```

#### Post-Submission Receipt Modal / View
Upon successful submission, the user receives an unmissable confirmation dialogue:
* **Unique Tracking Code Display:** Monospaced, highlighted code box (e.g., `TRK-8F92-K3A1`).
* **Copy to Clipboard Button:** Visual click-to-copy convenience with "Copied!" feedback.
* **Important Advisory:** *"Save this tracking code. It is your private key to check progress on the Status Lookup page. We do not display electronics reports publicly to protect your property."*

---

### 3.6 Private Status Lookup (`templates/status_lookup.html`)
Allows students to track the status of their confidential report without exposing any sensitive details.

#### Layout Blueprint
* **Input Card:**
  * Field: `Enter Your Private Tracking Code` (e.g., `TRK-XXXX-XXXX`).
  * Action: `[ Check Status ]`.
* **Status Output Display (When valid code is provided):**
  * Status Timeline / Stepper:
    1. `Report Submitted` (Checked)
    2. `Searching for Match` (In progress)
    3. `Under Staff Review` (Pending lead inspection)
    4. `Ready for Desk Handover` (Lead approved; attend desk)
    5. `Resolved` (Handover completed)
  * **Current Status Badge:** Prominent, high-contrast badge matching the current state.
  * **Next Steps Instructions:** E.g., *"If your status is 'Ready for Desk Handover', please visit the Central Custody Desk with your Student ID."*
* **Anti-Oracle Security Design:**
  * If an invalid or unknown tracking code is submitted, the UI displays a uniform neutral message: *"No status update found for this code. Please check that you entered the correct code."*
  * The interface does **not** state whether or not the report exists in the database.

---

### 3.7 Admin Portal: Login Screen (`templates/admin/login.html`)
A minimalist, hardened authentication portal for authorized campus staff.

```
+------------------------------------------------------------------------------------+
|                                                                                    |
|                            [FindBack 2.0 Admin Portal]                             |
|                           Authorized Campus Personnel Only                         |
|                                                                                    |
|                    +------------------------------------------+                    |
|                    | Username:                                |                    |
|                    | [ admin_username                       ] |                    |
|                    |                                          |                    |
|                    | Password:                                |                    |
|                    | [ •••••••••••••••••••••                ] |                    |
|                    |                                          |                    |
|                    | [ Hidden CSRF Token ]                    |                    |
|                    |                                          |                    |
|                    | [ Authenticate & Open Queue -> ]         |                    |
|                    +------------------------------------------+                    |
|                                                                                    |
|  Notice: All administrative actions and handovers are logged with timestamp        |
|  and individual administrator account ID.                                          |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

* **Error Handling:** Invalid credentials render: *"Invalid username or password."* (Never reveals whether the username or password specifically was incorrect).

---

### 3.8 Admin Portal: Lead Review Queue (`templates/admin/leads.html` & `disputes.html`)
The review queue allows authorized staff to inspect automated matching leads, compare evidence, and adjudicate disputes.

```
+------------------------------------------------------------------------------------+
|  FindBack Admin  |  [Lead Review Queue (3)]  [Disputes (1)]  [Handover Desk]        |
|  Logged in as: Officer Sharma (Campus Security)                     [Sign Out]     |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  MATCH LEADS FOR REVIEW (Sorted by Score)                                          |
|                                                                                    |
|  +------------------------------------------------------------------------------+  |
|  | MATCH LEAD #104  | Score: [ 85% High Match ] | Status: [ Pending Staff Review]|  |
|  +------------------------------------------------------------------------------+  |
|  | LOST REPORT (ID: #42)               | FOUND REPORT (ID: #58)                 |  |
|  | Device: Smartphone (Apple iPhone 13)| Device: Smartphone (Apple iPhone 13)   |  |
|  | Color: Midnight Blue                | Color: Midnight Blue / Dark Blue       |  |
|  | Location: Main Library 3rd Floor    | Location: Main Library Study Cubicle   |  |
|  | Date Lost: Oct 21, 2026             | Date Found: Oct 22, 2026 (1 day later) |  |
|  +-------------------------------------+----------------------------------------+  |
|  | CLAIMANT CLUES & EVIDENCE           | FOUND ITEM CLUES & EVIDENCE            |  |
|  | "Clear Spigen case with corner bumps| "Found in clear protective case with   |  |
|  | Lockscreen is photo of golden       | slight yellowing; lockscreen shows a   |  |
|  | retriever puppy."                   | dog."                                  |  |
|  +-------------------------------------+----------------------------------------+  |
|  | Scoring Factor Breakdown (Click to expand details):                          |  |
|  | • Device Type: 30/30 (Exact match: Smartphone)                               |  |
|  | • Brand & Make: 25/25 (Exact match: Apple)                                   |  |
|  | • Color Match: 15/15 (Exact match: Midnight Blue)                            |  |
|  | • Location Proximity: 15/15 (Same Building: Main Library)                    |  |
|  | • Time Plausibility: 0/15 (Found 1 day after report)                         |  |
|  +------------------------------------------------------------------------------+  |
|  | Admin Decision Actions:                                                      |  |
|  | [ Approve for Handover ]  [ Flag as Disputed ]  [ Mark Investigating ]       |  |
|  | [ Dismiss Lead ]                                                             |  |
|  +------------------------------------------------------------------------------+  |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

#### Dispute View (`disputes.html`)
* When an item has competing claims, it is displayed with a bold **Crimson Warning Banner**:  
  `[ ⚠️ COMPETING CLAIM CONFLICT: 2 Lost Reports Match Found Item #58 ]`.
* Handover token generation is **hard-locked** until an administrator evaluates both claimants and marks one claim as dismissed or resolved.

---

### 3.9 Admin Portal: Supervised Handover Desk (`templates/admin/handover.html`)
The physical custody desk interface to verify claimant identity, log verification, and record the handover token.

```
+------------------------------------------------------------------------------------+
|  FindBack Admin  |  SUPERVISED HANDOVER PROTOCOL                                   |
+------------------------------------------------------------------------------------+
|                                                                                    |
|  +------------------------------------------------------------------------------+  |
|  |  IN-PERSON VERIFICATION CHECKLIST (Mandatory Staff Protocol)                 |  |
|  |  [ ] 1. Verified student ID card matches claimant record.                    |  |
|  |  [ ] 2. Verified non-secret physical clues (case, stickers, scratches).      |  |
|  |  [ ] 3. DO NOT ASK STUDENT FOR PIN OR UNLOCK CREDENTIALS.                    |  |
|  |         Student may unlock their own screen to verify custody.                |  |
|  +------------------------------------------------------------------------------+  |
|                                                                                    |
|  Complete Handover Resolution:                                                     |
|  Item Reference: Lead #104 (iPhone 13 - Midnight Blue)                             |
|  Claimant: student_contact@campus.edu                                              |
|                                                                                    |
|  Single-Use Handover Token:                                                        |
|  [ HND-4928                                                                   ]    |
|  (Generated upon lead approval; valid for 30 minutes; one-time use)                |
|                                                                                    |
|  Staff Resolution Notes:                                                           |
|  [ Textarea: Physical ID verified. Lock screen confirmed by student in person.  ]  |
|                                                                                    |
|  [ Verify Token & Complete Handover ]                                              |
|                                                                                    |
+------------------------------------------------------------------------------------+
```

---

### 3.10 System Error Pages (`templates/errors/*.html`)
All error pages use a clean, consistent card layout extending `base.html` with friendly explanations and clear back-to-safety navigation.

* **400 Bad Request (`400.html`):** Used when category allowlist validation fails or prohibited credential keywords are detected.
  * *Message:* "We couldn't process this submission. Please verify that ordinary items use approved categories and that no passwords or PINs are included."
* **403 Forbidden (`403.html`):** Used when unauthenticated users attempt to access `/admin/*`.
  * *Message:* "Access to administrative dashboards is restricted to authorized campus staff. Please authenticate first."
* **404 Not Found (`404.html`):** Clean page indicating the requested URL or resource was not found.
* **500 Server Error (`500.html`):**
  * *Zero Leakage Invariant:* **Zero internal stack traces, SQLite errors, or database column names are rendered.**
  * *Message:* "An unexpected error occurred while processing your request. Campus desk staff have been notified. Please try again shortly."

---

## 4. Responsive Layouts & Breakpoint Behavior

The UI adapts gracefully across all screen sizes using fluid CSS Grid and Flexbox with three primary breakpoints:

| Device Class | Breakpoint Range | Key Layout Adjustments |
| :--- | :--- | :--- |
| **Mobile** | `< 640px` | Single-column stack; sticky bottom action bar for primary actions; collapsible hamburger navigation; full-width modal dialogues. |
| **Tablet** | `640px - 1024px` | 2-column ordinary card grid; stacked side-by-side comparison tables in admin; horizontal scrolling on dense data tables. |
| **Desktop** | `> 1024px` | 3 or 4-column ordinary card grid; full side-by-side match lead comparison; wide sticky admin filters; fixed 1200px / 1400px containers. |

### Mobile Touch Targets & Usability
* **Minimum Touch Target:** All buttons, form inputs, and clickable pill filters maintain a minimum clickable area of $44\text{px} \times 44\text{px}$.
* **Input Font Sizing:** Form controls use `font-size: 16px` on mobile to prevent iOS Safari from automatically zooming the viewport on focus.
* **Thumb Zone Layout:** Form submission buttons and primary workflow triggers span $100\%$ width on mobile screens for easy thumb tapping.

---

## 5. Form States, User Feedback & Microcopy

### 5.1 Interactive Element States
Every interactive element supports six distinct states to give users immediate feedback:

1. **Default:** Crisp border (`var(--color-border)`), neutral background, readable text.
2. **Hover:** Subtle background tint (`var(--color-surface-alt)`), cursor pointer.
3. **Focus:** High-contrast outline ring (`3px solid var(--color-border-focus)`), zero outline clipping.
4. **Active / Pressed:** Slight downward transform or darker shade (`filter: brightness(0.95)`).
5. **Disabled:** Opacity $0.5$, `cursor: not-allowed`, background gray.
6. **Error / Invalid:** Red border (`var(--color-danger)`), red inline error message below field, `aria-invalid="true"`.

---

### 5.2 Real-Time Client-Side Feedback (`static/js/main.js`)
Lightweight vanilla JavaScript enhances usability without becoming a single point of failure (server-side validation remains authoritative):

* **Category Change Alert:** On `report_ordinary.html`, if a user attempts to manually enter or select an unapproved category, a warning banner appears offering a link to the confidential electronics form.
* **Heuristic Credential Warning:** On `report_electronics.html`, as the user types in the "Distinctive Clues" field, a regex listener checks for obvious password keywords (e.g., `pin:`, `pass:`, `password:`, `code: 1234`). If detected, an inline warning highlights the text: *"Reminder: Never enter device PINs or passwords. Staff will verify ownership without needing your credentials."*
* **Submission Loading State:** Upon form submit, the submit button text changes to *"Submitting report..."* and disables itself to prevent duplicate submissions.

---

### 5.3 Empty States
When data is absent, the UI displays helpful, instructional empty states rather than blank pages:

* **Public Feed Empty:** *"No ordinary items are currently listed in this category. Have you found an item? [Submit a Found Item Report]"*.
* **Search Yields No Results:** *"No items match your search query. Try broadening your keywords or check back later."*
* **Admin Lead Queue Empty:** *"All caught up! There are currently no unreviewed match leads in the queue."*
* **Dispute Queue Empty:** *"No conflicting claims are currently flagged. All matching leads are clear."*

---

### 5.4 Campus Microcopy Guide

| UI Context | Prohibited Copy (Avoid) | Recommended Copy (Use) | Why |
| :--- | :--- | :--- | :--- |
| **Electronics Reporting** | "Enter your device unlock PIN for verification." | "Describe non-secret clues (wallpaper, case, stickers). Never enter your PIN or password." | Prevents credential theft; complies with project safety rules. |
| **Matching Lead** | "System has proven you own this item!" | "A high-similarity lead was identified. Campus staff will review the details." | Reinforces that automated scores are leads, not legal proof. |
| **Status Lookup Error** | "Report ID #42 not found in database." | "Status not available for this tracking code. Please verify the code." | Anti-oracle defense; prevents enumeration attacks. |
| **Handover Desk** | "Hand over device to student." | "Verify student ID and physical clues before recording handover token." | Enforces supervised in-person protocol. |

---

## 6. Implementation Sequence & File Architecture

To keep implementation manageable for a first-year student team, frontend development is divided into four incremental milestones aligned with [`IMPLEMENTATION_PLAN.md`](file:///c:/Users/omwor/Documents/findback/IMPLEMENTATION_PLAN.md):

```
┌────────────────────────────────────────────────────────┐
│ Milestone 1 (Phase 2): Foundation & Layout Shell       │
│ • static/css/style.css (variables, reset, typography)  │
│ • templates/base.html (header, nav, flash, footer)     │
│ • templates/errors/*.html (400, 403, 404, 500)         │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Milestone 2 (Phase 4): Public Feed & Ordinary Forms    │
│ • templates/index.html (card grid, search, filter)     │
│ • templates/report_choice.html (dual-workflow cards)   │
│ • templates/report_ordinary.html (allowlist form)      │
│ • static/js/main.js (filter pills, form helper)        │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Milestone 3 (Phase 5): Confidential Electronics & Track│
│ • templates/report_electronics.html (secure form)      │
│ • templates/status_lookup.html (status timeline)       │
│ • Post-submission tracking code receipt modal          │
└───────────────────────────┬────────────────────────────┘
                            │
┌───────────────────────────▼────────────────────────────┐
│ Milestone 4 (Phase 7-8): Admin Portal & Handover Desk  │
│ • static/css/admin.css (queues, side-by-side matrices) │
│ • templates/admin/login.html, leads.html, disputes.html│
│ • templates/admin/handover.html (token entry)          │
│ • static/js/admin.js (queue filters, clue toggles)     │
└────────────────────────────────────────────────────────┘
```

### Team Role Allocation for UI
* **Member 1 (Frontend Lead):** Primary owner of all HTML templates, CSS styles, responsive layouts, accessibility compliance, and visual polish.
* **Member 2 (Backend Routes):** Connects Flask route context variables to Jinja templates; ensures clean error handlers render correct templates.
* **Member 3 (Database & Auth):** Implements CSRF token generation in forms; sets up admin session flash messages.
* **Member 4 (Testing Lead):** Writes automated tests asserting that private electronics fields never appear in public HTML templates.

---

## 7. UI Acceptance Criteria & Testing Checklist

The UI implementation is considered complete only when all the following criteria are verified:

* [ ] **AC-UI-01 (Dual-Workflow Clarity):** Visiting `/report` presents two clearly differentiated choices with distinct color accents (Teal for Ordinary, Indigo for Electronics).
* [ ] **AC-UI-02 (Strict Allowlist Dropdown):** The category dropdown on `/report/ordinary` contains strictly the 7 allowlisted categories and no electronic categories.
* [ ] **AC-UI-03 (Zero Public Leakage in DOM):** Inspecting the rendered HTML of `/` (Home) reveals zero occurrences of private electronics attributes, tracking codes, or student phone numbers.
* [ ] **AC-UI-04 (Credential Defense Callout):** The electronics report page prominently displays the prohibited credential warning banner above all form inputs.
* [ ] **AC-UI-05 (Mobile Responsiveness):** All pages render without horizontal scrollbars or overflowing elements on mobile screens ($320\text{px} - 480\text{px}$).
* [ ] **AC-UI-06 (Keyboard Accessibility):** A user can navigate all form fields, buttons, and links using the `Tab` and `Enter` keys with clear visual focus indicators.
* [ ] **AC-UI-07 (Server-Enforced Admin UI):** Navigating directly to `/admin/leads` in an incognito window redirects immediately to `/admin/login`. Hiding navigation links is verified to not be the sole access control.
* [ ] **AC-UI-08 (Anti-Oracle Status Display):** Submitting an invalid tracking code on `/status` renders a generic neutral message without revealing whether the record exists.

---

## 8. Unresolved Design Decisions & Open Questions

The following UI-related items correspond to unresolved project decisions from [`DECISIONS.md`](file:///c:/Users/omwor/Documents/findback/DECISIONS.md) and must be formally resolved by the team during Phase 0:

1. **Physical Handover Desk Campus Label (DEC-10):**
   * *Status:* **Open**.
   * *UI Impact:* The exact physical desk name to display in the UI copy (e.g., *"Main Campus Security Office, Ground Floor, Building A"* vs. *"Central Student Union Information Desk"*).
   * *Interim Position:* UI mockups and templates will use the neutral placeholder: `"Central Campus Lost & Found Custody Desk"`.
2. **Student Identity Verification in Form UI (DEC-09):**
   * *Status:* **Open**.
   * *UI Impact:* Whether the email input `<input type="email">` should have client-side regex requiring `@campus.edu` or accept any valid email address while requiring physical student ID inspection at the desk.
3. **Public Listings Pagination vs. Single-Page Scroll:**
   * *Status:* **Open**.
   * *UI Impact:* Whether the public feed should implement server-side pagination (`?page=1`) or display the 20 most recent items with a "Load More" button.
4. **Dark Mode Theme Support:**
   * *Status:* **Deferred**.
   * *UI Impact:* To keep the codebase simple for first-year engineers, dark mode CSS is deferred post-MVP. The initial release will focus entirely on a high-contrast, accessible light theme.
5. **Printable Handover Receipt View:**
   * *Status:* **Deferred**.
   * *UI Impact:* Dedicated `@media print` stylesheets for physical handover paper receipts are deferred; on-screen confirmation and database audit logging fulfill MVP requirements.
