# Steps to Push to GitHub and Update VPS

## Step 1: Push Changes to GitHub (from your local Windows machine)

1. **Navigate to the project directory:**
   ```bash
   cd C:\Users\seowe\Downloads\frl_python_api
   ```
   (Or wherever your local project is located)

2. **Check what files have changed:**
   ```bash
   git status
   ```

3. **Add all new/modified files:**
   ```bash
   git add .
   ```

4. **Commit the changes:**
   ```bash
   git commit -m "Add Article.php endpoint with feededit=2 footer generation"
   ```

5. **Push to GitHub:**
   ```bash
   git push origin main
   ```

## Step 2: Update VPS (on your AlmaLinux server)

1. **SSH into your VPS:**
   ```bash
   ssh root@publichost1
   ```

2. **Navigate to the project directory:**
   ```bash
   cd /var/www/frl-python-api
   ```

3. **Activate the virtual environment:**
   ```bash
   source venv/bin/activate
   ```

4. **Pull the latest changes from GitHub:**
   ```bash
   git pull origin main
   ```

5. **Install any new dependencies (if requirements.txt was updated):**
   ```bash
   pip install -r requirements.txt
   ```

6. **Restart the FastAPI service (if running as systemd service):**
   ```bash
   sudo systemctl restart frl-api
   ```
   
   OR if running manually, stop the current process (Ctrl+C) and restart:
   ```bash
   uvicorn app.main:app --host 127.0.0.1 --port 8000
   ```

7. **Check if the service is running:**
   ```bash
   sudo systemctl status frl-api
   ```
   
   OR check the process:
   ```bash
   ps aux | grep uvicorn
   ```

8. **Test the endpoint:**
   ```bash
   curl "http://localhost:8000/feed/Article.php?feedit=2&domain=seolocal.it.com&apiid=53084&apikey=347819526879185&kkyy=AKhpU6QAbMtUDTphRPCezo96CztR9EXR"
   ```

## Troubleshooting

- **If git pull fails with conflicts:** You may need to stash local changes first:
  ```bash
  git stash
  git pull origin main
  git stash pop
  ```

- **If the service won't start:** Check the logs:
  ```bash
  sudo journalctl -u frl-api -n 50
  ```

- **If there are import errors:** Make sure you're in the virtual environment and all dependencies are installed.

