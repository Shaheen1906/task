#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -o errexit

# Install dependencies (Render already does this in build, so this is optional)
# pip install -r requirements.txt

# Run database migrations
python manage.py migrate --noinput

# Collect static files
python manage.py collectstatic --noinput


# start.sh

# Run one-time command
python manage.py createsuperuser --noinput \
  --username shaheenansari1906@gmail.com \
  --email shaheenansari1906@gmail.com

echo "from django.contrib.auth import get_user_model; \
  User = get_user_model(); \
  user = User.objects.get(username='shaheenansari1906@gmail.com'); \
  user.set_password('adminpass@123'); \
  user.save()" \
  | python manage.py shell


# Optional: create superuser (only runs if user doesn’t exist)
# echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.filter(username='admin').exists() or User.objects.create_superuser('admin', 'admin@example.com', 'adminpass')" | python manage.py shell

# Start Gunicorn server
gunicorn task_management.wsgi:application --bind 0.0.0.0:$PORT

