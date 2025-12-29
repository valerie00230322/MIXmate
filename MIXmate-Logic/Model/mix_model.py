import sqlite3
import os

class MixModel:

    def __init__(self, db_path=None):
        # Wenn kein Pfad angegeben wurde → Standardpfad nutzen
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        print("DB-Pfad:", db_path)

        # Pfad speichern - wichtig!!
        self.db_path = db_path

        # Eine einzige DB-Verbindung verwenden
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

        # Tabellen anzeigen (nur zum Debuggen)
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tabellen:", self.cursor.fetchall())


    def get_full_mix_data(self, cocktail_id):
        query = """
        SELECT
            c.cocktail_name,
            i.name AS ingredient_name,
            ci.amount_ml,
            ci.order_index,
            p.pump_number,
            p.flow_rate_ml_s,
            p.position_steps
        FROM cocktail_ingredients ci
        JOIN ingredients i 
            ON ci.ingredient_id = i.ingredient_id
        JOIN pumps p
            ON p.ingredient_id = ci.ingredient_id
        JOIN cocktails c
            ON c.cocktail_id = ci.cocktail_id
        WHERE ci.cocktail_id = ?
        ORDER BY
            CASE WHEN ci.order_index IS NULL THEN 999999 ELSE ci.order_index END ASC,
            ci.ingredient_id ASC;
        """

        self.cursor.execute(query, (cocktail_id,))
        rows = self.cursor.fetchall()

        if not rows:
            return None

        data = [dict(r) for r in rows]

        # optional: check auf doppelte order_index / fehlende order_index
        for d in data:
            if d.get("order_index") is None:
                raise ValueError("order_index ist NULL. Bitte in der DB setzen.")

        return data
