import sqlite3
import os


class PumpModel:
    
    def __init__(self, db_path=None):
        # Wenn kein Pfad angegeben wurde → Standardpfad nutzen
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")
        print("DB-Pfad:", db_path)

        # Pfad speichern - wichtig!!
        self.db_path = db_path

        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()


        

    def get_all_pumps(self):
        # Gibt alle Pumpen aus der Datenbank zurück.
        query = """
            SELECT
                pump_number,
                ingredient_id,
                flow_rate_ml_s,
                position_steps
            FROM pumps
            ORDER BY pump_number
        """

        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        #als Dict zurückgeben
        pumps = []
        for row in rows:
            pumps.append({
                "pump_number": row["pump_number"],
                "ingredient_id": row["ingredient_id"],
                "flow_rate_ml_s": row["flow_rate_ml_s"],
                "position_steps": row["position_steps"]
            })

        return pumps

    def update_position_steps(self, pump_number: int, steps: int):
        # Setzt die Position (in Steps) einer Pumpe neu.
        query = """
        UPDATE pumps
        SET position_steps = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (steps, pump_number))
        self.connection.commit()


    def update_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        # Setzt eine neue Flow-Rate direkt.
        query = """
        UPDATE pumps
        SET flow_rate_ml_s = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (flow_rate_ml_s, pump_number))
        self.connection.commit()

# keine gute Lösung, aber für jetzt ok:
    def update_ingredient(self, pump_number: int, ingredient_id: int):
        # Verknüpft eine Zutat mit einer Pumpe.
        query = """
        UPDATE pumps
        SET ingredient_id = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (ingredient_id, pump_number))
        self.connection.commit()