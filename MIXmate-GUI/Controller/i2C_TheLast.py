#!/usr/bin/env python3
import argparse
import sys
import time

try:
    from smbus2 import SMBus, i2c_msg
except ImportError:
    print("Fehler: smbus2 ist nicht installiert. Bitte mit 'pip install smbus2' nachinstallieren.")
    sys.exit(1)

I2C_BUS = 1       # typischerweise 1 auf dem Pi
I2C_ADDR = 0x13   # deine Slave-Adresse

CMD_FAHR     = 0
CMD_HOME     = 1
CMD_STATUS   = 2
CMD_PUMPE    = 3
CMD_BELADEN  = 4
CMD_ENTLADEN = 5

def i2c_write(payload: bytes, read_len: int = 0) -> bytes:
    """Schickt payload und liest optional read_len Bytes zurück."""
    with SMBus(I2C_BUS) as bus:
        write_msg = i2c_msg.write(I2C_ADDR, payload)
        if read_len > 0:
            read_msg = i2c_msg.read(I2C_ADDR, read_len)
            bus.i2c_rdwr(write_msg, read_msg)
            return bytes(read_msg)
        else:
            bus.i2c_rdwr(write_msg)
            return b""

    
def cmd_fahr(args):
    dist = int(args.dist)
    if not -128 <= dist <= 127:
        print("Warnung: dist wird als int8 übertragen (-128..127). Wert wird geclippt.")
        dist = max(-128, min(127, dist))

    payload = bytes([CMD_FAHR, dist & 0xFF])
    ack = i2c_write(payload, read_len=1)
    print(f"FAHR gesendet, ACK={list(ack)}")


def cmd_home(_args):
    payload = bytes([CMD_HOME])
    ack = i2c_write(payload, read_len=1)
    print(f"HOME gesendet, ACK={list(ack)}")


def cmd_status(_args):
    # Erst Status-Kommando senden
    payload = bytes([CMD_STATUS])
    _ = i2c_write(payload, read_len=1)  # hier könntest du auch nichts lesen

    # Dann Request auslösen: das macht normalerweise der Master durch einfaches Read
    # Hier lesen wir dafür direkt 5 Bytes
    with SMBus(I2C_BUS) as bus:
        read_msg = i2c_msg.read(I2C_ADDR, 5)
        bus.i2c_rdwr(read_msg)
        data = bytes(read_msg)

    if len(data) != 5:
        print(f"Unerwartete Status-Länge: {len(data)}")
        return

    busy = bool(data[0])
    pos = data[1] | (data[2] << 8) | (data[3] << 16) | (data[4] << 24)
    if pos & (1 << 31):  # Vorzeichen beachten (32-bit signed)
        pos -= (1 << 32)

    print(f"STATUS: busy={busy}, pos={pos} steps")


def cmd_pumpe(args):
    pump_id = int(args.pump_id)
    zeit_s  = int(args.zeit_s)
    if not (1 <= pump_id <= 6):
        print("Fehler: pump_id muss zwischen 1 und 6 sein.")
        sys.exit(1)
    if not (0 <= zeit_s <= 255):
        print("Achtung: zeit_s wird als 1 Byte übertragen (0..255).")
        zeit_s = max(0, min(255, zeit_s))

    payload = bytes([CMD_PUMPE, pump_id & 0xFF, zeit_s & 0xFF])
    ack = i2c_write(payload, read_len=1)
    print(f"PUMPE gesendet (id={pump_id}, zeit={zeit_s}s), ACK={list(ack)}")


def cmd_beladen(_args):
    payload = bytes([CMD_BELADEN])
    ack = i2c_write(payload, read_len=1)
    print(f"BELADEN gesendet, ACK={list(ack)}")


def cmd_entladen(_args):
    payload = bytes([CMD_ENTLADEN])
    ack = i2c_write(payload, read_len=1)
    print(f"ENTLADEN gesendet, ACK={list(ack)}")


def main():
    parser = argparse.ArgumentParser(
        description="CLI-Tool für MixMate-I2C-Slave 0x13"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # fahr
    p_fahr = sub.add_parser("fahr", help="PLF fahren (dist in Einheiten, -128..127)")
    p_fahr.add_argument("dist", type=int, help="Distanz in Einheiten (int8)")
    p_fahr.set_defaults(func=cmd_fahr)

    # home
    p_home = sub.add_parser("home", help="PLF homing")
    p_home.set_defaults(func=cmd_home)

    # status
    p_status = sub.add_parser("status", help="Status abfragen")
    p_status.set_defaults(func=cmd_status)

    # pumpe
    p_pumpe = sub.add_parser("pumpe", help="Pumpe starten (id 1..6, zeit in s)")
    p_pumpe.add_argument("pump_id", type=int, help="Pumpen-ID 1..6")
    p_pumpe.add_argument("zeit_s", type=int, help="Laufzeit in Sekunden (0..255)")
    p_pumpe.set_defaults(func=cmd_pumpe)

    # beladen
    p_beladen = sub.add_parser("beladen", help="Band im Belademodus starten (Sensor-gesteuert)")
    p_beladen.set_defaults(func=cmd_beladen)

    # entladen
    p_entladen = sub.add_parser("entladen", help="Band im Entlademodus für festen Zeitraum starten")
    p_entladen.set_defaults(func=cmd_entladen)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
