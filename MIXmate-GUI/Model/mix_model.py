import sqlite3
import os

class MixModel:
    def __init__(self, db_path=None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        print("DB-Pfad:", db_path)

        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()

        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tabellen:", self.cursor.fetchall())

    def get_ingredients_for_cocktail(self, cocktail_id):
        self.cursor.execute("""
            SELECT i.name, ci.amount_ml, ci.order_index
            FROM cocktail_ingredients ci
            JOIN ingredients i ON i.ingredient_id = ci.ingredient_id
            WHERE ci.cocktail_id = ?
            ORDER BY ci.order_index ASC
        """, (cocktail_id,))

        return self.cursor.fetchall()

