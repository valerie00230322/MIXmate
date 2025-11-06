# Controller/pump_controller.py
from __future__ import annotations
import math
import sqlite3
from pathlib import Path
from time import sleep, monotonic
from typing import Optional, Dict, Any, List

from Controller.i2c_driver import I2CDriver, I2CConfig


class PumpController:
    """
    Orchestriert Statuscheck + Dosierung.
    Nutzt Pumpen-/Zuordnungsdaten aus derselben DB wie das RecipeModel.
    """

    def __init__(
        self,
        *,
        db_filename: str = "mixmate-oida.db",
        i2c_bus: int = 1,
        arduino_addr: int = 0x13,
        dev_mode: bool = False,
        log_i2c: bool = False,
    ):
        self.db_path = Path(__file__).resolve().parents[1] / "Model" / db_filename
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA foreign_keys = ON;")
        self._conn.row_factory = sqlite3.Row

        self.i2c = I2CDriver(I2CConfig(bus=i2c_bus, addr=arduino_addr), dev_mode=dev_mode, log_i2c=log_i2c)
        self._init_tables()

        # Tuning
        self.poll_interval_s = 0.2
        self.start_idle_timeout_s = 8.0
        self.post_pump_idle_timeout_s = 6.0

    # ---------- public toggles ----------
    def enable_simulation(self): self.i2c.set_dev_mode(True)
    def disable_simulation(self): self.i2c.set_dev_mode(False)
    def is_simulation(self) -> bool: return self.i2c.dev_mode
    def set_log_i2c(self, enabled: bool): self.i2c.set_log(enabled)

    # ---------- schema for pumps (einmalig) ----------
    def _init_tables(self):
        cur = self._conn.cursor()
        cur.executescript(
            """
            CREATE TABLE IF NOT EXISTS Pumps (
                pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                channel INTEGER NOT NULL,          -- 1..5: Arduino-Kanal
                flow_ml_per_s REAL NOT NULL DEFAULT 1.0
            );

            CREATE TABLE IF NOT EXISTS PumpAssignments (
                ingredient_id INTEGER NOT NULL UNIQUE,
                pump_id INTEGER NOT NULL,
                FOREIGN KEY (ingredient_id) REFERENCES Ingredients(ingredient_id) ON DELETE CASCADE,
                FOREIGN KEY (pump_id)      REFERENCES Pumps(pump_id) ON DELETE RESTRICT
            );
            """
        )
        self._conn.commit()

    # ---------- db utils ----------
    def _get_pump(self, pump_id: int) -> Optional[sqlite3.Row]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM Pumps WHERE pump_id=?", (pump_id,))
        return cur.fetchone()

    def _time_for(self, pump_id: int, amount_ml: float) -> int:
        pump = self._get_pump(pump_id)
        if not pump:
            raise ValueError(f"Pumpe {pump_id} nicht gefunden")
        flow = max(float(pump["flow_ml_per_s"]), 0.0001)
        seconds = amount_ml / flow
        # runde auf ganze Sekunden (nach oben), min 1, max 65535
        t = int(max(1, math.ceil(seconds)))
        return min(t, 65535)

    # ---------- status helpers ----------
    def _wait_until_idle(self, timeout_s: float) -> Dict[str, Any]:
        """Wartet bis Arduino 'idle' (state==0) meldet oder timeout."""
        t0 = monotonic()
        last = {}
        while monotonic() - t0 <= timeout_s:
            last = self.i2c.status()
            if last.get("state", 1) == 0:
                return last
            sleep(self.poll_interval_s)
        raise TimeoutError(f"Arduino bleibt busy (state={last.get('state')}) > {timeout_s:.1f}s")

    # ---------- public api ----------
    def preflight_check(self) -> Dict[str, Any]:
        st = self.i2c.status()
        return {
            "ok": st.get("state", 255) == 0,
            "status_bit": st.get("state"),
            "distance_mm": st.get("pos_mm"),
            "last_cmd": st.get("last_cmd"),
        }

    def dispense_by_id(self, *, pump_id: int, amount_ml: float, pump_channel: Optional[int] = None):
        """
        Führt EINE Dosierung aus:
        - wartet auf Idle,
        - konvertiert ml -> s (flow der Pumpe),
        - schickt CMD_PUMPE(channel, sek),
        - wartet die Zeit und prüft wieder auf Idle.
        """
        pump = self._get_pump(pump_id)
        if not pump:
            raise ValueError(f"Pumpe {pump_id} nicht in DB")
        channel = int(pump_channel) if pump_channel else int(pump["channel"])
        if not (1 <= channel <= 5):
            raise ValueError("pump_channel muss 1..5 sein")

        # 1) vor Start idle?
        self._wait_until_idle(self.start_idle_timeout_s)

        # 2) Zeit berechnen
        seconds = self._time_for(pump_id, float(amount_ml))

        # 3) feuern
        self.i2c.pumpe(channel, seconds)

        # 4) grob warten (damit Befehle nicht überlappen)
        sleep(max(0.1, seconds))

        # 5) nachlaufend idle-check (kurz)
        try:
            self._wait_until_idle(self.post_pump_idle_timeout_s)
        except TimeoutError:
            # nicht fatal — viele Sketche melden kein busy während Pumpen
            pass

    # ---------- demo/helper ----------
    def ensure_demo_pumps_if_needed(self):
        """
        Lege 5 Pumpen an (Kanäle 1..5) mit Standard-Flow, wenn noch keine existiert.
        Weise optional die ersten 5 Ingredients automatisch zu (nur wenn keine Zuordnung existiert).
        """
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) AS c FROM Pumps;")
        if cur.fetchone()["c"] == 0:
            cur.executemany(
                "INSERT INTO Pumps (name, channel, flow_ml_per_s) VALUES (?, ?, ?)",
                [(f"Pump {i}", i, 20.0) for i in range(1, 6)]  # <- Flow grob 20 ml/s als Default
            )
            self._conn.commit()

        # auto-assign, falls noch KEINE einzige Zuordnung existiert
        cur.execute("SELECT COUNT(*) AS c FROM PumpAssignments;")
        if cur.fetchone()["c"] == 0:
            # nimm die ersten 5 Zutaten (alphabetisch) und mappe sie 1:1 auf Kanäle 1..5
            cur.execute("SELECT ingredient_id, name FROM Ingredients ORDER BY name LIMIT 5;")
            ingredients = cur.fetchall()
            for idx, row in enumerate(ingredients, start=1):
                cur.execute("SELECT pump_id FROM Pumps WHERE channel=?", (idx,))
                pump_id = cur.fetchone()["pump_id"]
                cur.execute(
                    "INSERT OR IGNORE INTO PumpAssignments (ingredient_id, pump_id) VALUES (?, ?)",
                    (row["ingredient_id"], pump_id)
                )
            self._conn.commit()
