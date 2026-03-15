# Hardware/i2C_logic.py
#
# I2C-Kommunikation mit Arduino.
#
# Statusformat (5 Byte):
# [busy, band, pos_low, pos_high, homing_ok]

try:
    from smbus2 import SMBus, i2c_msg
except ImportError as e:
    SMBus = None
    i2c_msg = None
    _IMPORT_ERROR = e
else:
    _IMPORT_ERROR = None

I2C_BUS = 1
I2C_ADDR = 0x13

# Kommandos, wie der Arduino sie erwartet
CMD_FAHR = 0
CMD_HOME = 1
CMD_STATUS = 2
CMD_PUMPE = 3
CMD_BELADEN = 4
CMD_ENTLADEN = 5


class i2C_logic:
    def __init__(self):
        if _IMPORT_ERROR is not None:
            raise RuntimeError(
                "smbus2 ist nicht installiert. Bitte im Zielsystem installieren: pip install smbus2"
            ) from _IMPORT_ERROR
        self.bus = SMBus(I2C_BUS)
        print("[I2C] Hardware aktiv.")

    def i2c_write(self, payload: bytes, read_len: int = 0) -> bytes:
        try:
            write_msg = i2c_msg.write(I2C_ADDR, payload)

            if read_len > 0:
                read_msg = i2c_msg.read(I2C_ADDR, read_len)
                self.bus.i2c_rdwr(write_msg, read_msg)
                return bytes(read_msg)

            self.bus.i2c_rdwr(write_msg)
            return b""
        except Exception as e:
            print(f"[I2C] Schreibfehler: {e}")
            return b""

    def move_to_position(self, position: int):
        # Zielposition muss in int16 passen
        if not -32768 <= position <= 32767:
            print("Zielposition zu gross, wird begrenzt.")
            position = max(-32768, min(32767, position))

        low = position & 0xFF
        high = (position >> 8) & 0xFF

        payload = bytes([CMD_FAHR, low, high])
        self.i2c_write(payload, read_len=1)

    def home(self):
        self.i2c_write(bytes([CMD_HOME]), read_len=1)

    def get_current_position(self):
        raw = self.getstatus_raw()
        if len(raw) != 5:
            print("[I2C] Keine gueltige Statusantwort.")
            return None
        return int.from_bytes(raw[2:4], "little", signed=True)

    def activate_pump(self, pump_id: int, seconds: int):
        # Sekundenbereich clampen (Arduino erwartet uint8)
        if seconds < 0:
            seconds = 0
        if seconds > 255:
            seconds = 255

        payload = bytes([CMD_PUMPE, pump_id, seconds])
        self.i2c_write(payload, read_len=1)

    def beladen(self):
        self.i2c_write(bytes([CMD_BELADEN]), read_len=1)

    def entladen(self):
        self.i2c_write(bytes([CMD_ENTLADEN]), read_len=1)

    def getstatus_raw(self) -> bytes:
        # Statusformat: [busy, band, pos_low, pos_high, homing_ok]
        try:
            result = self.i2c_write(bytes([CMD_STATUS]), read_len=5)
            return result if len(result) == 5 else b""
        except Exception as e:
            print(f"[I2C] Status lesen fehlgeschlagen: {e}")
            return b""

    def close(self):
        try:
            self.bus.close()
        except Exception:
            pass
