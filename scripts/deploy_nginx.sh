#!/bin/bash
# Fix Nginx config for GovernexPlus

cat > /etc/nginx/sites-available/governexplus << 'NEOF'
server {
    listen 80;
    server_name 212.47.75.51;

    location / {
        root /opt/governexplus/app/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8000/docs;
        proxy_set_header Host $host;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8000/redoc;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8000/openapi.json;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }

    location /auth/ {
        proxy_pass http://127.0.0.1:8000/auth/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    client_max_body_size 50M;
    gzip on;
    gzip_types text/plain application/json application/javascript text/css;
}
NEOF

nginx -t && systemctl restart nginx
echo "Nginx: $(systemctl is-active nginx)"

systemctl restart governexplus
sleep 5
echo "Backend: $(systemctl is-active governexplus)"
curl -s http://127.0.0.1:8000/health || echo "Backend not responding"
echo ""
echo "---DONE---"
