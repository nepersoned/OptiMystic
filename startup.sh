#!/bin/bash
set -e

echo "OptiMystic - Azure App Service Startup Script"

# Navigate to app directory
cd /home/site/wwwroot

# Create virtual environment if it doesn't exist
if [ ! -d "env" ]; then
    echo "Creating virtual environment..."
    python3.11 -m venv env
fi

# Activate virtual environment
source env/bin/activate

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear 2>/dev/null || true

# Run migrations (if database is used in future)
echo "Running migrations..."
python manage.py migrate --noinput 2>/dev/null || true

# Start Gunicorn with proper settings
echo "Starting OptiMystic with Gunicorn..."
gunicorn \
    --workers 4 \
    --worker-class sync \
    --timeout 300 \
    --bind 0.0.0.0:8000 \
    --access-logfile - \
    --error-logfile - \
    optimystic.wsgi:application
