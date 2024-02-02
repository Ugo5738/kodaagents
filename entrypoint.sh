#!/bin/sh

# Run collectstatic
python manage.py collectstatic --noinput

# Then start your application
exec "$@"

# make this script executable
# chmod +x entrypoint.sh