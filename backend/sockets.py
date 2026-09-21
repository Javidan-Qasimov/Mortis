"""
sockets.py - Socket.IO event handlers (real-time chat).

Importing this module (see app.py) is what registers these handlers on
the shared `socketio` instance from extensions.py - it has no exports of
its own that need to be called directly.
"""

import json
from datetime import datetime, timezone

from flask import request, session
from flask_socketio import join_room, emit
from sqlalchemy import or_, and_

from extensions import db, socketio
from db import get_room_name
from models import Message, User
from config import MAX_MESSAGE_LENGTH
from socket_security import message_rate_limiter


@socketio.on("join")
def handle_join(data):
    """Handle a client opening a chat window with another user.

    Event payload:
        data["with"] (str): username of the conversation partner.

    Side effects:
        * Joins the caller's socket to the shared room for this pair of
          users, so future broadcasts to that room reach both of them.
        * Emits a "history" event back to the caller containing every
          message previously exchanged between the two users, so the chat
          window can be populated on open.

    Unauthenticated sockets (no "username" in session) and payloads missing
    the "with" field are silently ignored.
    """
    me = session.get("username")
    if not me:
        return  # ignore events from unauthenticated sockets

    other = data.get("with") if isinstance(data, dict) else None
    if not isinstance(other, str) or not other.strip():
        return
    other = other.strip()

    if not db.session.scalar(db.select(User.id).filter_by(username=other)):
        return

    room = get_room_name(me, other)
    join_room(room)

    history_rows = db.session.scalars(
        db.select(Message)
        .where(
            or_(
                and_(Message.sender == me, Message.receiver == other),
                and_(Message.sender == other, Message.receiver == me),
            )
        )
        .order_by(Message.created_at.asc())
    ).all()

    # `created_at` comes back as a datetime object, which isn't JSON
    # serializable as-is. Convert it to a plain Unix timestamp (seconds)
    # so the client can format it with plain JavaScript, same as the
    # `time` field already used for the conversations list.
    history = []
    for message in history_rows:
        try:
            envelope = json.loads(message.text)
        except json.JSONDecodeError:
            # Records from before E2EE are intentionally not exposed as
            # plaintext through the encrypted-client message flow.
            envelope = None
        history.append(
            {
                "from": message.sender,
                "envelope": envelope,
                "time": message.created_at.timestamp() if message.created_at else None,
            }
        )

    emit("history", {"room": room, "messages": history})


@socketio.on("send_message")
def handle_send_message(data):
    """Handle a client sending a new chat message.

    Event payload:
        data["to"] (str): recipient's username.
        data["text"] (str): message body.

    Side effects:
        * Persists the message to the "messages" table so it survives page
          reloads and future logins.
        * Broadcasts a "receive_message" event to everyone currently in the
          shared room. Since the sender also joined this room in
          `handle_join`, they receive their own message back too, which is
          what keeps both participants' chat windows in sync in real time.

    Unauthenticated sockets, missing recipients, and empty/whitespace-only
    messages are silently ignored.
    """
    me = session.get("username")
    if not me:
        return  # ignore events from unauthenticated sockets

    other = data.get("to") if isinstance(data, dict) else None
    envelope = data.get("envelope") if isinstance(data, dict) else None
    if not isinstance(other, str) or not isinstance(envelope, dict):
        return
    other = other.strip()
    version = envelope.get("v")
    iv = envelope.get("iv")
    ciphertext = envelope.get("ciphertext")
    if (
        not other
        or version != 1
        or not isinstance(iv, str)
        or not isinstance(ciphertext, str)
        or len(iv) > 64
        or not ciphertext
        or len(ciphertext) > MAX_MESSAGE_LENGTH * 2
    ):
        return

    if not message_rate_limiter.is_allowed(request.remote_addr or me):
        emit("message_error", {"error": "Too many messages. Please wait a moment."})
        return

    if not db.session.scalar(db.select(User.id).filter_by(username=other)):
        emit("message_error", {"error": "Recipient does not exist."})
        return

    room = get_room_name(me, other)

    # Captured once up front so the timestamp we store in the database and the one
    # we broadcast to clients are guaranteed to match exactly.
    sent_at = datetime.now(timezone.utc)

    # Persist first, so the message isn't lost even if broadcasting fails.
    encrypted_text = json.dumps(
        {"v": version, "iv": iv, "ciphertext": ciphertext}, separators=(",", ":")
    )
    db.session.add(Message(sender=me, receiver=other, text=encrypted_text, created_at=sent_at))
    db.session.commit()

    # Broadcast to both participants (the room includes the sender too).
    msg = {"from": me, "envelope": json.loads(encrypted_text), "time": sent_at.timestamp()}
    emit("receive_message", msg, room=room)
