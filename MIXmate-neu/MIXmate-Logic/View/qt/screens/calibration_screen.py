from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class CalibrationRunWorker(QObject):
    finished = Signal(int)
    failed = Signal(str)

    def __init__(self, pump_controller, pump_number: int, seconds: int):
        super().__init__()
        self.pump_controller = pump_controller
        self.pump_number = int(pump_number)
        self.seconds = int(seconds)

    def run(self):
        try:
            actual_seconds = self.pump_controller.run_pump_for_calibration(
                self.pump_number,
                self.seconds,
            )
            self.finished.emit(int(actual_seconds))
        except Exception as e:
            self.failed.emit(str(e))


class CalibrationScreen(QWidget):
    def __init__(self, pump_controller, on_back):
        super().__init__()
        self.setObjectName("CocktailScreen")
        self.setAttribute(Qt.WA_StyledBackground, True)

        self.pump_controller = pump_controller
        self.on_back = on_back

        self.thread: QThread | None = None
        self.worker: CalibrationRunWorker | None = None
        self.current_pump_number: int | None = None

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

        title = QLabel("Pumpen kalibrieren")
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
        card_layout.setSpacing(12)

        help_text = QLabel(
            "Pumpe auswaehlen, Laufzeit eingeben, danach gemessene Menge in ml eintragen."
        )
        help_text.setObjectName("TileSubtitle")
        help_text.setWordWrap(True)
        card_layout.addWidget(help_text)

        self.scroll = QScrollArea()
        self.scroll.setObjectName("CocktailScroll")
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)

        self.list_container = QWidget()
        self.list_container.setObjectName("CocktailList")
        self.list_container.setAttribute(Qt.WA_StyledBackground, True)

        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        card_layout.addWidget(self.scroll, 1)

        self.info_label = QLabel("")
        self.info_label.setObjectName("InfoLabel")
        self.info_label.setWordWrap(True)
        card_layout.addWidget(self.info_label)

        root.addWidget(card, 1)

        self.overlay = QFrame(self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setAttribute(Qt.WA_StyledBackground, True)
        self.overlay.setVisible(False)

        ov = QVBoxLayout(self.overlay)
        ov.setContentsMargins(24, 24, 24, 24)
        ov.setSpacing(12)

        self.wait_label = QLabel("Bitte warten...")
        self.wait_label.setObjectName("OverlayTitle")
        self.wait_label.setAlignment(Qt.AlignCenter)
        ov.addWidget(self.wait_label)

        self.result_label = QLabel("")
        self.result_label.setObjectName("OverlayText")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        ov.addWidget(self.result_label)

        ov.addStretch(1)

    def resizeEvent(self, event):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def _go_back(self):
        self.stop()
        self.on_back()

    def start(self):
        self.refresh()

    def stop(self):
        self._hide_overlay()

    def refresh(self):
        self._clear_list()
        self.info_label.setText("Lade Pumpen...")

        try:
            pumps = self.pump_controller.list_pumps()
        except Exception as e:
            self.info_label.setText(f"Fehler beim Laden der Pumpen: {e}")
            return

        if not pumps:
            self.info_label.setText("Keine Pumpen gefunden.")
            return

        self.info_label.setText("")
        for p in pumps:
            self._add_pump_button(p)

    def _clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.list_layout.addStretch(1)

    def _pump_label(self, p: dict) -> str:
        number = p.get("pump_number")
        ing = p.get("ingredient_id")
        flow = p.get("flow_rate_ml_s")
        pos = p.get("position_mm")
        return (
            f"Pumpe {number} | ingredient_id={ing} | flow_rate={flow} ml/s | pos={pos}"
        )

    def _add_pump_button(self, pump: dict):
        pump_number = int(pump["pump_number"])

        btn = QPushButton(self._pump_label(pump))
        btn.setProperty("role", "cocktail")
        btn.setMinimumHeight(72)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _, pn=pump_number: self._start_calibration_flow(pn))

        self.list_layout.insertWidget(self.list_layout.count() - 1, btn)

    def _start_calibration_flow(self, pump_number: int):
        seconds, ok = QInputDialog.getInt(
            self,
            "Laufzeit",
            f"Laufzeit fuer Pumpe {pump_number} in Sekunden:",
            5,
            1,
            255,
            1,
        )
        if not ok:
            return

        self.current_pump_number = pump_number
        self._show_overlay("Bitte warten...", f"Pumpe {pump_number} laeuft {seconds} s")

        self.thread = QThread()
        self.worker = CalibrationRunWorker(self.pump_controller, pump_number, seconds)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._pump_run_done)
        self.worker.failed.connect(self._pump_run_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _pump_run_done(self, actual_seconds: int):
        pump_number = self.current_pump_number
        if pump_number is None:
            self._hide_overlay()
            return

        self._hide_overlay()

        measured_ml, ok = QInputDialog.getDouble(
            self,
            "Gemessene Menge",
            f"Geflossene Menge von Pumpe {pump_number} in ml:",
            10.0,
            0.1,
            5000.0,
            1,
        )
        if not ok:
            self.info_label.setText("Kalibrierung abgebrochen (keine Menge eingegeben).")
            return

        try:
            flow_rate = self.pump_controller.save_flow_rate_from_measurement(
                pump_number=pump_number,
                measured_ml=float(measured_ml),
                seconds=int(actual_seconds),
            )
        except Exception as e:
            QMessageBox.critical(self, "Fehler", str(e))
            return

        self.info_label.setText(
            f"Pumpe {pump_number} gespeichert: {flow_rate:.3f} ml/s (Menge {measured_ml} ml in {actual_seconds} s)."
        )
        success_msg = self.info_label.text()
        self.refresh()
        self.info_label.setText(success_msg)

    def _pump_run_failed(self, msg: str):
        self._hide_overlay()
        QMessageBox.critical(self, "Kalibrierung fehlgeschlagen", msg)

    def _show_overlay(self, title: str, details: str):
        self.overlay.setVisible(True)
        self.overlay.raise_()
        self.wait_label.setText(title)
        self.result_label.setText(details)

    def _hide_overlay(self):
        self.overlay.setVisible(False)
