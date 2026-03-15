from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFrame, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class StatusScreen(QWidget):
    def __init__(self, mix_controller, on_back):
        super().__init__()
        self.setObjectName("CocktailScreen")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.mix_controller = mix_controller
        self.on_back = on_back

        self._timer = QTimer(self)
        self._timer.setInterval(300)
        self._timer.timeout.connect(self.refresh_status)

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        header = QFrame()
        header.setObjectName("Header")
        header.setAttribute(Qt.WA_StyledBackground, True)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.back_btn = QPushButton("Zurueck")
        self.back_btn.setProperty("role", "nav")
        self.back_btn.setMinimumHeight(52)
        self.back_btn.clicked.connect(self._go_back)

        title = QLabel("Status (live)")
        title.setObjectName("ScreenTitle")
        title.setAlignment(Qt.AlignCenter)

        right_spacer = QLabel("")
        right_spacer.setFixedWidth(self.back_btn.sizeHint().width())

        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(title, 1)
        header_layout.addWidget(right_spacer)

        root.addWidget(header)

        card = QFrame()
        card.setObjectName("Card")
        card.setAttribute(Qt.WA_StyledBackground, True)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(14)

        grid = QGridLayout()
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(10)

        self.lbl_ok = self._value_label()
        self.lbl_severity = self._value_label()
        self.lbl_error = self._value_label(multiline=True)
        self.lbl_busy = self._value_label()
        self.lbl_band = self._value_label()
        self.lbl_pos = self._value_label()
        self.lbl_home = self._value_label()
        self.lbl_regal_connected = self._value_label()
        self.lbl_regal_busy = self._value_label()
        self.lbl_regal_band = self._value_label()
        self.lbl_regal_pos = self._value_label()
        self.lbl_regal_home = self._value_label()
        self.lbl_regal_wait_start = self._value_label()
        self.lbl_regal_wait_end = self._value_label()
        self.lbl_regal_mixer = self._value_label()
        self.lbl_regal_level1 = self._value_label()
        self.lbl_regal_level2 = self._value_label()
        self.lbl_regal_entladen_blocked = self._value_label()
        self.lbl_regal_error = self._value_label(multiline=True)

        self._add_row(grid, 0, "OK", self.lbl_ok)
        self._add_row(grid, 1, "Severity", self.lbl_severity)
        self._add_row(grid, 2, "Error", self.lbl_error)
        self._add_row(grid, 3, "Busy", self.lbl_busy)
        self._add_row(grid, 4, "Band belegt", self.lbl_band)
        self._add_row(grid, 5, "Position", self.lbl_pos)
        self._add_row(grid, 6, "Homing OK", self.lbl_home)
        self._add_row(grid, 7, "Regal erkannt", self.lbl_regal_connected)
        self._add_row(grid, 8, "Regal busy", self.lbl_regal_busy)
        self._add_row(grid, 9, "Regal Glas erkannt", self.lbl_regal_band)
        self._add_row(grid, 10, "Regal Position", self.lbl_regal_pos)
        self._add_row(grid, 11, "Regal Homing OK", self.lbl_regal_home)
        self._add_row(grid, 12, "Regal Wait Start", self.lbl_regal_wait_start)
        self._add_row(grid, 13, "Regal Wait Ende", self.lbl_regal_wait_end)
        self._add_row(grid, 14, "Regal Mixer Sensor", self.lbl_regal_mixer)
        self._add_row(grid, 15, "Regal Level1 Front", self.lbl_regal_level1)
        self._add_row(grid, 16, "Regal Level2 Front", self.lbl_regal_level2)
        self._add_row(grid, 17, "Regal Entladen Block", self.lbl_regal_entladen_blocked)
        self._add_row(grid, 18, "Regal Error", self.lbl_regal_error)

        card_layout.addLayout(grid)

        self.info = QLabel("")
        self.info.setObjectName("TileSubtitle")
        self.info.setWordWrap(True)
        card_layout.addWidget(self.info)

        root.addWidget(card, 1)

    def _value_label(self, multiline: bool = False) -> QLabel:
        lbl = QLabel("-")
        lbl.setObjectName("TileTitle")
        if multiline:
            lbl.setWordWrap(True)
        return lbl

    def _add_row(self, layout: QGridLayout, row: int, title: str, value_widget: QLabel):
        key = QLabel(title)
        key.setObjectName("TileSubtitle")
        layout.addWidget(key, row, 0, alignment=Qt.AlignTop)
        layout.addWidget(value_widget, row, 1, alignment=Qt.AlignTop)

    def _go_back(self):
        self.stop()
        self.on_back()

    def start(self):
        self.refresh_status()
        self._timer.start()

    def stop(self):
        self._timer.stop()

    def refresh_status(self):
        try:
            status = self.mix_controller.get_status() or {}
        except Exception as e:
            self.info.setText(f"Status konnte nicht gelesen werden: {e}")
            return

        self.lbl_ok.setText(str(status.get("ok")))
        self.lbl_severity.setText(str(status.get("severity")))

        error_msg = status.get("error_msg") or "-"
        self.lbl_error.setText(str(error_msg))

        self.lbl_busy.setText(str(status.get("busy")))
        self.lbl_band.setText(str(status.get("band_belegt")))
        self.lbl_pos.setText(str(status.get("ist_position")))
        self.lbl_home.setText(str(status.get("homing_ok")))
        self.lbl_regal_connected.setText(str(status.get("regal_connected")))
        self.lbl_regal_busy.setText(str(status.get("regal_busy")))
        self.lbl_regal_band.setText(str(status.get("regal_band_belegt")))
        self.lbl_regal_pos.setText(str(status.get("regal_ist_position")))
        self.lbl_regal_home.setText(str(status.get("regal_homing_ok")))
        self.lbl_regal_wait_start.setText(str(status.get("regal_wait_start_belegt")))
        self.lbl_regal_wait_end.setText(str(status.get("regal_wait_end_belegt")))
        self.lbl_regal_mixer.setText(str(status.get("regal_mixer_belegt")))
        self.lbl_regal_level1.setText(str(status.get("regal_level1_front_belegt")))
        self.lbl_regal_level2.setText(str(status.get("regal_level2_front_belegt")))
        self.lbl_regal_entladen_blocked.setText(str(status.get("regal_entladen_blocked")))
        self.lbl_regal_error.setText(str(status.get("regal_error_msg") or "-"))

        if status.get("ok"):
            self.info.setText("Statusmonitor laeuft.")
        else:
            self.info.setText("Statusmonitor meldet einen Fehlerzustand.")
