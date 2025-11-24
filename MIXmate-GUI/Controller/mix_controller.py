from Model.mix_model import MixModel

class MixController:
    def __init__(self):
        self.model = MixModel()   # <-- Model hier erzeugen

class MixController:
    def mix_cocktail(self, cocktail_id):
        recipe = self.model.get_ingredients_for_cocktail(cocktail_id)
        

