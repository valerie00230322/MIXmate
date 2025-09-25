from smbus2 import SMBus, i2c_msg
import struct

ARDUINO_ADDR = 0x12

def send_data(hoehe, richtung, distanz):
    # <HBB = little-endian: 16-bit A, dann 8-bit B, 8-bit C
    payload = struct.pack('<HBB', int(hoehe), int(bool(richtung)), int(distanz) & 0xFF)
    with SMBus(1) as bus:
        bus.i2c_rdwr(i2c_msg.write(ARDUINO_ADDR, payload))
    print("Gesendet:", list(payload))

send_data(140, 1, 42)
