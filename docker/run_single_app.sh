#!/bin/sh
set -e

if [ -z "$REDIS_URL" ] || [ "$REDIS_URL" = "redis://127.0.0.1:6379/0" ] || [ "$REDIS_URL" = "redis://localhost:6379/0" ]; then
  redis-server --bind 127.0.0.1 --port 6379 --protected-mode no --save "" --appendonly no &
  REDIS_HOST="127.0.0.1"
  REDIS_PORT="6379"
else
  REDIS_HOST=$(printf '%s' "$REDIS_URL" | sed -E 's#redis://([^:/]+).*#\1#')
  REDIS_PORT=$(printf '%s' "$REDIS_URL" | sed -E 's#redis://[^:]+:([0-9]+).*#\1#')
fi

for attempt in $(seq 1 30); do
  if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping >/dev/null 2>&1; then
    break
  fi
  if [ "$attempt" -eq 30 ]; then
    echo "Redis is not reachable at $REDIS_HOST:$REDIS_PORT" >&2
    exit 1
  fi
  sleep 1
done

celery -A config worker --loglevel=${CELERY_LOG_LEVEL:-info} --concurrency=${CELERY_CONCURRENCY:-2} &

exec gunicorn config.wsgi:application --bind 0.0.0.0:${APP_PORT:-8015} --timeout ${GUNICORN_TIMEOUT:-120}
