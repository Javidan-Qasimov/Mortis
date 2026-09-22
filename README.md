# Mortis

A real-time one-to-one messaging demo built with Flask, SQLAlchemy, and Socket.IO.

## End-to-End Encryption Prototype

New messages are encrypted in the browser using an AES-256-GCM key derived through ECDH P-256 via the Web Crypto API.

The Flask application only sees public identity keys, the encrypted message envelope, and messaging metadata (sender, recipient, timestamp). It never receives the private key or the message plaintext.

The private key exists only in that user's browser local storage.

This is **not Signal Protocol** and does not claim Signal-level security. Signal's official design includes PQXDH/X3DH, prekeys, Double Ratchet, continuously evolving message keys, multi-device session management, and long-term secure key storage.

This prototype does not provide forward secrecy, post-compromise recovery, multi-device support, or safety-number verification.

For any real-world sensitive communication product, use a well-audited Signal Protocol client library and obtain independent security audits instead of designing custom cryptography.

## Running on Any Computer

If Docker Desktop is installed, no Python or MySQL installation is required:

```powershell
git clone <GITHUB_REPOSITORY_URL>
cd <PROJECT_FOLDER>
Copy-Item .env.example .env
# Replace SECRET_KEY and passwords in .env with strong, unique values.
docker compose up --build
```

Open `http://localhost:5000` in your browser.

By default, the application is accessible only from the same computer.

To stop it, press `Ctrl+C`. If it is running in the background, use:

```powershell
docker compose down
```

To remove the database volume as well:

```powershell
docker compose down -v
```

Adminer is started only when needed:

```powershell
docker compose --profile tools up -d
```

Then access it at:

`http://localhost:8080`

## Making It Accessible from the Internet

GitHub only hosts source code. A publicly accessible application requires a server that remains online.

The most portable approach is to rent a VPS (free or paid), install Docker and Docker Compose, clone this repository, configure production `.env` values, set:

```text
APP_ENV=production
FLASK_DEBUG=false
SESSION_COOKIE_SECURE=true
```

and run the application behind an HTTPS-enabled reverse proxy such as Caddy or Nginx.

In that setup, anyone can access the application through your domain name or server address, and your personal computer does not need to stay online.

Never commit the `.env` file to GitHub.

Only `.env.example` should be shared.

In development, `AUTO_CREATE_SCHEMA=true` automatically creates database tables.

In production, use:

```text
APP_ENV=production
FLASK_DEBUG=false
SESSION_COOKIE_SECURE=true
AUTO_CREATE_SCHEMA=false
```

Run the application behind HTTPS using a production WSGI/ASGI server. Do not use Flask's built-in development server in production.

## Schema Changes

Manage production database schema changes with Flask-Migrate instead of `create_all()`:

```powershell
cd backend
flask --app app db init
flask --app app db migrate -m "describe change"
flask --app app db upgrade
```

## Testing

Run:

```powershell
pytest
```

from the project root.

The test suite uses an in-memory SQLite database.

## Security Notes

* `.env` is excluded from Git; only `.env.example` is shared.
* MySQL and Adminer ports are bound only to localhost.
* Forms are protected against CSRF attacks. Socket.IO events include recipient validation, message size limits, and per-operation rate limiting.
* For multi-process production deployments, configure a shared message queue for Socket.IO and a distributed rate-limit backend (for example, Redis).
