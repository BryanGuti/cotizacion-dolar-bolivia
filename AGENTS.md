# Repository Guidelines

## Project Overview

Dólar Bolivia is a web application that collects, stores, and displays USD exchange rates from the Banco Central de Bolivia (BCB) and commercial banks in Bolivia.

The project consists of:
- A Python-based data collection and validation system.
- A static frontend built with HTML, CSS, and vanilla JavaScript.
- Current exchange-rate data and historical JSONL records.
- A local cron entry point that validates and pushes successful data updates.

Preserve the existing architecture unless a change is explicitly requested and its impact has been evaluated.

## Project Structure

```text
scraper/
├── main.py
├── config.py
├── sources/
└── utils/

tests/

scripts/
└── update_exchange_rates.sh

frontend/
├── index.html
├── css/
├── js/
├── pages/
└── data/
    ├── current.json
    └── history/
        └── <year>/
            └── <entity>.jsonl

.github/
└── workflows/
requirements.txt
AGENTS.md
README.md
```

### Directory Responsibilities

- `scraper/`: Python scraper application.
- `scraper/sources/`: Source-specific extraction modules.
- `scraper/utils/`: Shared normalization, validation, storage, and logging utilities.
- `tests/`: Automated Python tests.
- `scripts/`: Local operational scripts, including the scheduled scraper runner.
- `frontend/`: Static website.
- `frontend/css/`: Stylesheets.
- `frontend/js/`: Frontend application logic and data processing.
- `frontend/pages/`: Additional frontend pages.
- `frontend/data/`: Public application data consumed by the frontend.
- `frontend/data/history/`: Historical JSONL records organized by year.
- `.github/workflows/`: CI and GitHub Pages deployment workflows. GitHub Actions does not run the scraper.
- `README.md`: Project setup and operating documentation.

## Architecture and Data Flow

The scraper collects exchange-rate information from configured sources.

The data flow is:

1. Collect source information.
2. Normalize and validate extracted values.
3. Generate the current exchange-rate dataset.
4. Insert or update the record for that entity and quotation date in its JSONL file.
5. Make both current and historical data available to the static frontend.

### Canonical Data Locations

All data required by the public frontend must be stored inside `frontend/data/`.

- Current data: `frontend/data/current.json`
- Historical data: `frontend/data/history/<year>/<entity>.jsonl`

Do not introduce new public frontend dependencies on files outside `frontend/`.

When modifying data paths, update the Python configuration, frontend loading logic, and related tests consistently.

When migrating historical data:
- Preserve all existing records.
- Do not overwrite or discard historical information.
- Avoid duplicate records.
- Verify record counts and file contents before considering the migration complete.
- Keep the original data until the migration has been successfully verified.

## Development Environment

Run commands from the repository root unless explicitly stated otherwise.

### Python Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Run the Scraper

```bash
python -m scraper.main
```

The scraper requires network access to retrieve source data.

For scheduled local scraping and data pushes, install the requirements in `.venv` and run:

```bash
bash scripts/update_exchange_rates.sh
```

The local runner activates `.venv` and runs `python -m scraper.main`. It stages, commits, and pushes only when files under `frontend/` changed. It appends all output to `logs/YYYY-MM-DD.log`, with start and end markers for each run; logs are restricted to the local user and ignored by Git. Configure a local cron job for the desired schedule. It can use the GNOME Keyring SSH agent socket when cron does not inherit `SSH_AUTH_SOCK`; do not place credentials in the script or crontab.

### Run Tests

```bash
python -m pytest -v
```

Run a focused test when appropriate:

```bash
python -m pytest tests/test_normalizer.py -v
```

### Run the Frontend

Serve the frontend directory as the web root:

```bash
python -m http.server 8000 --directory frontend
```

Open:

```text
http://localhost:8000
```

Do not use the repository root as the web server root when testing the intended static deployment structure.

## Coding Style

### Python

- Use four spaces for indentation.
- Use descriptive `snake_case` names.
- Use `PascalCase` for classes.
- Keep source-specific extraction inside its corresponding module.
- Place shared functionality in `scraper/utils/` or the appropriate shared module.
- Preserve existing JSON field names and entity identifiers.
- Validate normalized data before storage.

### Frontend

- Use standard HTML5, CSS, and vanilla JavaScript.
- Do not introduce frameworks or dependencies without approval.
- Use descriptive, lowercase file names.
- Keep responsibilities separated between HTML, CSS, and JavaScript.
- Avoid unnecessary global variables.
- Reuse existing components, styles, and application patterns.
- Ensure responsive behavior and accessibility.

## Application Rules

- Preserve all existing entity identifiers.
- Do not fabricate exchange rates or historical records.
- Handle missing or invalid values explicitly.
- Preserve the distinction between official BCB rates and commercial bank rates.
- Keep monetary and percentage calculations consistent with the existing implementation.
- Historical charts must use actual stored records.
- Missing historical values must not be replaced with invented data.
- Maintain compatibility between the scraper output and frontend data consumers.

## Testing and Validation

For changes involving the scraper:
- Run relevant automated tests.
- Validate generated JSON.
- Verify historical JSONL output.
- Confirm that existing records remain intact.

For frontend changes:
- Check the browser console for errors.
- Verify data loading and rendering.
- Test relevant interactions.
- Check responsive layouts.
- Verify that historical data loads correctly from the frontend web root.

For data-path or migration changes:
- Verify that the scraper writes to the canonical data directory.
- Verify that the frontend reads from the same directory.
- Test using the documented local server command.
- Confirm that existing historical data has been preserved.

Add or update automated tests when behavior changes.

## Git and Change Management

- Keep changes focused and logically grouped.
- Use short, imperative commit messages.
- Do not commit credentials, secrets, or unnecessary generated files.
- Avoid committing unrelated generated data changes.
- Never discard unrelated user changes.
- Review `git diff` before considering a task complete.

## AI Agent Workflow

Before implementing a task:

1. Inspect the relevant files and existing architecture.
2. Identify dependencies and possible side effects.
3. Explain the proposed implementation.
4. Wait for approval when the task requires significant architectural changes or data migration.

During implementation:

- Make the smallest coherent set of changes.
- Preserve existing working functionality.
- Do not rewrite entire files unnecessarily.
- Do not change unrelated functionality.
- Do not remove existing data without explicit authorization.
- Do not assume a file, function, or test exists without verifying it.

After implementation:

1. Summarize the changes.
2. List the modified files.
3. Explain relevant design decisions.
4. Run appropriate tests.
5. Report test results honestly.
6. Identify any remaining limitations or manual verification steps.

When a test fails, investigate the underlying cause instead of hiding, skipping, or weakening the test.

## Documentation

Update documentation when architecture, data locations, development commands, or application behavior changes.

Keep documentation consistent with the actual repository structure and implementation.
