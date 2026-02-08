from View.qt.run_qt import run_qt
from View.console_view import ConsoleView
from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
from Controller.admin_controller import AdminController

# wird für relais benötigt
"""
blablabla
from Hardware.relay_board import RelayBoard
from Services.startup_sequence_service import StartupSequenceService
"""
class MIXmate:
    def __init__(self):
        """
        bei sim modus unnötig
        #wird für Relais benötigt
        first_pair = [17, 27]
        second_pair = [22, 23]
        delay_secs= 2.0

        #wenn Low --> relais ist EIN
        relay_board = RelayBoard(pins=first_pair + second_pair, active_low=True)
        
        StartupSequenceService(relay_board).run(first_pair, second_pair, delay_secs)
        """
        #Initialisierung der Controller
        self.mix_controller = MixController()
        self.pump_controller = PumpController(self.mix_controller.engine)
        self.admin_controller = AdminController()

        #nur für consoleview
        #self.view = ConsoleView(mix_controller, pump_controller, admin_controller)

    def run(self):
        #nur für consoleview
        #self.view.run()
        run_qt(self.mix_controller, self.pump_controller, self.admin_controller)



if __name__ == "__main__":
    MIXmate().run()
