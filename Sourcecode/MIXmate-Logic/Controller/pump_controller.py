from Model.pump_model import PumpModel
from Services.mix_engine import MixEngine
from Services.pump_calibration_service import PumpCalibrationService
from Services.simulation_trace_service import get_simulation_trace_service


class PumpController:
    def __init__(self, mix_engine: MixEngine, db_path=None):
        # Pumpencontroller nutzt die laufende MixEngine fuer Hardwarezugriff.
        # engine liefert I2C, StatusMonitor und Simulationserkennung.
        self.engine = mix_engine
        # model speichert Pumpenposition, Zutat und Flow-Rate.
        self.model = PumpModel(db_path=db_path)
        # Kalibrierung teilt sich Monitor und StatusService mit dem Mixablauf.
        self.calibration_service = PumpCalibrationService(
            monitor=self.engine.monitor,
            status_service=self.engine.status_service,
        )
        # sim_trace zeigt Kalibrierbefehle im Simulationsmonitor.
        self.sim_trace = get_simulation_trace_service()

    def list_pumps(self):
        # Pumpenliste fuer Admin- und Kalibrieransicht.
        return self.model.get_all_pumps()

    def set_position_steps(self, pump_number: int, steps: int):
        # Alter Name bleibt kompatibel, intern wird mm verwendet.
        self.set_position_mm(pump_number, steps)

    def set_position_mm(self, pump_number: int, position_mm: int):
        if position_mm < 0:
            # Negative Positionen liegen ausserhalb des Fahrbereichs.
            raise ValueError("position_mm darf nicht negativ sein")
        self.model.update_position_mm(pump_number, position_mm)

    def set_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        if flow_rate_ml_s <= 0:
            # Flow-Rate muss fuer Zeitberechnung positiv sein.
            raise ValueError("flow_rate_ml_s muss groesser als 0 sein")
        self.model.update_flow_rate(pump_number, flow_rate_ml_s)

    def assign_ingredient(self, pump_number: int, ingredient_id: int):
        # Zuordnung entscheidet spaeter, welche Pumpe eine Zutat foerdert.
        self.model.update_ingredient(pump_number, ingredient_id)

    def ensure_homed(self):
        # Kalibrierfahrten starten nur nach Referenzfahrt sicher.
        self.engine.ensure_homed()

    def move_to_position(self, position_mm: int):
        # Direkte Fahrt fuer Pumpenpositionierung in der Kalibrierung.
        self.engine.move_to_position(position_mm)

    def run_pump_for_calibration(self, pump_number: int, seconds: int):
        if self.engine.is_simulation_mode():
            # Simulation protokolliert den Pumpenlauf ohne Hardware.
            sec = max(1, min(255, int(seconds)))
            self.sim_trace.log_i2c(
                0x13,
                [3, int(pump_number), sec],
                note=f"CMD_PUMPE (Kalibrierung) {pump_number} fuer {sec}s",
            )
            self.sim_trace.log_text(f"[SIM] Kalibrierlauf beendet: Pumpe {pump_number}, {sec}s")
            return sec

        # Echtbetrieb laeuft ueber den Kalibrier-Service mit Status-Waits.
        return self.calibration_service.run_pump_for_seconds(
            i2c=self.engine.i2c,
            pump_number=pump_number,
            seconds=seconds,
        )

    def save_flow_rate_from_measurement(self, pump_number: int, measured_ml: float, seconds: int):
        # Gemessene Menge wird in ml/s umgerechnet.
        flow_rate = self.calibration_service.calc_flow_rate_ml_s(
            measured_ml=measured_ml,
            seconds=seconds,
        )
        # Neuer Kalibrierwert wird direkt persistiert.
        self.model.update_flow_rate(pump_number, flow_rate)
        return flow_rate
