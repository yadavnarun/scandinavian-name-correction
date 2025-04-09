#!/bin/bash
set -e

echo "Starting application..."

# Debug directory structure
echo "Current directory: $(pwd)"
echo "Directory contents:"
ls -la

# Make sure the current directory is in Python path
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Create a temporary settings file that will be loaded by Django
cat > /app/fly_settings_override.py << EOF
from name_service.settings import *

# Allow all hosts to connect
ALLOWED_HOSTS = ['*']

# Make sure debug is off in production
DEBUG = False

# Display the applied settings
print("ALLOWED_HOSTS =", ALLOWED_HOSTS)
EOF

# Set the Django settings module to our override file
export DJANGO_SETTINGS_MODULE=fly_settings_override

# Verify we can import the Django project
python -c "import name_service" || {
  echo "ERROR: Could not import 'name_service' module!"
  echo "Project structure:"
  find . -type f -name "*.py" | sort
  exit 1
}

# Apply database migrations if needed
python manage.py migrate --noinput || echo "Could not run migrations"

# Create a simple health check handler
cat > /app/health_check.py << EOF
def health_check_handler(environ, start_response):
    status = '200 OK'
    headers = [('Content-type', 'text/plain')]
    start_response(status, headers)
    return [b'OK']
EOF

# Start Gunicorn with error logging and the health check app
echo "Starting Gunicorn with name_service.wsgi and health check..."
exec gunicorn --bind :8000 --workers 1 --log-level debug --error-logfile - --access-logfile - \
    --env DJANGO_SETTINGS_MODULE=fly_settings_override \
    --pythonpath /app \
    name_service.wsgi:application
