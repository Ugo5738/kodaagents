#!/bin/sh
set -e

# # Function to wait for PostgreSQL to be ready
# wait_for_postgres() {
#     echo "Waiting for postgres..."
#     while ! nc -z postgres 5432; do
#       sleep 0.1
#     done
#     echo "PostgreSQL started"
# }

# case "$1" in
#     migrate)
#         # Call the wait function before attempting to access the database
#         wait_for_postgres

#         # Run database migrations
#         echo "Running database migrations..."
#         python manage.py migrate --noinput

#         # Populate the database
#         echo "Populating the database..."
#         python manage.py populate_db

#         # Run collectstatic
#         echo "Collecting static files..."
#         python manage.py collectstatic --noinput
#         ;;

#     web)
#         # Wait for migration service to complete. This is handled by docker-compose dependency
#         echo "Starting Daphne server on port ${PORT}..."
#         daphne koda.asgi:application --port ${PORT} --bind 0.0.0.0
#         ;;

#     celery)
#         # Wait for migration service to complete. This is handled by docker-compose dependency
#         echo "Starting Celery worker..."
#         celery -A koda worker --loglevel=info
#         ;;

#     *)
#         echo "Unknown command: $1"
#         exit 1
#         ;;
# esac

# make this script executable
# chmod +x entrypoint.sh

# # Then start your application
exec "$@"