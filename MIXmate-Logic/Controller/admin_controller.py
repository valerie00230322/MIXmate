from Model.cocktail_model import CocktailModel
from Model.ingredient_model import IngredientModel

class AdminController:
    def __init__(self,  db_path=None):
        self.cocktail_model = CocktailModel(db_path=db_path)
        self.ingredient_model = IngredientModel(db_path=db_path)

    # Zutaten Methoden
    #auflistung aller Zutaten zur Orientierung
    def list_ingredients(self):
        return self.ingredient_model.get_all_ingredients()
    
    #zutaten hinzufügen
    def add_ingredient(self, name: str):
        self.ingredient_model.add_ingredient(name)

    #zutat umbenennen?
    def rename_ingredient(self, ingredient_id: int, new_name: str):
        self.ingredient_model.rename_ingredient(ingredient_id, new_name)
        
    #Methoden für Cocktails

    #auflistung aller Cocktails zur Orientierung
    def list_cocktails(self):
        return self.cocktail_model.get_all_cocktails()
    
    #cocktail hinzufügen
    def add_cocktail(self, cocktail_name: str):
        self.cocktail_model.add_cocktail(cocktail_name)

    #cocktail löschen
    def delete_cocktail(self, cocktail_id: int):
        self.cocktail_model.delete_cocktail(cocktail_id)
    