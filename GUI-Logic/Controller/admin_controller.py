# Controller/admin_controller.py
from kivymd.uix.snackbar import MDSnackbar
from Model.admin_model import AdminModel

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
            MDSnackbar(text="Admin erfolgreich eingeloggt!").open()
            self.app_controller.go_to_admin()
        else:
            self.is_admin_logged_in = False
            MDSnackbar(text="Falsche Admin-Daten!").open()

    def logout(self):
        self.is_admin_logged_in = False
        MDSnackbar(text="Admin abgemeldet").open()
        self.app_controller.go_to_welcome()

    # --- Admin-Funktionen ---
    def export_recipes(self):
        if not self.is_admin_logged_in:
            MDSnackbar(text="Kein Zugriff! Bitte zuerst einloggen.").open()
            return
        try:
            path = self.app_controller.recipe_model.export_recipes_to_json()
            MDSnackbar(text=f"Rezepte exportiert nach: {path.name}").open()
        except Exception as e:
            MDSnackbar(text=f"Fehler beim Export: {e}").open()

    def import_recipes(self):
        if not self.is_admin_logged_in:
            MDSnackbar(text="Kein Zugriff! Bitte zuerst einloggen.").open()
            return
        try:
            self.app_controller.recipe_model.import_recipes_from_json()
            MDSnackbar(text="Rezepte erfolgreich importiert!").open()
            # optional: Liste live aktualisieren, falls gerade offen
            if self.app_controller.sm.current == "recipes":
                self.app_controller.load_recipes_into_view()
        except Exception as e:
            MDSnackbar(text=f"Fehler beim Import: {e}").open()
