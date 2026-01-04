"""Shared components for monitoring pages: navigation menu and system metrics."""


def get_nav_menu_css() -> str:
    """Returns CSS for the navigation menu."""
    return """
        .nav-menu {
            background: white;
            padding: 15px 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .nav-menu ul {
            list-style: none;
            display: flex;
            gap: 20px;
            flex-wrap: wrap;
            margin: 0;
            padding: 0;
        }
        .nav-menu li {
            margin: 0;
        }
        .nav-menu a {
            color: #2c3e50;
            text-decoration: none;
            font-weight: 500;
            padding: 8px 16px;
            border-radius: 4px;
            transition: background-color 0.2s;
            display: inline-block;
        }
        .nav-menu a:hover {
            background-color: #f0f0f0;
        }
        .nav-menu a.active {
            background-color: #2c3e50;
            color: white;
        }
    """


def get_nav_menu_html(active_page: str = "") -> str:
    """
    Returns navigation menu HTML without workers link.
    
    Args:
        active_page: Name of the active page ('dashboard', 'health', or 'logs')
                    to apply the 'active' class
    """
    dashboard_class = ' class="active"' if active_page == 'dashboard' else ''
    health_class = ' class="active"' if active_page == 'health' else ''
    logs_class = ' class="active"' if active_page == 'logs' else ''
    
    return f"""
        <nav class="nav-menu">
            <ul>
                <li><a href="/monitor/dashboard/page"{dashboard_class}>Dashboard</a></li>
                <li><a href="/monitor/health/page"{health_class}>Health</a></li>
                <li><a href="/monitor/logs/page"{logs_class}>Logs</a></li>
            </ul>
        </nav>
    """


def get_system_metrics_css() -> str:
    """Returns CSS for the System Metrics section."""
    return """
        .system-metrics {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .system-metrics h2 {
            color: #2c3e50;
            font-size: 18px;
            margin-bottom: 15px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
        }
        .metric-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }
        .metric-label {
            font-size: 12px;
            color: #666;
            text-transform: uppercase;
            margin-bottom: 8px;
        }
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            color: #2c3e50;
            margin-bottom: 5px;
        }
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #e0e0e0;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 8px;
        }
        .progress-fill {
            height: 100%;
            background: #4CAF50;
            transition: width 0.9s ease;
        }
        .progress-fill.warning {
            background: #ff9800;
        }
        .progress-fill.danger {
            background: #f44336;
        }
    """


def get_system_metrics_html() -> str:
    """Returns System Metrics HTML structure."""
    return """
        <div class="system-metrics" id="system-metrics">
            <h2>System Metrics</h2>
            <div class="metrics-grid">
                <div class="metric-item">
                    <div class="metric-label">CPU Usage</div>
                    <div class="metric-value" id="cpu-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="cpu-progress" style="width: 0%"></div>
                    </div>
                </div>
                <div class="metric-item">
                    <div class="metric-label">Memory Usage</div>
                    <div class="metric-value" id="memory-percent">-</div>
                    <div class="progress-bar">
                        <div class="progress-fill" id="memory-progress" style="width: 0%"></div>
                    </div>
                    <div style="font-size: 12px; color: #666; margin-top: 5px;" id="memory-details">-</div>
                </div>
            </div>
        </div>
    """


def get_system_metrics_js() -> str:
    """Returns JavaScript function for fetching and updating system metrics."""
    return """
        async function fetchSystemMetrics() {
            try {
                const response = await fetch('/monitor/stats');
                const data = await response.json();
                
                if (data.system) {
                    const cpuPercent = data.system.cpu_percent;
                    const memPercent = data.system.memory_percent;
                    
                    document.getElementById('cpu-percent').textContent = cpuPercent.toFixed(1) + '%';
                    const cpuProgress = document.getElementById('cpu-progress');
                    cpuProgress.style.width = cpuPercent + '%';
                    cpuProgress.className = 'progress-fill' + 
                        (cpuPercent > 80 ? ' danger' : cpuPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-percent').textContent = memPercent.toFixed(1) + '%';
                    const memProgress = document.getElementById('memory-progress');
                    memProgress.style.width = memPercent + '%';
                    memProgress.className = 'progress-fill' + 
                        (memPercent > 80 ? ' danger' : memPercent > 60 ? ' warning' : '');
                    
                    document.getElementById('memory-details').textContent = 
                        data.system.memory_used_gb.toFixed(2) + ' GB / ' + 
                        data.system.memory_total_gb.toFixed(2) + ' GB';
                }
            } catch (error) {
                // Silently fail - don't break the page if system metrics fail
            }
        }
    """

