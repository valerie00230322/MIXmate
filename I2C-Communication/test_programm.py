#!/usr/bin/env python3
# ============================================================
# MixMate I2C Konsole (angepasst auf dein "I2C Programm")
# - smbus2
# - STOP-sichere Transaktionen (WRITE-only, READ-only separat)
# - FAHR: int16 little-endian (CMD, low, high)
# - STATUS: 5 Bytes: [busy, band, pos_low, pos_high, homed]
# ============================================================

import sys
import time
import shlex

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("Fehler: smbus2 ist nicht installiert. Bitte mit 'pip install smbus2' nachinstallieren.")
    sys.exit(1)

I2C_BUS = 1
I2C_ADDR = 0x13

CMD_FAHR     = 0
CMD_HOME     = 1
CMD_STATUS   = 2
CMD_PUMPE    = 3
CMD_BELADEN  = 4
CMD_ENTLADEN = 5


# ------------------------------------------------------------
# I2C Low-Level (wie in deinem I2C Programm)
# ------------------------------------------------------------

class MixMateI2C:
    def __init__(self, bus_no: int = I2C_BUS, addr: int = I2C_ADDR):
        self.bus_no = bus_no
        self.addr = addr
        self.bus = None

    def open(self):
        if self.bus is None:
            self.bus = SMBus(self.bus_no)

    def close(self):
        if self.bus is not None:
            try:
                self.bus.close()
            finally:
                self.bus = None

    def write_only(self, payload: bytes) -> None:
        """Nur WRITE (mit STOP am Ende)."""
        self.open()
        self.bus.i2c_rdwr(i2c_msg.write(self.addr, payload))

    def read_only(self, length: int) -> bytes:
        """Nur READ als separate Transaktion."""
        self.open()
        msg = i2c_msg.read(self.addr, length)
        self.bus.i2c_rdwr(msg)
        return bytes(msg)


i2c = MixMateI2C()


# ------------------------------------------------------------
# I2C Befehle (angepasst)
# ------------------------------------------------------------

def send_home():
    i2c.write_only(bytes([CMD_HOME]))
    print("HOME gesendet")


def send_status():
    # 1) Status-Kommando senden (STOP)
    i2c.write_only(bytes([CMD_STATUS]))

    # 2) Dann 5 Bytes lesen (separat)
    data = i2c.read_only(5)

    if len(data) != 5:
        print("STATUS: Ungültige Antwort:", list(data))
        return

    busy = bool(data[0])
    band = bool(data[1])
    pos = int.from_bytes(data[2:4], "little", signed=True)
    homed = bool(data[4])

    print(f"STATUS -> busy={busy}, band={band}, position={pos}, homed={homed}")


def send_fahr(dist: int):
    dist = int(dist)

    # int16, wie in deinem I2C Programm
    if not -32768 <= dist <= 32767:
        print("WARNUNG: dist muss in int16 passen (-32768..32767). Wert wird geclippt.")
        dist = max(-32768, min(32767, dist))

    low = dist & 0xFF
    high = (dist >> 8) & 0xFF

    payload = bytes([CMD_FAHR, low, high])
    i2c.write_only(payload)
    print(f"FAHR gesendet: dist={dist} (int16 LE)")


def send_beladen():
    i2c.write_only(bytes([CMD_BELADEN]))
    print("BELADEN gesendet")


def send_entladen():
    i2c.write_only(bytes([CMD_ENTLADEN]))
    print("ENTLADEN gesendet")


def send_pumpe(pump_id: int, time_s: int):
    pump_id = int(pump_id)
    time_s = int(time_s)

    if not (1 <= pump_id <= 10):
        print("FEHLER: pump_id muss 1..10 sein")
        return

    if time_s < 0:
        time_s = 0
    if time_s > 255:
        print("WARNUNG: Zeit >255s, auf 255 begrenzt")
        time_s = 255

    payload = bytes([CMD_PUMPE, pump_id & 0xFF, time_s & 0xFF])
    i2c.write_only(payload)
    print(f"PUMPE gesendet (id={pump_id}, zeit={time_s}s)")


# ------------------------------------------------------------
# Hilfe
# ------------------------------------------------------------

def print_help():
    print("""
Befehle:
  home
  status

  fahr <dist>              (dist: int16 -32768 .. 32767)

  beladen <dist>           -> fahr <dist> + BELADEN
  entladen <dist>          -> fahr <dist> + ENTLADEN

  pumpe <zeit_s>           -> Pumpe 1
  pumpe <id> <zeit_s>      -> Pumpe id (1..10)

  help
  exit | quit
""")


# ------------------------------------------------------------
# Main Loop
# ------------------------------------------------------------

def main():
    print("MixMate I2C Konsole gestartet (help für Befehle)")

    while True:
        try:
            line = input("mixmate> ").strip()
        except (KeyboardInterrupt, EOFError):
            print()
            break

        if not line:
            continue

        try:
            parts = shlex.split(line)
        except ValueError as e:
            print("Parse-Fehler:", e)
            continue

        cmd = parts[0].lower()
        args = parts[1:]

        try:
            if cmd in ("exit", "quit"):
                break

            elif cmd == "help":
                print_help()

            elif cmd == "home":
                send_home()

            elif cmd == "status":
                send_status()

            elif cmd == "fahr":
                if len(args) != 1:
                    print("Nutzung: fahr <dist>")
                else:
                    send_fahr(args[0])

            elif cmd == "beladen":
                if len(args) != 1:
                    print("Nutzung: beladen <dist>")
                else:
                    send_fahr(args[0])
                    time.sleep(0.05)
                    send_beladen()

            elif cmd == "entladen":
                if len(args) != 1:
                    print("Nutzung: entladen <dist>")
                else:
                    send_fahr(args[0])
                    time.sleep(0.05)
                    send_entladen()

            elif cmd == "pumpe":
                if len(args) == 1:
                    send_pumpe(1, args[0])
                elif len(args) == 2:
                    send_pumpe(args[0], args[1])
                else:
                    print("Nutzung: pumpe <zeit_s> ODER pumpe <id> <zeit_s>")

            else:
                print(f"Unbekannter Befehl: {cmd}")

        except OSError as e:
            print("I2C Fehler:", e)
        except Exception as e:
            print("Fehler:", e)

    i2c.close()
    print("Konsole beendet.")


if __name__ == "__main__":
    main()
