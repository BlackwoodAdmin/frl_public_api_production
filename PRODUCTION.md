# Production VPS Setup Guide for AlmaLinux 9

Complete step-by-step guide for setting up the FRL Python API in production on a fresh AlmaLinux 9 VPS.

## Step 1: Initial VPS Setup

```bash
# Update system
sudo dnf update -y

# Install Python 3.11
sudo dnf install python3.11 python3.11-pip python3.11-devel -y

# Install MySQL client libraries
sudo dnf install mariadb-connector-c-devel -y

# Install development tools (required for building Python packages like psutil)
sudo dnf groupinstall "Development Tools" -y
sudo dnf install git -y
```

## Step 2: Clone Repository

```bash
# Clone your GitHub repository
git clone https://github.com/BlackwoodAdmin/frl_public_api_production.git

# Navigate to project directory
cd frl_public_api_production
```

## Step 3: Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

## Step 4: Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt
```

### Troubleshooting: psutil Installation Error

If you encounter an error like `error: command 'gcc' failed: No such file or directory` when installing `psutil`, you need to install the C compiler and Python development headers:

```bash
# Install GCC compiler and Python development headers
sudo dnf install gcc python3.11-devel -y

# Then retry installing requirements
pip install -r requirements.txt
```

**Note:** The "Development Tools" group installed in Step 1 should include `gcc`, but if you skipped that step or it didn't install properly, run the command above. For a complete development environment:

```bash
# Install the full Development Tools group (includes gcc, make, etc.)
sudo dnf groupinstall "Development Tools" -y

# Ensure Python 3.11 development headers are installed
sudo dnf install python3.11-devel -y
```

## Step 5: Configure Environment

```bash
# Create .env file (if .env.example exists, copy it; otherwise create new)
if [ -f .env.example ]; then
    cp .env.example .env
else
    touch .env
fi

# Edit .env file with your database credentials
sudo nano .env
```

Add the following to your `.env` file:

```env
# Database settings
DB_HOST=your_database_host
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_CHARSET=utf8mb4

# Application settings
DEBUG=False
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000

# Logging configuration
USE_JOURNALCTL=true
LOG_FILE_PATH=/var/log/frl-python-api/app.log
ENVIRONMENT=production

# Monitoring dashboard authentication
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
```

**Important Notes:**
- Set `DEBUG=False` for production
- Set `HOST=127.0.0.1` (application listens only on localhost - Nginx handles external connections)
- `USE_JOURNALCTL=true` routes logs to systemd journal (recommended for production)
- The `.env` file is in `.gitignore` and will not be committed to GitHub

**Logging Configuration:**
- `USE_JOURNALCTL`: Set to "true" to use systemd journal for logs (recommended for production with systemd service)
- `LOG_FILE_PATH`: Path to log file if not using journalctl (default: "/var/log/frl-python-api/app.log")
- `ENVIRONMENT`: Set to "production" for production mode

## Step 6: Test Database Connection

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Test the connection
python3 -c "from app.database import db; print('Database connected')"
```

If successful, you should see "Database connected". If you encounter errors, verify your database credentials in the `.env` file.

## Step 6.5: Create Required Directories

Create the directories needed for logging and stats:

```bash
# Create log directory (for file-based logging fallback)
sudo mkdir -p /var/log/frl-python-api
sudo chown root:root /var/log/frl-python-api
sudo chmod 755 /var/log/frl-python-api

# Create stats directory (for request statistics)
sudo mkdir -p /var/run/frl-python-api
sudo chown root:root /var/run/frl-python-api
sudo chmod 755 /var/run/frl-python-api
```

**Note:** The stats directory will be automatically created by the application if it doesn't exist, but it's good practice to create it manually with proper permissions. The log directory is needed if `USE_JOURNALCTL=false` or as a fallback.

## Step 7: Create Systemd Service

Create a systemd service file to run the application as a service with automatic restart.

**Note:** Replace `/path/to/frl_public_api_production` in the service file with the actual path where you cloned the repository (e.g., `/home/your_username/frl_public_api_production` or `/var/www/frl_public_api_production`).

```bash
# Create systemd service file
sudo nano /etc/systemd/system/frl-python-api.service
```

Add this configuration (replace `/path/to/frl_public_api_production` with your actual project path):

```ini
[Unit]
Description=FRL Python API
After=network.target

[Service]
Type=notify
User=root
Group=root
WorkingDirectory=/path/to/frl_public_api_production
Environment="PATH=/path/to/frl_public_api_production/venv/bin"
EnvironmentFile=/path/to/frl_public_api_production/.env
ExecStart=/path/to/frl_public_api_production/venv/bin/gunicorn app.main:app -c gunicorn_config.py
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

**Note:** This configuration uses Gunicorn with Uvicorn workers for production. Gunicorn provides better performance and stability than running Uvicorn directly.

Enable and start the service:

```bash
# Reload systemd to recognize the new service
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable frl-python-api

# Start the service
sudo systemctl start frl-python-api

# Check service status
sudo systemctl status frl-python-api
```

### Verify Log Routing

The service file routes logs to systemd journal. Verify logs are properly categorized:

```bash
# Check recent logs - should show INFO for successful requests
sudo journalctl -u frl-python-api -n 50 --no-pager

# Filter by priority level
sudo journalctl -u frl-python-api -p info --no-pager
sudo journalctl -u frl-python-api -p err --no-pager

# Filter by syslog identifier (if SyslogIdentifier is set)
sudo journalctl -t frl-python-api --no-pager
```

**Log Routing Configuration Explained:**
- **StandardOutput=journal**: Routes stdout (access logs) to systemd journal
- **StandardError=journal**: Routes stderr (error logs) to systemd journal
- **SyslogLevel=info**: Sets default syslog priority to INFO, preventing successful requests from appearing as ERROR
- **SyslogIdentifier=frl-python-api**: Sets custom identifier for easier log filtering

## Step 8: Configure Firewall

Configure the firewall to allow HTTP (port 80) and HTTPS (port 443) traffic:

```bash
# Allow HTTP and HTTPS services
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https

# Reload firewall to apply changes
sudo firewall-cmd --reload

# Verify firewall rules
sudo firewall-cmd --list-all
```

## Step 9: Set Up Nginx as Reverse Proxy

This step sets up Nginx as a reverse proxy with HTTP only. After completing this step, proceed to Step 10 to configure HTTPS/SSL.

### Install Nginx

```bash
# Install Nginx
sudo dnf install nginx -y
```

### Create Nginx Configuration

```bash
# Create Nginx config file
sudo nano /etc/nginx/conf.d/frl-api.conf
```

Add initial HTTP-only configuration:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Replace `your-domain.com` with your actual domain name.

### Start and Test Nginx

```bash
# Enable Nginx to start on boot
sudo systemctl enable nginx

# Start Nginx
sudo systemctl start nginx

# Test Nginx configuration for syntax errors
sudo nginx -t

# If test passes, reload Nginx (not necessary if starting for first time)
sudo systemctl reload nginx
```

**Note:** After setting up SSL in Step 10, Nginx configuration will be automatically updated to include HTTPS and redirect HTTP to HTTPS.

## Step 10: Set Up SSL/HTTPS with Let's Encrypt

This step configures HTTPS using Let's Encrypt SSL certificates with Certbot. This is essential for production deployments.

### Prerequisites

- Domain name pointing to your VPS IP address (DNS A record must be configured)
- Nginx installed and running (from Step 9)
- Ports 80 and 443 open in firewall (from Step 8)

### Step 10.1: Install EPEL Repository

Certbot is available in the EPEL (Extra Packages for Enterprise Linux) repository. First, install EPEL:

```bash
# Install EPEL repository (required for certbot)
sudo dnf install epel-release -y
```

### Step 10.2: Install Certbot

```bash
# Install Certbot and Nginx plugin
sudo dnf install certbot python3-certbot-nginx -y
```

### Step 10.3: Obtain SSL Certificate

Replace `your-domain.com` with your actual domain name:

```bash
# Obtain SSL certificate (Certbot will automatically configure Nginx)
sudo certbot --nginx -d your-domain.com

# If you have www subdomain, include both:
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
```

Certbot will:
- Automatically verify your domain ownership
- Obtain and install the SSL certificate
- Update your Nginx configuration to use HTTPS
- Set up automatic HTTP to HTTPS redirect

Follow the prompts:
- Enter your email address (for renewal notifications)
- Agree to terms of service
- Choose whether to redirect HTTP to HTTPS (recommended: **Yes**)

### Step 10.4: Verify Nginx Configuration

After Certbot updates your configuration, verify it:

```bash
# Test Nginx configuration
sudo nginx -t

# If test passes, reload Nginx
sudo systemctl reload nginx
```

Your `/etc/nginx/conf.d/frl-api.conf` should now look similar to:

```nginx
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Step 10.5: Test SSL Configuration

```bash
# Test SSL certificate
sudo certbot certificates

# Verify HTTPS is working
curl -I https://your-domain.com

# Test automatic renewal (dry run)
sudo certbot renew --dry-run
```

### Step 10.6: Set Up Automatic Certificate Renewal

Let's Encrypt certificates expire after 90 days. Certbot should automatically set up a renewal timer, but verify it:

```bash
# Check if certbot renewal timer is active
sudo systemctl status certbot-renew.timer

# Enable and start if not already running
sudo systemctl enable certbot-renew.timer
sudo systemctl start certbot-renew.timer

# Verify timer is scheduled
sudo systemctl list-timers | grep certbot
```

Certbot typically renews certificates automatically before they expire (usually 30 days before expiration).

### Troubleshooting SSL Setup

**Certificate obtainment fails:**
- Verify domain DNS A record points to your VPS IP
- Ensure port 80 is accessible (temporarily needed for domain verification)
- Check firewall isn't blocking ports 80 and 443

**Nginx configuration errors:**
- Run `sudo nginx -t` to check for syntax errors
- Check Nginx error logs: `sudo tail -f /var/log/nginx/error.log`

**Certificate renewal issues:**
- Manually renew: `sudo certbot renew`
- Check renewal logs: `sudo journalctl -u certbot-renew.service`

**For detailed Certbot documentation:**
- Visit: https://eff-certbot.readthedocs.io/

### Important SSL Notes

1. **Domain DNS**: Ensure your domain's A record points to your VPS IP address before obtaining certificates
2. **Firewall**: Ports 80 (HTTP) and 443 (HTTPS) must be open for certificate verification and HTTPS traffic
3. **Automatic Renewal**: Certbot sets up automatic renewal, but verify it's working: `sudo systemctl list-timers | grep certbot`
4. **Nginx Configuration**: Certbot automatically updates your Nginx configuration to:
   - Redirect HTTP to HTTPS
   - Use SSL certificates
   - Enable HTTP/2

## Step 11: Access Monitoring Dashboard

The application includes a web-based monitoring dashboard accessible at `/monitor/*`.

### Set Up Authentication

The monitoring dashboard requires authentication. Credentials are configured in your `.env` file with `DASHBOARD_USERNAME` and `DASHBOARD_PASSWORD` (configured in Step 5).

See [MONITORING.md](MONITORING.md) for details on authentication setup.

### Access the Dashboard

Once the application is running, access the monitoring dashboard at:

```
https://your-domain.com/monitor/login
```

The dashboard provides:
- Real-time system metrics (CPU, memory usage)
- Worker process monitoring and details
- Request statistics and error tracking (only 5xx server errors counted)
- Application log viewing with filtering and detail pages
- Health status monitoring

### Dashboard Features

**Authentication:**
- HTML endpoints require authentication (Basic Auth)
- JSON endpoints do not require authentication
- Credentials are configured in your `.env` file

**Request Logging:**
- All requests are logged at INFO level (visible in logs page)
- Errors (status >= 400) are logged at WARNING level
- Request statistics are tracked automatically via middleware
- Error rate includes only 5xx server errors (4xx client errors are logged but not counted)

### Command Line Monitoring

Check service status:
```bash
sudo systemctl status frl-python-api
```

Check logs:
```bash
# Systemd service logs (follow mode)
sudo journalctl -u frl-python-api -f

# Recent logs
sudo journalctl -u frl-python-api -n 50 --no-pager

# Filter by priority level
sudo journalctl -u frl-python-api -p err --no-pager
```

For detailed monitoring documentation, see [MONITORING.md](MONITORING.md).

## Production Best Practices

### Security

- Application listens on `127.0.0.1` (localhost only) - Nginx handles external connections
- Use HTTPS/SSL for all external traffic
- Keep system and packages updated: `sudo dnf update -y`
- Use strong passwords for database and dashboard credentials
- Regularly rotate credentials

### Performance

- Gunicorn with multiple workers provides better performance than single Uvicorn process
- Nginx as reverse proxy handles SSL termination and static file serving
- Systemd service ensures automatic restart on failure or reboot

### Monitoring

- Use the built-in monitoring dashboard for real-time metrics
- Monitor systemd service status regularly
- Check logs for errors and warnings
- Set up alerts for service failures (outside scope of this guide)

## Differences: Production vs Development

### Production Mode
- `DEBUG=False` in `.env`
- No auto-reload
- Optimized logging
- Multiple worker processes (via Gunicorn)
- Runs as systemd service
- Listens on `127.0.0.1` (not `0.0.0.0`) - Nginx handles external connections
- HTTPS/SSL enabled
- Logs routed to systemd journal

### Development Mode
- `DEBUG=True` in `.env`
- Auto-reload enabled (`--reload` flag)
- More verbose logging
- Single worker process
- Manual startup
- May listen on `0.0.0.0` for direct access
- HTTP only (typically)

## Troubleshooting

### Service Won't Start

```bash
# Check service status
sudo systemctl status frl-python-api

# Check detailed logs
sudo journalctl -u frl-python-api -n 100 --no-pager

# Verify .env file exists and has correct paths
ls -la /path/to/frl_public_api_production/.env
```

### Database Connection Issues

- Verify database credentials in `.env` file
- Check if database server is accessible: `ping your_database_host`
- Test connection manually (Step 6)

### Nginx Issues

```bash
# Test Nginx configuration
sudo nginx -t

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Restart Nginx
sudo systemctl restart nginx
```

### SSL Certificate Issues

- Verify domain DNS A record points to VPS IP
- Check firewall allows ports 80 and 443
- See Step 10.5 Troubleshooting section

## Next Steps

Your production environment is now set up! You can:

1. Monitor the application using the dashboard at `https://your-domain.com/monitor/login`
2. Test your API endpoints
3. Set up automated backups (outside scope of this guide)
4. Configure additional security measures (fail2ban, etc.)
5. Set up monitoring/alerting systems

For additional documentation:
- [MONITORING.md](MONITORING.md) - Detailed monitoring documentation
- [README.md](README.md) - API endpoint documentation
