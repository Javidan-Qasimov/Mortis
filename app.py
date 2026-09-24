"""Run the Homis Flask app from the project root with ``python app.py``."""

import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir))

from app import app, socketio  # noqa: E402


if __name__ == "__main__":
    from app import FLASK_DEBUG, os  # noqa: E402

    socketio.run(
        app,
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", 5000)),
        debug=FLASK_DEBUG,
    )
