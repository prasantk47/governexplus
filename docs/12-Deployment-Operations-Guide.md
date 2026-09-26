# GovernexPlus — Deployment & Operations Guide

**Version:** 2.0
**Applies to:** GovernexPlus 2.x
**Last updated:** 2026-09-06

---

## Table of Contents

1. [Deployment Options](#1-deployment-options)
2. [Docker Setup](#2-docker-setup)
3. [Kubernetes Setup](#3-kubernetes-setup)
4. [Database Setup](#4-database-setup)
5. [Reverse Proxy](#5-reverse-proxy)
6. [Security Hardening](#6-security-hardening)
7. [Monitoring & Observability](#7-monitoring--observability)
8. [Performance Tuning](#8-performance-tuning)
9. [Backup & Disaster Recovery](#9-backup--disaster-recovery)
10. [Upgrade Procedures](#10-upgrade-procedures)

---

## 1. Deployment Options

GovernexPlus supports four deployment topologies. Choose based on your organization's infrastructure maturity, compliance requirements, and operational preferences.

| Topology | Recommended For | HA | Scalability | Ops Complexity |
|---|---|:---:|:---:|:---:|
| Docker Compose (dev) | Local development, demos, evaluations | No | Single host | Low |
| Docker Compose (production) | Small-to-medium deployments, single-server production | Limited | Vertical only | Low–Medium |
| Kubernetes | Enterprise production, multi-tenant SaaS | Yes | Horizontal | High |
| Bare metal / VM | Air-gapped environments, regulated industries with strict virtualization policies | Manual | Manual | High |

### 1.1 Port Reference

| Service | Internal Port | External Port (default) |
|---|---|---|
| FastAPI backend | 8000 | 8000 (behind proxy) |
| React frontend (dev) | 5173 | 5173 |
| Nginx (production) | 80/443 | 80/443 |
| PostgreSQL | 5432 | 5432 (internal only) |
| Redis (rate limiting) | 6379 | Not exposed externally |
| Prometheus | 9090 | Internal only |
| Grafana | 3000 | 3000 (admin access) |

---

## 2. Docker Setup

### 2.1 Dockerfile.prod (Multi-Stage Build)

The production Dockerfile uses a three-stage build:

**Stage 1 — Frontend Build:**
```dockerfile
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci --production=false
COPY frontend/ .
RUN npm run build
```

**Stage 2 — Python Dependencies:**
```dockerfile
FROM python:3.12-slim AS python-deps
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt
```

**Stage 3 — Production Image:**
```dockerfile
FROM python:3.12-slim AS production
WORKDIR /app

# Copy Python dependencies
COPY --from=python-deps /root/.local /root/.local

# Copy application code
COPY . .

# Copy built frontend
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# Copy NWRFC SDK (if SAP connectivity required)
# COPY --from=nwrfc-build /usr/local/sap/nwrfcsdk /usr/local/sap/nwrfcsdk
# ENV SAPNWRFC_HOME=/usr/local/sap/nwrfcsdk
# ENV LD_LIBRARY_PATH=/usr/local/sap/nwrfcsdk/lib:$LD_LIBRARY_PATH

ENV PATH=/root/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["gunicorn", "api.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--keep-alive", "5"]
```

### 2.2 docker-compose.prod.yml

```yaml
version: "3.9"

services:
  db:
    image: postgres:16-alpine
    restart: unless-stopped
    environment:
      POSTGRES_DB: governex
      POSTGRES_USER: grc
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init_db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U grc -d governex"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    restart: unless-stopped
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    networks:
      - backend

  backend:
    image: governexplus:${VERSION:-latest}
    build:
      context: .
      dockerfile: Dockerfile.prod
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    env_file: .env.production
    environment:
      DATABASE_URL: postgresql+asyncpg://grc:${DB_PASSWORD}@db:5432/governex
      RATE_LIMIT_STORAGE: redis://:${REDIS_PASSWORD}@redis:6379
    volumes:
      - ./logs:/app/logs
      - ./uploads:/app/uploads
      - ./exports:/app/exports
    networks:
      - backend
      - frontend
    labels:
      - "com.governex.service=backend"

  nginx:
    image: nginx:1.25-alpine
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - ./frontend/dist:/usr/share/nginx/html:ro
      - ./ssl:/etc/nginx/ssl:ro
      - nginx_cache:/var/cache/nginx
    depends_on:
      - backend
    networks:
      - frontend
    labels:
      - "com.governex.service=nginx"

volumes:
  postgres_data:
  redis_data:
  nginx_cache:

networks:
  backend:
    internal: true
  frontend:
```

### 2.3 Environment Variable Injection

Production environment variables are stored in `.env.production` (not committed to source control) and injected at container startup:

```bash
# Generate a strong JWT secret
JWT_SECRET=$(openssl rand -hex 64)

# Write production env file
cat > .env.production <<EOF
JWT_SECRET=${JWT_SECRET}
JWT_ALGORITHM=HS256
JWT_EXPIRY_HOURS=8
DATABASE_URL=postgresql+asyncpg://grc:${DB_PASSWORD}@db:5432/governex
CORS_ORIGINS=https://grc.acme.com
HTTPS_ENABLED=true
LOG_LEVEL=WARNING
LOG_FORMAT=json
SAP_USE_MOCK=false
SAP_HOST=sap-ecc.acme.com
# ... remaining vars
EOF

chmod 600 .env.production
```

### 2.4 Volume Mounts

| Mount | Purpose | Backup Required |
|---|---|---|
| `postgres_data` | PostgreSQL data directory | Yes — see Section 9 |
| `./logs` | Application and access logs | Yes (30-day rotation) |
| `./uploads` | User-uploaded documents and evidence files | Yes |
| `./exports` | Generated PDF/XLSX report files | No (regenerable) |
| `./ssl` | TLS certificates and private keys | Yes (separate from DB backup) |

---

## 3. Kubernetes Setup

### 3.1 Namespace and Secrets

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: governex
  labels:
    app: governexplus
---
# secret.yaml (apply with: kubectl create secret generic governex-secrets ...)
apiVersion: v1
kind: Secret
metadata:
  name: governex-secrets
  namespace: governex
type: Opaque
stringData:
  jwt-secret: "<64-char-hex-string>"
  db-password: "<postgres-password>"
  redis-password: "<redis-password>"
  sap-password: "<sap-rfc-password>"
```

### 3.2 ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: governex-config
  namespace: governex
data:
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRY_HOURS: "8"
  HTTPS_ENABLED: "true"
  LOG_LEVEL: "WARNING"
  LOG_FORMAT: "json"
  CORS_ORIGINS: "https://grc.acme.com"
  DEFAULT_TENANT_ID: "acme-corp"
  RATE_LIMIT_DEFAULT: "60/minute"
  RATE_LIMIT_AUTH: "10/minute"
  AUTO_MIGRATE: "false"
```

### 3.3 Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: governex-backend
  namespace: governex
  labels:
    app: governex-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: governex-backend
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1
      maxUnavailable: 0
  template:
    metadata:
      labels:
        app: governex-backend
    spec:
      terminationGracePeriodSeconds: 60
      containers:
        - name: backend
          image: your-registry/governexplus:2.0.0
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: governex-config
          env:
            - name: JWT_SECRET
              valueFrom:
                secretKeyRef:
                  name: governex-secrets
                  key: jwt-secret
            - name: DATABASE_URL
              value: "postgresql+asyncpg://grc:$(DB_PASSWORD)@postgres-svc:5432/governex"
            - name: DB_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: governex-secrets
                  key: db-password
            - name: RATE_LIMIT_STORAGE
              value: "redis://:$(REDIS_PASSWORD)@redis-svc:6379"
            - name: REDIS_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: governex-secrets
                  key: redis-password
          resources:
            requests:
              cpu: "500m"
              memory: "512Mi"
            limits:
              cpu: "2000m"
              memory: "2Gi"
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 15
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 10
            failureThreshold: 2
          volumeMounts:
            - name: uploads
              mountPath: /app/uploads
            - name: exports
              mountPath: /app/exports
      volumes:
        - name: uploads
          persistentVolumeClaim:
            claimName: governex-uploads-pvc
        - name: exports
          persistentVolumeClaim:
            claimName: governex-exports-pvc
```

### 3.4 Service and Ingress

```yaml
apiVersion: v1
kind: Service
metadata:
  name: governex-backend-svc
  namespace: governex
spec:
  selector:
    app: governex-backend
  ports:
    - port: 8000
      targetPort: 8000
  type: ClusterIP
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: governex-ingress
  namespace: governex
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - grc.acme.com
      secretName: governex-tls
  rules:
    - host: grc.acme.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: governex-backend-svc
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: governex-frontend-svc
                port:
                  number: 80
```

### 3.5 Horizontal Pod Autoscaling

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: governex-backend-hpa
  namespace: governex
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: governex-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

### 3.6 PersistentVolumeClaims

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: governex-uploads-pvc
  namespace: governex
spec:
  accessModes:
    - ReadWriteMany
  storageClassName: nfs-client
  resources:
    requests:
      storage: 50Gi
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: governex
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 100Gi
```

---

## 4. Database Setup

### 4.1 PostgreSQL Configuration

Recommended PostgreSQL 16 configuration (`postgresql.conf`) for a GovernexPlus production deployment on a server with 16 GB RAM:

```ini
# Connections
max_connections = 200
superuser_reserved_connections = 5

# Memory
shared_buffers = 4GB              # 25% of RAM
effective_cache_size = 12GB       # 75% of RAM
work_mem = 64MB                   # per-sort/hash operation
maintenance_work_mem = 1GB

# WAL
wal_level = replica
max_wal_senders = 5
wal_buffers = 64MB
checkpoint_completion_target = 0.9
checkpoint_timeout = 10min

# Query planner
random_page_cost = 1.1            # SSD-tuned
effective_io_concurrency = 200    # SSD

# Logging
log_min_duration_statement = 1000  # Log queries over 1 second
log_line_prefix = '%t [%p]: [%l-1] db=%d,user=%u '
log_checkpoints = on
log_connections = on
log_disconnections = on
log_lock_waits = on

# Performance
default_statistics_target = 100
```

### 4.2 Connection Pooling with PgBouncer

For production Kubernetes deployments, run PgBouncer between the application and PostgreSQL to handle connection multiplexing:

```ini
# pgbouncer.ini
[databases]
governex = host=postgres-svc port=5432 dbname=governex

[pgbouncer]
listen_port = 6432
listen_addr = *
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
max_client_conn = 500
default_pool_size = 25
min_pool_size = 5
reserve_pool_size = 10
server_idle_timeout = 600
```

Update `DATABASE_URL` to point to PgBouncer: `postgresql+asyncpg://grc:password@pgbouncer-svc:6432/governex`.

### 4.3 Alembic Migration Commands

```bash
# Apply all pending migrations (production — run before deployment)
alembic upgrade head

# Apply one specific migration
alembic upgrade <revision_id>

# Show current revision
alembic current

# Show migration history
alembic history --verbose

# Downgrade one revision
alembic downgrade -1

# Downgrade to specific revision
alembic downgrade <revision_id>

# Generate a new migration (after model changes)
alembic revision --autogenerate -m "description_of_change"

# Validate migration files without running them
alembic check
```

### 4.4 Backup and Restore Procedures

**Daily automated backup:**

```bash
#!/bin/bash
# /etc/cron.daily/governex-backup

BACKUP_DIR=/backups/governex
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="${BACKUP_DIR}/governex_${TIMESTAMP}.pgdump"

# Create compressed custom-format backup
pg_dump \
  --host=localhost \
  --port=5432 \
  --username=grc \
  --format=custom \
  --compress=9 \
  --file="${BACKUP_FILE}" \
  governex

# Verify backup integrity
pg_restore --list "${BACKUP_FILE}" > /dev/null && \
  echo "Backup verified: ${BACKUP_FILE}" || \
  echo "ERROR: Backup verification failed" >&2

# Retain 30 days of daily backups
find "${BACKUP_DIR}" -name "*.pgdump" -mtime +30 -delete

# Copy to remote storage
aws s3 cp "${BACKUP_FILE}" "s3://acme-grc-backups/db/${TIMESTAMP}.pgdump"
```

**Restore procedure:**

```bash
# 1. Stop the GovernexPlus application
docker-compose -f docker-compose.prod.yml stop backend

# 2. Drop and recreate the database
psql -h localhost -U postgres -c "DROP DATABASE IF EXISTS governex;"
psql -h localhost -U postgres -c "CREATE DATABASE governex OWNER grc;"

# 3. Restore from backup
pg_restore \
  --host=localhost \
  --port=5432 \
  --username=grc \
  --dbname=governex \
  --verbose \
  /backups/governex/governex_20260901_020000.pgdump

# 4. Run any pending migrations
alembic upgrade head

# 5. Restart the application
docker-compose -f docker-compose.prod.yml start backend
```

### 4.5 SQLite to PostgreSQL Migration

For environments migrating from SQLite (development) to PostgreSQL (production):

```bash
# 1. Export SQLite data using pgloader
pgloader sqlite:///./grc_platform.db \
  postgresql://grc:password@localhost/governex

# 2. Verify row counts
psql -U grc -d governex -c "
  SELECT table_name, (SELECT COUNT(*) FROM information_schema.tables WHERE table_name = t.table_name)
  FROM information_schema.tables t WHERE table_schema = 'public';"

# 3. Run Alembic stamp to mark current revision
alembic stamp head

# 4. Update DATABASE_URL and restart
```

---

## 5. Reverse Proxy

### 5.1 Nginx Configuration

```nginx
# /etc/nginx/conf.d/governex.conf

upstream governex_backend {
    server backend:8000;
    keepalive 64;
}

# HTTP — redirect to HTTPS
server {
    listen 80;
    server_name grc.acme.com;
    return 301 https://$host$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name grc.acme.com;

    # TLS configuration
    ssl_certificate     /etc/nginx/ssl/fullchain.pem;
    ssl_certificate_key /etc/nginx/ssl/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_stapling        on;
    ssl_stapling_verify on;

    # Security headers
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' wss://grc.acme.com;" always;
    add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;

    # Request size limits
    client_max_body_size 50M;
    client_body_buffer_size 128k;

    # Nginx rate limiting
    limit_req_zone $binary_remote_addr zone=auth:10m rate=10r/m;
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;

    # Static frontend
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1h;
        add_header Cache-Control "public, no-transform";
    }

    # API proxy
    location /api/ {
        limit_req zone=api burst=20 nodelay;

        proxy_pass http://governex_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 10s;
        proxy_send_timeout    120s;
        proxy_read_timeout    120s;

        # Remove any user-injected identity headers (security hardening)
        proxy_set_header X-User-ID "";
        proxy_set_header X-User-Roles "";
        proxy_set_header X-Is-Admin "";
    }

    # Auth endpoints — stricter rate limit
    location /api/v1/auth/ {
        limit_req zone=auth burst=5 nodelay;

        proxy_pass http://governex_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_set_header X-User-ID "";
        proxy_set_header X-User-Roles "";
        proxy_set_header X-Is-Admin "";
    }

    # WebSocket support for live session monitoring
    location /api/v1/firefighter/ws/ {
        proxy_pass http://governex_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 3600s;
    }

    # Health check (no rate limit, no auth)
    location /health {
        proxy_pass http://governex_backend;
        access_log off;
    }
}
```

### 5.2 SSL/TLS Certificate Setup

**Let's Encrypt (Certbot):**
```bash
certbot certonly --nginx \
  --email admin@acme.com \
  --agree-tos \
  --no-eff-email \
  -d grc.acme.com

# Auto-renewal (add to crontab)
0 3 * * * certbot renew --quiet --post-hook "nginx -s reload"
```

**Self-signed certificate (for internal/air-gapped deployments):**
```bash
openssl req -x509 -nodes -days 3650 -newkey rsa:4096 \
  -keyout /etc/nginx/ssl/privkey.pem \
  -out /etc/nginx/ssl/fullchain.pem \
  -subj "/C=US/O=ACME Corp/CN=grc.acme.com" \
  -addext "subjectAltName=DNS:grc.acme.com,IP:10.0.1.50"
```

---

## 6. Security Hardening

### 6.1 JWT Secret Rotation Procedure

JWT secrets should be rotated at least annually or immediately upon suspected compromise.

```bash
# 1. Generate a new secret
NEW_SECRET=$(openssl rand -hex 64)

# 2. Update the environment (rolling approach: support old + new for 1 hour)
# Set JWT_SECRET_PREVIOUS=<current_secret> and JWT_SECRET=<new_secret>
# The auth middleware verifies against both during the rotation window.

# 3. Update the secret in your secrets manager
aws secretsmanager update-secret \
  --secret-id governex/jwt-secret \
  --secret-string "${NEW_SECRET}"

# 4. Deploy the updated configuration (rolling restart in Kubernetes)
kubectl rollout restart deployment/governex-backend -n governex

# 5. Monitor for authentication errors during the rollout
kubectl logs -l app=governex-backend -n governex -f | grep "JWT"

# 6. After all pods are restarted, remove JWT_SECRET_PREVIOUS
# All existing tokens signed with the old secret will expire within JWT_EXPIRY_HOURS.
# Users will need to log in again after the old tokens expire.
```

### 6.2 CORS Lockdown

Never use wildcard CORS origins in production. The `CORS_ORIGINS` environment variable must list only exact, known origins:

```env
# CORRECT — exact origins only
CORS_ORIGINS=https://grc.acme.com,https://grc-staging.acme.com

# WRONG — never do this in production
CORS_ORIGINS=*
```

The API middleware (`api/middleware/tenant.py`) rejects requests with an `Origin` header that does not match the configured list.

### 6.3 Security Headers

The following headers are set by both Nginx (for the frontend) and the FastAPI middleware (for API responses):

| Header | Value | Purpose |
|---|---|---|
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | Force HTTPS for 2 years |
| `X-Frame-Options` | `DENY` | Prevent clickjacking |
| `X-Content-Type-Options` | `nosniff` | Prevent MIME sniffing |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Limit referrer data leakage |
| `Content-Security-Policy` | See Nginx config above | Prevent XSS and injection |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` | Disable browser APIs |

### 6.4 Secrets Management (Vault / AWS Secrets Manager)

**HashiCorp Vault integration:**

```bash
# Store secrets
vault kv put secret/governex/production \
  jwt_secret="$(openssl rand -hex 64)" \
  db_password="$(openssl rand -base64 32)" \
  sap_password="sap-service-account-password"

# Read secret in application startup script
JWT_SECRET=$(vault kv get -field=jwt_secret secret/governex/production)
export JWT_SECRET
```

**AWS Secrets Manager:**

```python
# In application startup (services/secrets.py)
import boto3
import json

def get_secrets():
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId='governex/production')
    return json.loads(response['SecretString'])
```

In Kubernetes, use the AWS Secrets and Configuration Provider (ASCP) or External Secrets Operator to mount secrets as environment variables without storing them in ConfigMaps.

---

## 7. Monitoring & Observability

### 7.1 Health Check Endpoints

| Endpoint | Method | Authentication | Response |
|---|---|---|---|
| `/health` | `GET` | None | `{"status": "ok", "version": "2.0.0", "db": "ok", "cache": "ok"}` |
| `/health/live` | `GET` | None | `200 OK` — process is running |
| `/health/ready` | `GET` | None | `200 OK` — DB connected, app ready to serve |
| `/api/v1/admin/system/status` | `GET` | `platform_admin` | Full system status including sync job states, queue depths |

### 7.2 Prometheus Metrics

GovernexPlus exposes Prometheus metrics at `/metrics` (requires `METRICS_ENABLED=true` and `METRICS_AUTH_TOKEN` for access control).

Key metrics exposed:

| Metric | Type | Description |
|---|---|---|
| `governex_http_requests_total` | Counter | Total HTTP requests by method, path, status code |
| `governex_http_request_duration_seconds` | Histogram | Request latency distribution |
| `governex_active_sessions` | Gauge | Current active user sessions |
| `governex_firefighter_sessions_active` | Gauge | Active firefighter sessions |
| `governex_sod_violations_total` | Gauge | Total open SoD violations by severity |
| `governex_sync_duration_seconds` | Histogram | SAP sync job duration |
| `governex_sync_errors_total` | Counter | SAP sync errors by connector type |
| `governex_db_pool_size` | Gauge | Database connection pool utilization |
| `governex_jwt_tokens_issued_total` | Counter | JWT tokens issued |
| `governex_jwt_tokens_blacklisted_total` | Counter | JWT tokens blacklisted (logout/revocation) |

**Prometheus scrape config:**
```yaml
scrape_configs:
  - job_name: governexplus
    static_configs:
      - targets: ['backend:8000']
    metrics_path: /metrics
    bearer_token: "${METRICS_AUTH_TOKEN}"
    scrape_interval: 30s
```

### 7.3 Structured Logging

GovernexPlus uses `structlog` for structured JSON logging. All log records include:

```json
{
  "timestamp": "2026-09-06T10:23:45.123Z",
  "level": "warning",
  "logger": "api.middleware.tenant",
  "event": "jwt_verification_failed",
  "tenant_id": "acme-corp",
  "user_id": null,
  "request_id": "req-uuid",
  "remote_ip": "10.0.0.50",
  "path": "/api/v1/ara/analyze",
  "method": "POST",
  "error": "Signature has expired"
}
```

Log levels and their GovernexPlus usage:
- `DEBUG`: SQL queries (only when `DB_ECHO=true`), RFC call details.
- `INFO`: Request/response, sync job starts/ends, provisioning actions.
- `WARNING`: Authentication failures, rate limit hits, sync retries.
- `ERROR`: Unhandled exceptions, database connection failures, RFC errors.
- `CRITICAL`: JWT secret missing, database unreachable at startup.

### 7.4 Log Aggregation

**ELK Stack (Elasticsearch, Logstash, Kibana):**

Configure Filebeat to ship GovernexPlus JSON logs:
```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/governex/*.log
    json.keys_under_root: true
    json.add_error_key: true
    fields:
      service: governexplus

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
  index: "governex-%{+yyyy.MM.dd}"
```

**Grafana Loki:**
```yaml
# promtail config
scrape_configs:
  - job_name: governex
    static_configs:
      - targets: [localhost]
        labels:
          job: governexplus
          __path__: /var/log/governex/*.log
    pipeline_stages:
      - json:
          expressions:
            level: level
            tenant_id: tenant_id
      - labels:
          level:
          tenant_id:
```

### 7.5 Error Tracking (Sentry)

```env
SENTRY_DSN=https://key@sentry.io/12345
SENTRY_ENVIRONMENT=production
SENTRY_TRACES_SAMPLE_RATE=0.1
SENTRY_PROFILES_SAMPLE_RATE=0.1
```

Sentry is initialized in `api/main.py` lifespan. All unhandled exceptions are captured with the request context, user ID (anonymized), and tenant ID.

### 7.6 Alerting Rules

Recommended Prometheus alerting rules:

```yaml
groups:
  - name: governexplus
    rules:
      - alert: GovernexBackendDown
        expr: up{job="governexplus"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "GovernexPlus backend is down"

      - alert: HighErrorRate
        expr: rate(governex_http_requests_total{status=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "GovernexPlus 5xx error rate above 5%"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(governex_http_request_duration_seconds_bucket[5m])) > 2
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "GovernexPlus P95 response time above 2 seconds"

      - alert: DatabasePoolExhausted
        expr: governex_db_pool_size > 0.9
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "GovernexPlus database connection pool is 90%+ utilized"

      - alert: FirefighterSessionOverdue
        expr: governex_firefighter_sessions_active > 0
        for: 8h
        labels:
          severity: warning
        annotations:
          summary: "Firefighter session active for more than 8 hours"
```

---

## 8. Performance Tuning

### 8.1 Worker Count

For Gunicorn with Uvicorn workers, the recommended formula is:

```
workers = (2 × CPU_count) + 1
```

For a 4-core server: 9 workers. For a 2-core container: 5 workers.

In Kubernetes, set workers conservatively per pod (3–5) and scale horizontally:

```dockerfile
CMD ["gunicorn", "api.main:app", \
     "-k", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--worker-connections", "1000", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--graceful-timeout", "30"]
```

### 8.2 Database Connection Pool Size

Set `DB_POOL_SIZE` to match the number of Gunicorn workers × concurrent DB connections per worker:

```
DB_POOL_SIZE = workers × 2   (minimum)
DB_MAX_OVERFLOW = workers × 4
```

For 4 workers: `DB_POOL_SIZE=8`, `DB_MAX_OVERFLOW=16`. With PgBouncer, the backend pool size can be smaller (4–8) since PgBouncer multiplexes efficiently.

### 8.3 React Query Cache Settings

Frontend API response caching is configured in `frontend/src/services/api.ts`:

| Data Type | `staleTime` | `cacheTime` | Rationale |
|---|---|---|---|
| User profile | 5 min | 30 min | Changes infrequently |
| SoD violations | 1 min | 10 min | Near-real-time awareness needed |
| Dashboard stats | 2 min | 15 min | Some staleness acceptable |
| Reference data (roles, rules) | 15 min | 60 min | Rarely changes |
| Audit logs | 0 | 5 min | Always fresh |

### 8.4 CDN for Static Assets

Configure a CDN (CloudFront, Cloudflare, or Azure CDN) to serve the compiled frontend bundle:

1. Point the CDN origin to your Nginx instance's `/` path.
2. Set cache TTL for `*.js` and `*.css` files to 1 year (Vite appends content hashes to filenames for cache busting).
3. Configure CDN to forward API calls (`/api/*`) to origin without caching.
4. Enable Brotli or gzip compression on the CDN for text assets.

With a CDN, `Time to First Byte` for the frontend drops to <50ms globally, and the API server is unburdened from serving static files.

---

## 9. Backup & Disaster Recovery

### 9.1 Database Backup Schedule

| Backup Type | Frequency | Retention | Storage |
|---|---|---|---|
| Full backup (pg_dump custom) | Daily at 02:00 | 30 days local + 1 year S3/Azure Blob | Encrypted at rest |
| WAL archiving (point-in-time) | Continuous (every 5 minutes) | 7 days | S3/Azure Blob |
| Weekly consolidation | Weekly on Sunday | 52 weeks | Cold storage (Glacier/Archive) |
| Pre-migration backup | Before every upgrade | Indefinitely | Tagged by version |

### 9.2 Point-in-Time Recovery (PITR)

PostgreSQL WAL archiving enables recovery to any point in the last 7 days:

```ini
# postgresql.conf — enable WAL archiving
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://acme-grc-wal/%f'
archive_timeout = 300   # Archive WAL every 5 minutes even if not full
```

**Restore to a point in time:**
```bash
# 1. Stop the application
systemctl stop governex-backend

# 2. Restore the most recent base backup
aws s3 cp s3://acme-grc-backups/base/20260901_020000.tar.gz /var/lib/postgresql/data/
tar -xzf /var/lib/postgresql/data/20260901_020000.tar.gz -C /var/lib/postgresql/data/

# 3. Create recovery configuration
cat > /var/lib/postgresql/data/postgresql.auto.conf <<EOF
restore_command = 'aws s3 cp s3://acme-grc-wal/%f %p'
recovery_target_time = '2026-09-05 14:30:00 UTC'
recovery_target_action = promote
EOF

# 4. Start PostgreSQL (recovery will replay WAL to target time)
systemctl start postgresql
```

### 9.3 Evidence File Backup

User-uploaded evidence files (stored in `/app/uploads`) must be backed up separately from the database:

```bash
# Daily evidence file sync to S3
aws s3 sync /app/uploads s3://acme-grc-evidence/uploads/ \
  --delete \
  --sse aws:kms \
  --sse-kms-key-id arn:aws:kms:us-east-1:account:key/key-id
```

Evidence files are immutable once uploaded (the upload API does not permit overwrite). Only deletion is logged, and deletions require `tenant_admin` authorization.

### 9.4 Disaster Recovery Runbook

**RTO target: 4 hours | RPO target: 1 hour**

**Scenario: Total server loss (hardware failure or cloud AZ outage)**

```
Step 1 — Activate DR (Time: 0)
  [ ] Notify on-call team via PagerDuty
  [ ] Declare incident in ITSM system
  [ ] Notify affected tenants (template: DR-001)

Step 2 — Provision replacement infrastructure (Time: 0–60 min)
  [ ] Launch new VM or activate standby Kubernetes cluster
  [ ] Install Docker or verify Kubernetes node availability
  [ ] Restore SSL certificates from vault

Step 3 — Restore database (Time: 60–150 min)
  [ ] Pull latest base backup from S3
  [ ] Configure PITR to the last consistent state
  [ ] Start PostgreSQL and verify restore
  [ ] Confirm row counts match pre-incident snapshot

Step 4 — Deploy application (Time: 150–200 min)
  [ ] Pull latest production Docker image from registry
  [ ] Inject environment variables from Secrets Manager
  [ ] Start backend: docker-compose -f docker-compose.prod.yml up -d
  [ ] Run alembic upgrade head (idempotent — safe to re-run)
  [ ] Restore evidence files from S3 to /app/uploads

Step 5 — Validate (Time: 200–230 min)
  [ ] Confirm /health returns 200
  [ ] Log in as platform_admin, verify dashboard loads
  [ ] Run POST /api/v1/integrations/sap/test-connection
  [ ] Verify latest audit log entries present
  [ ] Confirm no data loss beyond RPO window

Step 6 — Resume service (Time: 230–240 min)
  [ ] Update DNS to new IP
  [ ] Notify tenants service restored
  [ ] Close incident in ITSM
  [ ] Schedule post-incident review
```

---

## 10. Upgrade Procedures

### 10.1 Zero-Downtime Deployment (Kubernetes)

GovernexPlus uses a rolling update strategy in Kubernetes, ensuring at least `minReplicas` pods are available throughout the deployment:

```bash
# 1. Build and push new image
docker build -f Dockerfile.prod -t your-registry/governexplus:2.1.0 .
docker push your-registry/governexplus:2.1.0

# 2. Update the image tag (triggers rolling update)
kubectl set image deployment/governex-backend \
  backend=your-registry/governexplus:2.1.0 \
  -n governex

# 3. Monitor the rollout
kubectl rollout status deployment/governex-backend -n governex

# 4. Verify health
kubectl get pods -n governex -l app=governex-backend
```

### 10.2 Database Migration Strategy

Database migrations are managed by Alembic. The strategy for production:

1. **Always run migrations before the application upgrade**, not after. This prevents the running application from encountering missing columns.
2. **All migrations must be additive** (add columns, add tables). Never drop columns or tables in a migration that is deployed simultaneously with the application code.
3. **Use the two-phase approach for breaking schema changes:**
   - Phase 1: Add new columns/tables (application ignores them). Deploy.
   - Phase 2: Update application code to use new columns. Deploy.
   - Phase 3: Drop old columns (application no longer uses them). Deploy.

```bash
# Pre-deployment migration (run as a Kubernetes Job or Docker run before updating pods)
kubectl run alembic-upgrade \
  --image=your-registry/governexplus:2.1.0 \
  --restart=Never \
  --env="DATABASE_URL=${DATABASE_URL}" \
  --command -- alembic upgrade head \
  -n governex
```

### 10.3 Rollback Procedures

**Application rollback (Kubernetes):**
```bash
# Rollback to previous deployment
kubectl rollout undo deployment/governex-backend -n governex

# Rollback to specific revision
kubectl rollout undo deployment/governex-backend --to-revision=3 -n governex

# Check rollout history
kubectl rollout history deployment/governex-backend -n governex
```

**Database rollback:**

If a migration must be rolled back, use `alembic downgrade`:

```bash
# Downgrade one migration step
alembic downgrade -1

# Downgrade to a specific revision
alembic downgrade 20260822_121800

# IMPORTANT: Always restore from backup instead of downgrading destructive migrations.
# Alembic downgrade for DROP operations is not supported — only backup restore.
```

### 10.4 Version Compatibility Matrix

| GovernexPlus Version | Python | FastAPI | SQLAlchemy | Alembic | PostgreSQL | Node.js | React |
|---|---|---|---|---|---|---|---|
| 2.1.x | 3.12 | 0.115.x | 2.0.x | 1.13.x | 14–16 | 20 LTS | 18.x |
| 2.0.x | 3.11–3.12 | 0.111.x | 2.0.x | 1.12.x | 13–16 | 20 LTS | 18.x |
| 1.5.x | 3.10–3.11 | 0.100.x | 1.4.x | 1.9.x | 12–15 | 18 LTS | 18.x |

Upgrade path: Always upgrade one minor version at a time. Skipping minor versions (e.g., 1.5→2.1) is not supported. Run the full test suite (`pytest tests/`) after each minor version upgrade.

### 10.5 Post-Upgrade Validation Checklist

```
[ ] /health endpoint returns 200 with correct version
[ ] /api/v1/auth/login works (JWT issued successfully)
[ ] Dashboard loads with data (no blank panels)
[ ] Risk Intelligence Engine analysis returns violations correctly
[ ] Firefighter request workflow completes end-to-end
[ ] SAP sync job runs without errors (check /api/v1/admin/system/status)
[ ] Alembic current shows expected revision (alembic current)
[ ] No ERROR or CRITICAL entries in logs within first 15 minutes
[ ] Sentry shows no new error groups
[ ] Prometheus metrics endpoint responding
[ ] At least one report generated successfully (PDF/XLSX)
```

---

*For environment configuration details, see the [Configuration Reference Guide](./09-Configuration-Reference-Guide.md). For SAP connectivity setup, see the [SAP Integration Guide](./10-SAP-Integration-Guide.md). For AI feature operation, see the [AI Intelligence Guide](./11-AI-Intelligence-Guide.md).*
