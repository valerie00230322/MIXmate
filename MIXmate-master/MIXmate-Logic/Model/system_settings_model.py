import os
import sqlite3
from Model.db_bootstrap import ensure_database


class SystemSettingsModel:
    def __init__(self, db_path=None):
        if db_path is None:
            base = os.path.dirname(os.path.dirname(__file__))
            db_path = os.path.join(base, "Database", "MIXmate.db")

        ensure_database(db_path)
        self.db_path = db_path
        self.connection = sqlite3.connect(self.db_path)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()
        self._ensure_schema()

    def _ensure_schema(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS machine_parameters (
                param_key TEXT PRIMARY KEY,
                param_value REAL NOT NULL
            )
            """
        )
        self.connection.commit()

    def set_value(self, key: str, value: float):
        if not key:
            raise ValueError("param_key darf nicht leer sein")
        self.cursor.execute(
            """
            INSERT INTO machine_parameters (param_key, param_value)
            VALUES (?, ?)
            ON CONFLICT(param_key) DO UPDATE SET param_value=excluded.param_value
            """,
            (key, float(value)),
        )
        self.connection.commit()

    def get_value(self, key: str):
        self.cursor.execute(
            "SELECT param_value FROM machine_parameters WHERE param_key = ?",
            (key,),
        )
        row = self.cursor.fetchone()
        if row is None:
            return None
        return float(row["param_value"])

    def set_mixer_height(self, mm: float):
        self.set_value("mixer_height_mm", mm)

    def get_mixer_height(self):
        return self.get_value("mixer_height_mm")

    def set_mixer_ausschub_distance(self, mm: float):
        self.set_value("mixer_ausschub_distance_mm", mm)

    def get_mixer_ausschub_distance(self):
        return self.get_value("mixer_ausschub_distance_mm")

    def set_mixer_direction(self, left: bool):
        self.set_value("mixer_direction_left", 1.0 if bool(left) else 0.0)

    def get_mixer_direction(self):
        val = self.get_value("mixer_direction_left")
        if val is None:
            return None
        return bool(int(val))

    def set_waiting_position(self, mm: float):
        self.set_value("waiting_position_mm", mm)

    def get_waiting_position(self):
        return self.get_value("waiting_position_mm")

    def set_load_unload_position(self, mm: float):
        self.set_value("load_unload_position_mm", mm)

    def get_load_unload_position(self):
        return self.get_value("load_unload_position_mm")

    def set_homing_safe_height(self, mm: float):
        self.set_value("homing_safe_height_mm", mm)

    def get_homing_safe_height(self):
        return self.get_value("homing_safe_height_mm")

    def set_ausschub_distance(self, mm: float):
        self.set_value("ausschub_distance_mm", mm)

    def get_ausschub_distance(self):
        return self.get_value("ausschub_distance_mm")

    def set_level_ausschub_distance(self, levelnumber: int, mm: float):
        self.set_value(f"level_ausschub_distance_{int(levelnumber)}", mm)

    def get_level_ausschub_distance(self, levelnumber: int):
        return self.get_value(f"level_ausschub_distance_{int(levelnumber)}")

    def set_level_direction(self, levelnumber: int, forward: bool):
        self.set_value(f"level_direction_{int(levelnumber)}", 1.0 if bool(forward) else 0.0)

    def get_level_direction(self, levelnumber: int):
        val = self.get_value(f"level_direction_{int(levelnumber)}")
        if val is None:
            return None
        return bool(int(val))

    def set_level_height(self, levelnumber: int, mm: float):
        self.set_value(f"level_height_{int(levelnumber)}", mm)

    def get_level_height(self, levelnumber: int):
        return self.get_value(f"level_height_{int(levelnumber)}")

    def set_pump_distance(self, pump_number: int, distance_steps: float):
        self.set_value(f"pump_distance_{int(pump_number)}", distance_steps)

    def get_pump_distance(self, pump_number: int):
        return self.get_value(f"pump_distance_{int(pump_number)}")

    def set_cocktail_source_level(self, cocktail_id: int, levelnumber: int):
        self.set_value(f"cocktail_source_level_{int(cocktail_id)}", levelnumber)

    def get_cocktail_source_level(self, cocktail_id: int):
        val = self.get_value(f"cocktail_source_level_{int(cocktail_id)}")
        if val is None:
            return None
        return int(val)

    def set_simulation_mode(self, enabled: bool):
        self.set_value("simulation_mode_enabled", 1.0 if bool(enabled) else 0.0)

    def get_simulation_mode(self) -> bool:
        val = self.get_value("simulation_mode_enabled")
        if val is None:
            return False
        return bool(int(val))

    def close(self):
        try:
            self.connection.close()
        except Exception:
            pass
