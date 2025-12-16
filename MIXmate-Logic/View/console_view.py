from Controller.mix_controller import MixController
import time
import sys
import select
import os


class ConsoleView:
    def __init__(self, controller):
        # Der View kennt nur den Controller.
        # Er weiß nichts über I2C, Hardware oder Status-Polling.
        self.controller = controller

    def run(self):
        # Hauptmenü der Konsolenansicht
        while True:
            print("=== MIXMATE Console View ===")
            print("1) Cocktail mischen")
            print("2) Cocktail-Status anzeigen (live)")
            print("3) Exit")

            choice = input("Auswahl: ")

            if choice == "1":
                self.mix_cocktail()
            elif choice == "2":
                self.show_status_live()
            elif choice == "3":
                print("Bye!")
                break
            else:
                print("Ungültige Eingabe")

    def mix_cocktail(self):
        # Fragt den Benutzer nach der Cocktail-ID
        cocktail_id = input("Cocktail-ID eingeben: ")

        try:
            # Der Controller startet den kompletten Mixvorgang
            recipe = self.controller.mix_cocktail(int(cocktail_id))
        except Exception as e:
            # Fehler werden hier nur angezeigt,
            # die eigentliche Logik steckt in der Engine
            print("Fehler:", e)
            return

        # Nach dem Mix wird das Rezept nochmal ausgegeben (hauptsächlich zur Kontrolle / Debug)
        print("\nCocktail-Rezept:\n")
        for item in recipe:
            print(f"- {item}")

    def show_status_live(self):
        # Zeigt den aktuellen Status fortlaufend an.
        # Der Status kommt aus dem Cache der Engine und wird im Hintergrund automatisch aktualisiert.
        print("\nLive-Status (ENTER drücken zum Beenden)\n")

        try:
            while True:
                status = self.controller.get_status()

                # Bildschirm leeren, damit der Status nicht endlos scrollt
                print("\033c", end="")

                print("=== MIXMATE STATUS ===")
                print("OK:           ", status.get("ok"))
                print("Severity:     ", status.get("severity"))
                print("Busy:         ", status.get("busy"))
                print("Band belegt:  ", status.get("band_belegt"))
                print("Position:     ", status.get("ist_position"))
                print("Homing OK:    ", status.get("homing_ok"))

                # Anzeige von Fehlermeldungen
                if status.get("error_msg"):
                    print("\nHinweis:", status.get("error_msg"))

                print("\nENTER drücken zum Beenden")

                # Prüfen, ob der Benutzer ENTER gedrückt hat
                if self._enter_pressed():
                    break

                # Kurze Pause, damit das Terminal nicht flackert
                time.sleep(0.3)

        except KeyboardInterrupt:
            # Falls der Benutzer Ctrl+C drückt-Menü
            pass

    def _enter_pressed(self):
        # Auf Windows kann man stdin nicht mit select() pollen.
        # Dafür nehmen wir msvcrt (das ist der übliche Weg unter Windows).
        if os.name == "nt":
            import msvcrt
            if msvcrt.kbhit():
                key = msvcrt.getch()
                return key in (b"\r", b"\n")  # Enter
        return False

        # Auf Linux/Raspberry Pi funktioniert select() auf stdin.
        return bool(select.select([sys.stdin], [], [], 0)[0])
    
    





