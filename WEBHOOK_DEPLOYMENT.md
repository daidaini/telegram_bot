# Webhook Deployment Guide

This guide provides detailed instructions for deploying the Telegram bot in webhook mode, which is more efficient and scalable than polling mode.

## Overview

The bot supports two operational modes:
- **Polling Mode** (Default): Bot actively requests updates from Telegram API
- **Webhook Mode**: Telegram sends updates to your server when events occur

## When to Use Webhook Mode

### Advantages of Webhook Mode
- **Faster Response Time**: Instant notifications from Telegram
- **Lower Resource Usage**: No continuous polling
- **Better Scalability**: Supports multiple bot instances
- **Reduced API Calls**: Fewer requests to Telegram servers

### Requirements
- Publicly accessible HTTPS URL
- Valid SSL certificate
- Open firewall ports
- Static IP or reliable DNS

## Configuration

### 1. Environment Variables

Edit your `.env` file:

```bash
# Enable webhook mode
BOT_MODE=webhook

# Your public webhook URL (must be HTTPS)
WEBHOOK_URL=https://yourdomain.com/webhook

# Optional secret token for security
WEBHOOK_SECRET_TOKEN=your_secret_token_here

# Port for the web server (default: 5000)
WEBHOOK_PORT=8443
```

### 2. SSL Certificate Setup

#### Option A: Let's Encrypt (Recommended)
```bash
# Install certbot
sudo apt-get update
sudo apt-get install certbot

# Get certificate
sudo certbot certonly --standalone -d yourdomain.com

# Certificate paths:
# Private key: /etc/letsencrypt/live/yourdomain.com/privkey.pem
# Certificate: /etc/letsencrypt/live/yourdomain.com/fullchain.pem
```

#### Option B: Self-Signed Certificate
```bash
# Generate self-signed certificate
openssl req -x509 -newkey rsa:2048 -keyout key.pem -out cert.pem -days 365 -nodes
```

## Deployment Options

### Option 1: Direct Python Deployment

```bash
# 1. Configure environment
cp .env.example .env
nano .env  # Edit with your settings

# 2. Install dependencies
pip install -r requirements.txt

# 3. Test configuration
python setup_webhook.py --action info

# 4. Set webhook
python setup_webhook.py --action set --url https://yourdomain.com/webhook --secret your_secret_token

# 5. Run the bot
python app.py
```

### Option 2: Docker Deployment

#### Dockerfile
```dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Create non-root user
RUN useradd -m -u 1000 botuser
USER botuser

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
```

#### docker-compose.yml
```yaml
version: '3.8'

services:
  telegram-bot:
    build: .
    ports:
      - "5000:5000"
    environment:
      - BOT_MODE=webhook
      - WEBHOOK_URL=https://yourdomain.com/webhook
      - WEBHOOK_SECRET_TOKEN=${WEBHOOK_SECRET_TOKEN}
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

#### Deploy with Docker
```bash
# Build and run
docker-compose up -d

# Check logs
docker-compose logs -f

# Test webhook
python setup_webhook.py --action test --url https://yourdomain.com/webhook
```

### Option 3: Nginx Reverse Proxy

#### Nginx Configuration
```nginx
server {
    listen 443 ssl http2;
    server_name yourdomain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /webhook {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Webhook specific headers
        proxy_set_header X-Telegram-Bot-Api-Secret-Token $http_x_telegram_bot_api_secret_token;
    }

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Security Considerations

### 1. Webhook Security
- Always use HTTPS URLs
- Set a strong secret token
- Validate incoming requests
- Monitor for suspicious activity

### 2. Server Security
```bash
# Configure firewall
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Fail2ban for protection
sudo apt-get install fail2ban
```

### 3. Environment Variables
- Never commit `.env` files to version control
- Use strong, random tokens
- Regularly rotate API keys and tokens

## Monitoring and Maintenance

### 1. Health Checks
```bash
# Test bot health
curl https://yourdomain.com/health

# Expected response
{"status": "healthy", "timestamp": "2024-01-01T12:00:00"}
```

### 2. Log Monitoring
```bash
# View application logs
tail -f /var/log/telegram-bot/app.log

# Systemd service logs
journalctl -u telegram-bot -f
```

### 3. Webhook Status
```bash
# Check webhook status
python setup_webhook.py --action info

# Test webhook endpoint
python setup_webhook.py --action test --url https://yourdomain.com/webhook
```

## Troubleshooting

### Common Issues

#### 1. SSL Certificate Problems
```bash
# Check SSL certificate
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Verify certificate chain
curl -I https://yourdomain.com
```

#### 2. Webhook Not Receiving Updates
```bash
# Check webhook configuration
python setup_webhook.py --action info

# Test webhook endpoint manually
curl -X POST https://yourdomain.com/webhook \
     -H "Content-Type: application/json" \
     -d '{"update_id": 123456, "message": {"text": "test"}}'
```

#### 3. Server Connectivity Issues
```bash
# Check if port is open
telnet yourdomain.com 443

# Test from external network
curl https://yourdomain.com/health
```

#### 4. Firewall Issues
```bash
# Check firewall status
sudo ufw status

# Allow necessary ports
sudo ufw allow 443/tcp
sudo ufw reload
```

### Debug Mode

Enable debug logging:
```python
# In app.py
logging.basicConfig(level=logging.DEBUG)
```

Or via environment variable:
```bash
export LOG_LEVEL=DEBUG
python app.py
```

## Performance Optimization

### 1. Web Server Configuration
```bash
# Use gunicorn for production
pip install gunicorn

# Run with multiple workers
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

### 2. Caching
- Enable Redis for caching
- Use CDN for static assets
- Implement request rate limiting

### 3. Database Optimization
- Use connection pooling
- Optimize database queries
- Regular maintenance

## Testing

### 1. Pre-deployment Testing
```bash
# Test all functionality
python test_webhook_integration.py

# Test RSS functionality
python test_round_robin_rss.py

# Test channel forwarding
python test_channel_forwarding.py
```

### 2. Load Testing
```bash
# Install load testing tool
pip install locust

# Run load test
locust -f load_test.py --host=https://yourdomain.com
```

## Backup and Recovery

### 1. Configuration Backup
```bash
# Backup environment configuration
cp .env .env.backup.$(date +%Y%m%d)

# Backup RSS cache
cp rss_cache.json rss_cache.backup.$(date +%Y%m%d)
```

### 2. Automated Backup Script
```bash
#!/bin/bash
# backup.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/telegram-bot"

mkdir -p $BACKUP_DIR

# Backup configuration
cp .env $BACKUP_DIR/env.$DATE
cp rss_cache.json $BACKUP_DIR/rss_cache.$DATE

# Keep only last 7 days
find $BACKUP_DIR -name "*.env.*" -mtime +7 -delete
find $BACKUP_DIR -name "*.rss_cache.*" -mtime +7 -delete
```

## Production Checklist

- [ ] HTTPS URL configured with valid SSL certificate
- [ ] Firewall configured to allow HTTPS traffic
- [ ] Webhook secret token set and secured
- [ ] Environment variables configured
- [ ] Bot token verified and working
- [ ] RSS feeds tested and accessible
- [ ] Channel forwarding configured (if needed)
- [ ] Monitoring and logging setup
- [ ] Backup procedures implemented
- [ ] Security hardening completed
- [ ] Load testing performed
- [ ] Documentation updated

## Support

If you encounter issues:

1. Check the troubleshooting section
2. Review application logs
3. Test webhook configuration
4. Verify SSL certificate
5. Check firewall settings
6. Run integration tests

For additional help, refer to the main README.md or create an issue in the project repository.