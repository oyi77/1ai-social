# Deployment Guide

This guide covers deploying 1AI Social to production environments.

## Deployment Options

### Docker Deployment (Recommended)

The easiest way to deploy is using Docker and Docker Compose.

#### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB RAM minimum (4GB recommended)
- 20GB disk space

#### Quick Deploy

1. **Clone the repository**:
```bash
git clone https://github.com/yourusername/1ai-social.git
cd 1ai-social
```

2. **Configure environment**:
```bash
cp .env.example .env.production
```

Edit `.env.production` with production values (see Environment Variables section below).

3. **Build and start services**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

This starts:
- Web application (port 8000)
- PostgreSQL database
- Redis cache
- Celery worker for background jobs
- Nginx reverse proxy (port 80/443)

4. **Run database migrations**:
```bash
docker-compose -f docker-compose.prod.yml exec web alembic upgrade head
```

5. **Create admin user**:
```bash
docker-compose -f docker-compose.prod.yml exec web python scripts/create_admin.py
```

#### Docker Compose Configuration

Example `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  web:
    build: .
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000
    volumes:
      - ./app:/app/app
      - media:/app/media
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  worker:
    build: .
    command: celery -A app.worker worker --loglevel=info
    volumes:
      - ./app:/app/app
      - media:/app/media
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  beat:
    build: .
    command: celery -A app.worker beat --loglevel=info
    env_file:
      - .env.production
    depends_on:
      - db
      - redis
    restart: unless-stopped

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: 1ai_social
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
      - media:/usr/share/nginx/html/media
    depends_on:
      - web
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  media:
```

### Manual Deployment

For more control, deploy components separately.

#### 1. Database Setup

**PostgreSQL Installation**:
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# Create database
sudo -u postgres createdb 1ai_social
sudo -u postgres createuser 1ai_user
sudo -u postgres psql -c "ALTER USER 1ai_user WITH PASSWORD 'your_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE 1ai_social TO 1ai_user;"
```

**Configure PostgreSQL** (`/etc/postgresql/15/main/postgresql.conf`):
```conf
max_connections = 100
shared_buffers = 256MB
effective_cache_size = 1GB
work_mem = 4MB
```

#### 2. Redis Setup

```bash
# Ubuntu/Debian
sudo apt install redis-server

# Configure Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

#### 3. Application Setup

```bash
# Install Python dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Create systemd service
sudo nano /etc/systemd/system/1ai-social.service
```

**Systemd service file**:
```ini
[Unit]
Description=1AI Social Web Application
After=network.target postgresql.service redis.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/1ai-social
Environment="PATH=/var/www/1ai-social/venv/bin"
ExecStart=/var/www/1ai-social/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl enable 1ai-social
sudo systemctl start 1ai-social
```

#### 4. Worker Setup

Create worker service (`/etc/systemd/system/1ai-social-worker.service`):

```ini
[Unit]
Description=1AI Social Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=www-data
Group=www-data
WorkingDirectory=/var/www/1ai-social
Environment="PATH=/var/www/1ai-social/venv/bin"
ExecStart=/var/www/1ai-social/venv/bin/celery -A app.worker worker --loglevel=info --detach
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable 1ai-social-worker
sudo systemctl start 1ai-social-worker
```

## Environment Variables

### Required Variables

```env
# Application
SECRET_KEY=your-secret-key-min-32-chars
JWT_SECRET_KEY=your-jwt-secret-min-32-chars
ENVIRONMENT=production
DEBUG=false

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/1ai_social

# Redis
REDIS_URL=redis://localhost:6379/0

# AI Providers (choose at least one)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Social Platform Credentials
TWITTER_API_KEY=your-key
TWITTER_API_SECRET=your-secret
TWITTER_BEARER_TOKEN=your-bearer-token

INSTAGRAM_CLIENT_ID=your-client-id
INSTAGRAM_CLIENT_SECRET=your-client-secret

TIKTOK_CLIENT_KEY=your-client-key
TIKTOK_CLIENT_SECRET=your-client-secret

LINKEDIN_CLIENT_ID=your-client-id
LINKEDIN_CLIENT_SECRET=your-client-secret

# Storage (S3 recommended for production)
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_S3_BUCKET=your-bucket-name
AWS_REGION=us-east-1

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@yourdomain.com

# Payment Processing
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Application URLs
FRONTEND_URL=https://yourdomain.com
BACKEND_URL=https://api.yourdomain.com
```

### Optional Variables

```env
# Monitoring
SENTRY_DSN=https://...@sentry.io/...

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60

# Session
SESSION_TIMEOUT=3600

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB in bytes

# Logging
LOG_LEVEL=INFO
```

## SSL/TLS Configuration

### Using Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Auto-renewal is configured automatically
sudo certbot renew --dry-run
```

### Nginx Configuration

Example `/etc/nginx/sites-available/1ai-social`:

```nginx
upstream app_server {
    server localhost:8000;
}

server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name yourdomain.com www.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    client_max_body_size 100M;

    location / {
        proxy_pass http://app_server;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /media {
        alias /var/www/1ai-social/media;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /static {
        alias /var/www/1ai-social/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/1ai-social /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Database Management

### Backups

**Automated daily backups**:

```bash
#!/bin/bash
# /usr/local/bin/backup-db.sh

BACKUP_DIR="/var/backups/1ai-social"
DATE=$(date +%Y%m%d_%H%M%S)
FILENAME="1ai_social_$DATE.sql.gz"

mkdir -p $BACKUP_DIR

pg_dump -U 1ai_user 1ai_social | gzip > "$BACKUP_DIR/$FILENAME"

# Keep only last 30 days
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete

echo "Backup completed: $FILENAME"
```

Add to crontab:
```bash
sudo crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-db.sh
```

### Restore from Backup

```bash
gunzip -c /var/backups/1ai-social/1ai_social_20260416.sql.gz | psql -U 1ai_user 1ai_social
```

## Monitoring Setup

### Application Monitoring

**Using Sentry**:

1. Sign up at sentry.io
2. Create a new project
3. Add to `.env.production`:
```env
SENTRY_DSN=https://...@sentry.io/...
```

### Server Monitoring

**Install monitoring tools**:

```bash
# System monitoring
sudo apt install htop iotop nethogs

# Log monitoring
sudo apt install logwatch

# Uptime monitoring
# Use external service like UptimeRobot or Pingdom
```

### Log Management

**Configure log rotation** (`/etc/logrotate.d/1ai-social`):

```conf
/var/log/1ai-social/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload 1ai-social
    endscript
}
```

## Performance Optimization

### Database Optimization

```sql
-- Create indexes for common queries
CREATE INDEX idx_posts_user_id ON posts(user_id);
CREATE INDEX idx_posts_created_at ON posts(created_at);
CREATE INDEX idx_posts_scheduled_at ON posts(scheduled_at);
CREATE INDEX idx_analytics_post_id ON analytics(post_id);
```

### Redis Configuration

Edit `/etc/redis/redis.conf`:

```conf
maxmemory 512mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

### Application Caching

Enable caching in `.env.production`:

```env
CACHE_ENABLED=true
CACHE_TTL=3600
```

## Security Hardening

### Firewall Configuration

```bash
# UFW setup
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Fail2Ban

```bash
# Install
sudo apt install fail2ban

# Configure
sudo cp /etc/fail2ban/jail.conf /etc/fail2ban/jail.local
sudo systemctl enable fail2ban
sudo systemctl start fail2ban
```

### Regular Updates

```bash
# System updates
sudo apt update && sudo apt upgrade -y

# Application updates
cd /var/www/1ai-social
git pull
pip install -r requirements.txt --upgrade
alembic upgrade head
sudo systemctl restart 1ai-social
```

## Troubleshooting

### Check Service Status

```bash
sudo systemctl status 1ai-social
sudo systemctl status 1ai-social-worker
sudo systemctl status postgresql
sudo systemctl status redis
sudo systemctl status nginx
```

### View Logs

```bash
# Application logs
sudo journalctl -u 1ai-social -f

# Worker logs
sudo journalctl -u 1ai-social-worker -f

# Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

**Database connection errors**:
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test connection
psql -U 1ai_user -d 1ai_social -h localhost
```

**Worker not processing jobs**:
```bash
# Check Redis connection
redis-cli ping

# Restart worker
sudo systemctl restart 1ai-social-worker
```

**High memory usage**:
```bash
# Check processes
htop

# Restart services
sudo systemctl restart 1ai-social
sudo systemctl restart 1ai-social-worker
```

## Scaling Considerations

### Horizontal Scaling

- Use load balancer (HAProxy, AWS ALB)
- Run multiple web instances
- Shared PostgreSQL and Redis
- Centralized media storage (S3)

### Vertical Scaling

Recommended specs by usage:

**Small (< 1000 users)**:
- 2 CPU cores
- 4GB RAM
- 50GB SSD

**Medium (1000-10000 users)**:
- 4 CPU cores
- 8GB RAM
- 100GB SSD

**Large (10000+ users)**:
- 8+ CPU cores
- 16GB+ RAM
- 200GB+ SSD
- Separate database server

## Support

For deployment assistance:
- Email: support@1aisocial.com
- Documentation: https://docs.1aisocial.com
- Community: Discord server

Enterprise customers receive dedicated deployment support.
