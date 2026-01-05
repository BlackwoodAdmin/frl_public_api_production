# Production Mode Setup

## Environment Variables

Set these in your `.env` file on the VPS:

```env
DEBUG=False
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000

# Logging configuration
USE_JOURNALCTL=true
LOG_FILE_PATH=/var/log/frl-python-api/app.log

# Optional: Set to "development" for additional diagnostic output
ENVIRONMENT=production

# Dashboard authentication
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
```

**Logging Configuration:**
- `USE_JOURNALCTL`: Set to "true" to use systemd journal for logs (recommended for production with systemd service)
- `LOG_FILE_PATH`: Path to log file if not using journalctl (default: "/var/log/frl-python-api/app.log")
- `ENVIRONMENT`: Set to "development" for development mode, "production" for production (affects diagnostic output)

## Running with Gunicorn (Recommended for Production)

Gunicorn with Uvicorn workers provides better performance and stability in production:

```bash
cd /var/www/frl-python-api
source venv/bin/activate
gunicorn app.main:app -c gunicorn_config.py
```

## Systemd Service (Production)

### Updating the Service File on VPS

To update the systemd service file on your VPS, follow these steps:

1. **Edit the service file:**
   ```bash
   sudo nano /etc/systemd/system/frl-python-api.service
   ```

2. **Add the log routing configuration** (StandardOutput, StandardError, SyslogLevel, SyslogIdentifier) as shown in the example below.

3. **Save and exit** (Ctrl+X, then Y, then Enter in nano).

4. **Reload systemd** to recognize the changes:
   ```bash
   sudo systemctl daemon-reload
   ```

5. **Restart the service** to apply the new configuration:
   ```bash
   sudo systemctl restart frl-python-api
   ```

6. **Verify the service is running:**
   ```bash
   sudo systemctl status frl-python-api
   ```

7. **Check logs** to verify proper log routing:
   ```bash
   journalctl -u frl-python-api -n 20 --no-pager
   ```

### Service File Configuration

Update your systemd service file (`/etc/systemd/system/frl-python-api.service`) with this configuration:

```ini
[Unit]
Description=FRL Python API
After=network.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/var/www/frl-python-api
Environment="PATH=/var/www/frl-python-api/venv/bin"
EnvironmentFile=/var/www/frl-python-api/.env
ExecStart=/var/www/frl-python-api/venv/bin/gunicorn app.main:app -c gunicorn_config.py
Restart=always
RestartSec=10

# Log routing - route both stdout and stderr to journal
StandardOutput=journal
StandardError=journal
# Set default syslog priority to INFO (not ERROR)
SyslogLevel=info
# Optional: Set syslog identifier for easier filtering
SyslogIdentifier=frl-python-api

# Security settings
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Then reload and restart:

```bash
sudo systemctl daemon-reload
sudo systemctl restart frl-python-api
sudo systemctl status frl-python-api
```

### Log Routing Configuration

The service file includes log routing settings to ensure proper log levels in journalctl:

- **StandardOutput=journal**: Routes stdout (access logs) to systemd journal
- **StandardError=journal**: Routes stderr (error logs) to systemd journal
- **SyslogLevel=info**: Sets default syslog priority to INFO, preventing successful requests from appearing as ERROR
- **SyslogIdentifier=frl-python-api**: Sets custom identifier for easier log filtering

After updating the service file, verify logs are properly categorized:

```bash
# Check recent logs - should show INFO for successful requests
journalctl -u frl-python-api -n 50 --no-pager

# Filter by priority level
journalctl -u frl-python-api -p info --no-pager
journalctl -u frl-python-api -p err --no-pager

# Filter by syslog identifier (if SyslogIdentifier is set)
journalctl -t frl-python-api --no-pager
```

## SSL/HTTPS Configuration

For production deployments, it's essential to configure HTTPS/SSL to encrypt traffic between clients and your API server. This section provides a quick reference for SSL setup.

### Quick Setup

The recommended approach is to use Let's Encrypt with Certbot for free SSL certificates. For detailed step-by-step instructions, see [DEPLOYMENT.md](DEPLOYMENT.md) Step 12.

**Quick commands:**

```bash
# Install Certbot
sudo dnf install certbot python3-certbot-nginx -y

# Obtain SSL certificate (replace with your domain)
sudo certbot --nginx -d your-domain.com

# Verify certificate renewal is set up
sudo systemctl status certbot-renew.timer
```

### Important Notes

1. **Domain DNS**: Ensure your domain's A record points to your VPS IP address before obtaining certificates
2. **Firewall**: Ports 80 (HTTP) and 443 (HTTPS) must be open for certificate verification and HTTPS traffic
3. **Automatic Renewal**: Certbot sets up automatic renewal, but verify it's working: `sudo systemctl list-timers | grep certbot`
4. **Nginx Configuration**: Certbot automatically updates your Nginx configuration to:
   - Redirect HTTP to HTTPS
   - Use SSL certificates
   - Enable HTTP/2

### Nginx HTTPS Configuration

After Certbot setup, your Nginx configuration should include:
- HTTP server block that redirects to HTTPS
- HTTPS server block with SSL certificates
- Proper proxy headers including `X-Forwarded-Proto`

### Testing SSL

```bash
# Check certificate status
sudo certbot certificates

# Test HTTPS endpoint
curl -I https://your-domain.com

# Test renewal (dry run)
sudo certbot renew --dry-run
```

### Troubleshooting

- **Certificate issues**: See [DEPLOYMENT.md](DEPLOYMENT.md) Step 12.6 for troubleshooting tips
- **Renewal failures**: Check logs with `sudo journalctl -u certbot-renew.service`
- **Nginx errors**: Verify configuration with `sudo nginx -t`

For comprehensive SSL setup instructions, see [DEPLOYMENT.md](DEPLOYMENT.md) Step 12.

## Running with Uvicorn (Alternative)

If you prefer to use Uvicorn directly (simpler but less robust):

```bash
cd /var/www/frl-python-api
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4 --no-access-log
```

## Differences: Development vs Production

### Development Mode
- `DEBUG=True` in `.env`
- Auto-reload enabled (`--reload` flag)
- More verbose logging
- Single worker process

### Production Mode
- `DEBUG=False` in `.env`
- No auto-reload
- Optimized logging
- Multiple worker processes (via Gunicorn)
- Runs as systemd service
- Listens on `127.0.0.1` (not `0.0.0.0`) - Nginx handles external connections

## Monitoring

### Monitoring Dashboard

The application includes a web-based monitoring dashboard accessible at `/monitor/*`. 

**Access the dashboard:**
```
http://your-domain.com/monitor/login
```

**Features:**
- Real-time system metrics (CPU, memory usage)
- Worker process monitoring and details
- Request statistics and error tracking (only 5xx server errors counted)
- Application log viewing with filtering and detail pages
- Health status monitoring

**Authentication:**
- HTML endpoints require authentication (Basic Auth)
- JSON endpoints do not require authentication
- Credentials are configured in the authentication service
- See [MONITORING.md](MONITORING.md) for authentication setup

**Request Logging:**
- All requests are logged at INFO level (visible in logs page)
- Errors (status >= 400) are logged at WARNING level
- Request statistics are tracked automatically via middleware
- Error rate includes only 5xx server errors (4xx client errors are logged but not counted)

### Command Line Monitoring

Check logs:
```bash
# Systemd service logs
sudo journalctl -u frl-python-api -f

# Or if running directly
# Logs will appear in console/stdout
```

Check status:
```bash
sudo systemctl status frl-python-api
```

For detailed monitoring documentation, see [MONITORING.md](MONITORING.md).


