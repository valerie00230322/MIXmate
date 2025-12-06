from Services.mix_engine import MixEngine
from Services.status_service import MixStatus
from Model.mix_model import MixModel

# Controller Klasse für die Steuerung der Mix-Logik
class MixController:
    def __init__(self, simulation: bool =True, db_path=None):
        self.engine = MixEngine(simulation = simulation) # Steuerung für I2C oder Simulation der Mixlogik
        self.status_service = MixStatus()
        self.model = MixModel(db_path=db_path)

    # Übergabe der Mix-Anfrage an die  und Daten werden aus DB geholt
    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        print("Starte Mixvorgang für Cocktail-ID:", cocktail_id) # Debug-Ausgabe (TODO: löschen wenn GUI fertig)
        mix_data = self.model.get_full_mix_data(cocktail_id) # Daten aus der DB holen
        if not mix_data:
            raise ValueError(f"Kein Rezept für Cocktail-ID {cocktail_id} gefunden.")
        # Daten zur Weiterverarbeitung an MixEngine übergeben
        return self.engine.mix_cocktail(mix_data, factor)
    
    def get_status(self):
        return self.status_service.get_status()