# Einstieg fuer die Qt-App.
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from View.qt.main_window import MainWindow
from pathlib import Path

def run_qt(mix_controller, pump_controller, admin_controller):
    app = QApplication(sys.argv)
    assets_dir = Path(__file__).parent / "assets"
    for icon_path in [assets_dir / "mixmateLogo by chatBIG.PNG", assets_dir / "mixmateLogo by chat.png"]:
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
            break

    # QSS-Theme laden.
    qss_file = Path(__file__).parent / "styles" / "theme.qss"
    # Fehlendes Theme darf den Start nicht blockieren.
    if qss_file.exists():
        app.setStyleSheet(qss_file.read_text(encoding="utf-8"))

    main_window = MainWindow(mix_controller, pump_controller, admin_controller)

    # Windows-Start im normalen Fenster.
    main_window.show()

    # Qt-Eventloop starten.
    sys.exit(app.exec())
