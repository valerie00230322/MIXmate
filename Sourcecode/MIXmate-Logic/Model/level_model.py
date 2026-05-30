import os
import sqlite3

from Model.db_bootstrap import ensure_database


class LevelModel:
    def __init__(self, db_path: str | None = None):
        # Standardpfad zur lokalen MIXmate-Datenbank.
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        # Datenbank und Levels-Tabelle vor Zugriff vorbereiten.
        ensure_database(db_path)
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        # Spaltenzugriff per Name erleichtert Migrationen.
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        # Levels-Tabelle auf aktuelles Schema migrieren.
        self.cursor.execute("PRAGMA table_info(levels)")
        # Aktuelle Spaltenreihenfolge aus SQLite lesen.
        columns = [row["name"] for row in self.cursor.fetchall()]
        if columns == ["levelnumber"]:
            # Schema ist bereits aktuell.
            return

        # Alte Zusatzspalten werden in eine schlanke Tabelle migriert.
        self.cursor.execute("BEGIN")
        try:
            self.cursor.execute("CREATE TABLE levels_new (levelnumber INTEGER PRIMARY KEY)")
            # Nur die Ebenennummer bleibt fachlich relevant.
            self.cursor.execute("INSERT INTO levels_new (levelnumber) SELECT levelnumber FROM levels")
            self.cursor.execute("DROP TABLE levels")
            self.cursor.execute("ALTER TABLE levels_new RENAME TO levels")
            self.connection.commit()
        except Exception:
            self.connection.rollback()
            raise

    def close(self) -> None:
        # Datenbankverbindung schliessen.
        self.connection.close()

    def get_all_levels(self) -> list[dict]:
        # Alle vorhandenen Ebenennummern lesen.
        self.cursor.execute(
            """
            SELECT levelnumber
            FROM levels
            ORDER BY levelnumber
            """
        )
        rows = self.cursor.fetchall()

        # Views erwarten eine Liste einfacher Dicts.
        return [{"levelnumber": int(row["levelnumber"])} for row in rows]

    def add_level_auto(self) -> int:
        # Naechste freie Ebenennummer anlegen.
        self.cursor.execute("SELECT COALESCE(MAX(levelnumber), 0) + 1 AS next_level FROM levels")
        # Bei leerer Tabelle startet die Nummerierung mit 1.
        next_level = int(self.cursor.fetchone()["next_level"])

        self.cursor.execute(
            """
            INSERT INTO levels (levelnumber)
            VALUES (?)
            """,
            (next_level,),
        )
        self.connection.commit()

        return next_level

    def delete_level(self, levelnumber: int) -> None:
        # Unbenutzte Ebene und passende Parameter loeschen.
        self.cursor.execute("SELECT COUNT(*) AS cnt FROM levels")
        # Mindestens eine Ebene bleibt fuer Grundbetrieb erhalten.
        level_count = int(self.cursor.fetchone()["cnt"])
        if level_count <= 1:
            # Eine Ebene muss als Mindestbestand erhalten bleiben.
            raise ValueError("Die letzte Ebene kann nicht geloescht werden.")

        self.cursor.execute(
            """
            SELECT COUNT(*) AS cnt
            FROM machine_parameters
            WHERE param_key LIKE 'cocktail_source_level_%'
              AND CAST(param_value AS INTEGER) = ?
            """,
            (int(levelnumber),),
        )
        used_count = int(self.cursor.fetchone()["cnt"])
        if used_count > 0:
            # Rezept-Zuordnungen muessen vorher im Adminbereich geaendert werden.
            raise ValueError(
                f"Ebene {int(levelnumber)} ist als Glas-Quelle in {used_count} Cocktail(s) gesetzt."
            )

        # Erst Ebene loeschen, danach die zugehoerigen Parameter entfernen.
        self.cursor.execute("DELETE FROM levels WHERE levelnumber = ?", (int(levelnumber),))
        if self.cursor.rowcount == 0:
            # Keine geloeschte Zeile bedeutet unbekannte Ebenennummer.
            raise ValueError(f"levelnumber={levelnumber} nicht gefunden")

        # Hoehe und Richtung gehoeren fachlich zur geloeschten Ebene.
        self.cursor.execute(
            """
            DELETE FROM machine_parameters
            WHERE param_key IN (?, ?)
            """,
            (
                f"level_height_{int(levelnumber)}",
                f"level_direction_{int(levelnumber)}",
            ),
        )
        self.connection.commit()
