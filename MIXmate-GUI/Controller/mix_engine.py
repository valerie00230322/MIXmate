from Model.mix_model import MixModel
from i2c_controller import pump, move_to

class MixEngine:
    def __init__(self):
        self.model = MixModel()

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        # factor = Portionsgröße, z.B. 1.0 = normal, 2.0 = doppelt, 0.5 = halb
        mix_data = self.model.get_full_mix_data(cocktail_id)