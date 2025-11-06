# Controller/i2c_driver.py
from __future__ import annotations
from dataclasses import dataclass
import struct
import time

try:
    from smbus2 import SMBus, i2c_msg
except Exception:
    SMBus = None
    i2c_msg = None


@dataclass
class I2CConfig:
    bus: int = 1
    addr: int = 0x13     # <- deine Arduino-Adresse
    timeout_s: float = 2.0


class I2CDriver:
    """
    Dünne HW-Schicht für dein Arduino-Protokoll (wie im Dummy).
    dev_mode=True: simuliert Antworten ohne echte Hardware.
    """

    CMD_FAHREN   = 0
    CMD_HOME     = 1
    CMD_STATUS   = 2
    CMD_PUMPE    = 3
    CMD_BELADEN  = 4
    CMD_ENTLADEN = 5

    STATUS_REPLY_LEN = 6  # 4 (pos_mm) + 1 (state) + 1 (last_cmd)

    def __init__(self, cfg: I2CConfig = I2CConfig(), *, dev_mode: bool = False, log_i2c: bool = False):
        self.cfg = cfg
        self.dev_mode = dev_mode
        self.log_i2c = log_i2c
        self._sim_state = {"pos_mm": 0, "state": 0, "last_cmd": 255}

        if not self.dev_mode and SMBus is None:
            raise RuntimeError("smbus2 nicht verfügbar – entweder installieren oder dev_mode=True nutzen")

    # ---------- toggles ----------
    def set_dev_mode(self, enabled: bool): self.dev_mode = enabled
    def set_log(self, enabled: bool): self.log_i2c = enabled

    # ---------- low level ----------
    def _write(self, payload: bytes):
        if self.dev_mode:
            if self.log_i2c: print(f"[I2C SIM WRITE] {list(payload)}")
            return
        with SMBus(self.cfg.bus) as bus:
            bus.i2c_rdwr(i2c_msg.write(self.cfg.addr, payload))

    def _write_read(self, w_payload: bytes, r_len: int) -> bytes:
        if self.dev_mode:
            if self.log_i2c: print(f"[I2C SIM WR] {list(w_payload)}  -> RD {r_len}")
            if w_payload[:1] == bytes([self.CMD_STATUS]):
                return struct.pack("<iBB", self._sim_state["pos_mm"], self._sim_state["state"], self._sim_state["last_cmd"])
            return bytes([0] * r_len)
        with SMBus(self.cfg.bus) as bus:
            w = i2c_msg.write(self.cfg.addr, w_payload)
            r = i2c_msg.read(self.cfg.addr, r_len)
            bus.i2c_rdwr(w, r)
            return bytes(r)

    # ---------- high level (wie dein Dummy) ----------
    def fahren(self, distanz_mm: int):
        payload = struct.pack("<Bi", self.CMD_FAHREN, int(distanz_mm))
        self._write(payload)
        if self.dev_mode:
            self._sim_state["pos_mm"] += int(distanz_mm)
            self._sim_state["state"] = 1
            self._sim_state["last_cmd"] = self.CMD_FAHREN
            time.sleep(0.2)
            self._sim_state["state"] = 0
        if self.log_i2c: print(f"[SEND] Fahren {distanz_mm}mm")

    def home(self):
        payload = struct.pack("<B", self.CMD_HOME)
        self._write(payload)
        if self.dev_mode:
            self._sim_state["pos_mm"] = 0
            self._sim_state["last_cmd"] = self.CMD_HOME
        if self.log_i2c: print("[SEND] Home")

    def beladen(self):
        payload = struct.pack("<B", self.CMD_BELADEN)
        self._write(payload)
        if self.dev_mode: self._sim_state["last_cmd"] = self.CMD_BELADEN
        if self.log_i2c: print("[SEND] Beladen")

    def entladen(self):
        payload = struct.pack("<B", self.CMD_ENTLADEN)
        self._write(payload)
        if self.dev_mode: self._sim_state["last_cmd"] = self.CMD_ENTLADEN
        if self.log_i2c: print("[SEND] Entladen")

    def status(self) -> dict:
        payload = struct.pack("<B", self.CMD_STATUS)
        data = self._write_read(payload, self.STATUS_REPLY_LEN)
        if len(data) != self.STATUS_REPLY_LEN:
            raise RuntimeError(f"Status-Länge unerwartet: {len(data)}")
        pos_mm, state, last_cmd = struct.unpack("<iBB", data)
        info = {"pos_mm": pos_mm, "state": state, "last_cmd": last_cmd}
        if self.log_i2c: print(f"[SEND] Status -> {info}")
        return info

    def pumpe(self, pump_no: int, zeit_s: int):
        if not (1 <= pump_no <= 5): raise ValueError("Pumpennummer 1..5")
        if not (0 <= zeit_s <= 65535): raise ValueError("Zeit 0..65535")
        payload = struct.pack("<BBH", self.CMD_PUMPE, pump_no & 0xFF, zeit_s & 0xFFFF)
        self._write(payload)
        if self.dev_mode: self._sim_state["last_cmd"] = self.CMD_PUMPE
        if self.log_i2c: print(f"[SEND] Pumpe nr={pump_no} zeit={zeit_s}s")
