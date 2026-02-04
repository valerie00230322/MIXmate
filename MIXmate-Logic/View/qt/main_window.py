from PySide6.QtWidgets import QMainWindow, QStackedWidget

from View.qt.screens.home_screen import HomeScreen
from View.qt.screens.cocktail_screen import CocktailScreen
from Model.cocktail_model import CocktailModel


class MainWindow(QMainWindow):
    def __init__(self, mix_controller, pump_controller, admin_controller):
        super().__init__()
        self.setWindowTitle("MIXmate")

        # Controller-Instanzen aus main.py übernehmen (MVC bleibt erhalten)
        self.mix_controller = mix_controller
        self.pump_controller = pump_controller
        self.admin_controller = admin_controller

        # QStackedWidget verwaltet die einzelnen Screens (Home, Cocktails, ...)
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # HomeScreen (Hauptmenü) erstellen und Navigation per Signals verbinden
        self.home = HomeScreen()
        self.home.go_mix.connect(self.show_cocktails)
        self.home.go_status.connect(self.show_status)
        self.home.go_calibration.connect(self.show_calibration)
        self.home.go_admin.connect(self.show_admin)
        self.home.do_exit.connect(self.close)

        # Model für dynamische Cocktail-Liste aus SQLite
        self.cocktail_model = CocktailModel()

        # CocktailScreen bekommt Controller + Model, damit Buttons aus der DB gebaut werden können
        self.cocktails = CocktailScreen(
            mix_controller=self.mix_controller,
            cocktail_model=self.cocktail_model,
            on_back=self.show_home
        )

        # Screens im Stack registrieren (Reihenfolge ist egal, solange alle hinzugefügt werden)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.cocktails)

        # Startansicht
        self.show_home()

    def show_home(self):
        # Wechsel zurück ins Hauptmenü
        self.stack.setCurrentWidget(self.home)

    def show_cocktails(self):
        # Vor dem Anzeigen Cocktails neu aus  DB laden (keine Hardcodes)
        self.cocktails.refresh()
        self.stack.setCurrentWidget(self.cocktails)

    def show_status(self):
        # Platzhalter: hier kommt später ein eigener Status-Screen rein
        print("Status Screen öffnen")

    def show_calibration(self):
        # Platzhalter:  Kalibrierungs-Screen 
        print("Calibration Screen öffnen")

    def show_admin(self):
        # Platzhalter: hier kommt später ein eigener Admin-Screen rein
        print("Admin Screen öffnen")
