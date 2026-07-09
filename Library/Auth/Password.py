from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

class PasswordAPI:

    _HASHER_: PasswordHasher = PasswordHasher()

    @classmethod
    def hash(cls, password: str) -> str:
        return cls._HASHER_.hash(password)

    @classmethod
    def verify(cls, digest: str, password: str) -> bool:
        try:
            return cls._HASHER_.verify(digest, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            return False

    @classmethod
    def stale(cls, digest: str) -> bool:
        try:
            return cls._HASHER_.check_needs_rehash(digest)
        except (InvalidHashError, VerificationError):
            return False