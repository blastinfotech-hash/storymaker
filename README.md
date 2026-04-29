# Storymaker

Internal Django app for generating Instagram stories for `BLAST INFO & TECH` using AI text + image generation.

## Current Status
- Project bootstrap is ready.
- Django apps created: `core`, `branding`, `news`, `stories`.
- Environment-based settings are configured.
- Current URL available by default: `/admin/`.
- The story generation flow itself is still to be implemented.

## MVP Goal
Build a VPS-hosted internal panel where you can:
- choose a story type: `news`, `generic`, or `promotional`
- search curated tech news sources when the type is `news`
- generate story copy and visual direction with AI
- review and confirm the concept before image generation
- regenerate the image
- request punctual edits to text or image direction
- download the generated asset
- keep all versions and history saved in the database
- later connect the approved asset to the Instagram Graph API

## Brand Constraint
This project must follow the BLAST INFO & TECH visual identity manual shared in the project session.

Important rule for implementation:
- the BLAST visual manual should be stored as editable app data, not hardcoded forever into prompts

## Stack
- Python `3.12`
- Django `5.2`
- Postgres via `DATABASE_URL`
- Celery + Redis for async jobs
- OpenAI for text/image generation
- RSS ingestion for curated technology news

## Local Setup
1. Create or reuse the virtualenv:
```bash
python3 -m venv .venv
```

2. Install dependencies:
```bash
./.venv/bin/pip install -r requirements.txt
```

3. Create your environment file:
```bash
cp .env.example .env
```

4. Update `.env` with your real values.

5. Run migrations:
```bash
./.venv/bin/python manage.py migrate
```

6. Create an admin user:
```bash
./.venv/bin/python manage.py createsuperuser
```

7. Start the development server:
```bash
./.venv/bin/python manage.py runserver 0.0.0.0:8015
```

8. Open:
```text
http://127.0.0.1:8015/admin/
```

## Environment Variables
Use `.env.example` as the source of truth.

Main variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True` or `False`
- `ALLOWED_HOSTS`: comma-separated hosts
- `CSRF_TRUSTED_ORIGINS`: comma-separated origins with protocol
- `APP_PORT`: safe default is `8015`
- `DATABASE_URL`: use your VPS Postgres URL here
- `REDIS_URL`: Redis connection string for Celery
- `OPENAI_API_KEY`: OpenAI API key
- `OPENAI_TEXT_MODEL`: text model for copy generation
- `OPENAI_IMAGE_MODEL`: image model for visual generation

## Postgres Example
```env
DATABASE_URL=postgresql://postgres:your-password@your-host:5432/storymaker
```

## VPS Port Constraint
Do not use these host ports because they are already occupied by sibling apps:
- `80`
- `8000`
- `8011`
- `8085`
- `8086`
- `8091`
- `8501`

Safe default for this app:
- `8015`

## Suggested App Boundaries
- `core`: shared utilities, base models, common helpers
- `branding`: editable BLAST visual identity, prompt templates, brand rules
- `news`: RSS sources, ingested articles, ranking/filtering
- `stories`: story projects, versions, prompts, images, approvals, publishing state

## Suggested First Implementation Order
1. Create the core models for projects, versions, news sources, news articles, image assets, and brand guides.
2. Register everything in Django admin.
3. Add RSS ingestion from curated hardware/tech sources.
4. Add the text generation service.
5. Add visual-direction generation using the editable BLAST identity guide.
6. Add image generation and regeneration.
7. Add download/export support.
8. Add Instagram publishing later as a separate integration step.

## Verified Commands
```bash
./.venv/bin/python manage.py check
./.venv/bin/python manage.py migrate
./.venv/bin/python manage.py createsuperuser
./.venv/bin/python manage.py runserver 0.0.0.0:8015
```

## Notes
- The project currently falls back to SQLite if `DATABASE_URL` is not set.
- For production, point `DATABASE_URL` to Postgres and set `DEBUG=False`.
- The `.env` file is ignored by git.
