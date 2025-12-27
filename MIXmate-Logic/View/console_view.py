from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
import time
import sys
import select
import os


class ConsoleView:
    def __init__(self, mix_controller: MixController, pump_controller: PumpController):
        self.mix_controller = mix_controller
        self.pump_controller = pump_controller

    def run(self):
        while True:
            print("=== MIXMATE Console View ===")
            print("1) Cocktail mischen")
            print("2) Cocktail-Status anzeigen (live)")
            print("3) Kalibrierungsmenü")
            print("4) neuen Cocktail hinzufügen")  # TODO
            print("5) Cocktail löschen")           # TODO
            print("6) Exit")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                self.mix_cocktail()
            elif choice == "2":
                self.show_status_live()
            elif choice == "3":
                self.calibrate_pumps()
            elif choice == "6":
                print("Bye!")
                break
            else:
                print("Ungültige Eingabe")

    def mix_cocktail(self):
        cocktail_id = input("Cocktail-ID eingeben: ").strip()

        try:
            recipe = self.mix_controller.mix_cocktail(int(cocktail_id))
        except Exception as e:
            print("Fehler:", e)
            return

        print("\nCocktail-Rezept:\n")
        for item in recipe:
            print(f"- {item}")

    def calibrate_pumps(self):
        while True:
            print("\n=== KALIBRIERUNG ===")
            print("1) Pumpen anzeigen")
            print("2) Pumpenposition (Steps) setzen")
            print("3) Flow-Rate (ml/s) setzen")
            print("4) Zutat einer Pumpe zuweisen")
            print("5) Zurück")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                self._show_pumps()

            elif choice == "2":
                try:
                    pump_number = int(input("Pumpennummer: ").strip())
                    steps = int(input("Neue position_steps: ").strip())
                    self.pump_controller.set_position_steps(pump_number, steps)
                    print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif choice == "3":
                try:
                    pump_number = int(input("Pumpennummer: ").strip())
                    flow = float(input("Neue flow_rate_ml_s (ml/s): ").strip())
                    self.pump_controller.set_flow_rate(pump_number, flow)
                    print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif choice == "4":
                try:
                    pump_number = int(input("Pumpennummer: ").strip())
                    ingredient_id = int(input("Neue ingredient_id: ").strip())
                    self.pump_controller.assign_ingredient(pump_number, ingredient_id)
                    print("Gespeichert.")
                except Exception as e:
                    print("Fehler:", e)

            elif choice == "5":
                return

            else:
                print("Ungültige Eingabe")

    def _show_pumps(self):
        try:
            pumps = self.pump_controller.list_pumps()
        except Exception as e:
            print("Fehler:", e)
            return

        if not pumps:
            print("Keine Pumpen gefunden.")
            return

        print("\nPumpen in der Datenbank:")
        for p in pumps:
            # erwartete Keys passend zu DB Tabelle
            print(
                f"- Pumpe {p['pump_number']}: "
                f"ingredient_id={p['ingredient_id']}, "
                f"flow_rate_ml_s={p['flow_rate_ml_s']}, "
                f"position_steps={p['position_steps']}"
            )

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
