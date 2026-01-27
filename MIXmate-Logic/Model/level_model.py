import sqlite3
import os


class LevelModel:
    def __init__(self, db_path: str | None = None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

    def close(self) -> None:
        self.connection.close()

    def get_all_levels(self) -> list[dict]:
        query = """
            SELECT levelnumber, extension_distance
            FROM levels
            ORDER BY levelnumber
        """
        self.cursor.execute(query)
        rows = self.cursor.fetchall()

        return [
            {
                "levelnumber": int(row["levelnumber"]),
                "extension_distance": float(row["extension_distance"]),
            }
            for row in rows
        ]

    def get_distance(self, levelnumber: int) -> float:
        query = """
            SELECT extension_distance
            FROM levels
            WHERE levelnumber = ?
        """
        self.cursor.execute(query, (levelnumber,))
        row = self.cursor.fetchone()

        if row is None:
            raise ValueError(f"levelnumber={levelnumber} nicht gefunden")

        return float(row["extension_distance"])

    def update_distance(self, levelnumber: int, new_distance: float) -> None:
        if new_distance is None or float(new_distance) < 0:
            raise ValueError("new_distance muss >= 0 sein")

        query = """
            UPDATE levels
            SET extension_distance = ?
            WHERE levelnumber = ?
        """
        self.cursor.execute(query, (float(new_distance), levelnumber))
        self.connection.commit()

        if self.cursor.rowcount == 0:
            raise ValueError(f"levelnumber={levelnumber} nicht gefunden")

    def add_level_auto(self, extension_distance: float = 0.0) -> int:
        if extension_distance is None or float(extension_distance) < 0:
            raise ValueError("extension_distance muss >= 0 sein")

        # nächstes Level = MAX(levelnumber) + 1
        self.cursor.execute("SELECT COALESCE(MAX(levelnumber), 0) + 1 AS next_level FROM levels")
        next_level = int(self.cursor.fetchone()["next_level"])

        query = """
            INSERT INTO levels (levelnumber, extension_distance)
            VALUES (?, ?)
        """
        self.cursor.execute(query, (next_level, float(extension_distance)))
        self.connection.commit()

        return next_level

#TODO: delete_level(levelnumber)