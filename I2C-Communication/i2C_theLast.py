#!/usr/bin/env python3
import argparse
import sys

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


def i2c_write_only(payload: bytes) -> None:
    """Nur WRITE (mit STOP am Ende)."""
    with SMBus(I2C_BUS) as bus:
        bus.i2c_rdwr(i2c_msg.write(I2C_ADDR, payload))


def i2c_read_only(length: int) -> bytes:
    """Nur READ als separate Transaktion."""
    with SMBus(I2C_BUS) as bus:
        read_msg = i2c_msg.read(I2C_ADDR, length)
        bus.i2c_rdwr(read_msg)
        return bytes(read_msg)


def cmd_fahr(args):
    # Hier auf int16 umgestellt (robuster), falls du später mm sendest
    dist = int(args.dist)
    if not -32768 <= dist <= 32767:
        print("Warnung: dist muss in int16 passen (-32768..32767). Wert wird geclippt.")
        dist = max(-32768, min(32767, dist))

    low = dist & 0xFF
    high = (dist >> 8) & 0xFF

    payload = bytes([CMD_FAHR, low, high])
    i2c_write_only(payload)
    print(f"FAHR gesendet: dist={dist} (int16 LE)")


def cmd_home(_args):
    i2c_write_only(bytes([CMD_HOME]))
    print("HOME gesendet")


def cmd_status(_args):
    # 1) Status-Kommando senden (STOP)
    i2c_write_only(bytes([CMD_STATUS]))

    # 2) Dann 5 Bytes lesen (separat)
    data = i2c_read_only(5)

    if len(data) != 5:
        print(f"Unerwartete Status-Länge: {len(data)}")
        return

    # Dein Master-Format war: [busy, band, pos_low, pos_high, homed]
    busy = bool(data[0])
    band = bool(data[1])
    pos = int.from_bytes(data[2:4], "little", signed=True)
    homed = bool(data[4])

    print(f"STATUS: busy={busy}, band={band}, pos={pos}, homed={homed}")


def cmd_pumpe(args):
    pump_id = int(args.pump_id)
    zeit_s  = int(args.zeit_s)

    if not (1 <= pump_id <= 10):
        print("Fehler: pump_id muss zwischen 1 und 10 sein.")
        sys.exit(1)

    if not (0 <= zeit_s <= 255):
        print("Achtung: zeit_s wird als 1 Byte übertragen (0..255). Wert wird geclippt.")
        zeit_s = max(0, min(255, zeit_s))

    payload = bytes([CMD_PUMPE, pump_id & 0xFF, zeit_s & 0xFF])
    i2c_write_only(payload)
    print(f"PUMPE gesendet (id={pump_id}, zeit={zeit_s}s)")


def cmd_beladen(_args):
    i2c_write_only(bytes([CMD_BELADEN]))
    print("BELADEN gesendet")


def cmd_entladen(_args):
    i2c_write_only(bytes([CMD_ENTLADEN]))
    print("ENTLADEN gesendet")


def main():
    parser = argparse.ArgumentParser(description="CLI-Tool für MixMate-I2C-Slave 0x13 (STOP-sicher)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_fahr = sub.add_parser("fahr", help="PLF fahren (dist in int16, z.B. mm)")
    p_fahr.add_argument("dist", type=int, help="Distanz (int16)")
    p_fahr.set_defaults(func=cmd_fahr)

    p_home = sub.add_parser("home", help="PLF homing")
    p_home.set_defaults(func=cmd_home)

    p_status = sub.add_parser("status", help="Status abfragen (5 Bytes)")
    p_status.set_defaults(func=cmd_status)

    p_pumpe = sub.add_parser("pumpe", help="Pumpe starten/stoppen (id 1..10, zeit in s; 0=Stop)")
    p_pumpe.add_argument("pump_id", type=int, help="Pumpen-ID 1..10")
    p_pumpe.add_argument("zeit_s", type=int, help="Laufzeit in Sekunden (0..255, 0=Stop)")
    p_pumpe.set_defaults(func=cmd_pumpe)

    p_beladen = sub.add_parser("beladen", help="Band im Belademodus starten (Sensor-gesteuert)")
    p_beladen.set_defaults(func=cmd_beladen)

    p_entladen = sub.add_parser("entladen", help="Band im Entlademodus für festen Zeitraum starten")
    p_entladen.set_defaults(func=cmd_entladen)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
