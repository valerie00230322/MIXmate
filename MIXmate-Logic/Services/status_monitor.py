import threading
import time


class StatusMonitor:
    def __init__(self, i2c, status_service, poll_s: float = 0.3):
        self.i2c = i2c
        self.status_service = status_service
        self.poll_s = poll_s

        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread = None

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
        if self._thread and self._thread.is_alive():
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _run(self):
        while not self._stop_event.is_set():
            self.refresh()  # liest echten Status und aktualisiert Cache
            time.sleep(self.poll_s)
# LIest status einmal direkt vom Arduino und aktualisiert den Cache
    def refresh(self) -> dict:
        
        with self._lock:
            raw = self.i2c.getstatus_raw()
            self._latest = self.status_service.parse_status(raw)
            return dict(self._latest)

    def get_latest(self) -> dict:
        with self._lock:
            return dict(self._latest)
# Führt eine I2C-Aktion aus.
    def run_i2c(self, fn, *args, refresh_after: bool = True, **kwargs):
        
        with self._lock:
            result = fn(*args, **kwargs)

        if refresh_after:
            self.refresh()

        return result
