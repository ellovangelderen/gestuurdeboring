"""Wachtwoord utilities: bcrypt hashing + validatie."""
import bcrypt


def hash_password(plain: str) -> str:
    """Hash een wachtwoord met bcrypt."""
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Verifieer een wachtwoord tegen een bcrypt hash."""
    try:
        return bcrypt.checkpw(plain.encode(), hashed.encode())
    except Exception:
        return False


def validate_password(plain: str, username: str = "") -> list:
    """Valideer wachtwoord eisen. Returns lijst van foutmeldingen (leeg = OK)."""
    errors = []
    if len(plain) < 8:
        errors.append("Wachtwoord moet minimaal 8 tekens zijn")
    if not any(c.isupper() for c in plain):
        errors.append("Wachtwoord moet minimaal 1 hoofdletter bevatten")
    if not any(c.isdigit() for c in plain):
        errors.append("Wachtwoord moet minimaal 1 cijfer bevatten")
    if username and plain.lower() == username.lower():
        errors.append("Wachtwoord mag niet gelijk zijn aan de gebruikersnaam")
    return errors
