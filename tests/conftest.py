import os
import sys
from pathlib import Path

os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("DB_USER", "test-user")
os.environ.setdefault("DB_PASSWORD", "test-password")
os.environ.setdefault("AUTO_CREATE_SCHEMA", "false")

BACKEND_DIRECTORY = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIRECTORY))

import pytest

from app import create_app
from extensions import db


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
            "SQLALCHEMY_DATABASE_URI": "sqlite://",
        }
    )
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()
