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
    def get_full_mix_data(self, cocktail_id: int):
        self.cursor.execute("""
            SELECT
               c.cocktail_name,
                i.name AS ingredient_name,
                ci.amount_ml,
                ci.order_index,
                p.pump_number,
                p.flow_rate_ml_per_s,
                p.position_steps
           FROM cocktail_ingredients ci
            JOIN ingredients i ON i.ingredient_id = ci.ingredient_id
            JOIN cocktails c ON c.cocktail_id = ci.cocktail_id
            JOIN pumps p ON p.ingredient_id = ci.ingredient_id
            WHERE ci.cocktail_id = ?
            ORDER BY ci.order_index ASC
            """, (cocktail_id,))
        rows = self.cursor.fetchall()

        # Strukturierte Daten übergeben
        mix_data = []
        for row in rows:
            mix_data.append({
                "cocktail_name": row[0],
                "ingredient_name": row[1],
                "amount_ml": row[2],
                "order_index": row[3],
                "pump_number": row[4],
                "flow_rate_ml_per_s": row[5],
                "position_steps": row[6],
            })
            return mix_data