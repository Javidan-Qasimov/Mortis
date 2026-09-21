"""
routes.py - HTTP routes for the Homis app.

Registered on the Flask app as a Blueprint (see app.py), so this module
never needs to import the `app` object itself and can be imported safely
from app.py without circular-import issues.
"""

import json

from flask import Blueprint, abort, jsonify, request, session, redirect, render_template
from sqlalchemy import case, func, or_
from sqlalchemy.exc import IntegrityError

from extensions import db, limiter
from models import IdentityKey, Message, User
from security import hash_password, verify_password, validate_credentials

bp = Blueprint("main", __name__)


@bp.get("/keys/<username>")
def get_public_key(username):
    """Return a chat participant's public identity key to authenticated users."""
    if "username" not in session:
        abort(401)
    key = db.session.scalar(db.select(IdentityKey).filter_by(username=username))
    if key is None:
        return jsonify({"error": "Identity key not registered."}), 404
    return jsonify({"username": username, "public_key": json.loads(key.public_key)})


@bp.post("/keys/me")
def register_public_key():
    """Register a public key once; replacing it requires an explicit recovery flow."""
    username = session.get("username")
    if not username:
        abort(401)
    payload = request.get_json(silent=True) or {}
    public_key = payload.get("public_key")
    if not isinstance(public_key, dict) or public_key.get("kty") != "EC":
        return jsonify({"error": "Invalid public key."}), 400

    serialized_key = json.dumps(public_key, sort_keys=True, separators=(",", ":"))
    existing = db.session.scalar(db.select(IdentityKey).filter_by(username=username))
    if existing:
        if existing.public_key == serialized_key:
            return "", 204
        return jsonify({"error": "Identity key already exists."}), 409

    db.session.add(IdentityKey(username=username, public_key=serialized_key))
    db.session.commit()
    return "", 201


@bp.route("/")
def login():
    """GET / - Render the login form (entry point of the app)."""
    return render_template("login.html")


@bp.route("/login", methods=["POST"])
@limiter.limit("5 per minute")  # throttle brute-force login attempts per IP
def check():
    """POST /login - Authenticate an existing user.

    Request form fields:
        username (str)
        password (str)

    Flow:
        1. Validate the submitted credentials' format.
        2. Look up the username in the database.
        3. If found, verify the submitted password against the stored
           hash. If it matches, start a session and redirect to /home.
        4. If found but the password does NOT match, stay on the login
           page and show a "wrong password" error.
        5. If the username was not found at all, forward to the
           "create account" form, pre-filled with the username/password
           just typed, so a genuinely new user can register.

    Returns:
        flask.Response: either a redirect to /home on success, or a
        re-rendered login/create template on failure.
    """
    username = request.form["username"]
    password = request.form["password"]

    # --- Step 1: format validation --------------------------------------
    error = validate_credentials(username, password)
    if error:
        return render_template("login.html", error=error)

    # --- Step 2: look up the stored password hash for this username -----
    user = db.session.scalar(db.select(User).filter_by(username=username))

    # --- Step 3: username exists - verify the password against its hash --
    # The stored hash already encodes its own salt, so verify_password()
    # only needs the plaintext attempt and the stored hash - no separate
    # salt column or lookup required.
    if user:
        if verify_password(password, user.password):
            session.clear()
            session.permanent = True
            session["username"] = username
            return redirect("/home")

        # --- Step 4: username exists but the password is wrong -----------
        # Stay on the login page and report the mismatch. We deliberately
        # do NOT forward to create.html here, since that route now refuses
        # to touch an existing account anyway - showing it would just be a
        # dead end for the user.
        return render_template("login.html", error="Wrong password.", username=username)

    # --- Step 5: no account with this username - offer to create one -----
    return render_template("create.html", username=username, password=password)


@bp.route("/create", methods=["POST"])
@limiter.limit("5 per minute")  # throttle account-creation abuse per IP
def create():
    """POST /create - Create a brand-new account.

    Request form fields:
        username (str)
        password (str)

    SECURITY: this route explicitly checks whether the username already
    exists before inserting. If it does, the request is rejected instead
    of touching the existing password - only truly new usernames reach the
    persistence. The submitted password is hashed with hash_password()
    before the User model is saved, so plaintext passwords are never
    written to the database.

    Returns:
        flask.Response: redirect to /home on success, or a re-rendered
        create-account template if validation fails or the username is
        already taken.
    """
    username = request.form["username"]
    password = request.form["password"]

    # Re-validate here as well: this route can be hit directly (not only
    # via the /login fallback), so it needs its own copy of the same check.
    error = validate_credentials(username, password)
    if error:
        return render_template("create.html", username=username, password=password, error=error)

    # Hash before touching the database - the plaintext password is never
    # passed to the User model, only its hash.
    password_hash = hash_password(password)

    try:
        db.session.add(User(username=username, password=password_hash))
        db.session.commit()
    except IntegrityError:
        # The unique constraint is the authoritative check, preventing a
        # second concurrent request from creating the same account.
        db.session.rollback()
        return render_template(
            "create.html",
            username=username,
            password=password,
            error="This username is already taken. Please log in with the correct password instead.",
        )

    session.clear()
    session.permanent = True
    session["username"] = username
    return redirect("/home")


@bp.route("/home")
def home():
    """GET /home - Render the main inbox screen for the logged-in user.

    Requires an active session; unauthenticated visitors are redirected to
    the login page.

    Provides the template with:
        users (list[str]): every registered username, used to populate the
            "start a new chat" search box.
        conversations (list[dict]): one entry per conversation partner,
            containing the most recent message exchanged with them, used
            to render the Instagram-DM-style inbox list.

    Returns:
        flask.Response: the rendered home page, or a redirect to / if the
        user is not logged in.
    """
    if "username" not in session:
        return redirect("/")

    username = session["username"]

    # A conversation can only be started after the recipient has opened the
    # app once and registered a public E2EE identity key in their browser.
    users = list(
        db.session.scalars(
            db.select(User.username)
            .join(IdentityKey, IdentityKey.username == User.username)
            .order_by(User.username)
        ).all()
    )

    # Express the "latest message per partner" query with SQLAlchemy's
    # composable ORM API, rather than embedding a SQL string in the route.
    other_user = case((Message.sender == username, Message.receiver), else_=Message.sender)
    latest_per_partner = (
        db.select(
            other_user.label("other_user"),
            Message.text.label("last_text"),
            (Message.sender == username).label("last_from_me"),
            Message.created_at,
            func.row_number()
            .over(partition_by=other_user, order_by=Message.created_at.desc())
            .label("row_number"),
        )
        .where(or_(Message.sender == username, Message.receiver == username))
        .subquery()
    )
    rows = db.session.execute(
        db.select(latest_per_partner).where(latest_per_partner.c.row_number == 1)
        .order_by(latest_per_partner.c.created_at.desc())
    ).mappings().all()

    # Reshape the ORM result rows into the plain-dict format expected by the
    # template/frontend JS. `time` is converted to a Unix timestamp (in
    # seconds) so the client can sort conversations by recency using plain
    # JavaScript numbers, without needing a date-parsing library.
    conversations = [
        {
            "username": r["other_user"],
            "last_text": r["last_text"],
            "last_from_me": bool(r["last_from_me"]),
            "time": r["created_at"].timestamp() if r["created_at"] else 0,
        }
        for r in rows
    ]

    return render_template(
        "home.html",
        username=username,
        users=users,
        conversations=conversations,
    )


@bp.route("/logout", methods=["POST"])
def logout():
    """GET /logout - Clear the session, logging the current user out."""
    session.pop("username", None)
    return redirect("/")
