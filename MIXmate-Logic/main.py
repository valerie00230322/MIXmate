from View.console_view import ConsoleView
from Controller.mix_controller import MixController

class MIXmate:
    def __init__(self):
        controller = MixController()
        self.view = ConsoleView(controller)

    def run(self):
        self.view.run()

if __name__ == "__main__":
    MIXmate().run()
