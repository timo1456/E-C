# E-C Store

A small Flask e-commerce application using SQLite.

## Stack

- Flask
- Flask-SQLAlchemy
- SQLite
- HTML/CSS
- Gunicorn for conventional WSGI hosting

## Local setup

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000.

## Default admin

- Email: admin@store.com
- Password: admin

Change the credentials before using the application publicly.

## Vercel

Vercel supports Flask applications directly, so this project keeps the Flask entry point at `app.py` and does not use an `api/` wrapper.

The application automatically uses `/tmp/store.db` when Vercel sets the `VERCEL` environment variable. This makes SQLite usable for the running function, but Vercel's deployed filesystem is not persistent storage. Product/user changes made at runtime therefore should not be treated as permanent data.

For persistent SQLite data, use a host that provides a persistent disk. For a production multi-instance store, use a hosted database instead.

## Health check

Visit:

```
/health
```

Expected response:

```json
{"database":"sqlite","status":"ok"}
```
