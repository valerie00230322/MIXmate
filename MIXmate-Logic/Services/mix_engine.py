from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService


class MixEngine:
    def __init__(self, simulation: bool = True):
        # Die MixEngine spricht ausschließlich mit der Hardware-Schicht.
        # Sie kennt weder Datenbank noch GUI.
        self.i2c = i2C_logic(simulation=simulation)

        # Der StatusService wertet die Antworten vom Arduino aus
        # (busy, homing, Fehler, etc.)
        self.status_service = StatusService()

    def _wait_until_idle(self, timeout_s: float = 10.0) -> bool:
        # Wartet, bis der Arduino meldet, dass er nicht mehr busy ist.
        # Das verhindert, dass neue Befehle gesendet werden,
        # während Motor oder Pumpe noch laufen.
        return self.status_service.wait_until_idle(self.i2c, timeout_s=timeout_s)

    def move_to_position(self, target_position: int):
        # Zielposition darf nicht fehlen, sonst weiß der Schlitten nicht wohin
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")

        # Aktuelle Position nur zu Debug-Zwecken abfragen
        # (die echte Positionslogik liegt komplett auf dem Arduino)
        current_position = self.i2c.get_current_position()

        # Fahrbefehl: absolute Zielposition
        # Der Arduino berechnet intern selbst die Bewegung
        self.i2c.move_to_position(target_position)

        print(f"[MixEngine] Bewege von {current_position} nach {target_position}")

        # Warten, bis die Bewegung abgeschlossen ist
        # Wenn das fehlschlägt, lieber hart abbrechen
        if not self._wait_until_idle(timeout_s=15.0):
            raise RuntimeError("Schlitten hat Zielposition nicht erreicht.")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        # Ohne Mixdaten kann kein Cocktail gemischt werden
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")

        # Vor jedem Cocktail wird gehomed,
        # damit wir eine definierte Ausgangsposition haben
        self.i2c.home()

        if not self._wait_until_idle(timeout_s=20.0):
            raise RuntimeError("Homing fehlgeschlagen.")

        # Förderband starten, damit ein Glas im System ist
        self.i2c.beladen()

        # Alle Zutaten der Reihe nach abarbeiten
        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_steps = item["position_steps"]

            # Zutaten ohne Pumpe oder mit ungültiger Flussrate überspringen
            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"[MixEngine] {ingredient} hat keine gültige Pumpe → übersprungen.")
                continue

            print(
                f"[MixEngine] {ingredient}: "
                f"{amount_ml:.1f} ml über Pumpe {pump_number}"
            )

            # Schlitten zur richtigen Pumpe fahren
            self.move_to_position(position_steps)

            # Pumpdauer berechnen:
            # gewünschte ml / ml pro Sekunde
            dispense_time_s = amount_ml / flow_rate

            # Der Arduino akzeptiert nur 0–255 Sekunden
            seconds = max(1, min(255, int(round(dispense_time_s))))

            # Pumpe starten
            self.i2c.activate_pump(pump_number, seconds)

            # Warten, bis die Pumpe fertig ist
            if not self._wait_until_idle(timeout_s=seconds + 5):
                raise RuntimeError(
                    f"Pumpe {pump_number} für {ingredient} hat nicht rechtzeitig beendet."
                )

        # Cocktail ist fertig → Glas ausgeben
        self.i2c.entladen()

        # Rückgabe, damit der Controller weiß, dass alles durchlief
        return mix_data
