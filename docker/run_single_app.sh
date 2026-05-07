#!/bin/sh
set -e

if [ -z "$REDIS_URL" ] || [ "$REDIS_URL" = "redis://127.0.0.1:6379/0" ] || [ "$REDIS_URL" = "redis://localhost:6379/0" ]; then
  redis-server --daemonize yes
fi

celery -A config worker --loglevel=info &

exec gunicorn config.wsgi:application --bind 0.0.0.0:${APP_PORT:-8015}
