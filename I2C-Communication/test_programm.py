#!/usr/bin/env python3
# ============================================================
# MixMate I2C Konsole
# ============================================================

import sys
import time
import shlex

try:
    import i2C_theLast as i2c
except ImportError as e:
    print("FEHLER: i2C_theLast.py konnte nicht importiert werden.")
    print("Lege mixmate_console.py in den gleichen Ordner.")
    print(e)
    sys.exit(1)


# ------------------------------------------------------------
# Hilfsfunktionen
# ------------------------------------------------------------

def _clip_int8(val: int) -> int:
    if val < -128:
        return -128
    if val > 127:
        return 127
    return val


# ------------------------------------------------------------
# I2C Befehle
# ------------------------------------------------------------

def send_home():
    payload = bytes([i2c.CMD_HOME])
    ack = i2c.i2c_write(payload, read_len=1)
    print(f"HOME -> ACK={list(ack)}")


def send_status():
    payload = bytes([i2c.CMD_STATUS])
    data = i2c.i2c_write(payload, read_len=5)

    if len(data) != 5:
        print("STATUS: Ungültige Antwort:", list(data))
        return

    busy = data[0]
    pos = data[1] | (data[2] << 8) | (data[3] << 16) | (data[4] << 24)
    if pos & (1 << 31):
        pos -= (1 << 32)

    print(f"STATUS -> busy={busy}, position={pos}")


def send_fahr(dist: int):
    dist = int(dist)

    if dist < -128 or dist > 127:
        print("FEHLER: dist muss -128 .. 127 sein")
        return

    payload = bytes([i2c.CMD_FAHR, dist & 0xFF])
    ack = i2c.i2c_write(payload, read_len=1)

    print(f"FAHR {dist} -> ACK={list(ack)}")


def send_beladen():
    payload = bytes([i2c.CMD_BELADEN])
    ack = i2c.i2c_write(payload, read_len=1)
    print(f"BELADEN -> ACK={list(ack)}")


def send_entladen():
    payload = bytes([i2c.CMD_ENTLADEN])
    ack = i2c.i2c_write(payload, read_len=1)
    print(f"ENTLADEN -> ACK={list(ack)}")


def send_pumpe(pump_id: int, time_s: int):
    pump_id = int(pump_id)
    time_s = int(time_s)

    if pump_id < 1 or pump_id > 6:
        print("FEHLER: pump_id muss 1..6 sein")
        return

    if time_s < 0:
        time_s = 0
    if time_s > 255:
        print("WARNUNG: Zeit >255s, auf 255 begrenzt")
        time_s = 255

    payload = bytes([
        i2c.CMD_PUMPE,
        pump_id & 0xFF,
        time_s & 0xFF
    ])

    ack = i2c.i2c_write(payload, read_len=1)
    print(f"PUMPE {pump_id} {time_s}s -> ACK={list(ack)}")


# ------------------------------------------------------------
# Hilfe
# ------------------------------------------------------------

def print_help():
    print("""
Befehle:
  home
  status

  fahr <dist>              (dist: -128 .. 127)

  beladen <dist>           -> fahr <dist> + BELADEN
  entladen <dist>          -> fahr <dist> + ENTLADEN

  pumpe <zeit_s>           -> Pumpe 1
  pumpe <id> <zeit_s>      -> Pumpe id (1..6)

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

    print("Konsole beendet.")


if __name__ == "__main__":
    main()
