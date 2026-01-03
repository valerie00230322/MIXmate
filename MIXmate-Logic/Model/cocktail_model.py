import sqlite3
import os

class CocktailModel:
    def __init__(self, db_path=None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def get_all_cocktails(self):
        query = """
            SELECT cocktail_id, cocktail_name
            FROM cocktails
            ORDER BY cocktail_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        cocktails = []
        for row in rows:
            cocktails.append({
                "cocktail_id": row["cocktail_id"],
                "cocktail_name": row["cocktail_name"]
            })
        return cocktails

    def add_cocktail(self, cocktail_name: str):
        cocktail_name = (cocktail_name or "").strip()
        if not cocktail_name:
            raise ValueError("Cocktail-Name darf nicht leer sein")

        query = "INSERT INTO cocktails (cocktail_name) VALUES (?)"
        self.cursor.execute(query, (cocktail_name,))
        
        self.connection.commit()

    def rename_cocktail(self, cocktail_id: int, new_name: str):
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Neuer Name darf nicht leer sein")

        query = "UPDATE cocktails SET cocktail_name = ? WHERE cocktail_id = ?"
        self.cursor.execute(query, (new_name, cocktail_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError(f"cocktail_id={cocktail_id} nicht gefunden")

    def delete_cocktail(self, cocktail_id: int):
        # Erst Rezeptzeilen löschen, dann den Cocktail selbst.
        q1 = "DELETE FROM cocktail_ingredients WHERE cocktail_id = ?"
        self.cursor.execute(q1, (cocktail_id,))

        q2 = "DELETE FROM cocktails WHERE cocktail_id = ?"
        self.cursor.execute(q2, (cocktail_id,))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError(f"cocktail_id={cocktail_id} nicht gefunden")

    # Ab hier sind Methoden für das Rezeptmanagement.
    def get_recipe(self, cocktail_id: int):
        # Liefert das Rezept mit Namen, Menge und Reihenfolge.
        query = """
            SELECT
                ci.cocktail_id,
                ci.ingredient_id,
                i.name AS ingredient_name,
                ci.amount_ml,
                ci.order_index
            FROM cocktail_ingredients ci
            JOIN ingredients i ON i.ingredient_id = ci.ingredient_id
            WHERE ci.cocktail_id = ?
            ORDER BY ci.order_index
        """
        self.cursor.execute(query, (cocktail_id,))
        rows = self.cursor.fetchall()

        recipe = []
        for row in rows:
            recipe.append({
                "cocktail_id": row["cocktail_id"],
                "ingredient_id": row["ingredient_id"],
                "ingredient_name": row["ingredient_name"],
                "amount_ml": row["amount_ml"],
                "order_index": row["order_index"]
            })
        return recipe
    #hinzufügen von Rezepteinträgen
    def add_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        if amount_ml <= 0:
            raise ValueError("amount_ml muss > 0 sein")
        if order_index <= 0:
            raise ValueError("order_index muss >= 1 sein")

        query = """
            INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index)
            VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(query, (cocktail_id, ingredient_id, amount_ml, order_index))
        self.connection.commit()
        
    #update von Rezepteinträgen (Fehlerkorrektur etc.)
    def update_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        if amount_ml <= 0:
            raise ValueError("amount_ml muss > 0 sein")
        if order_index <= 0:
            raise ValueError("order_index muss >= 1 sein")

        if self._order_index_exists(cocktail_id, order_index, exclude_ingredient_id=ingredient_id):
            raise ValueError(f"order_index {order_index} ist für diesen Cocktail bereits vergeben")

        query = """
            UPDATE cocktail_ingredients
            SET amount_ml = ?, order_index = ?
            WHERE cocktail_id = ? AND ingredient_id = ?
        """
        self.cursor.execute(query, (amount_ml, order_index, cocktail_id, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError("Rezeptzeile nicht gefunden (cocktail_id/ingredient_id stimmt nicht)")


    def delete_recipe_item(self, cocktail_id: int, ingredient_id: int):
        query = """
            DELETE FROM cocktail_ingredients
            WHERE cocktail_id = ? AND ingredient_id = ?
        """
        self.cursor.execute(query, (cocktail_id, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError("Rezeptzeile nicht gefunden (cocktail_id/ingredient_id stimmt nicht)")
        
    def _order_index_exists(self, cocktail_id: int, order_index: int, exclude_ingredient_id: int = None) -> bool:
        if exclude_ingredient_id is None:
            q = """
                SELECT COUNT(*) AS cnt
                FROM cocktail_ingredients
                WHERE cocktail_id = ? AND order_index = ?
            """
            self.cursor.execute(q, (cocktail_id, order_index))
        else:
            q = """
                SELECT COUNT(*) AS cnt
                FROM cocktail_ingredients
                WHERE cocktail_id = ? AND order_index = ? AND ingredient_id != ?
            """
            self.cursor.execute(q, (cocktail_id, order_index, exclude_ingredient_id))

        row = self.cursor.fetchone()
        return (row["cnt"] if row else 0) > 0

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass