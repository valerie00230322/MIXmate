from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from Model.cocktail_model import CocktailModel
from Services.admin_auth_service import AdminAuthService
from View.qt.screens.admin_screen import AdminScreen
from View.qt.screens.calibration_screen import CalibrationScreen
from View.qt.screens.cocktail_screen import CocktailScreen
from View.qt.screens.home_screen import HomeScreen
from View.qt.screens.status_screen import StatusScreen


class AdminLoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Admin Login")
        self.setModal(True)
        self.resize(360, 150)

        root = QVBoxLayout(self)

        form = QFormLayout()
        self.username_edit = QLineEdit(self)
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        form.addRow("Benutzername:", self.username_edit)
        form.addRow("Passwort:", self.password_edit)
        root.addLayout(form)

        buttons = QHBoxLayout()
        btn_cancel = QPushButton("Abbrechen", self)
        btn_ok = QPushButton("Anmelden", self)
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self.accept)
        buttons.addStretch(1)
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_ok)
        root.addLayout(buttons)

    def credentials(self) -> tuple[str, str]:
        return self.username_edit.text().strip(), self.password_edit.text()


class MainWindow(QMainWindow):
    def __init__(self, mix_controller, pump_controller, admin_controller):
        super().__init__()
        self.setWindowTitle("MIXmate")
        self._set_window_icon()

        self.mix_controller = mix_controller
        self.pump_controller = pump_controller
        self.admin_controller = admin_controller
        self.admin_auth = AdminAuthService()

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        self.home = HomeScreen()
        self.home.go_mix.connect(self.show_cocktails)
        self.home.go_status.connect(self.show_status)
        self.home.go_calibration.connect(self.show_calibration)
        self.home.go_admin.connect(self.show_admin)
        self.home.do_exit.connect(self.close)

        self.cocktail_model = CocktailModel()

        self.cocktails = CocktailScreen(
            mix_controller=self.mix_controller,
            cocktail_model=self.cocktail_model,
            on_back=self.show_home,
        )

        self.status_screen = StatusScreen(
            mix_controller=self.mix_controller,
            on_back=self.show_home,
        )

        self.calibration_screen = CalibrationScreen(
            pump_controller=self.pump_controller,
            on_back=self.show_home,
        )

        self.admin_screen = AdminScreen(
            admin_controller=self.admin_controller,
            pump_controller=self.pump_controller,
            on_back=self.show_home,
        )

        self.stack.addWidget(self.home)
        self.stack.addWidget(self.cocktails)
        self.stack.addWidget(self.status_screen)
        self.stack.addWidget(self.calibration_screen)
        self.stack.addWidget(self.admin_screen)

        self._home_state_timer = QTimer(self)
        self._home_state_timer.setInterval(1000)
        self._home_state_timer.timeout.connect(self._refresh_home_if_visible)
        self._home_state_timer.start()

        self.show_home()

    def _set_window_icon(self):
        assets_dir = Path(__file__).resolve().parent / "assets"
        candidates = [
            assets_dir / "mixmateLogo by chatBIG.PNG",
            assets_dir / "mixmateLogo by chat.png",
        ]
        for icon_path in candidates:
            if icon_path.exists():
                self.setWindowIcon(QIcon(str(icon_path)))
                break

    def _hardware_ready(self) -> bool:
        try:
            status = self.mix_controller.get_status() or {}
        except Exception:
            return False
        return bool(status.get("ok", False))

    def _update_home_state(self):
        ready = False
        regal_connected = False
        try:
            status = self.mix_controller.get_status() or {}
            ready = bool(status.get("ok", False))
            regal_connected = bool(status.get("regal_connected", False))
        except Exception:
            ready = False
            regal_connected = False
        self.home.set_ready(ready)
        self.home.set_hardware_actions_enabled(ready)
        self.home.set_regal_connected(regal_connected)

    def _refresh_home_if_visible(self):
        if self.stack.currentWidget() is self.home:
            self._update_home_state()

    def _stop_live_views(self):
        self.status_screen.stop()
        self.calibration_screen.stop()

    def show_home(self):
        self._stop_live_views()
        self._update_home_state()
        self.stack.setCurrentWidget(self.home)

    def show_cocktails(self):
        self._stop_live_views()
        self.cocktails.refresh()
        self.stack.setCurrentWidget(self.cocktails)

    def show_status(self):
        self._stop_live_views()
        self.stack.setCurrentWidget(self.status_screen)
        self.status_screen.start()

    def show_calibration(self):
        self._stop_live_views()
        self.stack.setCurrentWidget(self.calibration_screen)
        self.calibration_screen.start()

    def show_admin(self):
        self._stop_live_views()
        dlg = AdminLoginDialog(self)
        if dlg.exec() != QDialog.Accepted:
            return

        username, password = dlg.credentials()
        if not self.admin_auth.verify(username, password):
            QMessageBox.critical(self, "Login fehlgeschlagen", "Benutzername oder Passwort ist falsch.")
            return

        self.admin_screen.setEnabled(True)
        self.admin_screen.show_menu()
        self.stack.setCurrentWidget(self.admin_screen)

    def closeEvent(self, event):
        self._stop_live_views()
        try:
            self.mix_controller.shutdown()
        except Exception:
            pass
        super().closeEvent(event)
