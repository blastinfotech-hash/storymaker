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

## VPS Setup
This project now includes a production starter with `Dockerfile` and `docker-compose.yml`.

Use this flow on your VPS.

### 1. Clone the project on the VPS
```bash
git clone <your-repo-url> storymaker
cd storymaker
```

### 2. Create the environment file
```bash
cp .env.example .env
```

### 3. Edit `.env` for production
Minimum recommended values:

```env
SECRET_KEY=put-a-long-random-secret-here
DEBUG=False
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com,https://www.your-domain.com
APP_PORT=8015
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
DATABASE_URL=postgresql://USER:PASSWORD@HOST:5432/DATABASE
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
OPENAI_API_KEY=your-openai-key
```

If your Postgres already exists on the VPS or another server, keep `DATABASE_URL` pointing to that external database.

### 4. Start the containers
```bash
docker compose up -d --build
```

This will start:
- `web`: Django + Gunicorn on host port `8015`
- `worker`: Celery worker
- `redis`: local Redis for async jobs

### 5. Create the Django admin user
```bash
docker compose exec web python manage.py createsuperuser
```

### 6. Open the app directly by port
If you want to test before attaching a domain:

```text
http://YOUR_VPS_IP:8015/admin/
```

### 7. Attach the domain in your VPS panel / reverse proxy
Point your domain to:

```text
http://YOUR_SERVER:8015
```

If you are using Easypanel or another reverse proxy manager, create a domain entry that forwards traffic to host port `8015`.

### 8. Update after changes
```bash
git pull
docker compose up -d --build
```

## Easypanel Fix For `DisallowedHost`
If you see this error:

```text
Invalid HTTP_HOST header
```

your environment is missing the public host used by Easypanel.

Use values like these in the app environment:

```env
DEBUG=False
ALLOWED_HOSTS=blast-storymaker.0ksds9.easypanel.host
CSRF_TRUSTED_ORIGINS=https://blast-storymaker.0ksds9.easypanel.host
USE_X_FORWARDED_HOST=True
USE_X_FORWARDED_PORT=True
SESSION_COOKIE_SECURE=True
CSRF_COOKIE_SECURE=True
```

If you also attach a custom domain, include both hosts:

```env
ALLOWED_HOSTS=blast-storymaker.0ksds9.easypanel.host,seu-dominio.com,www.seu-dominio.com
CSRF_TRUSTED_ORIGINS=https://blast-storymaker.0ksds9.easypanel.host,https://seu-dominio.com,https://www.seu-dominio.com
```

Then restart the app:

```bash
docker compose up -d --build
```

## VPS Quick Command List
```bash
cp .env.example .env
nano .env
docker compose up -d --build
docker compose exec web python manage.py createsuperuser
docker compose logs -f web
```

## VPS Notes
- `docker/entrypoint.sh` runs `migrate` and `collectstatic` automatically on web container start.
- The app listens on host port `8015` because your other ports are already occupied.
- `DATABASE_URL` should use your real Postgres connection string.
- If your reverse proxy serves HTTPS, `CSRF_TRUSTED_ORIGINS` must use `https://...`.
- `REDIS_URL=redis://redis:6379/0` is correct when using the included compose setup.

## Environment Variables
Use `.env.example` as the source of truth.

Main variables:
- `SECRET_KEY`: Django secret key
- `DEBUG`: `True` or `False`
- `ALLOWED_HOSTS`: comma-separated hosts
- `CSRF_TRUSTED_ORIGINS`: comma-separated origins with protocol
- `APP_PORT`: safe default is `8015`
- `USE_X_FORWARDED_HOST`: keep `True` behind Easypanel or another reverse proxy
- `USE_X_FORWARDED_PORT`: keep `True` behind Easypanel or another reverse proxy
- `SESSION_COOKIE_SECURE`: use `True` in production with HTTPS
- `CSRF_COOKIE_SECURE`: use `True` in production with HTTPS
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
