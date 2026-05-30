import sqlite3
import os
from Model.db_bootstrap import ensure_database

class CocktailModel:
    def __init__(self, db_path=None):
        # Standardpfad zur lokalen MIXmate-Datenbank.
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        # DB-Struktur vor dem ersten Zugriff absichern.
        ensure_database(db_path)
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        # Row-Factory erlaubt Spaltenzugriff per Name.
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def get_all_cocktails(self):
        # Cocktails stabil nach ID sortiert fuer Listenansichten.
        query = """
            SELECT cocktail_id, cocktail_name
            FROM cocktails
            ORDER BY cocktail_id
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        # SQLite-Rows in einfache Dicts fuer Controller und Views umformen.
        cocktails = []
        for row in rows:
            cocktails.append({
                "cocktail_id": row["cocktail_id"],
                "cocktail_name": row["cocktail_name"]
            })
        return cocktails

    def add_cocktail(self, cocktail_name: str):
        # Eingaben aus UI/Konsole ohne Rand-Leerzeichen speichern.
        cocktail_name = (cocktail_name or "").strip()
        if not cocktail_name:
            # Leere Namen wuerden spaeter in der Auswahl unklar wirken.
            raise ValueError("Cocktail-Name darf nicht leer sein")

        query = "INSERT INTO cocktails (cocktail_name) VALUES (?)"
        self.cursor.execute(query, (cocktail_name,))
        
        self.connection.commit()

    def rename_cocktail(self, cocktail_id: int, new_name: str):
        # Neuer Name wird wie beim Anlegen normalisiert.
        new_name = (new_name or "").strip()
        if not new_name:
            raise ValueError("Neuer Name darf nicht leer sein")

        query = "UPDATE cocktails SET cocktail_name = ? WHERE cocktail_id = ?"
        self.cursor.execute(query, (new_name, cocktail_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            # rowcount 0 bedeutet: ID existiert nicht.
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

    # Methoden für das Rezeptmanagement.
    def get_recipe(self, cocktail_id: int):
        # Liefert das Rezept mit Namen, Menge und Reihenfolge.
        # Join holt den lesbaren Zutatennamen zur Rezeptzeile.
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

        # Rezeptzeilen als Dicts an die UI weitergeben.
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
    # Rezeptzeile mit Menge und Reihenfolge anlegen.
    def add_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        if amount_ml <= 0:
            # Nullmenge waere im Mixablauf wirkungslos.
            raise ValueError("amount_ml muss > 0 sein")
        if order_index <= 0:
            # Reihenfolge startet bewusst bei 1.
            raise ValueError("order_index muss >= 1 sein")
        if self._order_index_exists(cocktail_id, order_index):
            # Doppelte Reihenfolge macht den Pumpenablauf uneindeutig.
            raise ValueError(f"order_index {order_index} ist für diesen Cocktail bereits vergeben")

        query = """
            INSERT INTO cocktail_ingredients (cocktail_id, ingredient_id, amount_ml, order_index)
            VALUES (?, ?, ?, ?)
        """
        self.cursor.execute(query, (cocktail_id, ingredient_id, amount_ml, order_index))
        self.connection.commit()
        
    # Bestehende Rezeptzeile korrigieren.
    def update_recipe_item(self, cocktail_id: int, ingredient_id: int, amount_ml: float, order_index: int):
        if amount_ml <= 0:
            raise ValueError("amount_ml muss > 0 sein")
        if order_index <= 0:
            raise ValueError("order_index muss >= 1 sein")

        if self._order_index_exists(cocktail_id, order_index, exclude_ingredient_id=ingredient_id):
            # Aktuelle Zutat wird beim Duplikat-Check ausgenommen.
            raise ValueError(f"order_index {order_index} ist für diesen Cocktail bereits vergeben")

        query = """
            UPDATE cocktail_ingredients
            SET amount_ml = ?, order_index = ?
            WHERE cocktail_id = ? AND ingredient_id = ?
        """
        self.cursor.execute(query, (amount_ml, order_index, cocktail_id, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            # Kein Treffer bedeutet falsche Cocktail- oder Zutaten-ID.
            raise ValueError("Rezeptzeile nicht gefunden (cocktail_id/ingredient_id stimmt nicht)")


    def delete_recipe_item(self, cocktail_id: int, ingredient_id: int):
        # Rezeptzeile anhand beider Schluessel entfernen.
        query = """
            DELETE FROM cocktail_ingredients
            WHERE cocktail_id = ? AND ingredient_id = ?
        """
        self.cursor.execute(query, (cocktail_id, ingredient_id))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError("Rezeptzeile nicht gefunden (cocktail_id/ingredient_id stimmt nicht)")
        
    def _order_index_exists(self, cocktail_id: int, order_index: int, exclude_ingredient_id: int = None) -> bool:
        # Beim Update darf die eigene Rezeptzeile den Index behalten.
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
        # COUNT liefert 0, wenn die Reihenfolge frei ist.
        return (row["cnt"] if row else 0) > 0

    def close(self):
        # DB-Verbindung defensiv schliessen.
        try:
            self.connection.close()
        except Exception:
            pass
