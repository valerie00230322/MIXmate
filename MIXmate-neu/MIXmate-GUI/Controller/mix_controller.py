from Logic.mix_engine import MixEngine

class MixController:
    def __init__(self):
        self.engine = MixEngine()
    # Übergabe der Mix-Anfrage an die MixEngine
    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        print(f"\n[Controller] Starte Mix für Cocktail ID {cocktail_id} (Faktor {factor})")
        return self.engine.mix_cocktail(cocktail_id, factor)
