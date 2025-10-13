from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.metrics import dp
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout

from View.screens import WelcomeScreen, LoginScreen, AdminScreen, RecipeScreen, AdminLoginScreen
from Model.recipe_model import RecipeModel
from Controller.admin_controller import AdminController  # <--- NEU


def map_font_style(style: str) -> str:
    mapping = {
        "DisplayLarge": "H2",
        "DisplayMedium": "H3",
        "DisplaySmall": "H4",
        "HeadlineLarge": "H3",
        "HeadlineMedium": "H4",
        "HeadlineSmall": "H5",
        "TitleLarge": "H5",
        "TitleMedium": "Subtitle1",
        "TitleSmall": "Subtitle2",
        "BodyLarge": "Body1",
        "BodyMedium": "Body1",
        "BodySmall": "Body2",
        "LabelLarge": "Button",
        "LabelMedium": "Caption",
        "LabelSmall": "Overline",
    }
    return mapping.get(style, style)


class AppController:
    def __init__(self, app):
        self.app = app
        self.recipe_model = RecipeModel()
        self.admin_controller = AdminController(self)  # <--- NEU

        # ScreenManager vorbereiten
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(WelcomeScreen(name="welcome"))
        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(AdminLoginScreen(name="admin_login"))  # <--- NEU
        self.sm.add_widget(AdminScreen(name="admin"))
        self.sm.add_widget(RecipeScreen(name="recipes"))

    # -----------------
    # Navigation
    # -----------------
    def go_to_welcome(self):
        self.sm.current = "welcome"

    def go_to_login(self):
        self.sm.current = "login"

    def go_to_admin_login(self):  # <--- NEU
        self.sm.current = "admin_login"

    def go_to_admin(self):
        self.sm.current = "admin"

    def go_to_recipes(self):
        self.sm.current = "recipes"
        self.load_recipes_into_view()

    # -----------------
    # Login
    # -----------------
    def check_login(self, username, password):
        """(Optional) normaler Benutzer-Login – unverändert."""
        if username == "user" and password == "pass":
            MDSnackbar(text="User eingeloggt").open()
            self.go_to_welcome()
        else:
            MDSnackbar(text="Falsche Login-Daten!").open()

    def check_admin_login(self, username, password):  # <--- NEU
        """Delegiert an AdminController (Rechte & Aktionen dort gebündelt)."""
        self.admin_controller.login(username, password)

    # -----------------
    # Dummy Funktionen
    # -----------------
    def on_manual_pressed(self):
        MDSnackbar(text="Manueller Mix gestartet").open()

    def on_calibration_pressed(self):
        MDSnackbar(text="Kalibrierung gestartet").open()

    def on_levels_pressed(self):
        MDSnackbar(text="Füllstände geprüft").open()

    def on_clean_pressed(self):
        MDSnackbar(text="Reinigung gestartet").open()

    def on_logs_pressed(self):
        MDSnackbar(text="Logs angezeigt").open()

    # -----------------
    # Rezepte laden
    # -----------------
    def load_recipes_into_view(self):
        screen = self.sm.get_screen("recipes")
        recipe_list = screen.ids.recipe_list
        recipe_list.clear_widgets()

        recipes = self.recipe_model.load_recipes()
        for recipe in recipes:
            ingredients_str = "\n".join(
                f"• {ing['name']} ({ing['amount_ml']} ml)" for ing in recipe["ingredients"]
            )

            card = MDCard(
                orientation="vertical",
                size_hint=(1, None),
                height=dp(140),
                padding=dp(16),
                spacing=dp(10),
                md_bg_color=(0.15, 0.2, 0.3, 1),
                radius=[12, 12, 12, 12],
                ripple_behavior=True,
            )

            box = MDBoxLayout(orientation="vertical", spacing=dp(6))

            box.add_widget(
                MDLabel(
                    text=recipe["name"],
                    font_style=map_font_style("HeadlineMedium"),
                    theme_text_color="Custom",
                    text_color=(1, 1, 1, 1),
                )
            )

            box.add_widget(
                MDLabel(
                    text=ingredients_str,
                    font_style=map_font_style("BodySmall"),
                    theme_text_color="Custom",
                    text_color=(0.8, 0.8, 0.8, 1),
                )
            )

            card.add_widget(box)
            recipe_list.add_widget(card)
