from Hardware.i2C_logic import i2C_logic
from Services.status_service import StatusService
from Services.status_monitor import StatusMonitor
import time


class MixEngine:
    HOME_TIMEOUT = 180
    MOVE_TIMEOUT = 180
    PUMP_TIMEOUT_EXTRA = 10
    HOME_POSITION_MM = 0

    BUSY_START_TIMEOUT = 3.0
    POST_HOME_STATUS_SYNC_TIMEOUT = 5.0

    POSITION_TOL_MM = 0  # falls du willst: 1..3

    def __init__(self, simulation: bool = False):
        self.i2c = i2C_logic(simulation=simulation)
        self.status_service = StatusService()
        self.monitor = StatusMonitor(self.i2c, self.status_service, poll_s=0.3)
        self.monitor.start()

    def get_status(self) -> dict:
        return self.monitor.get_latest()

    def _busy(self, status: dict) -> bool:
        return bool((status or {}).get("busy", False))

    def _homing_ok(self, status: dict) -> bool:
        return bool((status or {}).get("homing_ok", False))

    def _position_mm(self, status: dict):
        return (status or {}).get("ist_position", None)

    def _refresh_status(self) -> dict:
        raw = self.monitor.run_i2c(self.i2c.getstatus_raw)
        return self.status_service.parse_status(raw)

    def _wait_until_idle(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if not self._busy(last):
                return
            time.sleep(0.2)
        raise RuntimeError(f"{context}: Timeout. busy blieb True. Status={last}")

    def _wait_until_busy(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if self._busy(last):
                return
            time.sleep(0.05)
        raise RuntimeError(f"{context}: Timeout. busy wurde nicht True. Status={last}")

    def _wait_for_homing_ok(self, timeout_s: float, context: str):
        start = time.time()
        last = None
        while time.time() - start < timeout_s:
            last = self._refresh_status()
            if (not self._busy(last)) and self._homing_ok(last):
                return
            time.sleep(0.2)
        raise RuntimeError(f"{context}: homing_ok wurde nicht True. Status={last}")

    def _wait_until_position_reached(self, target_mm: int, timeout_s: float, context: str, tol_mm: int = 0):
        start = time.time()
        last = None
        target_mm = int(target_mm)
        tol_mm = int(tol_mm)

        while time.time() - start < timeout_s:
            last = self._refresh_status()
            pos = self._position_mm(last)

            if pos is not None:
                try:
                    pos_i = int(pos)
                except Exception:
                    pos_i = None

                if pos_i is not None and abs(pos_i - target_mm) <= tol_mm and (not self._busy(last)):
                    return

            time.sleep(0.2)

        raise RuntimeError(f"{context}: Zielposition nicht erreicht. target_mm={target_mm}, Status={last}")

    def ensure_homed(self):
        st = self._refresh_status()

        homing_ok = self._homing_ok(st)
        pos = self._position_mm(st)

        needs_home = (not homing_ok)
        if pos is not None and pos != self.HOME_POSITION_MM:
            needs_home = True

        if not needs_home:
            print("[MixEngine] Schlitten ist bereits gehomed")
            return

        print("[MixEngine] Schlitten ist nicht gehomed, starte Homing")

        self._wait_until_idle(self.HOME_TIMEOUT, "Homing vor Start")

        self.monitor.run_i2c(self.i2c.home)

        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Homing Start")
        self._wait_until_idle(self.HOME_TIMEOUT, "Homing nach Start")
        self._wait_for_homing_ok(self.POST_HOME_STATUS_SYNC_TIMEOUT, "Status-Sync nach Homing")

        print("[MixEngine] Homing abgeschlossen")

    def move_to_position(self, target_mm: int):
        if target_mm is None:
            raise ValueError("Zielposition darf nicht None sein")

        target_mm = int(target_mm)

        self._wait_until_idle(self.MOVE_TIMEOUT, "Bewegung vor Start")

        st = self._refresh_status()
        print(f"[MixEngine] Fahre Schlitten von {self._position_mm(st)} nach {target_mm}")

        self.monitor.run_i2c(self.i2c.move_to_position, target_mm)

        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Bewegung Start")

        self._wait_until_position_reached(
            target_mm=target_mm,
            timeout_s=self.MOVE_TIMEOUT,
            context="Bewegung nach Start",
            tol_mm=self.POSITION_TOL_MM
        )

        print("[MixEngine] Position erreicht")

    def _dispense(self, pump_number: int, seconds: int):
        seconds = int(seconds)
        timeout = seconds + self.PUMP_TIMEOUT_EXTRA

        self._wait_until_idle(timeout, "Pumpen vor Start")

        print(f"[MixEngine] Starte Pumpe {pump_number} für {seconds} Sekunden")
        self.monitor.run_i2c(self.i2c.activate_pump, int(pump_number), seconds)

        self._wait_until_busy(self.BUSY_START_TIMEOUT, "Pumpen Start")
        self._wait_until_idle(timeout, "Pumpen nach Start")

        print(f"[MixEngine] Pumpe {pump_number} beendet")

    def mix_cocktail(self, mix_data: list, factor: float = 1.0):
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        order_list = [(x.get("order_index"), x.get("ingredient_name")) for x in mix_data]
        print("[MixEngine] Reihenfolge:", order_list)

        self.ensure_homed()

        for item in mix_data:
            ingredient = item["ingredient_name"]
            amount_ml = float(item["amount_ml"]) * float(factor)
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_mm = item["position_steps"]  # bleibt so, ist bei euch mm

            if pump_number is None or flow_rate is None or float(flow_rate) <= 0:
                print(f"[MixEngine] {ingredient}: ungültige Pumpendaten, übersprungen")
                continue

            print(f"[MixEngine] Fahre zu {ingredient} (Pumpe {pump_number})")
            self.move_to_position(position_mm)

            dispense_time_s = amount_ml / float(flow_rate)
            seconds = max(1, min(255, int(round(dispense_time_s))))

            self._dispense(pump_number, seconds)

        print("[MixEngine] Cocktail vollständig gemixt")
        return mix_data
