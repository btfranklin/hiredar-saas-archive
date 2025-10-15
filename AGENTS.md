# Repository Guidelines

## Project Structure & Module Organization
- Django project settings live in `hiredar/`, while domain-specific apps sit under `apps/` (`authentication`, `job_seekers`, `recruiters`, `matching`, `resume_processing`, etc.).
- Shared LLM tooling is in `hiredar/llm/`, and reusable scripts live in `scripts/` for linting and import hygiene.
- Front-end assets start in `assets/` and are compiled into `static/`; collected runtime files land in `staticfiles/` and uploads in `media/`.
- Product documentation and decision records reside in `docs/`—use them for architectural context before large changes.

## Build, Test, and Development Commands
- `pdm install --group dev` — install Python dependencies plus lint/test extras.
- `python manage.py migrate` — apply database migrations before running the app.
- `pdm run pytest` — execute the Django/pytest suite in `apps/` and `hiredar/llm/tests`.
- `./scripts/lint.py` — run pylint with the project’s custom plugins; pair with `./scripts/fix_imports.py --all` as needed.
- `npm run build:css` — rebuild Tailwind CSS from `assets/css/tailwind.css` into `static/css/tailwind.css`.

## Coding Style & Naming Conventions
- Use 4-space indentation, type-annotate every function, and prefer native types (`list`, `dict`) with `| None` for optionals.
- Keep Django apps modular: new views, services, and tasks belong in the matching subpackages that already exist in each app.
- Follow template naming of `apps/<app>/templates/<app>/**` and keep HTMX partials in the same tree for clarity.
- Run the linter locally before committing; unresolved pylint errors will block CI.
- Use American English spelling in code comments, docstrings, and documentation (e.g., "specialized", "behavior").

## Testing Guidelines
- Tests belong next to their modules (e.g., `apps/job_seekers/tests/`) with filenames starting `test_`, classes `Test*`, and functions `test_*` per `pyproject.toml`.
- Cover new Celery tasks, LLM parsers, and services with deterministic fixtures; mock external APIs (OpenAI, Pinecone) to keep runs offline.
- When adding migrations or async flows, include regression tests demonstrating both success and failure paths.
- Execute the test suite with `pdm run pytest`; this command is available and should be used for local validation.

## Commit & Pull Request Guidelines
- Git history favors concise, sentence-case summaries that explain both the change and the intent (e.g., `Refactor reasoning effort retrieval in LLM processing services …`).
- Keep commits scoped; mention affected app names when it helps reviewers ("Update recruiter credits purchase flow").
- Pull requests should describe the change set, note migrations, list manual or automated test results, and attach UI screenshots or logs when behavior shifts.
- Link to relevant issues or docs pages (`docs/APP_STRUCTURE.md`, etc.) to help reviewers trace context quickly.
