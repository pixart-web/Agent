from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from argon2.low_level import Type

_password_hasher = PasswordHasher(type=Type.ID)
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$yoNMOSt074o2PM0jebU1Ug"
    "$xq1wXmFAadDGarAg5qfLMocRJ/XigGIOvN5l7ONcquo"
)


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def verify_password_or_dummy(password: str, password_hash: str | None) -> bool:
    """Keep invalid-login password work similar when the user does not exist."""
    valid = verify_password(password, password_hash or _DUMMY_PASSWORD_HASH)
    return password_hash is not None and valid
