#!/bin/bash
set -e

# Wait for database
wait_for_db() {
    if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
        echo "Waiting for database on $DB_HOST:$DB_PORT..."
        while ! nc -z "$DB_HOST" "$DB_PORT"; do
            sleep 0.5
        done
        echo "Database is available"
    fi
}

wait_for_db

# Apply migrations
echo "Applying database migrations..."
poetry run python manage.py migrate

# Start server based on environment
if [ "$DJANGO_ENV" = "production" ]; then
    echo "Starting Gunicorn server..."
    exec poetry run gunicorn myproject.wsgi:application \
        --bind 0.0.0.0:8000 \
        --workers ${GUNICORN_WORKERS:-3} \
        --worker-class ${GUNICORN_WORKER_CLASS:-sync} \
        --timeout ${GUNICORN_TIMEOUT:-30} \
        --access-logfile - \
        --error-logfile -
else
    echo "Starting development server..."
    exec poetry run python manage.py runserver 0.0.0.0:8000
fi