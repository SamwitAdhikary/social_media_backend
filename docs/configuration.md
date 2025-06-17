# Configuration Guide

This guide explains all environment variables and settings you can customize in the Social Media Backend. Copy and edit the `.env.example` to suit your environment.

---

## 1. Django Core Settings

| Variable                   | Description                                                      | Example                              |
| -------------------------- | ---------------------------------------------------------------- | ------------------------------------ |
| `DJANGO_SECRET_KEY`        | Secret key for cryptographic signing. **Must be unique & secret.** | `b7!x@9z#K3mL2pOqRsTuVwXyZ`        |
| `DEBUG`                    | Enable debug mode. Set to `1` for development, `0` for production. | `1`                                   |
| `DJANGO_SETTINGS_MODULE`   | The Python path to your settings module.                         | `social_network.settings`           |

---

## 2. Database Configuration

By default, the demo uses SQLite. To switch to PostgreSQL, uncomment the Postgres section and set the appropriate values.

### SQLite (default)

```dotenv
DATABASE_ENGINE=django.db.backends.sqlite3
DATABASE_NAME=db.sqlite3
```

### PostgreSQL
```dotenv
DATABASE_ENGINE=django.db.backends.postgresql_psycopg2
DATABASE_NAME=your_db_name
DATABASE_USER=your_db_user
DATABASE_PASSWORD=your_db_password
DATABASE_HOST=your_db_host      # e.g. db (Docker) or localhost
DATABASE_PORT=5432
```

---

## 3. AWS S3 Media Storage
```dotenv
AWS_ACCESS_KEY_ID=your-aws-access-key
AWS_SECRET_ACCESS_KEY=your-aws-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket-name
AWS_S3_REGION_NAME=ap-south-1
AWS_S3_ADDRESSING_STYLE=virtual

AWS_DEFAULT_ACL=public-read
AWS_LOCATION=media
AWS_S3_SIGNATURE_VERSION=s3v4

# Choose storage backend (default in settings)
DEFAULT_FILE_STORAGE=storages.backends.s3boto3.S3Boto3Storage
MEDIA_URL=https://your-bucket-name.s3.amazonaws.com/media/
```

---

## 4. Celery (Optional)
To enable background task processing (e.g. email sending, thumbnail generation):
```dotenv
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=django-db

# (Optional) Content types to accept
CELERY_ACCEPT_CONTENT=json
CELERY_TASK_SERIALIZER=json
CELERY_RESULT_SERIALIZER=json
```

---

## 5. Email Backend
Configure how emails (OTP, password reset) are sent:
```dotenv
# For development: use console backend
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend

# For production (SMTP)
# EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
# EMAIL_HOST=smtp.gmail.com
# EMAIL_PORT=587
# EMAIL_USE_TLS=True
# EMAIL_HOST_USER=your-email@example.com
# EMAIL_HOST_PASSWORD=your-email-password
DEFAULT_FROM_EMAIL=your-email@example.com
```

---

## 6. Django REST Framework & JWT
These are set in `settings.py`, but you can tweak token lifetimes:
```python
# in settings.py
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(days=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

--- 

## 7. CORS
Allow origins for cross‑domain API access:
```dotenv
# In .env.example (used by CORS middleware)
CORS_ALLOWED_ORIGINS=http://localhost:3000
```
Add any front‑end domains (e.g. staging or production URLs) separated by commas.

---

## 8. Miscellaneous
- **Time Zone**:
    - In `settings.py`:`TIME_ZONE = 'Asia/Kolkata'`
- **Static Files**:
    - Serve via `STATIC_URL = 'static/` and configure a static files storage if needed.
- **Logging**:
    - Adjust log levels and file paths in the `LOGGING` section of `settings.py`.

---

*For any further customization, refer directly to `settings.py`. Happy Coding!*