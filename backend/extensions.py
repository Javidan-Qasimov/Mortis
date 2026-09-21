"""
extensions.py - Shared Flask extension instances.

flask_socketio and flask_limiter objects are created here, uninitialized
(no app attached yet), and later wired up to the real Flask app in
app.py via socketio.init_app(app) / limiter.init_app(app).

Keeping them in their own module (instead of creating them directly inside
app.py) is what lets routes.py and sockets.py import and use `@limiter.limit`
/ `@socketio.on` as decorators without causing a circular import with
app.py (which needs to import routes.py and sockets.py to register them).
"""

from flask_socketio import SocketIO
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect

socketio = SocketIO()
db = SQLAlchemy()
migrate = Migrate()
csrf = CSRFProtect()

# `default_limits=[]` disables any global/implicit limit; every limit in
# this app is applied explicitly via the `@limiter.limit(...)` decorator
# on specific routes (currently /login and /create).
limiter = Limiter(get_remote_address, default_limits=[])
