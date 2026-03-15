import json
import hashlib
import hmac
import secrets
from pathlib import Path


class AdminAuthService:
    HASH_ALGO = "pbkdf2_sha256"
    HASH_ITERATIONS = 120000

    def __init__(self, credentials_file: Path | None = None):
        base_dir = Path(__file__).resolve().parents[1]
        if credentials_file is None:
            credentials_file = base_dir / "Config" / "admin_credentials.json"
        self.credentials_file = Path(credentials_file)
        self._ensure_credentials_file()

    def _ensure_credentials_file(self) -> None:
        self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
        if self.credentials_file.exists():
            return

        password_hash = self.hash_password("admin")
        default_data = {
            "username": "admin",
            "password_hash": password_hash,
        }
        self.credentials_file.write_text(
            json.dumps(default_data, indent=2, ensure_ascii=True),
            encoding="utf-8",
        )

    def verify(self, username: str, password: str) -> bool:
        try:
            raw = self.credentials_file.read_text(encoding="utf-8")
            data = json.loads(raw)
        except Exception:
            return False

        expected_user = str(data.get("username", ""))
        if username != expected_user:
            return False

        password_hash = data.get("password_hash")
        if isinstance(password_hash, str) and password_hash:
            return self.verify_password(password, password_hash)

        return False

    @classmethod
    def hash_password(cls, password: str) -> str:
        salt = secrets.token_hex(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            cls.HASH_ITERATIONS,
        ).hex()
        return f"{cls.HASH_ALGO}${cls.HASH_ITERATIONS}${salt}${digest}"

    @classmethod
    def verify_password(cls, password: str, encoded: str) -> bool:
        try:
            algo, iterations_s, salt, expected_digest = encoded.split("$", 3)
            if algo != cls.HASH_ALGO:
                return False
            iterations = int(iterations_s)
        except Exception:
            return False

        actual_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
        ).hex()
        return hmac.compare_digest(actual_digest, expected_digest)
