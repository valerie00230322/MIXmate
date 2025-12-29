from Services.mix_engine import MixEngine
from Model.mix_model import MixModel


class MixController:
    def __init__(self, simulation: bool = False, db_path=None):
        self.engine = MixEngine(simulation=simulation)
        self.model = MixModel(db_path=db_path)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept für Cocktail-ID {cocktail_id} gefunden.")
        return self.engine.mix_cocktail(mix_data, factor)

    def get_status(self):
        return self.engine.get_status()
