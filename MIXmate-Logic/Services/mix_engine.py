from Hardware.i2C_logic import i2C_logic


class MixEngine:
    # TODO: Simulation auf false setzen, wenn echte Hardware genutzt wird
    def __init__(self, simulation: bool = True):
        self.i2c = i2C_logic(simulation=simulation)

    def move_to_position(self, target_position: int):
        current_position = self.i2c.get_current_position() #TODO: Methode in i2C_logic implementieren
        
        if target_position is None:
            raise ValueError("Zielposition darf nicht None sein.")
             
        self.i2c.move_steps(target_position)
        print(f"Bewege von Position {current_position} zu {target_position}") # Debug-Ausgabe (TODO: löschen wenn GUI fertig)

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten dürfen nicht leer sein.")
        self.i2c.home() #vor mixen zu HomePosition fahren

        self.i2c.beladen() #TODO: Methode in i2C_logic implementieren- was macht beladen beim arduino?

        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = item["amount_ml"] * factor
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_per_s"]
            position_steps = item["position_steps"]

            print(f"[MixEngine] Mische {amount_ml} ml von {ingredient} mit Pumpe {pump_number} (Flussrate: {flow_rate} ml/s)")

            if pump_number is None or flow_rate is None or flow_rate <= 0:
                raise ValueError(f"{ingredient} hat keine Pumpe - wird deshalb übersprungen.")
                continue # Pumpe überspringen
            
            # auf absolute position fahren
            self.move_to_position(position_steps)

            # Pumpzeit berechnen
            dispense_time_s = amount_ml / flow_rate
            seconds= max(1,min(255,int(round(dispense_time_s)))) #Arduino kann nur 1-255 Sekunden annehmen

            self.i2c.activate_pump(pump_number, seconds) #TODO: Methode in i2C_logic implementieren
        
        #fertig gemixt
        self.i2c.entladen() #TODO: Methode in i2C_logic implementieren- was macht entladen beim arduino?

            