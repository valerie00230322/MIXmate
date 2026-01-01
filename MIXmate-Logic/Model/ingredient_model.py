import sqlite3
import os


class IngredientModel:
    def __init__(self, db_path=None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def get_all_ingredients(self):
        query = """
            SELECT ingredient_id, name
            FROM ingredients
            ORDER BY ingredient_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        ingredients = []
        for row in rows:
            ingredients.append({
                "ingredient_id": row["ingredient_id"],
                "name": row["name"]
            })
        return ingredients

    def add_ingredient(self, name: str):
        name = (name or "").strip()
        if not name:
            raise ValueError("Name darf nicht leer sein")

        query = "INSERT INTO ingredients (name) VALUES (?)"
        self.cursor.execute(query, (name,))
        self.connection.commit()

    def rename_ingredient(self, ingredient_id: int, new_name: str):
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Neuer Name darf nicht leer sein")

        query = "UPDATE ingredients SET name = ? WHERE ingredient_id = ?"
        self.cursor.execute(query, (new_name, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError(f"ingredient_id={ingredient_id} nicht gefunden")



    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass
