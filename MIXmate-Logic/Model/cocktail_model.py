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
            SELECT cocktail_id, name
            FROM cocktails
            ORDER BY cocktail_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        cocktails = []
        for row in rows:
            cocktails.append({
                "cocktail_id": row["cocktail_id"],
                "name": row["name"]
            })
        return cocktails
    
    def add_cocktail(self, cocktail_name: str):
        cocktail_name = (cocktail_name or "").strip()
        if not cocktail_name:
            raise ValueError("Cocktail-Name darf nicht leer sein")

        query = "INSERT INTO cocktails (name) VALUES (?)"
        self.cursor.execute(query, (cocktail_name,))
        self.connection.commit()

        