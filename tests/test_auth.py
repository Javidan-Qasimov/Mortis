from extensions import db
from models import User


def test_create_account_hashes_the_password(client, app):
    response = client.post(
        "/create", data={"username": "alice", "password": "safe-pass-123"}
    )

    assert response.status_code == 302
    with app.app_context():
        user = db.session.scalar(db.select(User).filter_by(username="alice"))
        assert user is not None
        assert user.password != "safe-pass-123"
        assert user.password.startswith("$argon2")


def test_home_requires_an_authenticated_session(client):
    assert client.get("/home").status_code == 302


def test_public_identity_key_is_registered_without_a_private_key(client):
    client.post("/create", data={"username": "alice", "password": "safe-pass-123"})
    key = {
        "kty": "EC",
        "crv": "P-256",
        "x": "example-public-x-coordinate",
        "y": "example-public-y-coordinate",
        "ext": True,
    }

    response = client.post("/keys/me", json={"public_key": key})

    assert response.status_code == 201
    response = client.get("/keys/alice")
    assert response.status_code == 200
    assert response.json["public_key"] == key
