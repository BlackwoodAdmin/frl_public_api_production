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
git clone https://github.com/YOUR_USERNAME/frl-python-api.git
cd frl-python-api
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

## Step 5: Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env file with your database credentials
nano .env
```

Update the `.env` file with your actual database credentials:
```
DB_HOST=your_database_host
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_CHARSET=utf8mb4
```

**Note:** The `.env` file is in `.gitignore` and will not be committed to GitHub. Make sure to configure it with your actual database credentials on the VPS.

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
WorkingDirectory=/home/your_username/frl-python-api
Environment="PATH=/home/your_username/frl-python-api/venv/bin"
ExecStart=/home/your_username/frl-python-api/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
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

```bash
# Install Nginx
sudo dnf install nginx -y

# Create Nginx config
sudo nano /etc/nginx/conf.d/frl-api.conf
```

Add:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Start Nginx:
```bash
sudo systemctl enable nginx
sudo systemctl start nginx
```

