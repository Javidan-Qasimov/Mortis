"""
security.py - Password hashing and input validation helpers.

argon2id (via argon2-cffi's PasswordHasher, which defaults to the argon2id
variant) is used instead of MySQL's own MD5()/SHA1()/SHA2() functions or a
raw hashlib call, because:
    * argon2id is deliberately slow AND memory-hard (tunable via time_cost /
      memory_cost / parallelism), which makes brute-force attacks expensive
      on both CPU and GPU/ASIC hardware - it won the 2015 Password Hashing
      Competition specifically for this.
    * argon2 generates and stores a random salt inside the hash string
      itself, so two users with the same password never get the same hash,
      and no separate `salt` column is needed.
    * MD5/SHA1/SHA2 are fast general-purpose hashes - great for checksums,
      bad for passwords, since attackers can test billions of guesses per
      second on commodity hardware / GPUs.

The DB column only ever stores the output of hash_password(); plaintext
passwords are never written to, or read back from, MySQL.
"""

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHash

# A single shared PasswordHasher instance, using argon2-cffi's default
# parameters (argon2id variant). Reused across calls instead of being
# recreated every time.
_password_hasher = PasswordHasher()


def hash_password(plain_password):
    """Hash a plaintext password for storage.

    Args:
        plain_password (str): the user-supplied password, as-is.

    Returns:
        str: an argon2id hash (includes algorithm version, cost
        parameters, and salt, all encoded together as one string), safe to
        store directly in the `password` column.
    """
    return _password_hasher.hash(plain_password)


def verify_password(plain_password, stored_hash):
    """Check a plaintext password against a stored argon2 hash.

    Uses argon2-cffi's own constant-time comparison internally, so this is
    safe against timing attacks (unlike `stored == computed` string
    comparison).

    Args:
        plain_password (str): the password submitted at login.
        stored_hash (str): the argon2 hash previously saved in MySQL.

    Returns:
        bool: True if the password matches the hash, False otherwise.
    """
    try:
        return _password_hasher.verify(stored_hash, plain_password)
    except VerifyMismatchError:
        # Correctly-formed hash, wrong password.
        return False
    except InvalidHash:
        # stored_hash isn't a valid argon2 hash (e.g. a leftover legacy
        # bcrypt/plaintext row) - treat as "does not match" rather than
        # crashing the login flow.
        return False


def validate_credentials(username, password):
    """Validate a username/password pair against the app's basic rules.

    This validation MUST happen server-side (not only in the HTML form or
    client-side JS), because a client can always bypass front-end checks by
    disabling JavaScript or sending a raw HTTP request directly (curl,
    Postman, etc.).

    Rules enforced:
        * username and password must both be non-empty
        * neither field may contain a space character
        * username must be at least 5 characters long
        * password must be at least 8 characters long

    Args:
        username (str): the submitted username.
        password (str): the submitted password.

    Returns:
        str | None: an error message describing the first validation
        failure encountered, or None if the credentials are valid.
    """
    if not username or not password:
        return "Username and password cannot be empty."

    if " " in username or " " in password:
        return "Username and password must not contain spaces."

    if len(username) < 5:
        return "Username must be at least 5 characters long."

    if len(password) < 8:
        return "Password must be at least 8 characters long."

    return None