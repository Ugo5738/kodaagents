#!/bin/sh

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