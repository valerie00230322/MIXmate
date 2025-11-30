from Model.mix_model import MixModel
from Controller.i2c_controller import move_to, pump
### hier wird nur das mixen gesteuert

class MixController:
    def __init__(self):
        self.model = MixModel()

    def mix_cocktail(self, cocktail_id: int):
        recipe = self.model.get_ingredients_for_cocktail(cocktail_id)
        # in db nachschauen, ob es das rezept gibt
        if recipe is None:
            print(f"Kein Rezept für Cocktail ID {cocktail_id} gefunden.")
            return None
        # wenn rezept gefunden, dann mischen
        
        print("Rezept gefunden:", recipe)
        return recipe
