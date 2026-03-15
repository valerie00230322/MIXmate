from Model.pump_model import PumpModel
from Services.mix_engine import MixEngine
from Services.pump_calibration_service import PumpCalibrationService
from Services.simulation_trace_service import get_simulation_trace_service


class PumpController:
    def __init__(self, mix_engine: MixEngine, db_path=None):
        self.engine = mix_engine
        self.model = PumpModel(db_path=db_path)
        self.calibration_service = PumpCalibrationService(
            monitor=self.engine.monitor,
            status_service=self.engine.status_service,
        )
        self.sim_trace = get_simulation_trace_service()

    def list_pumps(self):
        return self.model.get_all_pumps()

    def set_position_steps(self, pump_number: int, steps: int):
        self.set_position_mm(pump_number, steps)

    def set_position_mm(self, pump_number: int, position_mm: int):
        if position_mm < 0:
            raise ValueError("position_mm darf nicht negativ sein")
        self.model.update_position_mm(pump_number, position_mm)

    def set_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        if flow_rate_ml_s <= 0:
            raise ValueError("flow_rate_ml_s muss groesser als 0 sein")
        self.model.update_flow_rate(pump_number, flow_rate_ml_s)

    def assign_ingredient(self, pump_number: int, ingredient_id: int):
        self.model.update_ingredient(pump_number, ingredient_id)

    def ensure_homed(self):
        self.engine.ensure_homed()

    def move_to_position(self, position_mm: int):
        self.engine.move_to_position(position_mm)

    def run_pump_for_calibration(self, pump_number: int, seconds: int):
        if self.engine.is_simulation_mode():
            sec = max(1, min(255, int(seconds)))
            self.sim_trace.log_i2c(
                0x13,
                [3, int(pump_number), sec],
                note=f"CMD_PUMPE (Kalibrierung) {pump_number} fuer {sec}s",
            )
            self.sim_trace.log_text(f"[SIM] Kalibrierlauf beendet: Pumpe {pump_number}, {sec}s")
            return sec

        return self.calibration_service.run_pump_for_seconds(
            i2c=self.engine.i2c,
            pump_number=pump_number,
            seconds=seconds,
        )

    def save_flow_rate_from_measurement(self, pump_number: int, measured_ml: float, seconds: int):
        flow_rate = self.calibration_service.calc_flow_rate_ml_s(
            measured_ml=measured_ml,
            seconds=seconds,
        )
        self.model.update_flow_rate(pump_number, flow_rate)
        return flow_rate
