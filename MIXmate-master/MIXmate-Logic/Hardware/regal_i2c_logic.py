"""
Separate I2C communication module for the Regal controller (Regal.ino).

Protocol source:
- I2C address: 0x12
- Commands:
  CMD_LIFT     = 0
  CMD_HOME     = 1
  CMD_STATUS   = 2
  CMD_EBENE    = 3 (payload byte encodes level + optional direction)
  CMD_BELADEN  = 4
  CMD_ENTLADEN = 5
  CMD_AUSSCHUB = 6
  CMD_AUSSCHUB_HOME = 7
- Status format (5 bytes):
  [busy, sensor_flags, pos_low, pos_high, homing_ok]
  sensor_flags bitfield:
    bit0: lift sensor occupied
    bit1: waiting sensor start occupied
    bit2: waiting sensor end occupied
    bit3: level1 front occupied
    bit4: level2 front occupied
    bit5: reserved
    bit6: entladen blocked
"""

try:
    from smbus2 import SMBus, i2c_msg
except ImportError as e:
    SMBus = None
    i2c_msg = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None


I2C_BUS = 1
I2C_ADDR_REGAL = 0x12

CMD_LIFT = 0
CMD_HOME = 1
CMD_STATUS = 2
CMD_EBENE = 3
CMD_BELADEN = 4
CMD_ENTLADEN = 5
CMD_AUSSCHUB = 6
CMD_AUSSCHUB_HOME = 7


class RegalI2CLogic:
    def __init__(self, bus_number: int = I2C_BUS):
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "smbus2 ist nicht installiert. Bitte im Zielsystem installieren: pip install smbus2"
            ) from _IMPORT_ERROR
        self.bus = SMBus(bus_number)

    def _i2c_write(self, payload: bytes, read_len: int = 0) -> bytes:
        try:
            write_msg = i2c_msg.write(I2C_ADDR_REGAL, payload)
            if read_len > 0:
                read_msg = i2c_msg.read(I2C_ADDR_REGAL, read_len)
                self.bus.i2c_rdwr(write_msg, read_msg)
                return bytes(read_msg)
            self.bus.i2c_rdwr(write_msg)
            return b""
        except Exception as e:
            print(f"[Regal-I2C] Schreibfehler: {e}")
            return b""

    def lift_to_mm(self, mm: int):
        # Regal.ino expects int16 payload for CMD_LIFT.
        if mm < -32768:
            mm = -32768
        if mm > 32767:
            mm = 32767

        low = mm & 0xFF
        high = (mm >> 8) & 0xFF
        payload = bytes([CMD_LIFT, low, high])
        self._i2c_write(payload, read_len=1)

    def home(self):
        self._i2c_write(bytes([CMD_HOME]), read_len=1)

    def select_level(self, level_id: int, forward: bool = True):
        if level_id < 0:
            level_id = 0
        if level_id > 255:
            level_id = 255
        # New encoding:
        # bit6: direction flag is present
        # bit7: direction value (1=forward, 0=reverse)
        # bits0..5: level id
        encoded = (int(level_id) & 0x3F) | 0x40 | (0x80 if bool(forward) else 0x00)
        self._i2c_write(bytes([CMD_EBENE, encoded]), read_len=1)

    def beladen(self):
        self._i2c_write(bytes([CMD_BELADEN]), read_len=1)

    def entladen(self):
        self._i2c_write(bytes([CMD_ENTLADEN]), read_len=1)

    def ausschub_to_mm(self, mm: int):
        if mm < -32768:
            mm = -32768
        if mm > 32767:
            mm = 32767

        low = mm & 0xFF
        high = (mm >> 8) & 0xFF
        payload = bytes([CMD_AUSSCHUB, low, high])
        self._i2c_write(payload, read_len=1)

    def home_ausschub(self):
        self._i2c_write(bytes([CMD_AUSSCHUB_HOME]), read_len=1)

    def get_status_raw(self) -> bytes:
        # Regal.ino returns 5-byte status only after CMD_STATUS.
        try:
            _ = self._i2c_write(bytes([CMD_STATUS]), read_len=1)
            read_msg = i2c_msg.read(I2C_ADDR_REGAL, 5)
            self.bus.i2c_rdwr(read_msg)
            return bytes(read_msg)
        except Exception as e:
            print(f"[Regal-I2C] Status lesen fehlgeschlagen: {e}")
            return b""

    def get_status(self) -> dict:
        raw = self.get_status_raw()
        if len(raw) != 5:
            return {
                "ok": False,
                "error_code": "I2C_BAD_LENGTH",
                "error_msg": f"Statuslaenge ungueltig: {len(raw)}",
            }

        flags = raw[1]
        pos_mm = int.from_bytes(raw[2:4], "little", signed=True)
        return {
            "ok": True,
            "busy": bool(raw[0]),
            # Backward-compatible name:
            "band_belegt": bool(flags & (1 << 0)),
            "lift_sensor_belegt": bool(flags & (1 << 0)),
            "wait_start_belegt": bool(flags & (1 << 1)),
            "wait_end_belegt": bool(flags & (1 << 2)),
            "level1_front_belegt": bool(flags & (1 << 3)),
            "level2_front_belegt": bool(flags & (1 << 4)),
            # reserved in current Regal firmware (Mixer sensor is on mixer controller)
            "mixer_belegt": bool(flags & (1 << 5)),
            "entladen_blocked": bool(flags & (1 << 6)),
            "ist_position": pos_mm,
            "homing_ok": bool(raw[4]),
            "raw": list(raw),
        }

    def close(self):
        try:
            self.bus.close()
        except Exception:
            pass
