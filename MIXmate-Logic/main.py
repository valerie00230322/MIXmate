from View.console_view import ConsoleView
from Controller.mix_controller import MixController
from Controller.pump_controller import PumpController
from Controller.admin_controller import AdminController

class MIXmate:
    def __init__(self):
        mix_controller = MixController()
        pump_controller = PumpController(mix_controller.engine)  # nutzt die gleiche MixEngine
        admin_controller = AdminController()
        self.view = ConsoleView(mix_controller, pump_controller, admin_controller)

    def run(self):
        self.view.run()


if __name__ == "__main__":
    MIXmate().run()
