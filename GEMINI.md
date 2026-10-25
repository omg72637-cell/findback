# FindBack 2.0 — Project Instructions & Guidelines

## 1. Project Purpose
FindBack 2.0 is a campus lost-and-found platform designed with two distinct workflows:
1. **Ordinary / Lower-Risk Items**: Items such as water bottles, notebooks, umbrellas, and eyeglasses may have public listings for easy browsing and claiming.
2. **High-Value Electronics**: Items such as smartphones, laptops, tablets, chargers, and earbuds must **never** appear in public listings. Reports for lost and found electronics are strictly private and processed exclusively via an internal matching engine to protect student privacy and prevent opportunistic claims.

---

## 2. Proposed Technology Stack
* **Frontend**: Vanilla HTML5, CSS3, and JavaScript (clean, modular, and easy to inspect).
* **Backend**: Python with Flask (subject to environment and dependency compatibility checks).
* **Initial Database**: SQLite (lightweight, zero-configuration prototyping for local development).
* **Matching Engine**: Explainable, deterministic Python scoring logic; optional Google Gemini API assistance will only be introduced after the rule-based matching engine is fully built and tested.
* **Version Control**: Git and GitHub.

---

## 3. Safety and Privacy Guardrails
* **Confidentiality of High-Value Reports**: Never expose private electronics reports, ownership clues, claimant evidence, serial numbers, or user contact details in public API responses or public UI views.
* **Prohibited Data Requests**: Never ask users for device unlock PINs, passwords, biometric credentials, or account recovery codes.
* **Match Scores are Leads**: An automated match score is only an investigative lead, never definitive proof of ownership.
* **Human Review for Conflicts**: Any conflicting, disputed, or suspicious claims require review and approval by an authorized administrator or campus official.
* **Secret Protection**: Never store API keys, tokens, or credentials in client-side code, Git commits, or public repositories. Use environment variables.
* **Image Authenticity & Anti-Fraud**: Image authenticity checks must not be treated as infallible. Never automatically accuse a user of fraud based solely on an AI-generated image detector or automated heuristic.
* **Data Minimization & Input Security**: Strictly validate and sanitize all form inputs, protect file upload endpoints against malicious files, and collect only the minimum personal data necessary.

---

## 4. Development Workflow & Engineering Standards
* **Incremental Steps**: Work in small, clearly bounded steps. Do not attempt to generate or scaffold the entire application in a single turn.
* **Inspect Before Editing**: Always inspect existing files and environment state before making modifications.
* **Clear Explanations**: Explain proposed changes before making them, using beginner-friendly language suitable for first-year engineering students to understand and present.
* **Empirical Verification**: Run relevant automated or manual tests and report actual execution results. Never claim a feature works without verifiable testing.
* **Lean Architecture**: Avoid unnecessary third-party dependencies, complex frameworks, or out-of-scope modifications.
* **Clean Separation**: Keep generated configurations, environment setup scripts, and documentation strictly separated from core application code.
* **Explicit Approvals**: Always request explicit user approval before executing destructive actions, installing dependencies, altering Git remotes, or committing architectural changes.
