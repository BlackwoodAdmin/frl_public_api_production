# FRL Python API

Python implementation of the Free Relevant Links feed endpoints, replicating the PHP `/feed/` endpoints.

## Endpoints

### Feed Endpoints

#### `/feed/Article.php`
Main content router endpoint that handles various content generation requests.

**Methods:** `GET`, `POST`

**Parameters:**
- `domain` (optional) - Domain identifier
- `Action` (optional) - Action type to perform
- `apiid` (optional) - API identifier
- `apikey` (optional) - API key for authentication
- `kkyy` (optional) - WordPress plugin key
- `feedit` (optional) - Feed edit parameter
- `k` (optional) - Keyword parameter
- `key` (optional) - Alternative key parameter
- `pageid` (optional) - Page identifier
- `version` (optional, default: "1.0") - API version
- `agent` (optional) - User agent
- `referer` (optional) - Referer URL
- `address` (optional) - IP address
- `query` (optional) - Search query
- `uri` (optional) - URI parameter
- `cScript` (optional) - Script identifier
- `blnComplete` (optional) - Completion flag
- `page` (optional, default: "1") - Page number
- `city` (optional) - City parameter
- `cty` (optional) - Alternative city parameter
- `state` (optional) - State parameter
- `st` (optional) - Alternative state parameter
- `category` (optional) - Category parameter
- `c` (optional) - Alternative category parameter

**Notes:**
- Accepts both GET and POST requests
- POST requests can have parameters in query string, form data, or JSON body (replicates PHP `$_REQUEST` behavior)
- Routes to different handlers based on parameters (e.g., WordPress plugin feeds when `apiid`, `apikey`, and `kkyy` are present)

#### `/feed/Articles.php`
Generates homepage/footer content when Action is empty.

**Methods:** `GET`, `POST`

**Parameters:**
- `domain` (optional) - Domain identifier
- `Action` (optional) - Action type to perform
- `agent` (optional) - User agent
- `pageid` (optional) - Page identifier
- `k` (optional) - Keyword parameter
- `referer` (optional) - Referer URL
- `address` (optional) - IP address
- `query` (optional) - Search query
- `uri` (optional) - URI parameter
- `cScript` (optional) - Script identifier
- `version` (optional, default: "1.0") - API version
- `blnComplete` (optional) - Completion flag
- `page` (optional, default: "1") - Page number
- `city` (optional) - City parameter
- `cty` (optional) - Alternative city parameter
- `state` (optional) - State parameter
- `st` (optional) - Alternative state parameter
- `nocache` (optional, default: "0") - Cache control flag

**Notes:**
- Accepts both GET and POST requests
- POST requests can have parameters in query string, form data, or JSON body

### Monitoring Endpoints

The application includes a comprehensive monitoring dashboard accessible at `/monitor/*`. See [MONITORING.md](MONITORING.md) for detailed documentation.

**HTML Endpoints (require authentication):**
- `/monitor/login` - Login page
- `/monitor/logout` - Logout page
- `/monitor/dashboard/page` - Main dashboard
- `/monitor/workers/page` - Worker processes list
- `/monitor/worker/{pid}/page` - Worker details
- `/monitor/worker/{pid}/logs/page` - Worker logs
- `/monitor/health/page` - Health status
- `/monitor/logs/page` - Application logs
- `/monitor/log/{log_hash}/page` - Log entry details
- `/monitor/stats/page` - Statistics page

**JSON Endpoints (no authentication required):**
- `/monitor/dashboard` - Combined dashboard data
- `/monitor/workers` - Worker processes data
- `/monitor/worker/{pid}` - Worker details data
- `/monitor/worker/{pid}/logs` - Worker logs data
- `/monitor/stats` - Request statistics and metrics
- `/monitor/health` - Health check data
- `/monitor/logs` - Application logs data
- `/monitor/log/{log_hash}` - Log entry details data

## Requirements

- Python 3.9+
- AlmaLinux 9 (or compatible)
- MySQL/MariaDB database access

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure with your database credentials:

```bash
cp .env.example .env
# Edit .env with your actual database credentials
```

### Environment Variables

- Database configuration (DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD, DB_CHARSET)
- `USE_JOURNALCTL` - Set to "true" to use systemd journal for logs (default: "false")
- `LOG_FILE_PATH` - Path to log file if not using journalctl (default: "/var/log/frl-python-api/app.log")
- `ENVIRONMENT` - Set to "development" for development mode (affects diagnostic output)

## Running

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production (using Gunicorn - recommended)
gunicorn app.main:app -c gunicorn_config.py
```

For production deployment, see [PRODUCTION.md](PRODUCTION.md).

## Testing

```bash
pytest
```

## Project Structure

```
frl_public_api_production/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── database.py          # Database connection
│   ├── routes/
│   │   ├── feed/            # Feed endpoints
│   │   │   ├── article.py   # Article.php endpoint
│   │   │   └── articles.py  # Articles.php endpoint
│   │   └── monitor.py       # Monitoring endpoints
│   ├── services/            # Business logic
│   │   ├── auth.py          # Authentication services
│   │   └── content.py       # Content generation services
│   └── utils/               # Utilities
├── tests/                   # Tests
├── gunicorn_config.py       # Gunicorn configuration
├── requirements.txt         # Dependencies
└── README.md
```

## Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - VPS deployment guide
- [PRODUCTION.md](PRODUCTION.md) - Production setup and configuration
- [MONITORING.md](MONITORING.md) - Monitoring dashboard documentation

## Features

### Request Tracking
- Automatic request statistics tracking via middleware
- Error tracking (5xx server errors only, 4xx client errors are logged but not counted)
- Request logging at INFO level for all requests
- WARNING level logging for errors (status >= 400)
- Response time tracking

### System Metrics
- CPU usage monitoring
- Memory usage monitoring
- Disk usage monitoring
- Worker process monitoring
- System health checks

### Logging
- Integrated log viewing via web interface
- Log detail pages with traceback extraction
- Support for systemd journalctl or file-based logging
- Log filtering by level (ERROR, WARNING, INFO, DEBUG)
