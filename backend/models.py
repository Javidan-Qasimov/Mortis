"""SQLAlchemy models for the application's persistent data."""

from extensions import db


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)


class Message(db.Model):
    __tablename__ = "messages"

    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(150), nullable=False, index=True)
    receiver = db.Column(db.String(150), nullable=False, index=True)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now(), index=True
    )


class IdentityKey(db.Model):
    """A user's immutable public E2EE identity key.

    The matching private key is generated and kept only in that user's
    browser; it is never sent to this Flask application.
    """

    __tablename__ = "identity_keys"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False, index=True)
    public_key = db.Column(db.Text, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True), nullable=False, server_default=db.func.now()
    )
