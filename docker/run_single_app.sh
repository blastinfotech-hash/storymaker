#!/bin/sh
set -e

if [ -z "$REDIS_URL" ] || [ "$REDIS_URL" = "redis://127.0.0.1:6379/0" ] || [ "$REDIS_URL" = "redis://localhost:6379/0" ]; then
  redis-server --bind 127.0.0.1 --port 6379 --protected-mode no --save "" --appendonly no &
  sleep 2
fi

celery -A config worker --loglevel=info &

exec gunicorn config.wsgi:application --bind 0.0.0.0:${APP_PORT:-8015}
