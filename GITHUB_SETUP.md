# GitHub Setup Instructions

## Step 1: Initialize Git Repository

```bash
cd frl_python_api
git init
git add .
git commit -m "Initial commit: FRL Python API project structure"
```

## Step 2: Create Repository on GitHub

1. Go to your GitHub account
2. Click "New repository"
3. Name it: `frl-python-api` (or your preferred name)
4. Don't initialize with README (we already have one)
5. Click "Create repository"

## Step 3: Connect and Push

```bash
# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/frl-python-api.git

# Push to GitHub
git branch -M main
git push -u origin main
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 4: On Your VPS - Clone the Repository

```bash
# SSH into your VPS
ssh user@your-vps-ip

# Clone the repository
git clone https://github.com/YOUR_USERNAME/frl-python-api.git
cd frl-python-api
```

