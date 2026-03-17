import os
from Controller.admin_controller import AdminController
from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
from Model.mix_model import MixModel
from Model.pump_model import PumpModel
from Model.system_settings_model import SystemSettingsModel
from Services.simulation_trace_service import get_simulation_trace_service
from View.qt.run_qt import run_qt
#Test

class NoHardwareMixController:
    def __init__(self, db_path: str, init_error: Exception | None = None):
        # Fallback-Controller: gleiche API wie MixController, aber ohne echte I2C-Hardware.
        self._init_error = init_error
        self.db_path = db_path
        self.model = MixModel(db_path=db_path)
        self.sim_trace = get_simulation_trace_service()
        self._sim_position_mm = 0
        self._sim_homed = False

    def _simulation_enabled(self) -> bool:
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            return bool(settings.get_simulation_mode())
        finally:
            settings.close()

    def _assert_simulation_enabled(self):
        # Im Fallback darf nur gearbeitet werden, wenn Simulation explizit aktiv ist.
        if not self._simulation_enabled():
            raise RuntimeError("Hardware nicht verfuegbar (I2C). Bitte Simulation im Admin aktivieren.")

    def _sim_log_mixer(self, payload: list[int], note: str = ""):
        self.sim_trace.log_i2c(0x13, payload, note=note)

    def _sim_log_regal(self, payload: list[int], note: str = ""):
        self.sim_trace.log_i2c(0x12, payload, note=note)

    def mix_cocktail(self, cocktail_id: int, factor: float = 1.0):
        mix_data = self.prepare_mix(cocktail_id)
        return self.run_mix(mix_data, factor=factor)

    def get_status(self):
        if self._simulation_enabled():
            return {
                "ok": True,
                "severity": "OK",
                "error_code": None,
                "error_msg": "SIMULATION_MODE (ohne Hardware)",
                "busy": False,
                "band_belegt": True,
                "ist_position": int(self._sim_position_mm),
                "homing_ok": bool(self._sim_homed),
                "regal_connected": True,
                "regal_ok": True,
                "regal_busy": False,
                "regal_band_belegt": True,
                "regal_lift_sensor_belegt": True,
                "regal_wait_start_belegt": False,
                "regal_wait_end_belegt": False,
                "regal_level1_front_belegt": True,
                "regal_level2_front_belegt": True,
                "regal_mixer_belegt": True,
                "regal_entladen_blocked": False,
                "regal_ist_position": int(self._sim_position_mm),
                "regal_homing_ok": bool(self._sim_homed),
                "regal_error_msg": "SIMULATION_MODE",
            }

        msg = "Hardware nicht verfuegbar (I2C)."
        if self._init_error is not None:
            msg = f"{msg} Detail: {self._init_error}"
        return {
            "ok": False,
            "severity": "error",
            "error_code": "I2C_UNAVAILABLE",
            "error_msg": msg,
            "busy": False,
            "band_belegt": False,
            "ist_position": None,
            "homing_ok": False,
            "regal_connected": False,
            "regal_ok": False,
            "regal_busy": False,
            "regal_band_belegt": False,
            "regal_lift_sensor_belegt": False,
            "regal_wait_start_belegt": False,
            "regal_wait_end_belegt": False,
            "regal_level1_front_belegt": False,
            "regal_level2_front_belegt": False,
            "regal_mixer_belegt": False,
            "regal_entladen_blocked": False,
            "regal_ist_position": None,
            "regal_homing_ok": False,
            "regal_error_msg": "Regal nicht verfuegbar (Laptop-Modus).",
        }

    def prepare_mix(self, cocktail_id: int):
        self._assert_simulation_enabled()
        mix_data = self.model.get_full_mix_data(cocktail_id)
        if not mix_data:
            raise ValueError(f"Kein Rezept fuer Cocktail-ID {cocktail_id} gefunden.")
        for item in mix_data:
            item["cocktail_id"] = int(cocktail_id)
        return mix_data

    def run_mix(self, mix_data, factor: float = 1.0):
        self._assert_simulation_enabled()
        if not mix_data:
            raise ValueError("Mix-Daten sind leer")

        cocktail_id = mix_data[0].get("cocktail_id")
        # Dieselben Parameter wie im echten Ablauf lesen, damit sich Verhalten deckt.
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            level = settings.get_cocktail_source_level(int(cocktail_id)) if cocktail_id is not None else None
            level_ausschub_mm = settings.get_level_ausschub_distance(int(level)) if level is not None else None
            if level_ausschub_mm is None:
                level_ausschub_mm = settings.get_ausschub_distance()
            if level_ausschub_mm is None:
                level_ausschub_mm = 0.0
            load_unload_pos_mm = settings.get_load_unload_position()
            if load_unload_pos_mm is None:
                load_unload_pos_mm = settings.get_waiting_position()
            if load_unload_pos_mm is None:
                load_unload_pos_mm = 0.0
            homing_safe_height_mm = settings.get_homing_safe_height()
            if homing_safe_height_mm is None:
                homing_safe_height_mm = 0.0
            level_direction = settings.get_level_direction(int(level)) if level is not None else None
        finally:
            settings.close()
        if level is None:
            level = 1
        if level_direction is None:
            level_direction = True

        load_unload_i = int(round(float(load_unload_pos_mm)))
        ausschub_i = int(round(float(level_ausschub_mm)))
        homing_safe_i = int(round(float(homing_safe_height_mm)))
        encoded_level = (int(level) & 0x3F) | 0x40 | (0x80 if bool(level_direction) else 0x00)
        direction_name = "vorwaerts" if level_direction else "rueckwaerts"
        # Regal-/Mixer-Sequenz wird nur geloggt, damit die Schritte im Monitor nachvollziehbar bleiben.
        self._sim_log_mixer([1], note="CMD_HOME")
        self._sim_homed = True
        self._sim_position_mm = 0
        self._sim_log_regal([1], note="CMD_HOME (Lift+Ausschub)")
        self._sim_log_regal([0, homing_safe_i & 0xFF, (homing_safe_i >> 8) & 0xFF], note=f"CMD_LIFT -> sichere Homing-Hoehe {homing_safe_i} mm")
        self._sim_log_mixer([0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm")
        self._sim_position_mm = load_unload_i
        self._sim_log_regal([6, ausschub_i & 0xFF, (ausschub_i >> 8) & 0xFF], note=f"CMD_AUSSCHUB -> {ausschub_i} mm")
        self._sim_log_regal(
            [3, int(encoded_level)],
            note=f"CMD_EBENE {level} ({direction_name}, ausschub={level_ausschub_mm})",
        )
        self._sim_log_regal([4], note="CMD_BELADEN")
        self._sim_log_mixer([0, load_unload_i & 0xFF, (load_unload_i >> 8) & 0xFF], note=f"CMD_FAHR Mixer -> Uebergabe {load_unload_i} mm (vor Entladen)")
        self._sim_position_mm = load_unload_i
        self._sim_log_regal([6, ausschub_i & 0xFF, (ausschub_i >> 8) & 0xFF], note=f"CMD_AUSSCHUB -> {ausschub_i} mm (vor Entladen)")
        self._sim_log_regal([5], note="CMD_ENTLADEN")
        self.sim_trace.log_text("[SIM] Regal-Sequenz abgeschlossen")

        for item in mix_data:
            ingredient = str(item["ingredient_name"])
            amount_ml = float(item["amount_ml"]) * float(factor)
            pump_number = item["pump_number"]
            flow_rate = item["flow_rate_ml_s"]
            position_mm = int(item.get("position_mm", item.get("position_steps")))

            if pump_number is None or flow_rate is None or float(flow_rate) <= 0:
                self.sim_trace.log_text(f"[SIM] {ingredient}: ungueltige Pumpendaten, uebersprungen")
                continue

            low = position_mm & 0xFF
            high = (position_mm >> 8) & 0xFF
            self._sim_log_mixer([0, low, high], note=f"CMD_FAHR -> {position_mm} mm")
            self._sim_position_mm = position_mm

            dispense_time_s = amount_ml / float(flow_rate)
            seconds = max(1, min(255, int(round(dispense_time_s))))
            self._sim_log_mixer([3, int(pump_number), seconds], note=f"CMD_PUMPE {pump_number} fuer {seconds}s")
            self.sim_trace.log_text(f"[SIM] Schritt: {ingredient}, {amount_ml:.1f} ml")

        self.sim_trace.log_text("[SIM] Cocktail vollstaendig gemixt")
        return mix_data

    def shutdown(self):
        return None


class NoHardwarePumpController:
    def __init__(self, db_path=None):
        # Fallback fuer Kalibrier-Ansicht ohne physische Hardware.
        self.db_path = db_path
        self.model = PumpModel(db_path=db_path)
        self.sim_trace = get_simulation_trace_service()

    def _simulation_enabled(self) -> bool:
        settings = SystemSettingsModel(db_path=self.db_path)
        try:
            return bool(settings.get_simulation_mode())
        finally:
            settings.close()

    def list_pumps(self):
        return self.model.get_all_pumps()

    def set_position_steps(self, pump_number: int, steps: int):
        self.set_position_mm(pump_number, steps)

    def set_position_mm(self, pump_number: int, position_mm: int):
        self.model.update_position_mm(pump_number, position_mm)

    def set_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        self.model.update_flow_rate(pump_number, flow_rate_ml_s)

    def assign_ingredient(self, pump_number: int, ingredient_id: int):
        self.model.update_ingredient(pump_number, ingredient_id)

    def ensure_homed(self):
        if self._simulation_enabled():
            self.sim_trace.log_i2c(0x13, [1], note="CMD_HOME")
            return
        raise RuntimeError("Homing nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def move_to_position(self, position_mm: int):
        if self._simulation_enabled():
            mm = int(position_mm)
            self.sim_trace.log_i2c(0x13, [0, mm & 0xFF, (mm >> 8) & 0xFF], note=f"CMD_FAHR -> {mm} mm")
            return
        raise RuntimeError("Bewegung nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def run_pump_for_calibration(self, pump_number: int, seconds: int):
        if self._simulation_enabled():
            sec = max(1, min(255, int(seconds)))
            self.sim_trace.log_i2c(0x13, [3, int(pump_number), sec], note=f"CMD_PUMPE (Kalibrierung) {pump_number} fuer {sec}s")
            self.sim_trace.log_text(f"[SIM] Kalibrierlauf beendet: Pumpe {pump_number}, {sec}s")
            return sec
        raise RuntimeError("Pumpenlauf nicht moeglich: Hardware/I2C nicht verfuegbar.")

    def save_flow_rate_from_measurement(self, pump_number: int, measured_ml: float, seconds: int):
        if seconds <= 0:
            raise ValueError("seconds muss > 0 sein")
        flow_rate = float(measured_ml) / float(seconds)
        if flow_rate <= 0:
            raise ValueError("Gemessener Flow muss > 0 sein")
        self.model.update_flow_rate(pump_number, flow_rate)
        return flow_rate


class MIXmate:
    def __init__(self):
        base = os.path.dirname(__file__)
        db_path = os.path.join(base, "Database", "MIXmate.db")
        init_error = None
        try:
            # Normalfall: echte Controller mit echter Engine.
            self.mix_controller = MixController(db_path=db_path)
            self.pump_controller = PumpController(self.mix_controller.engine, db_path=db_path)
        except Exception as e:
            init_error = e
            # Fallback fuer Entwicklungsrechner ohne I2C (z. B. Windows/Laptop).
            print(f"[Startup] Hardware nicht verfuegbar, starte im Laptop-Modus: {e}")
            self.mix_controller = NoHardwareMixController(db_path=db_path, init_error=e)
            self.pump_controller = NoHardwarePumpController(db_path=db_path)
        self.admin_controller = AdminController(db_path=db_path)
        self.init_error = init_error

    def run(self):
        run_qt(self.mix_controller, self.pump_controller, self.admin_controller)


if __name__ == "__main__":
    app = MIXmate()
    app.run()
