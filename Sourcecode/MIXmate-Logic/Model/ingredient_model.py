import sqlite3
import os
from Model.db_bootstrap import ensure_database


class IngredientModel:
    def __init__(self, db_path=None):
        # Standardpfad zur lokalen MIXmate-Datenbank.
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        # Tabellen bei Bedarf vor dem Zugriff erstellen.
        ensure_database(db_path)
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        # Spaltennamen bleiben beim Mapping lesbar.
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def get_all_ingredients(self):
        # Zutatenliste stabil nach ID sortieren.
        query = """
            SELECT ingredient_id, name
            FROM ingredients
            ORDER BY ingredient_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        # DB-Rows in einfache Dicts fuer die Views umwandeln.
        ingredients = []
        for row in rows:
            ingredients.append({
                "ingredient_id": row["ingredient_id"],
                "name": row["name"]
            })
        return ingredients

    def add_ingredient(self, name: str):
        # Namen trimmen, damit keine optischen Dubletten entstehen.
        name = (name or "").strip()
        if not name:
            # Leere Zutaten koennen keiner Pumpe sinnvoll zugeordnet werden.
            raise ValueError("Name darf nicht leer sein")

        query = "INSERT INTO ingredients (name) VALUES (?)"
        self.cursor.execute(query, (name,))
        self.connection.commit()

    def rename_ingredient(self, ingredient_id: int, new_name: str):
        # Umbenennung nutzt dieselbe Normalisierung wie das Anlegen.
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Neuer Name darf nicht leer sein")

        query = "UPDATE ingredients SET name = ? WHERE ingredient_id = ?"
        self.cursor.execute(query, (new_name, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            # rowcount 0 zeigt eine nicht vorhandene Zutaten-ID.
            raise ValueError(f"ingredient_id={ingredient_id} nicht gefunden")



    def close(self):
        # DB-Verbindung defensiv schliessen.
        try:
            self.connection.close()
        except Exception:
            pass
