#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status

echo "Cleaning up migration files (except __init__.py)..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

echo "Cleaning up .pyc files..."
find . -path "*/migrations/*.pyc" -delete

echo "Cleaning up __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -r {} +

echo "Cleaning up cache directories, except __init__.py..., migrations done."

echo "Cleaning up virtual environment directories..."

# Check if PostgreSQL is running
if ! systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL..."
    sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main start
else
    echo "PostgreSQL is already running"
fi
# Setup Database
if [ -f ".env" ]; then
    read -p "An .env file already exists. Do you want to update it? (y/n): " update_env
    if [ "$update_env" = "y" ]; then
        ./devops/database-setter.sh
    else
        echo "Skipping database setup. Using existing .env configuration."
    fi
else
    ./devops/database-setter.sh
fi

set -e  # Exit immediately if a command exits with a non-zero status

echo "Cleaning up migration files (except __init__.py)..."
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

echo "Cleaning up .pyc files..."
find . -path "*/migrations/*.pyc" -delete

echo "Cleaning up __pycache__ directories..."
find . -type d -name "__pycache__" -exec rm -r {} +

echo "Cleaning up virtual environment directories..."

# Function to remove a directory if it exists
remove_dir_if_exists() {
    if [[ -d "$1" ]]; then
        rm -rf "$1"
        echo "$1 directory removed."
    else
        echo "$1 directory does not exist."
    fi
}

# Deactivate the virtual environment if active
if [[ -n "$VIRTUAL_ENV" ]]; then
    if command -v deactivate &> /dev/null; then
        deactivate
    else
        echo "No virtual environment to deactivate."
    fi
fi

# Check and remove env, venv, and .venv directories
remove_dir_if_exists "env"
remove_dir_if_exists "venv"
remove_dir_if_exists ".venv"

echo "Installing virtualenv..."
python3 -m virtualenv .venv

echo "Activating virtualenv..."
source .venv/bin/activate


# Clean Reinstall Django
echo "Clean-Reinstalling Django..."
pip uninstall -y Django
pip install --upgrade Django

echo "Installing requirements..."
pip install --upgrade pip
pip install --upgrade -r requirements.txt --upgrade

echo "Migration cleanup and cache cleanup completed."

echo "Running migrations..."
python manage.py createcachetable
python manage.py makemigrations
python manage.py migrate

echo "Migration completed."
echo "Listing all superusers..."
python manage.py shell <<EOF
from django.contrib.auth import get_user_model
from django.contrib.auth.models import User
from django.conf import settings
import os
import secrets
User = get_user_model()
superusers = User.objects.filter(is_superuser=True)
if superusers.count() == 0:
    print("No superusers exist. Creating admin user.")
    username = os.environ.get('DJANGO_SUPERUSER_USERNAME', 'admin')
    email = os.environ.get('DJANGO_SUPERUSER_EMAIL', 'admin@example.com')
    password = os.environ.get('DJANGO_SUPERUSER_PASSWORD') or secrets.token_urlsafe(32)
    User.objects.create_superuser(email=email, password=password, username=username)
    if settings.DEBUG:
        print(f"Superuser created with password: {password}")
    else:
        print("Superuser created with secure password.")
else:
    print(f"\nFound {superusers.count()} superuser(s):")
    for superuser in superusers:
        print("\n-------------------")
        print(f"Email: {superuser.email}")
        print(f"Username: {superuser.username}")
        print(f"Last Login: {superuser.last_login}")
        print(f"Date Joined: {superuser.date_joined}")
        print(f"Is Active: {superuser.is_active}")
        if settings.DEBUG:
            try:
                raw_password = os.environ.get(f'DJANGO_SUPERUSER_PASSWORD_{superuser.username}')
                if raw_password:
                    print(f"Password (from env): {raw_password}")
            except:
                pass
EOF

echo "Cleaning up cache..."
python manage.py clear_cache
python manage.py clean_pyc

echo "Cache cleanup completed."

# Check and create certificates if they don't exist
if [ -f "cert.pem" ] && [ -f "key.pem" ]; then
    echo "SSL certificates already exist, skipping creation..."
else
    echo "Creating SSL certificates..."
    openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem -days 365 -nodes
fi

echo "Running server..."
python manage.py runserver_plus --cert-file cert.pem --key-file key.pem


echo "Done."
