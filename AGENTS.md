# AGENTS

## Current Shape
- This repo is a root-level Django project. The real entrypoints today are `manage.py`, `config/settings.py`, and `config/urls.py`.
- Local Django apps already created: `core`, `branding`, `news`, `stories`.
- A local virtualenv exists at `.venv/`. Prefer calling tools through `./.venv/bin/...` instead of assuming global `python`, `pip`, or `django-admin` are available.

## Verified Commands
- Run Django management commands with `./.venv/bin/python manage.py <command>`.
- Start the dev server with `./.venv/bin/python manage.py runserver`.
- Use `./.venv/bin/python manage.py check` for the fastest project sanity check.
- Install dependencies with `./.venv/bin/pip install -r requirements.txt`.
- Seed the default RSS sources with `./.venv/bin/python manage.py seed_initial_data`.
- Run the async worker locally with `./.venv/bin/celery -A config worker --loglevel=info`.
- Start the production-style stack with `docker compose up -d --build`.

## Repo Constraints
- This project is being built for a BLAST INFO & TECH story/image generator. Visual-direction work must preserve the BLAST identity rules provided in the session and keep that guidance editable in-app rather than hardcoding it irreversibly.
- VPS host ports shown as already occupied by sibling apps must be treated as unavailable: `80`, `8000`, `8011`, `8085`, `8086`, `8091`, `8501`.
- If you need to expose this app from Docker or another process manager, use a different host port. `8015` is the current safe default chosen during setup.

## What Not To Assume
- `README.md`, `.env.example`, and `requirements.txt` now exist and should stay aligned with real settings and commands.
- `Dockerfile`, `docker-compose.yml`, and `docker/entrypoint.sh` now exist and should stay aligned with the actual deploy flow.
- There is still no verified CI workflow, lint config, formatter config, or test suite. Do not invent repository commands; add them only when you also add the backing config.
- Trust executable config over chat history once additional project files are added. Update this file when the repo gains real build/test/deploy sources of truth.
