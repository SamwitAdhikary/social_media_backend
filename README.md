# Django Social Media Backend

**Version:** 1.0.0 <br>
**Last Updated:** June 16, 2025

A fully-featured, production-ready Django backend for social networking applications. Supports user accounts, posts with media, stories, groups, connections, real-time notifications, and more-packaged with a Docker Compose demo and fixtures for rapid onboarding.

---

## 🔥 Features
- **User Management**
    - Email/password registration with OTP verification
    - JWT-based authentication with optional 2FA via email OTP
    - Password reset and change endpoints

- **Content Models**
    - **Posts**: text content + image/video uploads, hashtags, reactions, comments, shares
    - **Stories**: ephemeral 24-hour media and text stories, view tracking, reactions
    - **Groups**: public/private/secret groups, join requests, member roles, group posts

- **Social Graphs**
    - **Connections**: friend requests (mutual) and one-way follows
    - **Blocking**: user block/unblock endpoints prevent unwanted interactions

- **Real-Time Updates**
    - WebSocket support for live notifications and new-post broadcasts
    - Custom ASGI middleware to authenticate via JWT

- **Storage & Async Tasks**
    - AWS S3 media storage (images, videos, thumbnails)
    - Celery-ready for background tasks (email, thumbnail generations)

- **Administration**
    - Custom Django admin site with dashboard metrics
    - Inline media previews, read-only auditing of notifications

- **Developer Experience**
    - OpenAPI/Swagger-compatible DRF schema
    - Postman collection & curl/HTTPie examples
    - Docker Compose demo with Postgres & Redis
    - JSON fixtures for preloaded demo data

---

## 📦 What's Included
```bash
social_media_backend_v1.0/
├── manage.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── LICENSE.txt
├── CHANGELOG.md
├── social_network/         # Django project settings, URLs, ASGI/WSGI, custom admin
├── accounts/               # User & profile app
├── posts/                  # Post, media, comment, reaction, hashtag apps
├── connections/            # Friend & follower logic
├── groups/                 # Group creation & membership
├── notifications/          # Notification model, WebSocket consumers, API
├── stories/                # Story creation, views, reactions
├── utils/
│   └── aws.py              # S3 upload helper
└── docs/                   # Guides & API reference
    ├── installation.md
    ├── configuration.md
    ├── usage.md
    └── api_reference.md
```
---

## 🚀 Demo Setup
1. **Copy env file**
```bash
cp .env.example .env
```
Edit `.env` to add your own secret key and (optional) credentials.

2. **Start services**
```bash
docker-compose up --build
```
- **PostgreSQL** runs on port 5432
- **Redis** runs on port 6379
- **Django API** runs on port 8000

3. **Access API** <br>
Open your browser or API client to:
```text
http://localhost:8000/
```
---

## ⚙ Manual Installation (Without Docker)
```bash
# 1. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Apply migrations & load demo data
python manage.py migrate

# 5. Run development server
python manage.py runserver
```

---

## 🛠 Configuration
Edit `.env` to configure:
- **Django settings**
    - `DJANGO_SECRET_KEY`
    - `DEBUG=1` or `0`
    - `DJANGO_SETTINGS_MODULE=social_network.settings`

- **Database**
    - `DATABASE_ENGINE` (sqlite3 or postgresql)
    - `DATABASE_NAME`, `DATABASE_USER`, `DATABASE_PASSWORD`, `DATABASE_HOST`, `DATABASE_PORT`

- **AWS S3**
    - `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_STORAGE_BUCKET_NAME`, etc.

- **Celery (optional)**
    - `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`

- **Email**
    - `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`

Refer to docs/configuration.md for full details.

---

## 📚 Documentation & API Reference
- **Installation Guide**: `docs/installation.md`
- **Configuration Guide**: `docs/configuration.md`
- **Usage Examples**: `docs/usage.md`
- **Full API Reference**: `docs/api_reference.md`

---

## 🤝 Support & License
- Licensed under the **MIT License**. See `LICENSE.txt`.
- Includes **3 months** of free email support and minor updates.
- Extended support and custom integrations available upon request.

*Thank you for choosing this Django Social Media Backend -- Happy Coding !*