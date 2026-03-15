from Services.mix_engine import MixEngine
from Model.mix_model import MixModel


class MixController:
    def __init__(self, db_path=None):
        self.engine = MixEngine()
        self.model = MixModel(db_path=db_path)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            item["cocktail_id"] = int(cocktail_id)
        return self.engine.mix_cocktail(mix_data, factor)

    def get_status(self):
        return self.engine.get_status()

    # Fuer GUI: vorbereiten des DB Teils im UI Thread, verhindert GUI freeze.
    def prepare_mix(self, cocktail_id: int):
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            item["cocktail_id"] = int(cocktail_id)
        return mix_data

    def run_mix(self, mix_data, factor: float = 1.0):
        return self.engine.mix_cocktail(mix_data, factor)

    def shutdown(self):
        try:
            self.engine.close()
        finally:
            self.model.close()
