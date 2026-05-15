# Agent Repository Workflow

This document defines repository-level operating rules for coding agents.

## Safe Inspection

Run from the repository root:

    pwd
    git status --short
    find . -maxdepth 2 -type f | sort | sed 's#^\./##' | head -200

## Local Run

    python -m app.main

## Docker

    docker-compose config
    docker-compose up --build

Oracle-specific deployment:

    docker-compose -f docker-compose.oracle.yml config
    docker-compose -f docker-compose.oracle.yml up --build

## Tests

    pytest -q
    pytest tests/ -v
    pytest tests/ -v --cov=app

Single test file example:

    pytest tests/safety/test_crisis_detector.py -v

## Alembic / Database Migrations

`DATABASE_URL` must be in the shell environment before any alembic command.
It is **not** loaded automatically — source `.env` explicitly:

    set -a && source .env && set +a

Then run alembic via the venv module:

    python -m alembic upgrade head       # apply all pending migrations
    python -m alembic current            # show current revision
    python -m alembic check              # verify models are in sync with head
    python -m alembic history            # list migration history
    python -m alembic downgrade -1       # roll back one revision
    python -m alembic upgrade head --sql # preview SQL without connecting (offline mode)

In Docker (no manual env loading needed — compose sets DATABASE_URL):

    docker-compose exec app python -m alembic upgrade head

Omitting the env source produces:
`sqlalchemy.exc.NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:driver`

PostgreSQL notes:
- `users.id` maps to `BIGSERIAL`; secondary-table ids map to `SERIAL`.
- `risklevel` is created as a native PostgreSQL `ENUM` type; `downgrade` drops it with `checkfirst=True`.
- `TIMESTAMP WITHOUT TIME ZONE` is used for all datetime columns (timezone-aware columns are a future migration).

Do not run `alembic revision --autogenerate` without first confirming `alembic check` is clean.

## Lint and Format

Check only:

    ruff check .
    ruff format --check .

Auto-format only when explicitly allowed:

    ruff format .

## Type Checking

    mypy app/ --ignore-missing-imports

If mypy is not installed, report it. Do not silently skip.

## Security Scan

    bandit -r app/

If bandit is not installed, report it. Do not silently skip.

## Secret Handling

Never print `.env`.

Never expose:

- Telegram bot tokens;
- OpenRouter API keys;
- database URLs containing credentials;
- Redis credentials;
- cloud provider secrets;
- private deployment credentials;
- sensitive user data.

Safe environment review:

    grep -R "os.getenv\|Settings\|BaseSettings\|Field(" app -n
    sed -n '1,220p' .env.example
    sed -n '1,220p' .env.test.example

Unsafe unless explicitly requested:

    cat .env
    printenv
    env

## Git Discipline

Before changes:

    git status --short

After changes:

    git diff --stat
    git diff

Rules:

- do not overwrite user changes;
- do not commit unless explicitly asked;
- do not create branches unless explicitly asked;
- do not modify generated/cache files;
- do not include `.env`, `.venv`, caches, or local IDE state.

Avoid editing:

    .venv/
    .pytest_cache/
    __pycache__/
    *.pyc
    .env

## Dependency Policy

Do not add dependencies casually.

Before adding a dependency, explain:

- why existing dependencies or the standard library are insufficient;
- runtime vs development use;
- deployment impact;
- Docker image impact;
- security/maintenance impact.

## Verification Policy

Do not claim verification unless the command was actually run.

Use exact wording when blocked:

- Not verified; command was not run.
- Not verified; dependency is missing.
- Partially verified with targeted tests.
- Static review only.

## Audit Mode

For read-only audits:

- do not modify files;
- do not format files;
- do not install dependencies;
- do not print secrets;
- do not read `.env`;
- write findings by severity;
- include commands run and commands not run.
