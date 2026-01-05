from View.console_view import ConsoleView
from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
from Controller.admin_controller import AdminController

# wird für relais benötigt
from Hardware.relay_board import RelayBoard
from Services.startup_sequence_service import StartupSequenceService

class MIXmate:
    def __init__(self):

        #wird für Relais benötigt
        first_pair = [17, 27]
        second_pair = [22, 23]
        delay_secs= 2.0

        #wenn Low --> relais ist EIN
        relay_board = RelayBoard(pins= first_pair + second_pair, is_active_low=True)
        StartupSequenceService(relay_board).run(first_pair, second_pair, delay_secs)
        #Initialisierung der Controller
        mix_controller = MixController()
        pump_controller = PumpController(mix_controller.engine)  # nutzt die gleiche MixEngine
        admin_controller = AdminController()
        self.view = ConsoleView(mix_controller, pump_controller, admin_controller)

    def run(self):
        self.view.run()


if __name__ == "__main__":
    MIXmate().run()
