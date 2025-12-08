from Services.mix_engine import MixEngine
from Services.status_service import MixStatus
from Model.mix_model import MixModel

class MixController:
    def __init__(self, simulation: bool = True, db_path=None):
        # MixEngine steuert Pumpe + Schlitten
        self.engine = MixEngine(simulation=simulation)

        # Statusservice nur als Dummy (kann später erweitert werden)
        self.status_service = MixStatus()

        # Datenbankzugriff
        self.model = MixModel(db_path=db_path)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        print("Starte Mixvorgang für Cocktail-ID:", cocktail_id)

        # Rezept aus der Datenbank holen
        mix_data = self.model.get_full_mix_data(cocktail_id)

        if not mix_data:
            raise ValueError(f"Kein Rezept für Cocktail-ID {cocktail_id} gefunden.")

        # MixEngine macht die eigentliche Arbeit und gibt mix_data zurück
        result = self.engine.mix_cocktail(mix_data, factor)
        return result

    def get_status(self):
        return self.status_service.get_status()
