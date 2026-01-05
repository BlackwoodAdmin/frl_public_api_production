# VPS Deployment Guide for AlmaLinux 9

## Step 1: Initial VPS Setup

```bash
# Update system
sudo dnf update -y

# Install Python 3.11
sudo dnf install python3.11 python3.11-pip python3.11-devel -y

# Install MySQL client libraries
sudo dnf install mariadb-connector-c-devel -y

# Install development tools
sudo dnf groupinstall "Development Tools" -y
sudo dnf install git -y
```

## Step 2: Clone Repository

```bash
# Clone your GitHub repository
git clone https://github.com/BlackwoodAdmin/frl_public_api_production.git
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
# Copy example env file
cp .env.example .env

# Edit .env file with your database credentials
nano .env
```

Update the `.env` file with your actual database credentials and monitoring dashboard credentials:
```
DB_HOST=your_database_host
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_CHARSET=utf8mb4

# Monitoring dashboard authentication
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
```

**Note:** The `.env` file is in `.gitignore` and will not be committed to GitHub. Make sure to configure it with your actual database credentials and dashboard credentials on the VPS.

## Step 6: Test Database Connection

```bash
# Test the connection (create a simple test script)
python3 -c "from app.database import db; print('Database connected!')"
```

## Step 7: Run the Application

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the main.py directly
python app/main.py
```

## Step 8: Test the Endpoints

```bash
# Test health endpoint
curl http://localhost:8000/health

# Test root endpoint
curl http://localhost:8000/
```

## Step 9: Set Up as a Service (Production)

Create systemd service file:

```bash
sudo nano /etc/systemd/system/frl-api.service
```

Add this content:
```ini
[Unit]
Description=FRL Python API
After=network.target

[Service]
User=your_username
WorkingDirectory=/home/your_username/frl_public_api_production
Environment="PATH=/home/your_username/frl_public_api_production/venv/bin"
ExecStart=/home/your_username/frl_public_api_production/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable frl-api
sudo systemctl start frl-api
sudo systemctl status frl-api
```

## Step 10: Configure Firewall

```bash
# Allow port 8000 (or your chosen port)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```

## Step 11: Set Up Nginx (Optional but Recommended)

This step sets up Nginx as a reverse proxy with HTTP only. After completing this step, proceed to Step 12 to configure HTTPS/SSL.

```bash
# Install Nginx
sudo dnf install nginx -y

# Create Nginx config
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

Start and test Nginx:
```bash
sudo systemctl enable nginx
sudo systemctl start nginx
sudo nginx -t  # Test configuration
```

**Note:** After setting up SSL in Step 12, you'll need to update this configuration to include HTTPS and redirect HTTP to HTTPS.

## Step 12: Set Up SSL/HTTPS with Let's Encrypt

This step configures HTTPS using Let's Encrypt SSL certificates with Certbot. This is recommended for production deployments.

### Prerequisites

- Domain name pointing to your VPS IP address
- Nginx installed and running (from Step 11)
- Ports 80 and 443 open in firewall

### Step 12.1: Install Certbot

```bash
# Install Certbot and Nginx plugin
sudo dnf install certbot python3-certbot-nginx -y
```

### Step 12.2: Configure Firewall for HTTPS

```bash
# Allow HTTP (port 80) and HTTPS (port 443)
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

### Step 12.3: Obtain SSL Certificate

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
- Choose whether to redirect HTTP to HTTPS (recommended: Yes)

### Step 12.4: Verify Nginx Configuration

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

### Step 12.5: Test SSL Configuration

```bash
# Test SSL certificate
sudo certbot certificates

# Verify HTTPS is working
curl -I https://your-domain.com

# Test automatic renewal (dry run)
sudo certbot renew --dry-run
```

### Step 12.6: Set Up Automatic Certificate Renewal

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

### Troubleshooting

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

## Step 13: Access Monitoring Dashboard

The application includes a monitoring dashboard accessible at `/monitor/*`. 

### Set Up Authentication

The monitoring dashboard requires authentication. Credentials are configured in the authentication service. See [MONITORING.md](MONITORING.md) for details on authentication setup.

### Access the Dashboard

Once the application is running, access the monitoring dashboard at:

```
https://your-domain.com/monitor/login
```

Or if accessing locally (no SSL):
```
http://localhost:8000/monitor/login
```

The dashboard provides:
- Real-time system metrics (CPU, memory)
- Worker process monitoring
- Request statistics and error tracking
- Application log viewing
- Health status monitoring

For detailed documentation on all monitoring features, see [MONITORING.md](MONITORING.md).

