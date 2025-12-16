import time


class StatusService:
    
   # Verarbeitet den Status vom I2C-Slave (Arduino).

    # Statusformat (5 Bytes):
    # Byte 0: busy
    # Byte 1: band_belegt
    # Byte 2: ist_position (LSB)
    # Byte 3: ist_position (MSB)
    # Byte 4: homing_ok
    

    def parse_status(self, raw: bytes) -> dict:
        # Grundstruktur des Statusobjekts
        status = {
            "ok": False,
            "severity": "ERROR",
            "error_code": None,
            "error_msg": None,
            "busy": None,
            "band_belegt": None,
            "ist_position": None,
            "homing_ok": None,
            "raw": raw
        }

        # Keine Antwort vom I2C-Slave
        if not raw:
            status["error_code"] = "I2C_NO_RESPONSE"
            status["error_msg"] = "Keine Antwort vom I2C-Slave."
            return status

        # Falsche Paketlänge = Protokollfehler
        if len(raw) != 5:
            status["error_code"] = "I2C_BAD_LENGTH"
            status["error_msg"] = f"Statuspaket hat Länge {len(raw)} statt 5."
            return status

        # Bytes in sinnvolle Werte umwandeln
        status["busy"] = bool(raw[0] & 0x01)
        status["band_belegt"] = bool(raw[1] & 0x01)
        status["ist_position"] = int.from_bytes(raw[2:4], "little", signed=True)
        status["homing_ok"] = bool(raw[4] & 0x01)

        # Ohne Homing darf nichts passieren
        if not status["homing_ok"]:
            status["error_code"] = "NOT_HOMED"
            status["error_msg"] = "Schlitten ist nicht gehomed."
            return status

        # Glas fehlt, aber Maschine ist nicht beschäftigt → Warnung
        if not status["band_belegt"] and not status["busy"]:
            status["severity"] = "LOW"
            status["error_msg"] = "Kein Glas auf dem Förderband."
            status["ok"] = True
            return status

        # Alles passt
        status["ok"] = True
        status["severity"] = "OK"
        return status

    def is_ready_to_mix(self, status: dict) -> bool:
        # Prüft, ob ein neuer Mix gestartet werden darf
        return (
            status.get("ok") and
            not status.get("busy") and
            status.get("homing_ok")
        )

    def wait_until_idle(self, i2c, timeout_s: float = 10.0, poll_s: float = 0.2) -> bool:
        # Wartet, bis der Mixer nicht mehr busy ist oder ein Timeout erreicht wird
        start = time.time()

        while time.time() - start < timeout_s:
            raw = i2c.getstatus_raw()
            status = self.parse_status(raw)

            # Bei Fehler sofort abbrechen
            if not status["ok"]:
                return False

            # Maschine ist frei
            if not status["busy"]:
                return True

            time.sleep(poll_s)

        # Timeout erreicht
        return False


    def wait_until_idle_cached(self, get_status_fn, timeout_s: float = 10.0, poll_s: float = 0.2) -> bool:
        start = time.time()

        while time.time() - start < timeout_s:
            status = get_status_fn()

            if not status.get("ok"):
                return False

            if not status.get("busy"):
                return True

            time.sleep(poll_s)

        return False
