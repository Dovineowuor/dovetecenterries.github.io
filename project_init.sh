# Create the clean_migrations_and_cache.sh file
touch clean_migrations_and_cache.sh

# Add the necessary commands to the script
echo '#!/bin/bash

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
    deactivate
fi

# Check and remove env, venv, and .venv directories
remove_dir_if_exists "env"
remove_dir_if_exists "venv"
remove_dir_if_exists ".venv"

echo "Installing virtualenv..."
python3 -m venv .venv

echo "Activating virtualenv..."
source .venv/bin/activate

echo "Installing requirements..."
pip install -r requirements.txt

echo "Migration cleanup and cache cleanup completed."

echo "Running migrations..."
python manage.py makemigrations
python manage.py migrate

echo "Migration completed."

echo "Cleaning up cache..."
# python manage.py clear_cache

echo "Cache cleanup completed."

echo "Running server..."
python manage.py runserver

echo "Server started."



echo "Done."' > clean_migrations_and_cache.sh

echo "Make the script executable"
chmod +x clean_migrations_and_cache.sh

echo "Created  executable script clean_migrations_and_cache.sh"

echo"Starting Environment Setup"
sleep 3
./clean_migrations_and_cache.sh
