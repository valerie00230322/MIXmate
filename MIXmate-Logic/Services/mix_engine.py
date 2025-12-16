from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor


class MixEngine:
    def __init__(self, simulation: bool = True):
        # I2C-Logik für die Kommunikation mit dem Arduino.
        # Im Simulationsmodus wird keine echte Hardware angesprochen.
        self.i2c = i2C_logic(simulation=simulation)

        # Der StatusService interpretiert die rohen Statusdaten
        # (busy, Position, Fehlerzustände, Homing, usw.).
        self.status_service = StatusService()

        # Der StatusMonitor pollt den Status im Hintergrund
        # und speichert immer den zuletzt bekannten Zustand.
        # Alle I2C-Zugriffe laufen über ihn, damit es keine
        # gleichzeitigen Lese-/Schreibzugriffe gibt.
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()

    def get_status(self):
        # Gibt den zuletzt bekannten Status zurück.
        # Hier wird kein I2C-Zugriff gemacht, sondern nur der Cache gelesen.
        return self.monitor.get_latest()

    def _wait_until_idle(self, timeout_s: float = 10.0) -> bool:
        # Wartet, bis der Mixer nicht mehr busy ist.
        # Dabei wird der gecachte Status verwendet, nicht direkt I2C.
        # Gibt False zurück, wenn ein Fehler auftritt oder das Timeout erreicht ist.
        return self.status_service.wait_until_idle_cached(
            self.monitor.get_latest,
            timeout_s=timeout_s,
            poll_s=0.2
        )

    def move_to_position(self, target_position: int):
        # Ohne Zielposition kann der Schlitten nicht fahren.
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")

        # Aktuelle Position nur zu Debug-Zwecken abfragen.
        # Die echte Positionslogik liegt vollständig auf dem Arduino.
        current_position = self.i2c.get_current_position()
        print(f"[MixEngine] Bewege von {current_position} nach {target_position}")

        # Fahrbefehl exklusiv über den StatusMonitor senden.
        # Währenddessen pausiert das Status-Polling automatisch.
        self.monitor.run_i2c(self.i2c.move_to_position, target_position)

        # Warten, bis die Bewegung abgeschlossen ist.
        # Falls der Schlitten hängen bleibt, wird hier abgebrochen.
        if not self._wait_until_idle(timeout_s=15.0):
            raise RuntimeError("Schlitten hat Zielposition nicht erreicht.")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        # Ohne Mixdaten kann kein Cocktail gemischt werden.
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")

        # Vor jedem Cocktail wird ein Homing durchgeführt,
        # damit der Schlitten eine definierte Referenzposition hat.
        self.monitor.run_i2c(self.i2c.home)

        if not self._wait_until_idle(timeout_s=20.0):
            raise RuntimeError("Homing fehlgeschlagen.")

        # Förderband starten, damit ein Glas in Position gebracht wird.
        self.monitor.run_i2c(self.i2c.beladen)

        # Zutaten der Reihe nach abarbeiten.
        # Die Reihenfolge kommt aus der Datenbank (order_index).
        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_steps = item["position_steps"]

            # Zutaten ohne zugewiesene Pumpe oder mit ungültiger Flussrate
            # werden übersprungen, um Fehler zu vermeiden.
            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"[MixEngine] {ingredient} hat keine gültige Pumpe - übersprungen.")
                continue

            print(f"[MixEngine] {ingredient}: {amount_ml:.1f} ml über Pumpe {pump_number}")

            # Schlitten zur Position der entsprechenden Pumpe fahren.
            self.move_to_position(position_steps)

            # Pumpdauer berechnen:
            # gewünschte Menge (ml) geteilt durch Flussrate (ml/s).
            dispense_time_s = amount_ml / flow_rate

            # Der Arduino akzeptiert nur Werte zwischen 1 und 255 Sekunden.
            seconds = max(1, min(255, int(round(dispense_time_s))))

            # Pumpe starten.
            self.monitor.run_i2c(self.i2c.activate_pump, pump_number, seconds)

            # Warten, bis der Pumpvorgang abgeschlossen ist.
            # Timeout etwas größer als die eigentliche Pumpzeit.
            if not self._wait_until_idle(timeout_s=seconds + 5):
                raise RuntimeError(
                    f"Pumpe {pump_number} für {ingredient} hat nicht rechtzeitig beendet."
                )

        # Nach dem Mixen das Glas aus dem System fahren.
        self.monitor.run_i2c(self.i2c.entladen)

        # Rückgabe der Mixdaten, damit der Controller weiß,
        # dass der komplette Ablauf erfolgreich durchgelaufen ist.
        return mix_data
