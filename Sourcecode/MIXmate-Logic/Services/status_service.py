import time


class StatusService:
    
   # Statuspakete vom Mixer-Arduino auswerten.

    # Statusformat (5 Bytes):
    # Byte 0: busy
    # Byte 1: band_belegt
    # Byte 2: ist_position (LSB)
    # Byte 3: ist_position (MSB)
    # Byte 4: homing_ok
    

    def parse_status(self, raw: bytes) -> dict:
        # Grundstruktur des Statusobjekts.
        status = {
            # ok beschreibt die technische Lesbarkeit des Status.
            "ok": False,
            # severity steuert die UI-Einstufung.
            "severity": "ERROR",
            # error_code ist fuer Programmlogik und Diagnose gedacht.
            "error_code": None,
            # error_msg ist der lesbare Text fuer UI und Logs.
            "error_msg": None,
            # busy zeigt laufende Motor- oder Pumpenaktion.
            "busy": None,
            # band_belegt kommt vom Glas-Sensor am Mixer.
            "band_belegt": None,
            # ist_position ist die aktuelle Schlittenposition in mm.
            "ist_position": None,
            # homing_ok zeigt eine gueltige Referenzfahrt.
            "homing_ok": None,
            # raw bleibt fuer Diagnose erhalten.
            "raw": raw
        }

        # Leere Antwort bedeutet Kommunikationsfehler.
        if not raw:
            status["error_code"] = "I2C_NO_RESPONSE"
            status["error_msg"] = "Keine Antwort vom I2C-Slave."
            return status

        # Falsche Paketlaenge bedeutet Protokollfehler.
        if len(raw) != 5:
            status["error_code"] = "I2C_BAD_LENGTH"
            status["error_msg"] = f"Statuspaket hat Länge {len(raw)} statt 5."
            return status

        # Rohbytes in Werte umwandeln.
        status["busy"] = bool(raw[0] & 0x01)
        status["band_belegt"] = bool(raw[1] & 0x01)
        # Position besteht aus Low- und High-Byte im Little-Endian-Format.
        status["ist_position"] = int.from_bytes(raw[2:4], "little", signed=True)
        status["homing_ok"] = bool(raw[4] & 0x01)

        # Statuspaket ist gueltig; fehlendes Homing ist ein Betriebszustand,
        # kein Kommunikationsfehler.
        status["ok"] = True

        # Ohne Homing darf nicht gemixt werden, aber der Status bleibt gueltig.
        if not status["homing_ok"]:
            status["error_code"] = "NOT_HOMED"
            status["error_msg"] = "Schlitten ist nicht gehomed."
            status["severity"] = "WARN"
            return status

        # Fehlendes Glas ist eine Warnung, kein Kommunikationsfehler.
        if not status["band_belegt"] and not status["busy"]:
            status["severity"] = "LOW"
            status["error_msg"] = "Kein Glas auf dem Förderband."
            status["ok"] = True
            return status

        # Gueltiger Status ohne Warnung.
        status["severity"] = "OK"
        return status

    def is_ready_to_mix(self, status: dict) -> bool:
        # Startfreigabe fuer einen neuen Mix pruefen.
        return (
            status.get("ok") and
            not status.get("busy") and
            status.get("homing_ok")
        )

    def wait_until_idle(self, i2c, timeout_s: float = 10.0, poll_s: float = 0.2) -> bool:
        # Warten, bis der Mixer frei ist oder das Timeout greift.
        start = time.time()

        while time.time() - start < timeout_s:
            raw = i2c.getstatus_raw()
            status = self.parse_status(raw)

            # Bei ungueltiger Kommunikation weiter pollen bis Timeout.
            if not status["ok"]:
                time.sleep(poll_s)
                continue

            # Maschine ist frei.
            if not status["busy"]:
                return True

            time.sleep(poll_s)

        # Timeout erreicht.
        return False


    def wait_until_idle_cached(self, get_status_fn, timeout_s: float = 10.0, poll_s: float = 0.2) -> bool:
        # Variante fuer bereits gepollte Statuswerte aus dem Monitor.
        start = time.time()

        while time.time() - start < timeout_s:
            status = get_status_fn()

            # Initiale/temporare Statusfehler tolerieren, bis ein gueltiger Status da ist.
            if not status.get("ok"):
                time.sleep(poll_s)
                continue

            if not status.get("busy"):
                # Cache meldet freien Mixer.
                return True

            time.sleep(poll_s)

        return False
