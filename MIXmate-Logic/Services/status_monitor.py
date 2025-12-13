import threading
import time


class StatusMonitor:
    def __init__(self, i2c, status_service, poll_s: float = 0.3):
        # Referenz auf die I2C-Schicht.
        # Darüber wird der rohe Status vom Arduino gelesen.
        self.i2c = i2c

        # Der StatusService weiß, wie die rohen Bytes zu interpretieren sind.
        # (busy, Position, Fehler, usw.)
        self.status_service = status_service

        # Wie oft der Status abgefragt werden soll (in Sekunden).
        # 0.3s ist ein guter Kompromiss zwischen Reaktionszeit und Buslast.
        self.poll_s = poll_s

        # Lock, damit niemals gleichzeitig gelesen und geschrieben wird.
        # Sehr wichtig, weil I2C nicht threadsicher ist.
        self._lock = threading.Lock()

        # Event zum sauberen Stoppen des Hintergrund-Threads.
        self._stop_event = threading.Event()

        # Referenz auf den Thread selbst.
        self._thread = None

        # Hier liegt immer der zuletzt bekannte Status.
        # Wird regelmäßig überschrieben, sobald neue Daten da sind.
        self._latest = {
            "ok": False,
            "severity": "ERROR",
            "error_code": "NOT_STARTED",
            "error_msg": "Statusmonitor läuft noch nicht.",
            "busy": None,
            "band_belegt": None,
            "ist_position": None,
            "homing_ok": None,
            "raw": b""
        }

    def start(self):
        # Startet den Hintergrund-Thread, falls er noch nicht läuft.
        # Mehrfaches Starten soll keinen neuen Thread erzeugen.
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()

        # Daemon-Thread: beendet sich automatisch,
        # wenn das Hauptprogramm endet.
        self._thread = threading.Thread(
            target=self._run,
            daemon=True
        )
        self._thread.start()

    def stop(self):
        # Signalisiert dem Thread, dass er sich beenden soll.
        self._stop_event.set()

        # Kurz warten, damit der Thread sauber rauskommt.
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        # Diese Methode läuft im Hintergrund.
        # Sie fragt regelmäßig den Status ab und cached ihn.
        while not self._stop_event.is_set():
            with self._lock:
                # Rohstatus vom Arduino holen
                raw = self.i2c.getstatus_raw()

                # Rohstatus interpretieren (Bytes → sinnvolle Werte)
                self._latest = self.status_service.parse_status(raw)

            # Kleine Pause, damit wir den I2C-Bus nicht zuspammen
            time.sleep(self.poll_s)

    def get_latest(self) -> dict:
        # Gibt den zuletzt bekannten Status zurück.
        # Kein I2C-Zugriff hier, nur ein schneller Cache-Zugriff.
        with self._lock:
            return dict(self._latest)

    def run_i2c(self, fn, *args, **kwargs):
        # Führt eine I2C-Aktion exklusiv aus.
        # Währenddessen pausiert das Status-Polling automatisch,
        # weil derselbe Lock verwendet wird.
        #
        # Das verhindert Race-Conditions zwischen:
        # - Statusabfragen
        # - Fahr- oder Pumpbefehlen
        with self._lock:
            return fn(*args, **kwargs)
