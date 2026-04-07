#!/bin/sh
# Startup script for the combined ProteoSurviver container.
# Runs Django database migrations, loads initial fixtures, then starts gunicorn.
set -e

cd /app

echo "==> Running database migrations..."
python manage.py migrate --noinput

echo "==> Loading initial fixtures..."
python manage.py loaddata data/fixtures/initial_datasets.json

echo "==> Starting gunicorn on 0.0.0.0:8080..."
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8080 \
    --workers "${GUNICORN_WORKERS:-2}" \
    --timeout "${GUNICORN_TIMEOUT:-120}"
