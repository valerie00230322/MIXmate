#!/usr/bin/env python3
from smbus2 import SMBus, i2c_msg
import struct

ARDUINO_ADDR = 0x12

# CMD-IDs müssen zu deinem Arduino-Code passen
CMD_FAHREN = 0
CMD_HOME = 1
CMD_STATUS = 2

def send_packet(cmd, hoehe, richtung, distanz):
    # Begrenzen/normalisieren
    cmd = int(cmd) & 0xFF                  # 0..255, Arduino nutzt 0,1,2
    hoehe = int(hoehe) & 0xFFFF            # 16 Bit
    richtung = 1 if int(bool(richtung)) else 0
    distanz = int(distanz) & 0xFF          # 0..255

    # Reihenfolge: CMD, Höhe(LSB,MSB), Richtung, Distanz
    payload = struct.pack('<BHBB', cmd, hoehe, richtung, distanz)

    with SMBus(1) as bus:
        bus.i2c_rdwr(i2c_msg.write(ARDUINO_ADDR, payload))

    print(f"Gesendet Bytes: {list(payload)}  "
          f"(CMD={cmd}, Hoehe={hoehe}, Richtung={richtung}, Distanz={distanz})")

def prompt_loop():
    print("Eingaben für I2C an Arduino (5 Bytes: CMD, H_LSB, H_MSB, R, D)")
    print("CMD: 0=Fahren, 1=Home, 2=Status | Abbruch: q")
    last = {
        'cmd': CMD_FAHREN,
        'hoehe': 0,
        'richtung': 0,
        'distanz': 0
    }

    while True:
        try:
            s = input(f"CMD (0=Fahren,1=Home,2=Status) [{last['cmd']}]: ").strip()
            if s.lower() == 'q': break
            cmd = last['cmd'] if s == '' else int(s)

            h = input(f"Höhe (0-65535) [{last['hoehe']}]: ").strip()
            if h.lower() == 'q': break
            hoehe = last['hoehe'] if h == '' else int(h)

            r = input(f"Richtung (0/1) [{last['richtung']}]: ").strip()
            if r.lower() == 'q': break
            richtung = last['richtung'] if r == '' else int(r)

            d = input(f"Distanz (0-255) [{last['distanz']}]: ").strip()
            if d.lower() == 'q': break
            distanz = last['distanz'] if d == '' else int(d)

            # Werte begrenzen
            if cmd not in (CMD_FAHREN, CMD_HOME, CMD_STATUS):
                print("Hinweis: CMD unüblich; erlaubt sind 0,1,2. Sende trotzdem.")
            hoehe = max(0, min(65535, hoehe))
            richtung = 1 if richtung else 0
            distanz = max(0, min(255, distanz))

            send_packet(cmd, hoehe, richtung, distanz)

            last.update({'cmd': cmd, 'hoehe': hoehe, 'richtung': richtung, 'distanz': distanz})

        except ValueError:
            print("Ungültige Eingabe. Bitte Zahlen verwenden oder 'q' zum Beenden.")
        except KeyboardInterrupt:
            print("\nAbbruch.")
            break

if __name__ == "__main__":
    prompt_loop()