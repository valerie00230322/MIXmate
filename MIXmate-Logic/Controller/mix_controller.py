from Services.mix_engine import MixEngine
from Services.status_service import MixStatus

class MixController:
    def __init__(self):
        self.engine = MixEngine()
        self.status_service = MixStatus()

    # Übergabe der Mix-Anfrage an die MixEngine
    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        print(f"\n[Controller] Starte Mix für Cocktail ID {cocktail_id} (Faktor {factor})")
        return self.engine.mix_cocktail(cocktail_id, factor)
    
    def get_status(self):
        return self.status_service.get_status()