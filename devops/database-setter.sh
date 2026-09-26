#!/bin/bash

# filepath: /home/trinityschool/LMS/database-setter.sh

# Start PostgreSQL if not running
if ! systemctl is-active --quiet postgresql; then
    echo "Starting PostgreSQL..."
    sudo -u postgres /usr/lib/postgresql/16/bin/pg_ctl -D /var/lib/postgresql/16/main start
fi
read -p "Select environment (dev, production, staging): " env
read -p "Select database (postgresql, mariadb, mongo): " db_choice
read -p "Enter database name: " db_name
read -p "Enter database user: " db_user
read -sp "Enter database password: " db_password
echo

create_postgresql_db() {
    sudo -u postgres psql -c "CREATE DATABASE $db_name;" 2>/dev/null
    sudo -u postgres psql -c "ALTER USER $db_user WITH PASSWORD '$db_password';"
    sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $db_name TO $db_user;"
}

create_mariadb_db() {
    sudo mysql -e "CREATE DATABASE $db_name;" 2>/dev/null
    sudo mysql -e "CREATE USER '$db_user'@'localhost' IDENTIFIED BY '$db_password';"
    sudo mysql -e "GRANT ALL PRIVILEGES ON $db_name.* TO '$db_user'@'localhost';"
    sudo mysql -e "FLUSH PRIVILEGES;"
}

create_mongo_db() {
    mongo --eval "db = db.getSiblingDB('$db_name'); db.createUser({user: '$db_user', pwd: '$db_password', roles: [{role: 'readWrite', db: '$db_name'}]});"
}

case $db_choice in
    postgresql)
        create_postgresql_db
        DB_PORT=5432
        ;;
    mariadb)
        create_mariadb_db
        DB_PORT=3306
        ;;
    mongo)
        create_mongo_db
        DB_PORT=27017
        ;;
    *)
        echo "Invalid database choice"
        exit 1
        ;;
esac

# Update or append database variables in .env file
if [ -f ".env" ]; then
    # Update existing database variables
    sed -i "/^ENV=/c\ENV=$env" .env
    sed -i "/^DB_NAME=/c\DB_NAME=$db_name" .env
    sed -i "/^DB_USER=/c\DB_USER=$db_user" .env
    sed -i "/^DB_PASSWORD=/c\DB_PASSWORD=$db_password" .env
    sed -i "/^DB_HOST=/c\DB_HOST=localhost" .env
    sed -i "/^DB_PORT=/c\DB_PORT=$DB_PORT" .env
else
    # Create new .env file with database variables
    cat <<EOL >> .env
ENV=$env
DB_NAME=$db_name
DB_USER=$db_user
DB_PASSWORD=$db_password
DB_HOST=localhost
DB_PORT=$DB_PORT
EOL
fi

echo "Database setup complete and .env file created."
