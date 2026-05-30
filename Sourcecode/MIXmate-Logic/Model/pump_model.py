import sqlite3
import os
from Model.db_bootstrap import ensure_database


class PumpModel:
    
    def __init__(self, db_path=None):
        # Standardpfad zur lokalen MIXmate-Datenbank.
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")
        print("DB-Pfad:", db_path)

        # Datenbank und Tabellen vor Pumpenzugriff absichern.
        ensure_database(db_path)
        # DB-Pfad fuer spaetere Zugriffe merken.
        self.db_path = db_path

        self.connection = sqlite3.connect(self.db_path)
        # Row-Objekte erlauben Zugriff per Spaltenname.
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._ensure_pump_schema()


        

    def _ensure_pump_schema(self):
        # Migration: alte CHECK-Constraint (1..6) auf 1..10 erweitern.
        self.cursor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='pumps'"
        )
        # Originales CREATE TABLE zeigt alte CHECK-Constraints.
        row = self.cursor.fetchone()

        if row is None:
            # Frische DB bekommt direkt das aktuelle Pumpenschema.
            self.cursor.execute(
                """
                CREATE TABLE pumps (
                    pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 10),
                    ingredient_id INTEGER,
                    flow_rate_ml_s REAL NOT NULL,
                    position_steps INTEGER NOT NULL,
                    FOREIGN KEY (ingredient_id)
                        REFERENCES ingredients(ingredient_id)
                        ON UPDATE CASCADE
                        ON DELETE SET NULL
                )
                """
            )
            self.connection.commit()
            return

        create_sql = (row["sql"] or "").upper()
        if "BETWEEN 1 AND 6" not in create_sql:
            # Schema erlaubt bereits zehn Pumpen.
            return

        # Migration laeuft in einer Transaktion.
        self.cursor.execute("BEGIN")
        try:
            self.cursor.execute(
                """
                CREATE TABLE pumps_new (
                    pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pump_number INTEGER NOT NULL UNIQUE CHECK (pump_number BETWEEN 1 AND 10),
                    ingredient_id INTEGER,
                    flow_rate_ml_s REAL NOT NULL,
                    position_steps INTEGER NOT NULL,
                    FOREIGN KEY (ingredient_id)
                        REFERENCES ingredients(ingredient_id)
                        ON UPDATE CASCADE
                        ON DELETE SET NULL
                )
                """
            )

            self.cursor.execute(
                """
                INSERT INTO pumps_new (pump_id, pump_number, ingredient_id, flow_rate_ml_s, position_steps)
                SELECT pump_id, pump_number, ingredient_id, flow_rate_ml_s, position_steps
                FROM pumps
                """
            )

            # Alte Tabelle durch aktualisierte Kopie ersetzen.
            self.cursor.execute("DROP TABLE pumps")
            self.cursor.execute("ALTER TABLE pumps_new RENAME TO pumps")
            self.connection.commit()
        except Exception:
            # Bei Fehlern bleibt das alte Schema erhalten.
            self.connection.rollback()
            raise

    def get_all_pumps(self):
        # Alle Pumpen fuer Admin- und Kalibrieransicht laden.
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

        # Rows in einfache Dicts fuer die Views umwandeln.
        pumps = []
        for row in rows:
            # position_steps ist historisch, fachlich wird der Wert als mm genutzt.
            position_mm = row["position_steps"]
            pumps.append({
                "pump_number": row["pump_number"],
                "ingredient_id": row["ingredient_id"],
                "flow_rate_ml_s": row["flow_rate_ml_s"],
                # Neuer, klarer Name in mm.
                "position_mm": position_mm,
                # Rueckwaertskompatibel fuer bestehende Views.
                "position_steps": position_mm
            })

        return pumps

    def update_position_steps(self, pump_number: int, steps: int):
        # Pumpenposition in der historischen Steps-Spalte speichern.
        query = """
        UPDATE pumps
        SET position_steps = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (steps, pump_number))
        self.connection.commit()
        if self.cursor.rowcount == 0:
            # Update ohne Treffer zeigt eine unbekannte Pumpennummer.
            raise ValueError(f"pump_number={pump_number} nicht gefunden")

    def update_position_mm(self, pump_number: int, position_mm: int):
        # DB-Spalte heisst  position_steps, wird aber als mm verwendet.
        self.update_position_steps(pump_number, int(position_mm))


    def update_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        # Neue Flow-Rate aus der Kalibrierung speichern.
        query = """
        UPDATE pumps
        SET flow_rate_ml_s = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (flow_rate_ml_s, pump_number))
        self.connection.commit()
        if self.cursor.rowcount == 0:
            # Update ohne Treffer zeigt eine unbekannte Pumpennummer.
            raise ValueError(f"pump_number={pump_number} nicht gefunden")

    def update_ingredient(self, pump_number: int, ingredient_id: int):
        # Zutat einer Pumpe zuordnen.
        query = """
        UPDATE pumps
        SET ingredient_id = ?
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (ingredient_id, pump_number))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            # Update ohne Treffer zeigt eine unbekannte Pumpennummer.
            raise ValueError(f"pump_number={pump_number} nicht gefunden")

    def add_pump(self, pump_number: int, flow_rate_ml_s: float = 1.0, position_steps: int = 0):
        if pump_number < 1 or pump_number > 10:
            # UI und Schema erlauben Pumpen 1 bis 10.
            raise ValueError("pump_number muss zwischen 1 und 10 sein")
        if flow_rate_ml_s <= 0:
            # Positive Flow-Rate wird fuer Dosierzeit benoetigt.
            raise ValueError("flow_rate_ml_s muss > 0 sein")
        if position_steps < 0:
            # Negative Positionen sind mechanisch ungueltig.
            raise ValueError("position_steps muss >= 0 sein")

        query = """
        INSERT INTO pumps (pump_number, ingredient_id, flow_rate_ml_s, position_steps)
        VALUES (?, NULL, ?, ?)
        """
        self.cursor.execute(query, (pump_number, float(flow_rate_ml_s), int(position_steps)))
        self.connection.commit()

    def delete_pump(self, pump_number: int):
        # Pumpe anhand der sichtbaren Pumpennummer loeschen.
        query = """
        DELETE FROM pumps
        WHERE pump_number = ?
        """
        self.cursor.execute(query, (pump_number,))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            # Delete ohne Treffer zeigt eine unbekannte Pumpennummer.
            raise ValueError(f"pump_number={pump_number} nicht gefunden")

    def close(self):
        # DB-Verbindung defensiv schliessen.
        try:
            self.connection.close()
        except Exception:
            pass
