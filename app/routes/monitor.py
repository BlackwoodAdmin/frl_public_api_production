"""Monitoring endpoints for Gunicorn workers and system health."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse, JSONResponse
from typing import List, Dict, Any, Optional
import psutil
import os
import time
import logging
from datetime import datetime
from app.database import db

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory stats tracking
_stats = {
    "total_requests": 0,
    "request_times": [],
    "errors": 0,
    "start_time": time.time(),
    "last_minute_requests": [],
}


def _get_gunicorn_processes():
    """Find Gunicorn master and worker processes."""
    processes = []
    master_pid = None
    
    # Strategy 1: Look for process with 'gunicorn' and 'app.main:app' in cmdline
    for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
        try:
            pinfo = proc.info
            cmdline = pinfo.get('cmdline', [])
            
            if not cmdline:
                continue
                
            cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
            
            # Check if this is a Gunicorn master process
            if 'gunicorn' in cmdline_str and 'app.main:app' in cmdline_str:
                master_pid = pinfo['pid']
                break
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue
    
    # Strategy 2: If not found, look for gunicorn process with proc_name 'frl-python-api'
    if not master_pid:
        for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'ppid', 'create_time']):
            try:
                pinfo = proc.info
                cmdline = pinfo.get('cmdline', [])
                
                if not cmdline:
                    continue
                    
                cmdline_str = ' '.join(str(arg) for arg in cmdline).lower()
                
                if 'gunicorn' in cmdline_str:
                    # Check if it's the master (has proc_name or no gunicorn parent)
                    try:
                        parent = psutil.Process(pinfo['pid']).parent()
                        parent_cmdline = parent.cmdline() if parent else []
                        parent_str = ' '.join(str(arg) for arg in parent_cmdline).lower()
                        
                        # Master process typically doesn't have a gunicorn parent
                        if 'gunicorn' not in parent_str:
                            master_pid = pinfo['pid']
                            break
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        # If we can't check parent, assume it might be master
                        if 'frl-python-api' in cmdline_str or 'gunicorn_config' in cmdline_str:
                            master_pid = pinfo['pid']
                            break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    # Get worker processes from master
    if master_pid:
        try:
            master_proc = psutil.Process(master_pid)
            # Get all child processes (workers)
            for child in master_proc.children(recursive=False):
                try:
                    create_time = child.create_time()
                    mem_info = child.memory_info()
                    
                    processes.append({
                        "pid": child.pid,
                        "cpu_percent": 0,  # Will be updated in get_workers
                        "memory_mb": round(mem_info.rss / 1024 / 1024, 2),
                        "uptime_seconds": int(time.time() - create_time),
                        "status": child.status()
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    return processes, master_pid


@router.get("/workers", response_class=JSONResponse)
async def get_workers():
    """Get Gunicorn worker process information."""
    try:
        workers, master_pid = _get_gunicorn_processes()
        
        # Update CPU percentages (needs a small delay for accurate reading)
        for worker in workers:
            try:
                proc = psutil.Process(worker['pid'])
                worker['cpu_percent'] = proc.cpu_percent(interval=0.1)
                mem_info = proc.memory_info()
                worker['memory_mb'] = round(mem_info.rss / 1024 / 1024, 2)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                worker['status'] = 'dead'
        
        return {
            "master_pid": master_pid,
            "total_workers": len(workers),
            "workers": workers
        }
    except Exception as e:
        logger.error(f"Error getting worker info: {e}")
        return {
            "master_pid": None,
            "total_workers": 0,
            "workers": [],
            "error": str(e)
        }


@router.get("/stats", response_class=JSONResponse)
async def get_stats():
    """Get request statistics and performance metrics."""
    try:
        current_time = time.time()
        
        # Clean old request times (older than 1 minute)
        _stats["last_minute_requests"] = [
            t for t in _stats["last_minute_requests"]
            if current_time - t < 60
        ]
        
        # Calculate average response time
        avg_response_time = 0
        if _stats["request_times"]:
            recent_times = _stats["request_times"][-100:]  # Last 100 requests
            avg_response_time = sum(recent_times) / len(recent_times) if recent_times else 0
        
        # Calculate error rate
        total_requests = _stats["total_requests"]
        error_rate = _stats["errors"] / total_requests if total_requests > 0 else 0
        
        # Get active workers
        workers, _ = _get_gunicorn_processes()
        active_workers = len([w for w in workers if w.get('status') == 'running'])
        
        return {
            "total_requests": total_requests,
            "requests_per_minute": len(_stats["last_minute_requests"]),
            "average_response_time_ms": round(avg_response_time * 1000, 2),
            "error_rate": round(error_rate, 4),
            "active_workers": active_workers,
            "uptime_seconds": int(current_time - _stats["start_time"]),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        return {
            "error": str(e),
            "total_requests": 0,
            "requests_per_minute": 0,
            "average_response_time_ms": 0,
            "error_rate": 0,
            "active_workers": 0
        }


@router.get("/health", response_class=JSONResponse)
async def get_health():
    """Get system health status."""
    try:
        # Check database connectivity
        db_healthy = False
        try:
            db.fetch_one("SELECT 1")
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        
        # Check worker availability
        workers, master_pid = _get_gunicorn_processes()
        workers_healthy = len(workers) > 0 and master_pid is not None
        
        overall_status = "healthy" if (db_healthy and workers_healthy) else "degraded"
        
        return {
            "status": overall_status,
            "database": {
                "status": "healthy" if db_healthy else "unhealthy",
                "connected": db_healthy
            },
            "workers": {
                "status": "healthy" if workers_healthy else "unhealthy",
                "count": len(workers),
                "master_pid": master_pid
            },
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except Exception as e:
        logger.error(f"Error getting health: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """HTML dashboard for monitoring Gunicorn workers."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gunicorn Worker Monitor</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            color: #333;
            padding: 20px;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            color: #2c3e50;
            font-size: 24px;
        }
        .refresh-indicator {
            display: flex;
            align-items: center;
            gap: 10px;
            color: #666;
            font-size: 14px;
        }
        .refresh-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            background: #4CAF50;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .stat-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .stat-value {
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }
        .stat-unit {
            font-size: 14px;
            color: #999;
            font-weight: normal;
        }
        .workers-section {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .workers-section h2 {
            margin-bottom: 20px;
            color: #2c3e50;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th {
            text-align: left;
            padding: 12px;
            background: #f8f9fa;
            color: #666;
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            border-bottom: 2px solid #e0e0e0;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e0e0e0;
        }
        tr:hover {
            background: #f8f9fa;
        }
        .status-badge {
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }
        .status-running {
            background: #d4edda;
            color: #155724;
        }
        .status-idle {
            background: #fff3cd;
            color: #856404;
        }
        .status-dead {
            background: #f8d7da;
            color: #721c24;
        }
        .loading {
            text-align: center;
            padding: 40px;
            color: #666;
        }
        .error {
            background: #f8d7da;
            color: #721c24;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 20px;
        }
        .uptime {
            color: #666;
            font-size: 12px;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Gunicorn Worker Monitor</h1>
            <div class="refresh-indicator">
                <div class="refresh-dot"></div>
                <span>Auto-refreshing every 5 seconds</span>
            </div>
        </header>
        
        <div id="error-container"></div>
        
        <div class="stats-grid" id="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Requests</div>
                <div class="stat-value" id="total-requests">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Requests/Min</div>
                <div class="stat-value" id="requests-per-minute">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Avg Response Time</div>
                <div class="stat-value" id="avg-response-time">-<span class="stat-unit"> ms</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Error Rate</div>
                <div class="stat-value" id="error-rate">-<span class="stat-unit">%</span></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Active Workers</div>
                <div class="stat-value" id="active-workers">-</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Uptime</div>
                <div class="stat-value" id="uptime">-</div>
            </div>
        </div>
        
        <div class="workers-section">
            <h2>Worker Processes</h2>
            <div id="workers-container" class="loading">Loading workers...</div>
        </div>
    </div>
    
    <script>
        function formatUptime(seconds) {
            const days = Math.floor(seconds / 86400);
            const hours = Math.floor((seconds % 86400) / 3600);
            const minutes = Math.floor((seconds % 3600) / 60);
            const secs = seconds % 60;
            
            if (days > 0) return `${days}d ${hours}h ${minutes}m`;
            if (hours > 0) return `${hours}h ${minutes}m`;
            if (minutes > 0) return `${minutes}m ${secs}s`;
            return `${secs}s`;
        }
        
        function formatMemory(mb) {
            if (mb >= 1024) return (mb / 1024).toFixed(2) + ' GB';
            return mb.toFixed(2) + ' MB';
        }
        
        async function fetchWorkers() {
            try {
                const response = await fetch('/monitor/workers');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                if (data.workers.length === 0) {
                    document.getElementById('workers-container').innerHTML = 
                        '<div class="loading">No workers found. Make sure Gunicorn is running.</div>';
                    return;
                }
                
                let html = '<table><thead><tr>';
                html += '<th>PID</th>';
                html += '<th>CPU %</th>';
                html += '<th>Memory</th>';
                html += '<th>Uptime</th>';
                html += '<th>Status</th>';
                html += '</tr></thead><tbody>';
                
                data.workers.forEach(worker => {
                    html += '<tr>';
                    html += '<td>' + worker.pid + '</td>';
                    html += '<td>' + worker.cpu_percent.toFixed(2) + '%</td>';
                    html += '<td>' + formatMemory(worker.memory_mb) + '</td>';
                    html += '<td class="uptime">' + formatUptime(worker.uptime_seconds) + '</td>';
                    html += '<td><span class="status-badge status-' + worker.status + '">' + worker.status + '</span></td>';
                    html += '</tr>';
                });
                
                html += '</tbody></table>';
                html += '<div style="margin-top: 10px; color: #666; font-size: 12px;">';
                html += 'Master PID: ' + (data.master_pid || 'N/A') + ' | Total Workers: ' + data.total_workers;
                html += '</div>';
                
                document.getElementById('workers-container').innerHTML = html;
            } catch (error) {
                document.getElementById('workers-container').innerHTML = 
                    '<div class="error">Error fetching workers: ' + error.message + '</div>';
            }
        }
        
        async function fetchStats() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.error) {
                    document.getElementById('error-container').innerHTML = 
                        '<div class="error">Error: ' + data.error + '</div>';
                    return;
                }
                
                document.getElementById('total-requests').textContent = data.total_requests.toLocaleString();
                document.getElementById('requests-per-minute').textContent = data.requests_per_minute;
                document.getElementById('avg-response-time').innerHTML = 
                    data.average_response_time_ms.toFixed(2) + '<span class="stat-unit"> ms</span>';
                document.getElementById('error-rate').innerHTML = 
                    (data.error_rate * 100).toFixed(2) + '<span class="stat-unit">%</span>';
                document.getElementById('active-workers').textContent = data.active_workers;
                document.getElementById('uptime').textContent = formatUptime(data.uptime_seconds);
                
                document.getElementById('error-container').innerHTML = '';
            } catch (error) {
                document.getElementById('error-container').innerHTML = 
                    '<div class="error">Error fetching stats: ' + error.message + '</div>';
            }
        }
        
        async function refresh() {
            await Promise.all([fetchWorkers(), fetchStats()]);
        }
        
        // Initial load
        refresh();
        
        // Auto-refresh every 5 seconds
        setInterval(refresh, 5000);
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)

