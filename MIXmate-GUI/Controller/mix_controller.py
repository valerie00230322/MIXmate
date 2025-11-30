from Model.mix_model import MixModel
from Controller.i2c_controller import move_to, pump
### hier wird nur das mixen gesteuert

class MixController:
    def __init__(self):
        self.model = MixModel()

    def mix_cocktail(self, cocktail_id: int):
        recipe = self.model.get_ingredients_for_cocktail(cocktail_id)
        print("Rezept gefunden:", recipe)
        return recipe
