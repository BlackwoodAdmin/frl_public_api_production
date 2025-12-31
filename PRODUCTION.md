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

Update your systemd service file (`/etc/systemd/system/frl-python-api.service`):

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

