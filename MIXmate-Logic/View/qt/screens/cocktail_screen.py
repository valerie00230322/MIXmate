from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QProgressBar, QSizePolicy
)


class MixWorker(QObject):
    finished = Signal(list)
    failed = Signal(str)

    def __init__(self, mix_controller, mix_data):
        super().__init__()
        self.mix_controller = mix_controller
        self.mix_data = mix_data

    def run(self):
        try:
            recipe = self.mix_controller.run_mix(self.mix_data, factor=1.0)
            self.finished.emit(recipe if recipe is not None else [])
        except Exception as e:
            self.failed.emit(str(e))


class CocktailScreen(QWidget):
    def __init__(self, mix_controller, cocktail_model, on_back):
        super().__init__()
        self.mix_controller = mix_controller
        self.cocktail_model = cocktail_model
        self.on_back = on_back

        self.thread: QThread | None = None
        self.worker: MixWorker | None = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        # Header (Zurück + Titel)
        header = QFrame()
        header.setObjectName("Header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(12)

        self.back_btn = QPushButton("⬅ Zurück")
        self.back_btn.setProperty("role", "nav")
        self.back_btn.setMinimumHeight(70)
        self.back_btn.clicked.connect(self.on_back)

        title = QLabel("Cocktail auswählen")
        title.setObjectName("ScreenTitle")
        title.setAlignment(Qt.AlignCenter)

        right_spacer = QLabel("")
        right_spacer.setFixedWidth(self.back_btn.sizeHint().width())

        header_layout.addWidget(self.back_btn)
        header_layout.addWidget(title, 1)
        header_layout.addWidget(right_spacer)
        root.addWidget(header)

        # Card mit Scroll-Liste
        card = QFrame()
        card.setObjectName("Card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.list_layout.addStretch(1)

        self.scroll.setWidget(self.list_container)
        card_layout.addWidget(self.scroll, 1)

        self.info_label = QLabel("")
        self.info_label.setObjectName("InfoLabel")
        self.info_label.setAlignment(Qt.AlignCenter)
        card_layout.addWidget(self.info_label)

        root.addWidget(card, 1)

        # Overlay (Please wait / Fehler / Fertig)
        self.overlay = QFrame(self)
        self.overlay.setObjectName("Overlay")
        self.overlay.setVisible(False)

        ov = QVBoxLayout(self.overlay)
        ov.setContentsMargins(24, 24, 24, 24)
        ov.setSpacing(12)

        self.wait_label = QLabel("Please wait…")
        self.wait_label.setObjectName("OverlayTitle")
        self.wait_label.setAlignment(Qt.AlignCenter)
        ov.addWidget(self.wait_label)

        self.busy = QProgressBar()
        self.busy.setTextVisible(False)
        self.busy.setRange(0, 0)  # indeterminate
        self.busy.setFixedHeight(10)
        ov.addWidget(self.busy)

        self.result_label = QLabel("")
        self.result_label.setObjectName("OverlayText")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setWordWrap(True)
        ov.addWidget(self.result_label)

        ov.addStretch(1)

    def resizeEvent(self, event):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    def refresh(self):
        self._clear_list()
        self.info_label.setText("Lade Cocktails…")

        try:
            cocktails = self.cocktail_model.get_all_cocktails()
            if not cocktails:
                self.info_label.setText("Keine Cocktails gefunden.")
                return

            self.info_label.setText("")
            for c in cocktails:
                cid = int(c["cocktail_id"])
                name = str(c["cocktail_name"])
                self._add_cocktail_button(cid, name)

        except Exception as e:
            self.info_label.setText(f"Fehler beim Laden: {e}")

    def _clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
        self.list_layout.addStretch(1)

    def _add_cocktail_button(self, cocktail_id: int, name: str):
        btn = QPushButton(f"🍸  {name}")
        btn.setProperty("role", "cocktail")
        btn.setMinimumHeight(90)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda _, cid=cocktail_id: self.start_mix(cid))

        # vor dem Stretch einfügen
        self.list_layout.insertWidget(self.list_layout.count() - 1, btn)

    def start_mix(self, cocktail_id: int):
        try:
            mix_data = self.mix_controller.prepare_mix(cocktail_id)
        except Exception as e:
            self._show_overlay("Fehler!", str(e), show_busy=False)
            return

        self._show_overlay("Please wait…\nCocktail wird gemischt", "", show_busy=True)

        self.thread = QThread()
        self.worker = MixWorker(self.mix_controller, mix_data)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self._mix_done)
        self.worker.failed.connect(self._mix_failed)

        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def _mix_done(self, recipe: list):
        self._show_overlay("Fertig ✅", "", show_busy=False)
        QTimer.singleShot(1200, self._hide_overlay)

    def _mix_failed(self, msg: str):
        self._show_overlay("Fehler!", msg, show_busy=False)

    def _show_overlay(self, title: str, details: str, show_busy: bool):
        self.overlay.setVisible(True)
        self.wait_label.setText(title)
        self.result_label.setText(details)
        self.busy.setVisible(show_busy)

    def _hide_overlay(self):
        self.overlay.setVisible(False)
