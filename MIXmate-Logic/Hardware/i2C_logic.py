# Hardware/i2C_logic.py
# Kümmert sich um die I2C-Kommunikation. Simulation möglich.

import time

# Versuch smbus2 zu laden (geht unter Windows nicht)
try:
    from smbus2 import SMBus, i2c_msg
    SMBUS_AVAILABLE = True
except ImportError:
    SMBUS_AVAILABLE = False


I2C_BUS = 1
I2C_ADDR = 0x13

# Kommandos, wie der Arduino sie erwartet
CMD_FAHR     = 0
CMD_HOME     = 1
CMD_STATUS   = 2
CMD_PUMPE    = 3
CMD_BELADEN  = 4
CMD_ENTLADEN = 5


class i2C_logic:
    def __init__(self, simulation: bool = True):

        # Wenn kein smbus existiert (Windows), Simulation erzwingen
        if not SMBUS_AVAILABLE:
            simulation = True

        self.simulation = simulation

        # Simulation speichert eigenen Zustand
        self.sim_position = 0
        self.sim_busy = False
        self.sim_last_pump = None
        self.sim_beladen_active = False
        self.sim_entladen_active = False

        if not simulation:
            # echte Hardware öffnen
            try:
                self.bus = SMBus(I2C_BUS)
                print("[I2C] Hardware aktiv.")
            except Exception as e:
                print("[I2C] Hardware konnte nicht geöffnet werden. Wechsele zu Simulation.")
                print("Grund:", e)
                self.simulation = True
        else:
            print("[I2C] Simulation aktiv.")


    def i2c_write(self, payload: bytes, read_len: int = 0) -> bytes:
        if self.simulation:
            print(f"[SIM I2C] sende {list(payload)}, lese {read_len} Byte")
            return b"\x01" * read_len

        write_msg = i2c_msg.write(I2C_ADDR, payload)

        if read_len > 0:
            read_msg = i2c_msg.read(I2C_ADDR, read_len)
            self.bus.i2c_rdwr(write_msg, read_msg)
            return bytes(read_msg)

        self.bus.i2c_rdwr(write_msg)
        return b""


    def move_to_position(self, position: int):
        # Zielposition muss in int16 passen
        if not -32768 <= position <= 32767:
            print("Zielposition zu groß, wird begrenzt.")
            position = max(-32768, min(32767, position))

        if self.simulation:
            print(f"[SIM] bewege auf Position {position}")
            self.sim_busy = True

            diff = position - self.sim_position
            time.sleep(min(abs(diff) / 600.0, 1.0))

            self.sim_position = position
            self.sim_busy = False
            print(f"[SIM] neue Position: {self.sim_position}")
            return

        low = position & 0xFF
        high = (position >> 8) & 0xFF

        payload = bytes([CMD_FAHR, low, high])
        self.i2c_write(payload, read_len=1)


    def home(self):
        if self.simulation:
            print("[SIM] homing...")
            self.sim_busy = True
            time.sleep(1)
            self.sim_position = 0
            self.sim_busy = False
            print("[SIM] Homing fertig")
            return

        self.i2c_write(bytes([CMD_HOME]), read_len=1)


    def get_current_position(self):
        if self.simulation:
            print(f"[SIM] Status: busy={self.sim_busy}, pos={self.sim_position}")
            return self.sim_position

        self.i2c_write(bytes([CMD_STATUS]), read_len=1)

        read_msg = i2c_msg.read(I2C_ADDR, 5)
        self.bus.i2c_rdwr(read_msg)
        data = bytes(read_msg)

        if len(data) != 5:
            print("Statuspaket zu kurz.")
            return 0

        busy = bool(data[0])
        pos = int.from_bytes(data[1:], "little", signed=True)

        print(f"[I2C] Status: busy={busy}, pos={pos}")
        return pos


    def activate_pump(self, pump_id: int, seconds: int):
        if seconds < 0: seconds = 0
        if seconds > 255: seconds = 255

        if self.simulation:
            print(f"[SIM] Pumpe {pump_id} läuft {seconds}s")
            self.sim_last_pump = (pump_id, seconds)
            time.sleep(min(seconds, 1.0))
            print("[SIM] Pumpe fertig.")
            return

        payload = bytes([CMD_PUMPE, pump_id, seconds])
        self.i2c_write(payload, read_len=1)


    def beladen(self):
        if self.simulation:
            print("[SIM] Beladen aktiv")
            self.sim_beladen_active = True
            return

        self.i2c_write(bytes([CMD_BELADEN]), read_len=1)


    def entladen(self):
        if self.simulation:
            print("[SIM] Entladen aktiv")
            self.sim_entladen_active = True
            time.sleep(1)
            self.sim_entladen_active = False
            print("[SIM] Entladen fertig")
            return

        self.i2c_write(bytes([CMD_ENTLADEN]), read_len=1)
