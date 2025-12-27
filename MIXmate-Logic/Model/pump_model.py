
class PumpModel:
    
    def __init__(self):
        pass

    def get_all_pumps(self):
        # Gibt alle Pumpen aus der Datenbank zurück.
        pass

    def update_position_steps(self, pump_number: int, steps: int):
        # Setzt die Position (in Steps) einer Pumpe neu.
        pass

    def update_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        # Setzt eine neue Flow-Rate direkt.
        pass

    def update_ingredient(self, pump_number: int, ingredient_id: int):
        # Verknüpft eine Zutat mit einer Pumpe.
        pass