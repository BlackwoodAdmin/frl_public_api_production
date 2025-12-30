# FRL Python API

Python implementation of the Free Relevant Links feed endpoints, replicating the PHP `/feed/` endpoints.

## Endpoints

- `/feed/Article.php` - Main content router
- `/feed/Articles.php` - Footer/homepage content
- `/feed/apifeed*.php` - WordPress plugin feeds

## Requirements

- Python 3.9+
- AlmaLinux 9 (or compatible)
- MySQL database access to `freerele_blackwoodproductions` at `10.248.48.202`

## Installation

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
DB_HOST=10.248.48.202
DB_NAME=freerele_blackwoodproductions
DB_USER=freerele_bwp
DB_PASSWORD=your_password
DB_PORT=3306
```

## Running

```bash
# Development
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## Testing

```bash
pytest
```

## Project Structure

```
frl_python_api/
├── app/
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration
│   ├── database.py          # Database connection
│   ├── routes/
│   │   └── feed/            # Feed endpoints
│   ├── services/            # Business logic
│   └── utils/               # Utilities
├── tests/                   # Tests
├── requirements.txt         # Dependencies
└── README.md
```

