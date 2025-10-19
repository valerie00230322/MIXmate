# Model/pump_model.py

from __future__ import annotations

import sqlite3
from pathlib import Path
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Optional, Tuple, List

# Optional: echte I²C – in Dev/PC-Umgebung oft nicht vorhanden
try:
    from smbus2 import SMBus, i2c_msg  # pip install smbus2
except Exception:
    SMBus = None
    i2c_msg = None


# -----------------------------
# Hilfsfunktionen (Framing/CRC)
# -----------------------------
def crc8_maxim(data: bytes) -> int:
    """CRC-8 (Dallas/Maxim, poly 0x31, init 0x00). Notfalls durch simple Checksum ersetzbar."""
    crc = 0x00
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 0x80:
                crc = (crc << 1) ^ 0x31
            else:
                crc <<= 1
            crc &= 0xFF
    return crc


def le16(n: int) -> bytes:
    return int(n).to_bytes(2, "little", signed=False)


def frame(cmd: int, pump_id: int, param1: int = 0, param2: int = 0) -> bytes:
    """
    Einfaches Frame-Layout:
    [CMD(1B)] [PUMP_ID(1B)] [PARAM1(2B LE)] [PARAM2(2B LE)] [CRC8(1B)]
    """
    core = bytes([cmd & 0xFF, pump_id & 0xFF]) + le16(param1) + le16(param2)
    return core + bytes([crc8_maxim(core)])


# -----------------------------
# Datenklassen
# -----------------------------
@dataclass(frozen=True)
class Pump:
    pump_id: int
    name: str
    i2c_address: int
    channel: int
    flow_ml_per_s: float
    is_enabled: bool


# -----------------------------
# PumpModel
# -----------------------------
class PumpModel:
    """
    Eigenständiges Model für Pumpen & I²C.
    - Verwaltet Pumpenstammdaten (Kalibrierung)
    - Loggt optional I²C-Nachrichten
    - Führt PREPARE -> DISPENSE aus und protokolliert PumpRuns
    """

    # Befehle (mit Firmware abstimmen)
    CMD_STATUS = 0x10
    CMD_PREPARE = 0x20
    CMD_DISPENSE = 0x21

    def __init__(
        self,
        db_filename: str = "mixmate-oida.db",
        i2c_bus: int = 1,
        log_i2c: bool = False,     # bei Bedarf Debug-Log einschalten
        dev_mode: bool = False,    # erzwingt Dummy-Responses auch wenn smbus2 vorhanden
    ) -> None:
        self.db_path = Path(__file__).resolve().parent / db_filename
        self.i2c_bus_num = int(i2c_bus)
        self.log_i2c = bool(log_i2c)
        self.dev_mode = bool(dev_mode)
        self._init_db()

    # ---------------- DB ----------------
    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self):
        with self._connect() as conn:
            cur = conn.cursor()
            cur.executescript(
                """
                CREATE TABLE IF NOT EXISTS Pumps (
                    pump_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    i2c_address INTEGER NOT NULL CHECK (i2c_address BETWEEN 0 AND 127),
                    channel INTEGER NOT NULL,
                    flow_ml_per_s REAL NOT NULL CHECK (flow_ml_per_s > 0),
                    is_enabled INTEGER NOT NULL DEFAULT 1
                );

                CREATE TABLE IF NOT EXISTS PumpRuns (
                    run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pump_id INTEGER NOT NULL,
                    target_ml REAL NOT NULL CHECK (target_ml > 0),
                    duration_ms INTEGER NOT NULL CHECK (duration_ms > 0),
                    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    finished_at DATETIME,
                    status TEXT NOT NULL DEFAULT 'done', -- simple: done|error
                    error_code TEXT,
                    FOREIGN KEY (pump_id) REFERENCES Pumps(pump_id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS I2CLog (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    direction TEXT NOT NULL CHECK (direction IN ('tx','rx')),
                    bus INTEGER NOT NULL,
                    i2c_address INTEGER NOT NULL,
                    msg_type TEXT,
                    payload BLOB NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );

                -- Optionaler Status-Cache: letztes Sample (statt Langzeit-Log)
                CREATE TABLE IF NOT EXISTS PlatformStatus (
                    id INTEGER PRIMARY KEY CHECK (id=1),
                    status_bit INTEGER NOT NULL DEFAULT 0,
                    distance_mm REAL,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                );
                INSERT OR IGNORE INTO PlatformStatus (id, status_bit, distance_mm)
                VALUES (1, 0, NULL);
                """
            )

    # ------------- Pumpen-CRUD -------------
    def add_or_update_pump(
        self,
        name: str,
        i2c_address: int,
        channel: int,
        flow_ml_per_s: float,
        enabled: bool = True,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO Pumps (name, i2c_address, channel, flow_ml_per_s, is_enabled)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    i2c_address=excluded.i2c_address,
                    channel=excluded.channel,
                    flow_ml_per_s=excluded.flow_ml_per_s,
                    is_enabled=excluded.is_enabled
                """,
                (name, int(i2c_address), int(channel), float(flow_ml_per_s), 1 if enabled else 0),
            )

    def get_pump_by_name(self, name: str) -> Optional[Pump]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT pump_id, name, i2c_address, channel, flow_ml_per_s, is_enabled FROM Pumps WHERE name = ?",
                (name,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return Pump(
                pump_id=row["pump_id"],
                name=row["name"],
                i2c_address=row["i2c_address"],
                channel=row["channel"],
                flow_ml_per_s=row["flow_ml_per_s"],
                is_enabled=bool(row["is_enabled"]),
            )

    def list_pumps(self) -> List[Pump]:
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT pump_id, name, i2c_address, channel, flow_ml_per_s, is_enabled FROM Pumps ORDER BY name"
            )
            return [
                Pump(
                    pump_id=r["pump_id"],
                    name=r["name"],
                    i2c_address=r["i2c_address"],
                    channel=r["channel"],
                    flow_ml_per_s=r["flow_ml_per_s"],
                    is_enabled=bool(r["is_enabled"]),
                )
                for r in cur.fetchall()
            ]

    # ------------- I²C Low-Level -------------
    def _should_use_dummy(self) -> bool:
        return self.dev_mode or SMBus is None or i2c_msg is None

    def _log(self, direction: str, addr: int, payload: bytes, msg_type: str | None):
        if not self.log_i2c:
            return
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO I2CLog (direction, bus, i2c_address, msg_type, payload) VALUES (?, ?, ?, ?, ?)",
                (direction, self.i2c_bus_num, int(addr), msg_type, payload),
            )

    def _i2c_write(self, addr: int, payload: bytes, msg_type: str | None):
        self._log("tx", addr, payload, msg_type)
        if self._should_use_dummy():
            return
        with SMBus(self.i2c_bus_num) as bus:
            bus.i2c_rdwr(i2c_msg.write(addr, payload))

    def _i2c_read(self, addr: int, nbytes: int, msg_type: str | None) -> bytes:
        if self._should_use_dummy():
            # Dummy: [HDR, status=1, distance=123mm LE]
            data = bytes([0xAA, 0x01, 0x7B, 0x00])
            self._log("rx", addr, data, msg_type)
            return data
        with SMBus(self.i2c_bus_num) as bus:
            msg = i2c_msg.read(addr, nbytes)
            bus.i2c_rdwr(msg)
            data = bytes(msg)
            self._log("rx", addr, data, msg_type)
            return data

    # ------------- Schritt 1: Status/Distanz -------------
    def query_platform(self, addr: int, expected_len: int = 4) -> Tuple[int, Optional[float], bytes]:
        """
        Sendet STATUS_REQUEST an 'addr' und liest Antwort.
        Erwartete Dummy-Antwort: [HDR, status_bit(1B), distance_mm(2B LE)]
        Rückgabe: (status_bit, distance_mm|None, raw_bytes)
        """
        tx = frame(self.CMD_STATUS, pump_id=0)
        self._i2c_write(addr, tx, "STATUS_REQUEST")
        rx = self._i2c_read(addr, expected_len, "STATUS_RESPONSE")

        status_bit = rx[1] if len(rx) >= 2 else 0
        distance_mm = int.from_bytes(rx[2:4], "little") if len(rx) >= 4 else None

        # Status-Cache aktualisieren (kein Langzeit-Log – bewusst schlank)
        with self._connect() as conn:
            conn.execute(
                "UPDATE PlatformStatus SET status_bit=?, distance_mm=?, updated_at=CURRENT_TIMESTAMP WHERE id=1",
                (int(status_bit), float(distance_mm) if distance_mm is not None else None),
            )
        return int(status_bit), (float(distance_mm) if distance_mm is not None else None), rx

    # ------------- Schritt 2: Dosieren -------------
    def dispense(
        self,
        pump: Pump,
        target_ml: float,
        cocktail_id: int | None = None,
        ingredient_id: int | None = None,
    ) -> int:
        """
        PREPARE -> DISPENSE
        Berechnet Dauer aus Kalibrierung (flow_ml_per_s).
        Legt einen PumpRun an und gibt die run_id zurück.
        """
        if not pump.is_enabled:
            raise RuntimeError(f"Pumpe '{pump.name}' ist deaktiviert.")
        if target_ml <= 0:
            raise ValueError("target_ml muss > 0 sein.")

        duration_ms = max(1, int((float(target_ml) / float(pump.flow_ml_per_s)) * 1000))

        # Run anlegen (simple: sofort done – wenn du ACK/Timeout brauchst, erweitere hier)
        with self._connect() as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO PumpRuns (pump_id, target_ml, duration_ms, status, error_code)
                VALUES (?, ?, ?, 'done', NULL)
                """,
                (pump.pump_id, float(target_ml), int(duration_ms)),
            )
            run_id = cur.lastrowid

        # 1) PREPARE (stellt Kanal/Ventil)
        tx_prepare = frame(self.CMD_PREPARE, pump_id=pump.pump_id, param1=int(pump.channel), param2=0)
        self._i2c_write(pump.i2c_address, tx_prepare, "PREPARE")

        # 2) DISPENSE (Zeit in ms; param2 kann optional flow_hint tragen)
        tx_dispense = frame(
            self.CMD_DISPENSE,
            pump_id=pump.pump_id,
            param1=int(duration_ms),
            param2=int(pump.flow_ml_per_s),
        )
        self._i2c_write(pump.i2c_address, tx_dispense, "DISPENSE")

        # Wenn du echte Rückmeldungen/ACKs auswertest, aktualisiere hier started/finished/status
        return int(run_id)
        
            # --- Simulation/Logging toggeln (saubere API) ---
    def set_dev_mode(self, enabled: bool):
        """Schaltet Simulation (Dummy-I²C) an/aus."""
        self.dev_mode = bool(enabled)

    def set_log_i2c(self, enabled: bool):
        """Schaltet DB-Logging der I²C-Frames an/aus."""
        self.log_i2c = bool(enabled)

