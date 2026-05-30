import threading
import time


class StatusMonitor:
    def __init__(self, i2c, status_service, poll_s: float = 0.3):
        # Cache, Sperre und Polling-Intervall initialisieren.
        self.i2c = i2c
        self.status_service = status_service
        self.poll_s = poll_s

        self._lock = threading.Lock()
        # Lock schuetzt I2C-Bus und Statuscache gemeinsam.
        self._stop_event = threading.Event()
        self._thread = None

        # Startwert zeigt der UI klar, dass noch kein Polling lief.
        self._latest = {
            "ok": False,
            "severity": "ERROR",
            "error_code": "NOT_STARTED",
            "error_msg": "Statusmonitor laeuft noch nicht.",
            "busy": None,
            "band_belegt": None,
            "ist_position": None,
            "homing_ok": None,
            "raw": b"",
        }

    def start(self):
        # Status-Polling im Hintergrund starten.
        if self._thread and self._thread.is_alive():
            # Laufender Thread bleibt erhalten.
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        # Polling-Thread stoppen.
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        # Statuscache in festem Takt aktualisieren.
        while not self._stop_event.is_set():
            self.refresh()
            time.sleep(self.poll_s)

    def refresh(self) -> dict:
        # Status einmal neu lesen und Cache aktualisieren.
        with self._lock:
            # Rohdaten erst lesen, dann direkt in ein UI-taugliches Dict parsen.
            raw = self.i2c.getstatus_raw()
            self._latest = self.status_service.parse_status(raw)
            return dict(self._latest)

    def get_latest(self) -> dict:
        # Zuletzt gelesenen Status zurueckgeben.
        with self._lock:
            return dict(self._latest)

    def run_i2c(self, fn, *args, refresh_after: bool = True, **kwargs):
        # I2C-Befehl exklusiv ausfuehren.
        with self._lock:
            # Polling kann waehrend aktiver Befehle nicht dazwischenfunken.
            result = fn(*args, **kwargs)

        if refresh_after:
            # Nach Befehlen sofort einen frischen Status bereitstellen.
            self.refresh()

        return result
