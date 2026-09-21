"""
app.py - Entry point for the Homis app.

A small Flask + Flask-SocketIO application that provides:
    * username/password authentication (login + on-the-fly account creation)
    * an inbox view listing every conversation the logged-in user has had
    * real-time 1-to-1 chat powered by Socket.IO rooms

Data is persisted in a MySQL database (see docker-compose.yml for the local
dev container). Connection settings are read from environment variables so
the same code can run locally and in production without modification (see
config.py).

SECURITY: passwords are hashed with argon2id before ever reaching MySQL
(see security.py). The database only ever stores/sees the argon2 hash -
never the plaintext password.

This module only wires the pieces together (config, extensions, routes,
sockets) and starts the server - it intentionally contains no business
logic of its own. See:
    config.py     - environment/config loading
    extensions.py - shared socketio/limiter instances
    db.py         - Socket.IO room-name helper
    security.py   - password hashing + credential validation
    routes.py     - HTTP routes (Blueprint)
    sockets.py    - Socket.IO event handlers
"""

import os

from flask import Flask

from config import (
    APP_ENV,
    AUTO_CREATE_SCHEMA,
    FLASK_DEBUG,
    MAX_CONTENT_LENGTH,
    PERMANENT_SESSION_LIFETIME,
    SECRET_KEY,
    SESSION_COOKIE_HTTPONLY,
    SESSION_COOKIE_SAMESITE,
    SESSION_COOKIE_SECURE,
    SOCKETIO_CORS_ALLOWED_ORIGINS,
    SQLALCHEMY_DATABASE_URI,
    SQLALCHEMY_TRACK_MODIFICATIONS,
)
from extensions import csrf, db, limiter, migrate, socketio
from routes import bp as main_bp

# Importing sockets.py has the side effect of registering its @socketio.on(...)
# handlers on the shared `socketio` instance from extensions.py. It has no
# other exports, so the "unused import" it looks like to a linter is
# intentional - keep it.
import sockets  # noqa: F401


def create_app(test_config=None):
    """Build and configure the Flask application instance.

    Wrapped in a factory function (rather than doing this at module import
    time) so tests or other entry points can create fresh, isolated app
    instances if needed.

    Returns:
        flask.Flask: the fully configured Flask app.
    """
    # template_folder / static_folder are given explicitly (and pointed one
    # directory up) because app.py now lives inside backend/, one level
    # below the project root where templates/ and static/ actually are.
    # Flask resolves these paths relative to this file's own location, not
    # the current working directory, so this works no matter where you run
    # `python app.py` from.
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_mapping(
        SECRET_KEY=SECRET_KEY,
        SQLALCHEMY_DATABASE_URI=SQLALCHEMY_DATABASE_URI,
        SQLALCHEMY_TRACK_MODIFICATIONS=SQLALCHEMY_TRACK_MODIFICATIONS,
        SESSION_COOKIE_SECURE=SESSION_COOKIE_SECURE,
        SESSION_COOKIE_HTTPONLY=SESSION_COOKIE_HTTPONLY,
        SESSION_COOKIE_SAMESITE=SESSION_COOKIE_SAMESITE,
        PERMANENT_SESSION_LIFETIME=PERMANENT_SESSION_LIFETIME,
        MAX_CONTENT_LENGTH=MAX_CONTENT_LENGTH,
    )
    if test_config:
        app.config.update(test_config)

    db.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)
    limiter.init_app(app)
    socketio.init_app(app, cors_allowed_origins=SOCKETIO_CORS_ALLOWED_ORIGINS)

    app.register_blueprint(main_bp)

    if AUTO_CREATE_SCHEMA or app.config.get("TESTING"):
        with app.app_context():
            db.create_all()

    @app.after_request
    def add_security_headers(response):
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.headers.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self' https://cdn.socket.io; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; img-src 'self' data:; "
            "connect-src 'self' ws: wss:; frame-ancestors 'none'; base-uri 'self'",
        )
        if APP_ENV == "production":
            response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
        return response

    return app


app = create_app()


if __name__ == "__main__":
    # debug=True enables the auto-reloader and interactive debugger - handy
    # for local development, but must be disabled in production since it
    # can expose a remote code execution vector via the Werkzeug debugger.
    socketio.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=FLASK_DEBUG,
    )
