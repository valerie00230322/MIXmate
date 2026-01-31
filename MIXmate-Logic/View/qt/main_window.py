# Navigation der Hauptfenster-Screens
from PySide6.QtWidgets import QMainWindow, QStackedWidget
from View.qt.screens.home_screen import HomeScreen

class MainWindow(QMainWindow):
    def __init__(self, mix_controller, pump_controller, admin_controller):
        super().__init__()
        self.setWindowTitle("MIXmate")

        # Stack = Seitenverwaltung
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # Screens erstellen
        self.home = HomeScreen()
        self.home.go_mix.connect(self.show_cocktails)
        self.home.go_status.connect(self.show_status)
        self.home.go_calibration.connect(self.show_calibration)
        self.home.go_admin.connect(self.show_admin)
        self.home.do_exit.connect(self.close)

        self.stack.addWidget(self.home)

        # Startscreen
        self.stack.setCurrentWidget(self.home)

    # Platzhalter-Navigation (baust du später mit echten Screens)
    def show_cocktails(self):
        print("Cocktail Screen öffnen")

    def show_status(self):
        print("Status Screen öffnen")

    def show_calibration(self):
        print("Calibration Screen öffnen")

    def show_admin(self):
        print("Admin Screen öffnen")
