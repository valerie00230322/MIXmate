# Controller/app_controller.py

from kivy.uix.screenmanager import ScreenManager, NoTransition
from kivy.metrics import dp
from kivymd.uix.label import MDLabel
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.card import MDCard
from kivymd.uix.boxlayout import MDBoxLayout

from View.screens import WelcomeScreen, LoginScreen, AdminScreen, RecipeScreen, AdminLoginScreen
from Model.recipe_model import RecipeModel
from Controller.admin_controller import AdminController
from Controller.pump_controller import PumpController

import threading


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
        self.admin_controller = AdminController(self)

        # PumpController: falls du Simulation als Default willst, gib dev_mode=True/log_i2c=True mit
        self.pump_controller = PumpController(
            # db_filename="mixmate-oida.db",
            # i2c_bus=1,
            # status_addr=0x10,
            # debug=False,
            # dev_mode=True,   # <- einkommentieren, wenn Simulation beim Start aktiv sein soll
            # log_i2c=True,    # <- optionales I²C-Logging
        )

        # ScreenManager vorbereiten
        self.sm = ScreenManager(transition=NoTransition())
        self.sm.add_widget(WelcomeScreen(name="welcome"))
        self.sm.add_widget(LoginScreen(name="login"))
        self.sm.add_widget(AdminLoginScreen(name="admin_login"))
        self.sm.add_widget(AdminScreen(name="admin"))
        self.sm.add_widget(RecipeScreen(name="recipes"))

    # -----------------
    # Navigation
    # -----------------
    def go_to_welcome(self):
        self.sm.current = "welcome"

    def go_to_login(self):
        self.sm.current = "login"

    def go_to_admin_login(self):
        self.sm.current = "admin_login"

    def go_to_admin(self):
        self.sm.current = "admin"
        self.sync_admin_view()  # stellt den Simulations-Switch passend ein

    def go_to_recipes(self):
        self.sm.current = "recipes"
        self.load_recipes_into_view()

    # -----------------
    # Login
    # -----------------
    def check_login(self, username, password):
        if username == "user" and password == "pass":
            Snackbar(text="User eingeloggt").open()
            self.go_to_welcome()
        else:
            Snackbar(text="Falsche Login-Daten!").open()

    def check_admin_login(self, username, password):
        self.admin_controller.login(username, password)

    # -----------------
    # Admin: Simulation Toggle (vom AdminScreen-Switch)
    # -----------------
    def set_simulation(self, enabled: bool):
        """
        Wird von MDSwitch im AdminScreen aufgerufen:
        on_active: app.controller.set_simulation(self.active)
        """
        if enabled:
            self.pump_controller.enable_simulation()
            # Optional: im Sim-Modus Logging einschalten (hilfreich zum Testen)
            self.pump_controller.set_log_i2c(True)
            Snackbar(text="Simulation: EIN (I²C wird emuliert)").open()
        else:
            self.pump_controller.disable_simulation()
            self.pump_controller.set_log_i2c(False)
            Snackbar(text="Simulation: AUS (echte I²C-Hardware erwartet)").open()

    def sync_admin_view(self):
        """
        Den Switch im AdminScreen an den aktuellen Simulationsstatus anpassen.
        Aufruf bei go_to_admin().
        """
        try:
            screen = self.sm.get_screen("admin")
            sim_switch = screen.ids.get("sim_switch")
            if sim_switch:
                sim_switch.active = self.pump_controller.is_simulation()
        except Exception:
            # UI nicht blockieren, wenn der Screen/ID noch nicht bereit ist
            pass

    # -----------------
    # Pumpen-Aktionen
    # -----------------
    def preflight_check(self):
        """Schritt 1: Statusbit + Distanz anfragen und anzeigen (threaded, blockiert UI nicht)."""
        def _run():
            try:
                result = self.pump_controller.preflight_check()
                Snackbar(
                    text=f"Preflight: Status={result.get('status_bit')}  Distanz={result.get('distance_mm')} mm"
                ).open()
            except Exception as e:
                Snackbar(text=f"Preflight-Fehler: {e}").open()
        threading.Thread(target=_run, daemon=True).start()

    def pour_cocktail(self, cocktail_name: str):
        """Schritt 2: Dispense-Plan aus DB holen und nacheinander dosieren (threaded)."""
        plan = self.recipe_model.get_dispense_plan(cocktail_name)
        if not plan:
            Snackbar(text=f"Cocktail nicht gefunden: {cocktail_name}").open()
            return

        unresolved = [step for step in plan if not step.get("pump_id")]
        if unresolved:
            names = ", ".join(s["ingredient"] for s in unresolved)
            Snackbar(text=f"Keine Pumpe gesetzt für: {names}").open()
            return

        def _run():
            try:
                # optional für Dev: Demo-Pumpen anlegen, falls DB leer
                self.pump_controller.ensure_demo_pumps_if_needed()

                # optional vor dem Ausgießen: Preflight
                # self.preflight_check()

                for step in plan:
                    self.pump_controller.dispense_by_id(
                        pump_id=int(step["pump_id"]),
                        amount_ml=float(step["amount_ml"]),
                        pump_channel=step.get("pump_channel"),
                    )
                Snackbar(text=f"🍹 {cocktail_name} fertig!").open()
            except Exception as e:
                Snackbar(text=f"Dosierfehler bei {cocktail_name}: {e}").open()

        threading.Thread(target=_run, daemon=True).start()

    # -----------------
    # Buttons / Dummy
    # -----------------
    def on_manual_pressed(self):
        # Beispiel: Preflight als schneller Test
        self.preflight_check()

    def on_calibration_pressed(self):
        # Platzhalter für Kalibrierfluss (Mengen ausgeben, Zeit/Volumen messen, flow_ml_per_s anpassen)
        Snackbar(text="Kalibrierung gestartet (Platzhalter)").open()

    def on_levels_pressed(self):
        Snackbar(text="Füllstände geprüft").open()

    def on_clean_pressed(self):
        Snackbar(text="Reinigung gestartet").open()

    def on_logs_pressed(self):
        Snackbar(text="Logs angezeigt").open()

    # -----------------
    # Rezepte laden (View-Befüllung)
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

            # Karte klickbar: startet Cocktail
            def _on_release(instance, name=recipe["name"]):
                self.pour_cocktail(name)
            card.bind(on_release=_on_release)

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
