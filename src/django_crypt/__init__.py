from cryptography.fernet import Fernet

from django_crypt import settings


class Crypt:
    """Symmetric encryption helper backed by Fernet.

    Loads salt from `settings.CRYPT_SALT` if not explicitly provided.
    Generated ciphertexts are non-deterministic — for lookup hashing use a
    separate HMAC helper, not Crypt.
    """

    salt: str

    def __init__(self, salt: str | None = None):
        if salt is None:
            if settings.CRYPT_SALT is None:
                raise ValueError("CRYPT_SALT is not set in settings")
            salt = settings.CRYPT_SALT
        self.salt = salt

    @staticmethod
    def generate_salt() -> str:
        return Fernet.generate_key().decode()

    def encrypt(self, text: str | None) -> str | None:
        if text is None:
            return None
        return Fernet(self.salt).encrypt(text.encode()).decode()

    def decrypt(self, text: str | None) -> str | None:
        if text is None:
            return None
        return Fernet(self.salt).decrypt(text).decode()
