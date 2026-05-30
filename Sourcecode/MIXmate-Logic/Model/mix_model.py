import sqlite3
import os
from Model.db_bootstrap import ensure_database

class MixModel:

    def __init__(self, db_path=None):
        # Standardpfad zur lokalen MIXmate-Datenbank.
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        ensure_database(db_path)
        print("DB-Pfad:", db_path)

        # DB-Pfad fuer spaetere Zugriffe merken.
        self.db_path = db_path

        # Eine Verbindung pro Model-Instanz.
        self.connection = sqlite3.connect(self.db_path)
        # Row-Factory erlaubt Dict-aehnlichen Spaltenzugriff.
        self.connection.row_factory = sqlite3.Row
        # Cursor fuehrt alle Rezept- und Debugabfragen aus.
        self.cursor = self.connection.cursor()

        # Debugausgabe der vorhandenen Tabellen.
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        print("Tabellen:", self.cursor.fetchall())


    def get_full_mix_data(self, cocktail_id):
        # Rezept, Pumpen und Positionen fuer einen Cocktail lesen.
        # Ergebnis enthaelt alles, was die Engine fuer den Mix braucht.
        query = """
        SELECT
            c.cocktail_name,
            i.name AS ingredient_name,
            ci.amount_ml,
            ci.order_index,
            p.pump_number,
            p.flow_rate_ml_s,
            p.position_steps AS position_mm,
            p.position_steps
        FROM cocktail_ingredients ci
        JOIN ingredients i 
            ON ci.ingredient_id = i.ingredient_id
        LEFT JOIN pumps p
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
            # Kein Rezept fuer diese Cocktail-ID vorhanden.
            return None

        # SQLite-Rows in normale Dicts fuer die Engine wandeln.
        data = [dict(r) for r in rows]

        for d in data:
            # order_index steuert die Dosierreihenfolge.
            if d.get("order_index") is None:
                raise ValueError("order_index ist NULL. Bitte in der DB setzen.")

        # Zutaten ohne Pumpe werden gesammelt und gemeinsam gemeldet.
        missing_pumps = []
        for d in data:
            if (
                d.get("pump_number") is None
                or d.get("flow_rate_ml_s") is None
                or d.get("position_mm") is None
            ):
                missing_pumps.append(str(d.get("ingredient_name")))

        if missing_pumps:
            # Mixstart ohne Pumpenzuordnung verhindern.
            # Set entfernt doppelte Zutatennamen aus der Fehlermeldung.
            names = ", ".join(sorted(set(missing_pumps)))
            raise ValueError(
                f"Keine Pumpenzuordnung/Kalibrierung fuer Zutaten: {names}. "
                "Bitte im Admin jeder Zutat eine Pumpe mit Flow-Rate und Position zuweisen."
            )

        # Jeder Eintrag entspricht einem Dosierschritt.
        return data

    def close(self):
        # Datenbankverbindung schliessen.
        try:
            self.connection.close()
        except Exception:
            pass
