#!/bin/sh
set -e

python manage.py repair_legacy_schema
python manage.py migrate --noinput
python manage.py seed_initial_data || true
python manage.py collectstatic --noinput

exec "$@"
