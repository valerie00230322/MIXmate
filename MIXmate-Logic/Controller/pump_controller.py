from Model.pump_model import PumpModel
from Services.pump_calibration_service import PumpCalibrationService
from Services.mix_engine import MixEngine


class PumpController:
    def __init__(self, mix_engine: MixEngine):
        # Der PumpController bekommt die bestehende MixEngine übergeben.
        # Damit arbeiten Mischen und Kalibrieren mit exakt derselben Hardware,
        # demselben StatusMonitor und derselben Busy-/Homing-Logik.
        self.engine = mix_engine

        # Das Model ist ausschließlich für Datenbankzugriffe zuständig.
        # Hier wird nichts berechnet und keine Hardware bewegt.
        self.model = PumpModel()

        # Dieser Service enthält die eigentliche Kalibrierungslogik:
        # warten bis busy False ist, Pumpe laufen lassen, ml/s berechnen.
        self.calibration_service = PumpCalibrationService(
            monitor=self.engine.monitor,
            status_service=self.engine.status_service
        )

    def list_pumps(self):
        # Gibt alle Pumpen aus der Datenbank zurück.
        
        return self.model.get_all_pumps()

    def set_position_steps(self, pump_number: int, steps: int):
        # Setzt die Position (in Steps) einer Pumpe neu.
       
        if steps < 0:
            raise ValueError("position_steps darf nicht negativ sein")

        self.model.update_position_steps(pump_number, steps)

    def set_flow_rate(self, pump_number: int, flow_rate_ml_s: float):
        # Setzt eine neue Flow-Rate direkt.-->
        if flow_rate_ml_s <= 0:
            raise ValueError("flow_rate_ml_s muss größer als 0 sein")

        self.model.update_flow_rate(pump_number, flow_rate_ml_s)

    def assign_ingredient(self, pump_number: int, ingredient_id: int):
        # Verknüpft eine Zutat mit einer Pumpe.
        # Damit weiß das System später, zu welcher Pumpe der Schlitten fahren muss.
        self.model.update_ingredient(pump_number, ingredient_id)

    def ensure_homed(self):
        # Homing bei MixEngine aufrufen.
    
        self.engine.ensure_homed()

    def move_to_position(self, position_steps: int):
        # Bewegt den Schlitten zu einer bestimmten Position.
        
        self.engine.move_to_position(position_steps)

    def run_pump_for_calibration(self, pump_number: int, seconds: int):
        # Lässt eine Pumpe für Kalibrierungszwecke laufen.
        # Hier geht es nicht um Cocktails, sondern nur um einen kontrollierten Testlauf.
        return self.calibration_service.run_pump_for_seconds(
            i2c=self.engine.i2c,
            pump_number=pump_number,
            seconds=seconds
        )

    def save_flow_rate_from_measurement(self, pump_number: int, measured_ml: float, seconds: int):
        # Aus den gemessenen ml und der Laufzeit wird die Flow-Rate berechnet und in der DB gespeichert.
        
        flow_rate = self.calibration_service.calc_flow_rate_ml_s(
            measured_ml=measured_ml,
            seconds=seconds
        )

        self.model.update_flow_rate(pump_number, flow_rate)
        return flow_rate
