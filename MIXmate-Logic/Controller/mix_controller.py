from Services.mix_engine import MixEngine
from Model.mix_model import MixModel


class MixController:
    # nicht vergessen :  sim modus
    def __init__(self, simulation: bool = True, db_path=None):
        self.engine = MixEngine(simulation=simulation)
        self.model = MixModel(db_path=db_path)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept für Cocktail-ID {cocktail_id} gefunden.")
        return self.engine.mix_cocktail(mix_data, factor)

    def get_status(self):
        return self.engine.get_status()
    
    #für gui : vorbereiten des DB Teils im UI Thread--> verhindert gui freeze
    def prepare_mix(self, cocktail_id: int):
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept für Cocktail-ID {cocktail_id} gefunden.")
        return mix_data
   
    def run_mix(self, mix_data, factor: float = 1.0):
        return self.engine.mix_cocktail(mix_data, factor)