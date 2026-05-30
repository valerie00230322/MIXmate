class CalibrationView:
    def __init__(self, pump_controller):
        self.pump_controller = pump_controller

    def run(self):
        while True:
            print("\n=== KALIBRIERUNG ===")
            print("1) Pumpen anzeigen")
            print("2) Schlitten homen")
            print("3) Zu Position fahren (Steps)")
            print("4) Flow-Rate kalibrieren (ml/s)")
            print("5) Position_steps setzen (DB)")
            print("6) Zurück")

            choice = input("Auswahl: ").strip()

            if choice == "1":
                self._show_pumps()
            elif choice == "2":
                self._home()
            elif choice == "3":
                self._move_to_position()
            elif choice == "4":
                self._calibrate_flow_rate()
            elif choice == "5":
                self._set_position_steps()
            elif choice == "6":
                return
            else:
                print("Ungültige Eingabe")

    def _show_pumps(self):
        pumps = self.pump_controller.list_pumps()
        if not pumps:
            print("Keine Pumpen gefunden.")
            return

        for p in pumps:
            print(
                f"Pumpe {p['pump_number']}: ingredient_id={p['ingredient_id']}, "
                f"flow_rate_ml_s={p['flow_rate_ml_s']}, position_steps={p['position_steps']}"
            )

    def _home(self):
        try:
            self.pump_controller.ensure_homed()
            print("Homing abgeschlossen.")
        except Exception as e:
            print("Fehler:", e)

    def _move_to_position(self):
        try:
            steps = int(input("Zielposition (steps): ").strip())
            self.pump_controller.move_to_position(steps)
            print("Position erreicht.")
        except Exception as e:
            print("Fehler:", e)

    def _calibrate_flow_rate(self):
        try:
            pump_number = int(input("Pumpennummer: ").strip())
            seconds = int(input("Wie lange laufen lassen (Sekunden): ").strip())

            used_seconds = self.pump_controller.run_pump_for_calibration(pump_number, seconds)

            measured_ml = float(input("Gemessene ml: ").strip())
            flow = self.pump_controller.save_flow_rate_from_measurement(pump_number, measured_ml, used_seconds)

            print(f"Neue flow_rate_ml_s gespeichert: {flow}")
        except Exception as e:
            print("Fehler:", e)

    def _set_position_steps(self):
        try:
            pump_number = int(input("Pumpennummer: ").strip())
            steps = int(input("Neue position_steps: ").strip())
            self.pump_controller.set_position_steps(pump_number, steps)
            print("Gespeichert.")
        except Exception as e:
            print("Fehler:", e)
