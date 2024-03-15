#!/bin/sh

# Function to wait for PostgreSQL to be ready
wait_for_postgres() {
    echo "Waiting for postgres..."
    while ! nc -z postgres 5432; do
      sleep 0.1
    done
    echo "PostgreSQL started"
}

# Call the wait function before attempting to access the database
wait_for_postgres

# Run database migrations
python manage.py migrate --noinput

# Populate the database
python manage.py populate_db

# Run collectstatic
python manage.py collectstatic --noinput

# Then start your application
exec "$@"

# make this script executable
# chmod +x entrypoint.sh