# Installation Guide

This guide will help you get the Django Social Media Backend up and running, either using Docker Compose (recommended) or via a manual Python setup.

---

## Prerequisites

- **Python 3.10+**
- **Docker & Docker Compose** (optional but recommended)

---

## 1. Unzip the Package
1. Download and unzip `social_media_backend_v1.0.zip`
2. `cd` into the extracted folder:
```bash
cd social_media_backend
```

## 2. Configure Environment Variables
1. Copy the example env file:
```bash
cp .env.example .env
```
2. Open `.env` in your editor and fill in:
    - `DJANGO_SECRET_KEY` (a secure random string)
    - Database settings (SQLite is the default; to user PostgreSQL, set `DATABASE_ENGINE=django.db.backends.postgresql_psycopg2` and the related vars)
    - Optional Celery, AWS S3m and Email credentials

---

## 3. Docker Compose Setup (Recommended)
This starts PostgreSQL, Redis, and Django in containers.
```bash
docker-compose up --build
```
- The first run may take a minute to download images and build the project.
- Containers started:
    - **db** (PostgreSQL) on port 5432
    - **redis** on port 6379
    - **web** (Django) on port 8000

### Create an Admin User
Once up, open a new terminal and run:
```bash
docker-compose exec web python manage.py createsuperuser
```

---

## 4. Manual Python Setup
If you prefer not to use Docker:
```bash
# 1. Create & activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Apply migrations
python manage.py migrate

# 5. Run the development server
python manage.py runserver 0.0.0.0:8000
```

---

## 5. Verify Installation
- **API Base URL**: `http://localhost:8000/api/`
- **Admin Site**: `http://localhost:8000/admin/`

Use Postman or your HTTP client to test endpoints (see `docs/usage.md`).

---

*Now you have the backend running locally. Next, check **docs/usage.md** for example requests.*