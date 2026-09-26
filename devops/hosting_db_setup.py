#!/usr/bin/env python
"""
Database setup script for Dovetec Enterprises project.
This script will check the database connection and create necessary tables.
"""
import os
import sys
import django
from django.db import connections
from django.db.utils import OperationalError

# Set up Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'dovetecenterprises.settings')
django.setup()

def check_db_connection():
    """Check if the database connection is working."""
    try:
        connection = connections['default']
        connection.cursor()
        print("✅ Database connection successful!")
        return True
    except OperationalError as e:
        print(f"❌ Database connection failed: {e}")
        return False

def print_db_settings():
    """Print the current database settings."""
    from django.conf import settings
    db_settings = settings.DATABASES['default']
    
    # Hide password
    db_settings_safe = db_settings.copy()
    if 'PASSWORD' in db_settings_safe:
        db_settings_safe['PASSWORD'] = '********'
    
    print("\nCurrent Database Settings:")
    for key, value in db_settings_safe.items():
        print(f"  {key}: {value}")

def main():
    """Main function to check database connection and run migrations."""
    print("\n=== Dovetec Enterprises Database Setup ===\n")
    
    print_db_settings()
    
    if check_db_connection():
        print("\nRunning migrations...")
        from django.core.management import call_command
        call_command('migrate')
        print("\n✅ Database setup complete!")
    else:
        print("\n❌ Cannot proceed with migrations due to connection error.")
        print("\nPossible solutions:")
        print("1. Make sure MySQL server is running")
        print("2. Verify that the database user exists with correct permissions")
        print("3. Check that the database exists")
        print("4. Verify the password is correct")
        print("\nTo create the database and user, run the following SQL commands:")
        print("""
CREATE DATABASE IF NOT EXISTS dovetec_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'dovetec_user'@'localhost' IDENTIFIED BY 'YourSecurePasswordHere';
GRANT ALL PRIVILEGES ON dovetec_db.* TO 'dovetec_user'@'localhost';
FLUSH PRIVILEGES;
        """)

if __name__ == "__main__":
    main()
