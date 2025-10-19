# Controller/admin_controller.py
from kivy.metrics import dp
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import MDSnackbar
from Model.admin_model import AdminModel


def _snack(text: str, width: float = 0.7, y_offset: int = 24):
    """
    Zeigt eine einfache Snackbar mit Text (API ab KivyMD 1.2.0).
    width: relative Breite (0..1) über size_hint_x
    y_offset: Abstand vom unteren Rand in dp
    """
    MDSnackbar(
        MDLabel(text=text),
        y=dp(y_offset),
        pos_hint={"center_x": 0.5},
        size_hint_x=width,
    ).open()


class AdminController:
    """Bündelt alle Admin-Aktionen und den Login-Status."""
    def __init__(self, app_controller):
        self.app_controller = app_controller
        self.admin_model = AdminModel()
        self.is_admin_logged_in = False

    # --- Auth ---
    def login(self, username, password):
        if self.admin_model.check_login(username, password):
            self.is_admin_logged_in = True
            _snack("Admin erfolgreich eingeloggt!")
            self.app_controller.go_to_admin()
        else:
            self.is_admin_logged_in = False
            _snack("Falsche Admin-Daten!")

    def logout(self):
        self.is_admin_logged_in = False
        _snack("Admin abgemeldet")
        self.app_controller.go_to_welcome()

    # --- Admin-Funktionen ---
    def export_recipes(self):
        if not self.is_admin_logged_in:
            _snack("Kein Zugriff! Bitte zuerst einloggen.")
            return
        try:
            path = self.app_controller.recipe_model.export_recipes_to_json()
            # path kann z.B. pathlib.Path sein
            _snack(f"Rezepte exportiert nach: {getattr(path, 'name', str(path))}")
        except Exception as e:
            _snack(f"Fehler beim Export: {e}")

    def import_recipes(self):
        if not self.is_admin_logged_in:
            _snack("Kein Zugriff! Bitte zuerst einloggen.")
            return
        try:
            self.app_controller.recipe_model.import_recipes_from_json()
            _snack("Rezepte erfolgreich importiert!")
            # optional: Liste live aktualisieren, falls gerade offen
            if self.app_controller.sm.current == "recipes":
                self.app_controller.load_recipes_into_view()
        except Exception as e:
            _snack(f"Fehler beim Import: {e}")
