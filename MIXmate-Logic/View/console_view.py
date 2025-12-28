from View.cocktail_view import CocktailView
from View.calibration_view import CalibrationView
from View.admin_view import AdminView

import time
import sys
import select
import os


class ConsoleView:
    def __init__(self, mix_controller, pump_controller, admin_controller):
        self.mix_controller = mix_controller
        self.pump_controller = pump_controller
        self.admin_controller = admin_controller

        self.cocktail_view = CocktailView(self.mix_controller)
        self.calibration_view = CalibrationView(self.pump_controller)
        self.admin_view = AdminView(self.admin_controller, self.pump_controller)

    def run(self):
        while True:
            print("=== MIXMATE ===")
            print("1) Cocktail mischen")
            print("2) Cocktail-Status anzeigen (live)")
            print("3) Kalibrierung")
            print("4) Admin")
            print("6) Exit")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                self._mix_menu()
            elif choice == "2":
                self.show_status_live()
            elif choice == "3":
                self.calibration_view.run()
            elif choice == "4":
                self.admin_view.run()
            elif choice == "6":
                print("Bye!")
                break
            else:
                print("Ungültige Eingabe")

    def _mix_menu(self):
        # Menüpunkt 1 ist absichtlich kurz gehalten.
        # Wenn später mal mehr Auswahl kommt (Liste, Suche, Favoriten),
        # passiert das im CocktailView und nicht hier.
        try:
            self.cocktail_view.run_mix_flow()
        except Exception as e:
            print("Fehler:", e)

    def show_status_live(self):
        print("\nLive-Status (ENTER drücken zum Beenden)\n")

        try:
            while True:
                status = self.mix_controller.get_status()

                print("\033c", end="")
                print("=== MIXMATE STATUS ===")
                print("OK:           ", status.get("ok"))
                print("Severity:     ", status.get("severity"))
                print("Busy:         ", status.get("busy"))
                print("Band belegt:  ", status.get("band_belegt"))
                print("Position:     ", status.get("ist_position"))
                print("Homing OK:    ", status.get("homing_ok"))

                if status.get("error_msg"):
                    print("\nHinweis:", status.get("error_msg"))

                print("\nENTER drücken zum Beenden")

                if self._enter_pressed():
                    break

                time.sleep(0.3)

        except KeyboardInterrupt:
            pass

    def _enter_pressed(self):
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                return key in (b"\r", b"\n")
        return False

        return bool(select.select([sys.stdin], [], [], 0)[0])
