#!/bin/sh
set -e

celery -A config worker --loglevel=info &

exec gunicorn config.wsgi:application --bind 0.0.0.0:${APP_PORT:-8015}
