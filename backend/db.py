"""Helpers shared by the real-time chat handlers."""

def get_room_name(user1, user2):
    """Build a deterministic Socket.IO room name for a 1-to-1 conversation.

    The two usernames are sorted alphabetically before being joined so the
    resulting room name is identical regardless of who initiated the chat
    (e.g. always "alice_bob", never "bob_alice").

    Args:
        user1 (str): first participant's username.
        user2 (str): second participant's username.

    Returns:
        str: room name in the form "<lower_user>_<higher_user>".
    """
    names = sorted([user1, user2])
    return f"{names[0]}_{names[1]}"
