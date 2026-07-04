import secrets

def generate_session_token() -> str:
    """Generates a secure 32-character hexadecimal session token for authentication."""
    return secrets.token_hex(16)
