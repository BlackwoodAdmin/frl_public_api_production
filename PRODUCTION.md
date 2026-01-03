# Production Mode Setup

## Environment Variables

Set these in your `.env` file on the VPS:

```env
DEBUG=False
LOG_LEVEL=INFO
HOST=127.0.0.1
PORT=8000
```

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


