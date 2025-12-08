from Hardware.i2C_logic import i2C_logic

class MixEngine:
    def __init__(self, simulation: bool = True):
        # I2C-Logik (Simulation oder Hardware)
        self.i2c = i2C_logic(simulation=simulation)

    def move_to_position(self, target_position: int):
        # aktuelle Position vom Arduino/Simulation holen
        current_position = self.i2c.get_current_position()

        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")

        # tatsächlicher Fahrbefehl (absolute Position)
        self.i2c.move_to_position(target_position)

        print(f"Bewege von Position {current_position} zu {target_position}")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")

        # Erst homing, damit die Startposition stimmt
        self.i2c.home()

        # Förderband starten (Simulation macht einfach nur Text)
        self.i2c.beladen()

        # Jede Zutat der Reihe nach verarbeiten
        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_steps = item["position_steps"]

            print(f"[MixEngine] Mische {amount_ml} ml von {ingredient} "
                  f"mit Pumpe {pump_number} (Flussrate: {flow_rate} ml/s)")

            # Sicherheit: ignorieren falls keine Pumpe oder ungültige Flussrate
            if pump_number is None or flow_rate is None or flow_rate <= 0:
                print(f"{ingredient} hat keine Pumpe -> übersprungen.")
                continue
            
            # Auf die Zielposition fahren
            self.move_to_position(position_steps)

            # Pumpdauer berechnen
            dispense_time_s = amount_ml / flow_rate
            seconds = max(1, min(255, int(round(dispense_time_s))))

            # Pumpe steuern
            self.i2c.activate_pump(pump_number, seconds)

        # Am Ende wieder entladen (Simulation zeigt nur Text)
        self.i2c.entladen()

        # wichtig: etwas zurückgeben, damit der Controller nicht None erhält
        return mix_data
