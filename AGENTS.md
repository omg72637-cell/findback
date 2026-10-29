# FindBack agent rules

## Project
Flask modular monolith, PostgreSQL, SQLAlchemy, Alembic, pytest.
Read ARCHITECTURE.md and docs/security-plan.md before changing anything.

## Non-negotiables
- Never put secrets, tokens, emails, PRNs or contact details in code, logs, fixtures or error pages.
- Never expose private_electronics data, clues, serials or contacts in public routes or JSON.
- Every state-changing route needs CSRF, a rate limit, an authorisation decorator, and an audit entry if sensitive.
- SQL is parameterised only. No string formatting in queries.
- Login accepts only verified emails ending exactly in @vit.edu. Roles are read from the database on every request.
- Work on auth, crypto, uploads or migrations starts with a written plan; stop and wait for my review.

## How to work
- One small mission per branch. Write tests first for security-relevant logic.
- Run pytest, ruff and bandit before finishing. Finish with a walkthrough.
- Do not add a dependency without stating why and listing alternatives.
- Never run destructive commands (drop, rm -rf, force push) without asking.

## Done means
Tests pass on SQLite and Postgres, a security test exists, docs are updated, nothing security-related is left as TODO.
