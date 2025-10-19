#!/usr/bin/env python3
from smbus2 import SMBus, i2c_msg
import struct

ARDUINO_ADDR = 0x12

# Befehls-IDs
CMD_FAHREN = 0       # Payload: int32 distanz_mm
CMD_HOME   = 1       # Payload: —
CMD_STATUS = 2       # Payload: —; Antwort: int32 pos_mm, uint8 state, uint8 last_cmd
CMD_PUMPE  = 3       # Payload: uint8 pump_no (1-5), uint16 zeit_s

# Erwartete Antwortlänge für Status
STATUS_REPLY_LEN = 6  # 4 (pos_mm) + 1 (state) + 1 (last_cmd)

def i2c_write(payload: bytes):
    with SMBus(1) as bus:
        bus.i2c_rdwr(i2c_msg.write(ARDUINO_ADDR, payload))

def i2c_write_then_read(w_payload: bytes, r_len: int) -> bytes:
    with SMBus(1) as bus:
        w = i2c_msg.write(ARDUINO_ADDR, w_payload)
        r = i2c_msg.read(ARDUINO_ADDR, r_len)
        bus.i2c_rdwr(w, r)
        return bytes(r)

# ---------------- Befehle ----------------

def cmd_fahren(distanz_mm: int):
    # distanz_mm als signed int32, damit +/- möglich ist
    dist = int(distanz_mm)
    payload = struct.pack('<Bi', CMD_FAHREN, dist)
    i2c_write(payload)
    print(f"[SEND] Fahren: distanz_mm={dist} -> {list(payload)}")

def cmd_home():
    payload = struct.pack('<B', CMD_HOME)
    i2c_write(payload)
    print(f"[SEND] Home -> {list(payload)}")

def cmd_status():
    payload = struct.pack('<B', CMD_STATUS)
    data = i2c_write_then_read(payload, STATUS_REPLY_LEN)
    if len(data) != STATUS_REPLY_LEN:
        raise RuntimeError(f"Status-Länge unerwartet: {len(data)} Bytes")
    pos_mm, state, last_cmd = struct.unpack('<iBB', data)
    info = {
        'pos_mm': pos_mm,
        'state': state,        # state vom Arduino definieren (z.B. 0=idle,1=busy,2=error,…)
        'last_cmd': last_cmd   # Echo der letzten CMD-ID
    }
    print(f"[SEND] Status -> {list(payload)}")
    print(f"[RECV] {list(data)}  parsed={info}")
    return info

def cmd_pumpe(pump_no: int, zeit_s: int):
    p = int(pump_no)
    t = int(zeit_s)
    if not (1 <= p <= 5):
        raise ValueError("Pumpennummer muss 1..5 sein.")
    if not (0 <= t <= 65535):
        raise ValueError("Zeit in Sekunden muss 0..65535 sein.")
    payload = struct.pack('<BBH', CMD_PUMPE, p & 0xFF, t & 0xFFFF)
    i2c_write(payload)
    print(f"[SEND] Pumpe: nr={p}, zeit_s={t} -> {list(payload)}")

# --------------- CLI / Prompt ---------------

def prompt_loop():
    print("I2C zu Arduino @ 0x%02X" % ARDUINO_ADDR)
    print("Befehle:")
    print("  0: Fahren (mm)        -> sendet int32 Distanz in mm")
    print("  1: Home               -> ohne Parameter")
    print("  2: Statusabfrage      -> liest pos_mm,int state,last_cmd")
    print("  3: Pumpe (nr,sek)     -> nr=1..5, sek=0..65535")
    print("Beenden: q\n")

    while True:
        try:
            s = input("CMD (0/1/2/3): ").strip().lower()
            if s == 'q':
                break
            if s == '':
                continue

            cmd = int(s)
            if cmd == CMD_FAHREN:
                dist = int(input("Distanz in mm (int, +/- erlaubt): ").strip())
                cmd_fahren(dist)

            elif cmd == CMD_HOME:
                cmd_home()

            elif cmd == CMD_STATUS:
                info = cmd_status()
                print(f"Status: pos={info['pos_mm']} mm, state={info['state']}, last_cmd={info['last_cmd']}")

            elif cmd == CMD_PUMPE:
                p = int(input("Pumpennummer (1-5): ").strip())
                t = int(input("Zeit in Sekunden (0-65535): ").strip())
                cmd_pumpe(p, t)

            else:
                print("Unbekannter CMD. Erlaubt: 0,1,2,3.")

        except ValueError as e:
            print(f"Ungültige Eingabe: {e}")
        except KeyboardInterrupt:
            print("\nAbbruch.")
            break
        except Exception as e:
            print(f"Fehler: {e}")

if __name__ == "__main__":
    prompt_loop()
