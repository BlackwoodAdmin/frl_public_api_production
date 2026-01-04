# Monitoring Dashboard Documentation

The FRL Python API includes a comprehensive monitoring dashboard for tracking system health, worker processes, request statistics, and application logs.

## Overview

The monitoring dashboard provides:
- Real-time system metrics (CPU, memory, disk usage)
- Worker process monitoring and details
- Request statistics and error tracking
- Application log viewing with filtering
- Health status monitoring
- Detailed log entry viewing with traceback extraction

## Accessing the Dashboard

### Login

Access the monitoring dashboard at:
```
http://your-domain.com/monitor/login
```

Or if accessing locally:
```
http://localhost:8000/monitor/login
```

### Authentication

HTML endpoints require authentication using Basic Authentication. JSON endpoints do not require authentication.

**Setting Up Authentication:**

Authentication credentials are configured via environment variables. Set these in your `.env` file:

```env
DASHBOARD_USERNAME=your_username
DASHBOARD_PASSWORD=your_password
```

The `validate_dashboard_credentials()` function in `app/services/auth.py` validates credentials against these environment variables.

**Default Behavior:**
- HTML endpoints redirect to `/monitor/login` if not authenticated
- JSON endpoints are publicly accessible (no authentication)
- Session credentials are stored in browser sessionStorage for HTML page requests

## Dashboard Pages

### Main Dashboard (`/monitor/dashboard/page`)

The main dashboard provides an overview of:
- System metrics (CPU usage, memory usage, disk usage)
- Request statistics (total requests, requests per minute, average response time, error rate)
- Active workers count
- Application uptime
- Worker processes table with real-time updates

**Features:**
- Auto-refreshes every 0.5 seconds
- System metrics update in real-time
- Worker process status and resource usage

### Workers Page (`/monitor/workers/page`)

Displays a list of all Gunicorn worker processes with:
- Process ID (PID)
- CPU usage percentage
- Memory usage
- Uptime
- Process status (running, idle, dead)

Click on a PID to view detailed information about that worker.

### Worker Details (`/monitor/worker/{pid}/page`)

Detailed information about a specific worker process:
- Process information (PID, name, status, command line)
- CPU usage and times
- Memory usage (RSS, VMS, shared, text, data)
- Child processes
- Threads information
- Open files
- I/O statistics
- Worker logs

### Worker Logs (`/monitor/worker/{pid}/logs/page`)

View logs filtered by a specific worker PID:
- Log entries from the specified worker process
- Filter by log level (ERROR, WARNING, INFO, DEBUG)
- Adjustable limit (100, 500, 1000, 5000)
- Auto-refresh option

### Health Status (`/monitor/health/page`)

System health monitoring:
- Overall system status (healthy, degraded, unhealthy)
- Database connectivity status
- Worker availability status
- Worker count and master PID
- System metrics (CPU, memory, disk)

### Logs Page (`/monitor/logs/page`)

Application log viewer:
- View all application logs
- Filter by log level (ERROR, WARNING, INFO, DEBUG, or All)
- Adjustable limit (100, 500, 1000, 5000)
- Auto-scroll and auto-refresh options
- Click on log timestamps to view detailed log entry information
- System metrics display (CPU, memory, disk)

### Log Details (`/monitor/log/{log_hash}/page`)

Detailed view of a specific log entry:
- Full log message
- Raw log message (for copying)
- Traceback extraction (if present)
- Metadata (PID, file path, line number, source, log hash)
- System metrics display (CPU, memory, disk)

**Features:**
- Copy raw message button
- Copy traceback button (if traceback exists)
- Link back to logs page

### Statistics Page (`/monitor/stats/page`)

Request statistics and performance metrics:
- Total requests
- Requests per minute
- Average response time
- Error rate (only 5xx server errors)
- Active workers
- Uptime
- System metrics (CPU, memory, disk)

## JSON API Endpoints

All monitoring data is also available as JSON endpoints for programmatic access:

### `/monitor/dashboard`
Returns combined dashboard data including stats and workers.

**Response:**
```json
{
  "stats": {
    "total_requests": 1234,
    "errors": 5,
    "requests_per_minute": 10.5,
    "average_response_time_ms": 45.2,
    "error_rate": 0.0041,
    "active_workers": 4,
    "uptime_seconds": 3600,
    "system": {
      "cpu_percent": 25.5,
      "cpu_count": 4,
      "memory_percent": 45.2,
      "memory_total_gb": 8.0,
      "memory_used_gb": 3.6,
      "memory_available_gb": 4.4,
      "disk_percent": 62.5,
      "disk_total_gb": 100.0,
      "disk_used_gb": 62.5,
      "disk_free_gb": 37.5
    }
  },
  "workers": {
    "master_pid": 12345,
    "total_workers": 4,
    "workers": [...]
  }
}
```

### `/monitor/workers`
Returns worker process information.

**Response:**
```json
{
  "master_pid": 12345,
  "total_workers": 4,
  "workers": [
    {
      "pid": 12346,
      "status": "running",
      "cpu_percent": 5.2,
      "memory_mb": 125.5,
      "uptime_seconds": 3600
    },
    ...
  ]
}
```

### `/monitor/worker/{pid}`
Returns detailed information about a specific worker process.

### `/monitor/worker/{pid}/logs`
Returns logs for a specific worker process.

**Query Parameters:**
- `limit` (optional, default: 1000) - Maximum number of log entries
- `level` (optional) - Filter by log level (ERROR, WARNING, INFO, DEBUG)

### `/monitor/stats`
Returns request statistics and system metrics.

**Response:**
```json
{
  "total_requests": 1234,
  "errors": 5,
  "requests_per_minute": 10.5,
  "average_response_time_ms": 45.2,
  "error_rate": 0.0041,
  "active_workers": 4,
  "uptime_seconds": 3600,
  "system": {
    "cpu_percent": 25.5,
    "cpu_count": 4,
    "memory_percent": 45.2,
    "memory_total_gb": 8.0,
    "memory_used_gb": 3.6,
    "memory_available_gb": 4.4,
    "disk_percent": 62.5,
    "disk_total_gb": 100.0,
    "disk_used_gb": 62.5,
    "disk_free_gb": 37.5
  },
  "timestamp": "2026-01-04T12:00:00Z"
}
```

### `/monitor/health`
Returns system health status.

**Response:**
```json
{
  "status": "healthy",
  "database": {
    "status": "healthy",
    "connected": true
  },
  "workers": {
    "status": "healthy",
    "count": 4,
    "master_pid": 12345
  },
  "timestamp": "2026-01-04T12:00:00Z"
}
```

### `/monitor/logs`
Returns application logs.

**Query Parameters:**
- `limit` (optional, default: 1000) - Maximum number of log entries
- `level` (optional) - Filter by log level (ERROR, WARNING, INFO, DEBUG)

**Response:**
```json
{
  "logs": [
    {
      "timestamp": "2026-01-04T12:00:00",
      "level": "INFO",
      "message": "Request processed",
      "module": "app.routes.feed"
    },
    ...
  ],
  "total": 100,
  "source": "journalctl"
}
```

### `/monitor/log/{log_hash}`
Returns detailed information about a specific log entry identified by its hash.

**Response:**
```json
{
  "log_hash": "abc123...",
  "timestamp": "2026-01-04T12:00:00",
  "level": "ERROR",
  "message": "Error message",
  "raw_message": "Full raw log message",
  "module": "app.routes.feed",
  "source": "journalctl",
  "metadata": {
    "pid": 12346,
    "file_path": "/app/routes/feed/article.py",
    "line_number": 123
  },
  "traceback": "Traceback (most recent call last):\n..."
}
```

## Request Statistics and Error Tracking

### Request Tracking

The application automatically tracks all requests via middleware:
- All requests are logged at INFO level (visible in logs page)
- Response times are tracked
- Request counts are maintained
- Statistics are stored in `/var/run/frl-python-api/stats.json`

### Error Tracking

**Error Counting:**
- Only 5xx server errors (500, 502, 503, etc.) are counted in the error rate
- 4xx client errors (400, 401, 404, etc.) are logged at WARNING level but not counted in error rate
- Exceptions (uncaught errors) are counted as errors

**Error Rate Calculation:**
```
error_rate = errors / total_requests
```

**Error Logging:**
- Errors (status >= 400) are logged at WARNING level
- All requests are logged at INFO level
- DEBUG level logs are available for detailed debugging

### Statistics Reset

- Statistics reset automatically when the application restarts (detected via Gunicorn master PID change)
- Error counts reset every 3 hours automatically
- Uptime resets on application restart

## System Metrics

### CPU Usage
- Real-time CPU usage percentage
- Non-blocking measurement (uses cached values)
- Updates every 0.5 seconds on dashboard pages

### Memory Usage
- Real-time memory usage percentage
- Total, used, and available memory in GB
- Updates every 0.5 seconds on dashboard pages

### Disk Usage
- Real-time disk usage percentage
- Total, used, and free disk space in GB
- Updates every 0.5 seconds on dashboard pages

## Logging Configuration

### Log Sources

The application supports two log sources:

1. **systemd journalctl** (recommended for production)
   - Set `USE_JOURNALCTL=true` in `.env`
   - Uses systemd journal for log retrieval
   - Works with systemd service configuration

2. **File-based logging**
   - Set `USE_JOURNALCTL=false` in `.env`
   - Uses log file specified by `LOG_FILE_PATH`
   - Default: `/var/log/frl-python-api/app.log`

### Log Levels

- **ERROR**: Error messages and exceptions
- **WARNING**: Warning messages (including HTTP status >= 400)
- **INFO**: Informational messages (including all requests)
- **DEBUG**: Debug messages (detailed debugging information)

### Request Logging

All requests are logged at INFO level with format:
```
{method} {path} - {status_code} - {response_time}s
```

Example:
```
GET /feed/Article.php - 200 - 0.036s
```

Errors are logged at WARNING level:
```
Request error: GET /feed/Article.php - Status 404 - 0.036s
```

## Troubleshooting

### Dashboard Not Loading

1. Check if the application is running:
   ```bash
   sudo systemctl status frl-python-api
   ```

2. Check application logs:
   ```bash
   sudo journalctl -u frl-python-api -n 50
   ```

3. Verify authentication is configured correctly in `app/services/auth.py`

### Logs Not Appearing

1. Verify logging configuration:
   - Check `USE_JOURNALCTL` environment variable
   - If using file logging, verify `LOG_FILE_PATH` exists and is readable
   - If using journalctl, verify the service is configured with log routing

2. Check log permissions:
   ```bash
   # For file logging
   ls -l /var/log/frl-python-api/app.log
   
   # For journalctl
   journalctl -u frl-python-api -n 50
   ```

### Worker Processes Not Showing

1. Verify Gunicorn is running:
   ```bash
   ps aux | grep gunicorn
   ```

2. Check worker process detection:
   - The monitoring system detects Gunicorn master and worker processes
   - Verify processes are named correctly (gunicorn)

### Statistics Not Updating

1. Check stats file:
   ```bash
   ls -l /var/run/frl-python-api/stats.json
   ```

2. Verify file permissions:
   - Stats file is stored at `/var/run/frl-python-api/stats.json`
   - Ensure the directory exists and is writable

3. Check for app restarts:
   - Statistics reset on application restart
   - Check if the application has been restarted recently

## Security Considerations

- HTML endpoints require authentication
- JSON endpoints are publicly accessible (by design, to prevent authentication loops)
- Session credentials are stored in browser sessionStorage
- Authentication should be configured in `app/services/auth.py`
- Consider firewall rules to restrict access to monitoring endpoints if needed

