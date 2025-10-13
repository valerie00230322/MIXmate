from pathlib import Path
import json
from typing import Optional


class AdminModel:
    """
    Verwaltet Admin-Credentials.
    Standard-Datei: Model/admin.json mit Defaults: admin / 1234
    (bewusst simpel – kann später auf Hashing erweitert werden)
    """

    def __init__(self, credentials_file: str = "admin.json"):
        self.file_path = Path(__file__).resolve().parent / credentials_file
        self._data = {}
        self._load_or_create_default()

    # -------- intern --------
    def _load_or_create_default(self) -> None:
        if not self.file_path.exists():
            # Defaults schreiben
            defaults = {"username": "admin", "password": "1234"}
            self.file_path.write_text(json.dumps(defaults, indent=4), encoding="utf-8")
        # Laden
        self._data = json.loads(self.file_path.read_text(encoding="utf-8"))
        # Minimal-Validierung
        self._data.setdefault("username", "admin")
        self._data.setdefault("password", "1234")

    def _save(self) -> None:
        self.file_path.write_text(json.dumps(self._data, indent=4), encoding="utf-8")

    # -------- öffentlich --------
    def check_login(self, username: str, password: str) -> bool:
        """Prüft Benutzername & Passwort (plain)."""
        return (
            str(username) == str(self._data.get("username", ""))
            and str(password) == str(self._data.get("password", ""))
        )

    def get_username(self) -> str:
        return str(self._data.get("username", ""))

    def change_credentials(self, username: Optional[str] = None, password: Optional[str] = None) -> None:
        """Ändert Zugangsdaten (optional einzeln)."""
        if username:
            self._data["username"] = str(username)
        if password:
            self._data["password"] = str(password)
        self._save()
