# Create Gunicorn configuration
cat > gunicorn_config.py << 'EOL'
import multiprocessing

bind = "unix:/run/gunicorn.sock"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "gthread"
threads = 4
timeout = 120
keepalive = 5
max_requests = 1000
max_requests_jitter = 50
accesslog = "/var/log/zoobee/gunicorn_access.log"
errorlog = "/var/log/zoobee/gunicorn_error.log"
loglevel = "warning"
EOL

# Create Nginx configuration
sudo bash -c 'cat > /etc/nginx/sites-available/zobeestores << EOL
server {
    listen 80;
    server_name zobeestores.com [www.zobeestores.com](www.zobeestores.com);
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name zobeestores.com [www.zobeestores.com](www.zobeestores.com);

    ssl_certificate /etc/letsencrypt/live/zobeestores.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/zobeestores.com/privkey.pem;

    location = /static/icons/favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias /home/dovetecenterprises/Work/Zoobee-Cart/staticfiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location /media/ {
        alias /home/dovetecenterprises/Work/Zoobee-Cart/mediafiles/;
        expires 30d;
        add_header Cache-Control "public, no-transform";
    }

    location / {
        proxy_set_header Host $http_host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_pass http://unix:/run/gunicorn.sock;
    }
}
EOL'

# Create systemd service
sudo bash -c 'cat > /etc/systemd/system/zoobee.service << EOL
[Unit]
Description=Zoobee Cart Django Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/home/dovetecenterprises/Work/Zoobee-Cart
Environment="PATH=/home/dovetecenterprises/Work/Zoobee-Cart/venv/bin"
ExecStart=/home/dovetecenterprises/Work/Zoobee-Cart/venv/bin/gunicorn \
    --config gunicorn_config.py \
    zoobee.wsgi:application

[Install]
WantedBy=multi-user.target
EOL'

# Install required packages
pip install gunicorn redis

# Set up log directory
sudo mkdir -p /var/log/zoobee
sudo chown -R www-data:www-data /var/log/zoobee

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Create maintenance script
cat > maintenance.sh << 'EOL'
#!/bin/bash

# Backup database
mysqldump -u zobenqxh_Zobee -p zobenqxh_zobeestores > backup_$(date +%Y%m%d).sql

# Clear sessions
python manage.py clearsessions

# Clear expired tokens
python manage.py cleanup_expired_tokens

# Check for security updates
sudo apt update
sudo apt list --upgradable

# Rotate logs
sudo logrotate /etc/logrotate.d/zoobee
EOL

chmod +x maintenance.sh

# Enable and start services
sudo systemctl daemon-reload
sudo systemctl enable zoobee
sudo systemctl start zoobee

# Create symbolic link for Nginx configuration
sudo ln -s /etc/nginx/sites-available/zobeestores /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# Test the configuration
python manage.py check --deploy