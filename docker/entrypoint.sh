#!/bin/sh
set -e

python manage.py migrate --noinput
python manage.py seed_initial_data
python manage.py collectstatic --noinput

exec "$@"
