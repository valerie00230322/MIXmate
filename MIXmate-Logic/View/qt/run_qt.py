# start für die qt app
import sys
from PySide6.QtWidgets import QApplication
from View.qt.main_window import MainWindow
from pathlib import Path

def run_qt(mix_controller, pump_controller, admin_controller):
    app = QApplication(sys.argv)

    # theme laden
    qss_file = Path(__file__).parent / "styles" / "theme.qss"
    # überprüfen, ob die Datei existiert
    if qss_file.exists():
        app.setStyleSheet(qss_file.read_text(encoding="utf-8"))

    main_window = MainWindow(mix_controller, pump_controller, admin_controller)

    # am Windows-PC: Fenster normal anzeigen
    main_window.show()

    # am Raspberry Pi im Vollbild starten und Maus ausblenden (für Produktivbetrieb)
    # main_window.showFullScreen()
    # main_window.setCursor(Qt.BlankCursor)

    # hier wird eventloop gestartet
    sys.exit(app.exec())
