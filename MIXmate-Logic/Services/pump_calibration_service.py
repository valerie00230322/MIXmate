from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor


class PumpCalibrationService:
    def __init__(self, monitor: StatusMonitor, status_service: StatusService):
        # Der Service nutzt den StatusMonitor, damit es keine I2C-Kollisionen gibt.
        # Und er nutzt den StatusService, um "busy warten" sauber zu machen.
        self.monitor = monitor
        self.status_service = status_service

    def _wait_until_idle(self, timeout_s: float, context: str):
        ok = self.status_service.wait_until_idle_cached(
            self.monitor.get_latest,
            timeout_s=timeout_s,
            poll_s=0.2
        )
        if not ok:
            status = self.monitor.get_latest()
            raise RuntimeError(f"{context}: busy blieb True oder Status ok=False. Status={status}")

    def run_pump_for_seconds(self, i2c, pump_number: int, seconds: int, timeout_extra_s: float = 10.0):
        # Erst warten bis Maschine frei ist, dann pumpen, dann wieder warten bis frei.
        if seconds <= 0:
            raise ValueError("seconds muss größer als 0 sein")

        seconds = max(1, min(255, int(seconds)))
        timeout_s = seconds + timeout_extra_s

        self._wait_until_idle(timeout_s=timeout_s, context="Vor Pumpenlauf")

        # run_i2c sorgt dafür, dass der Monitor währenddessen nicht parallel pollt
        self.monitor.run_i2c(i2c.activate_pump, pump_number, seconds)

        self._wait_until_idle(timeout_s=timeout_s, context="Nach Pumpenlauf")

        return seconds

    def calc_flow_rate_ml_s(self, measured_ml: float, seconds: int) -> float:
        # gemessene Menge / Zeit = ml pro Sekunde
        if measured_ml <= 0:
            raise ValueError("measured_ml muss größer als 0 sein")
        if seconds <= 0:
            raise ValueError("seconds muss größer als 0 sein")

        return float(measured_ml) / float(seconds)
