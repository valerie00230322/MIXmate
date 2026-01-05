# Hardware/i2C_logic.py
#
# I2C-Kommunikation mit Arduino, optionaler Simulationsmodus.
# Simulation ist aktiv, wenn smbus2 nicht verfügbar ist oder simulation=True übergeben wurde.
#
# Statusformat (5 Byte):
# [busy, band, pos_low, pos_high, homing_ok]

import time
import threading

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
        # Wenn smbus2 nicht existiert (z.B. Windows), wird Simulation erzwungen
        if not SMBUS_AVAILABLE:
            simulation = True

        self.simulation = simulation

        # Simulationszustand
        self.sim_position = 0
        self.sim_busy = False
        self.sim_last_pump = None
        self.sim_beladen_active = False
        self.sim_entladen_active = False

        # Homing-Status in der Simulation (realistisch: initial unbekannt)
        self.sim_homing_ok = False

        # Token verhindert, dass alte Pump-Threads einen neuen Pumpvorgang vorzeitig beenden
        self._sim_pump_token = 0
        self._sim_pump_thread = None

        if not self.simulation:
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
        # Simulation: Logging und Dummy-Bytes
        if self.simulation:
            print(f"[SIM I2C] sende {list(payload)}, lese {read_len} Byte")
            return b"\x01" * read_len

        # Hardware: Schreiben und optional Lesen
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
            print("Zielposition zu groß, wird begrenzt.")
            position = max(-32768, min(32767, position))

        if self.simulation:
            # In einer echten Anlage wäre Bewegung ohne homing_ok riskant,
            # da die Position nicht zuverlässig ist
            if not self.sim_homing_ok:
                print("[SIM WARN] Bewegung ohne homing_ok (Positionsreferenz unbekannt)")

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

            # Homing setzt die Referenz; je nach Mechanik endet das oft bei Position 0
            self.sim_position = 0
            self.sim_homing_ok = True

            self.sim_busy = False
            print("[SIM] Homing fertig")
            return

        self.i2c_write(bytes([CMD_HOME]), read_len=1)

    def get_current_position(self):
        raw = self.getstatus_raw()
        if len(raw) != 5:
            print("[I2C] Keine gültige Statusantwort.")
            return None
        return int.from_bytes(raw[2:4], "little", signed=True)

    def activate_pump(self, pump_id: int, seconds: int):
        # Sekundenbereich clampen (Arduino erwartet uint8)
        if seconds < 0:
            seconds = 0
        if seconds > 255:
            seconds = 255

        if self.simulation:
            print(f"[SIM] Pumpe {pump_id} läuft {seconds}s")
            self.sim_last_pump = (pump_id, seconds)

            # busy sofort setzen, damit die Steuerlogik den Pump-Start erkennt
            self.sim_busy = True

            self._sim_pump_token += 1
            token = self._sim_pump_token

            def finish():
                # Simulation: busy bleibt lang genug aktiv, um Polling zu ermöglichen
                time.sleep(min(seconds, 1.0))
                if token == self._sim_pump_token:
                    self.sim_busy = False
                    print("[SIM] Pumpe fertig.")

            t = threading.Thread(target=finish, daemon=True)
            t.start()
            self._sim_pump_thread = t
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
            self.sim_beladen_active = False
            print("[SIM] Entladen fertig")
            return

        self.i2c_write(bytes([CMD_ENTLADEN]), read_len=1)

    def getstatus_raw(self) -> bytes:
        # Statusformat: [busy, band, pos_low, pos_high, homing_ok]
        if self.simulation:
            busy = 1 if self.sim_busy else 0
            band = 1 if self.sim_beladen_active else 0
            pos = int(self.sim_position) & 0xFFFF
            homing = 1 if self.sim_homing_ok else 0
            return bytes([busy, band, pos & 0xFF, (pos >> 8) & 0xFF, homing])

        try:
            # Manche Arduino-Implementierungen erwarten erst ein "CMD_STATUS" Write
            _ = self.i2c_write(bytes([CMD_STATUS]), read_len=1)
            read_msg = i2c_msg.read(I2C_ADDR, 5)
            self.bus.i2c_rdwr(read_msg)
            return bytes(read_msg)
        except Exception as e:
            print(f"[I2C] Status lesen fehlgeschlagen: {e}")
            return b""

    def close(self):
        if not self.simulation:
            try:
                self.bus.close()
            except Exception:
                pass
