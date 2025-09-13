import json
import os


class RecipeModel:
    def __init__(self, filepath="recipes.json"):
        self.filepath = filepath
        if not os.path.exists(self.filepath):
            self._save_default_recipes()

    def _save_default_recipes(self):
        data = [
            {
                "name": "Mojito",
                "ingredients": [
                    {"name": "Rum", "amount_ml": 50},
                    {"name": "Limettensaft", "amount_ml": 30},
                    {"name": "Zucker", "amount_ml": 10},
                    {"name": "Soda", "amount_ml": 100},
                ],
            },
            {
                "name": "Tequila Sunrise",
                "ingredients": [
                    {"name": "Tequila", "amount_ml": 50},
                    {"name": "Orangensaft", "amount_ml": 100},
                    {"name": "Grenadine", "amount_ml": 10},
                ],
            },
        ]
        self.save_recipes(data)

    def load_recipes(self):
        with open(self.filepath, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_recipes(self, recipes):
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(recipes, f, indent=4, ensure_ascii=False)

    def get_recipe_by_name(self, name):
        recipes = self.load_recipes()
        for r in recipes:
            if r["name"].lower() == name.lower():
                return r
        return None

    def add_recipe(self, recipe):
        recipes = self.load_recipes()
        recipes.append(recipe)
        self.save_recipes(recipes)

    def delete_recipe(self, name):
        recipes = self.load_recipes()
        recipes = [r for r in recipes if r["name"].lower() != name.lower()]
        self.save_recipes(recipes)
