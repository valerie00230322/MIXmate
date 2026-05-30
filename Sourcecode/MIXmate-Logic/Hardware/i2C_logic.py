# I2C-Kommunikation mit dem Mixer-Arduino.
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

# Kommandos
CMD_FAHR = 0
CMD_HOME = 1
CMD_STATUS = 2
CMD_PUMPE = 3
CMD_BELADEN = 4
CMD_ENTLADEN = 5
CMD_STOP = 6


class i2C_logic:
    def __init__(self):
        if _IMPORT_ERROR is not None:
            # Zielsystem braucht smbus2 fuer den echten I2C-Bus.
            raise RuntimeError(
                "smbus2 ist nicht installiert. Bitte im Zielsystem installieren: pip install smbus2"
            ) from _IMPORT_ERROR
        # Bus 1 ist der Standard-I2C-Bus am Raspberry Pi.
        self.bus = SMBus(I2C_BUS)
        print("[I2C] Hardware aktiv.")

    def i2c_write(self, payload: bytes, read_len: int = 0) -> bytes:
        # Gemeinsamer Schreibpfad fuer alle Firmware-Kommandos.
        try:
            write_msg = i2c_msg.write(I2C_ADDR, payload)

            if read_len > 0:
                # Kombinierter Write/Read fuer Befehle mit Antwortbyte.
                read_msg = i2c_msg.read(I2C_ADDR, read_len)
                self.bus.i2c_rdwr(write_msg, read_msg)
                return bytes(read_msg)

            # Reine Schreibbefehle brauchen keinen Rueckgabewert.
            self.bus.i2c_rdwr(write_msg)
            return b""
        except Exception as e:
            print(f"[I2C] Schreibfehler: {e}")
            return b""

    def move_to_position(self, position: int):
        # Zielposition muss in int16 passen.
        if not -32768 <= position <= 32767:
            print("Zielposition zu gross, wird begrenzt.")
            # Firmware verarbeitet signed int16.
            position = max(-32768, min(32767, position))

        # Position wird little-endian in Low/High-Byte gesendet.
        low = position & 0xFF
        high = (position >> 8) & 0xFF

        payload = bytes([CMD_FAHR, low, high])
        self.i2c_write(payload, read_len=1)

    def home(self):
        # Referenzfahrt des Mixer-Schlittens starten.
        self.i2c_write(bytes([CMD_HOME]), read_len=1)

    def get_current_position(self):
        # Position aus dem normalen Statuspaket lesen.
        raw = self.getstatus_raw()
        if len(raw) != 5:
            print("[I2C] Keine gueltige Statusantwort.")
            return None
        return int.from_bytes(raw[2:4], "little", signed=True)

    def activate_pump(self, pump_id: int, seconds: int):
        # Sekundenbereich auf uint8 fuer die Firmware begrenzen.
        if seconds < 0:
            # Negative Laufzeiten werden als 0 behandelt.
            seconds = 0
        if seconds > 255:
            # Firmwarefeld ist ein Byte.
            seconds = 255

        payload = bytes([CMD_PUMPE, pump_id, seconds])
        self.i2c_write(payload, read_len=1)

    def beladen(self):
        # Mixerband in Beladen-Richtung starten.
        self.i2c_write(bytes([CMD_BELADEN]), read_len=1)

    def entladen(self):
        # Mixerband in Entladen-Richtung starten.
        self.i2c_write(bytes([CMD_ENTLADEN]), read_len=1)

    def stop(self):
        # Alle laufenden Mixeraktionen stoppen.
        self.i2c_write(bytes([CMD_STOP]), read_len=1)

    def getstatus_raw(self) -> bytes:
        # Statusformat: [busy, band, pos_low, pos_high, homing_ok]
        try:
            # Firmware erwartet erst CMD_STATUS, dann den Read.
            _ = self.i2c_write(bytes([CMD_STATUS]), read_len=1)
            read_msg = i2c_msg.read(I2C_ADDR, 5)
            self.bus.i2c_rdwr(read_msg)
            return bytes(read_msg)
        except Exception as e:
            print(f"[I2C] Status lesen fehlgeschlagen: {e}")
            return b""

    def close(self):
        # I2C-Bus beim Programmende freigeben.
        try:
            self.bus.close()
        except Exception:
            pass
