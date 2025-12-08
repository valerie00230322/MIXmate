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
        
#Liefert alle Zutaten, die zum Mixen benötigt werden
    def get_full_mix_data(self, cocktail_id):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

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
        ORDER BY ci.order_index ASC;
        """

        cur.execute(query, (cocktail_id,))
        rows = cur.fetchall()
        conn.close()

        return [dict(row) for row in rows]
