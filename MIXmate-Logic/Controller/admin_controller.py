from Model.cocktail_model import CocktailModel
from Model.ingredient_model import IngredientModel

class AdminController:
    def __init__(self, db_path=None):
        # Modelle für DB-Zugriff
        self.cocktail_model = CocktailModel(db_path=db_path)
        self.ingredient_model = IngredientModel(db_path=db_path)

    # Zutaten

    def list_ingredients(self):
        # Alle Zutaten aus der DB holen
        return self.ingredient_model.get_all_ingredients()

    def add_ingredient(self, name: str):
        # Neue Zutat speichern
        self.ingredient_model.add_ingredient(name)

    def rename_ingredient(self, ingredient_id: int, new_name: str):
        # Zutat umbenennen
        self.ingredient_model.rename_ingredient(ingredient_id, new_name)

    # Cocktails

    def list_cocktails(self):
        # Alle Cocktails aus der DB holen
        return self.cocktail_model.get_all_cocktails()

    def add_cocktail(self, cocktail_name: str):
        # Neuen Cocktail speichern
        self.cocktail_model.add_cocktail(cocktail_name)
        return None

    def delete_cocktail(self, cocktail_id: int):
        # Cocktail und Rezeptzeilen löschen
        self.cocktail_model.delete_cocktail(cocktail_id)

    def rename_cocktail(self, cocktail_id: int, new_name: str):
        # Cocktail umbenennen
        self.cocktail_model.rename_cocktail(cocktail_id, new_name)

    # Rezepte

    def get_recipe(self, cocktail_id: int):
        # Rezept eines Cocktails anzeigen
        return self.cocktail_model.get_recipe(cocktail_id)

    def add_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        # Zutat ins Rezept einfügen
        self.cocktail_model.add_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)

    def update_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        # Rezeptzeile ändern (Menge/Reihenfolge)
        self.cocktail_model.update_recipe_item(cocktail_id, ingredient_id, amount_ml, order_index)

    def delete_recipe_item(self, cocktail_id: int, ingredient_id: int):
        # Zutat aus Rezept entfernen
        self.cocktail_model.delete_recipe_item(cocktail_id, ingredient_id)
