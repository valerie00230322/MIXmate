from __future__ import annotations

from PySide6.QtCore import Qt, QObject, Signal, QThread, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QFrame, QScrollArea
)

# Worker-Klasse für das Mischen im Hintergrundthread
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

# CocktailScreen Klasse
class CocktailScreen(QWidget):
    def __init__(self, mix_controller, cocktail_model, on_back):
        super().__init__()
        self.mix_controller = mix_controller
        self.cocktail_model = cocktail_model
        self.on_back = on_back

        self.thread = None
        self.worker = None

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(12)

        title = QLabel("Cocktail auswählen")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 34px; font-weight: 600;")
        root.addWidget(title)

        back = QPushButton(" Zurück")
        back.setMinimumHeight(70)
        back.clicked.connect(self.on_back)
        root.addWidget(back)

        # ScrollArea für Cocktail-Liste
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        root.addWidget(self.scroll, 1)

        self.list_container = QWidget()
        self.list_layout = QVBoxLayout(self.list_container)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(10)
        self.scroll.setWidget(self.list_container) #setzt das Container-Widget in  ScrollArea

        self.info_label = QLabel("") # Info-Label für Statusmeldungen
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("font-size: 16px; color: rgba(255,255,255,0.75);")
        root.addWidget(self.info_label)

        # Please-wait Overlay
        self.overlay = QFrame(self)
        self.overlay.setVisible(False)
        self.overlay.setStyleSheet("QFrame{background: rgba(0,0,0,180); border-radius: 18px;}")

        ov = QVBoxLayout(self.overlay)
        ov.setContentsMargins(24, 24, 24, 24)
        ov.setSpacing(10)

        self.wait_label = QLabel("Please wait…\nCocktail wird gemischt")
        self.wait_label.setAlignment(Qt.AlignCenter)
        self.wait_label.setStyleSheet("font-size: 28px; font-weight: 600;")
        ov.addWidget(self.wait_label)

        self.result_label = QLabel("")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 18px;")
        ov.addWidget(self.result_label)

    def resizeEvent(self, event):
        self.overlay.setGeometry(0, 0, self.width(), self.height())
        super().resizeEvent(event)

    # aufrufen, wenn Screen angezeigt wird
    def refresh(self):
        self._clear_list()
        self.info_label.setText("Lade Cocktails…")

        try:
            cocktails = self.cocktail_model.get_all_cocktails()
            if not cocktails:
                self.info_label.setText("Keine Cocktails gefunden,oida.")
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

    def _add_cocktail_button(self, cocktail_id: int, name: str):
        b = QPushButton(name)
        b.setMinimumHeight(90)
        b.setStyleSheet("font-size: 26px;")
        b.clicked.connect(lambda _, cid=cocktail_id: self.start_mix(cid))
        self.list_layout.addWidget(b)

    def start_mix(self, cocktail_id: int):
        # DB-Teil im UI Thread vorbereiten (thread-sicher)
        try:
            mix_data = self.mix_controller.prepare_mix(cocktail_id)
        except Exception as e:
            self._show_overlay("Fehler!", str(e))
            return

        self._show_overlay("Please wait…\nCocktail wird gemischt", "")

        # Engine-Teil im Worker Thread
        self.thread = QThread()
        #übergeben des MixControllers und der Mixdaten an den Worker
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
        self._show_overlay("Fertig ", "")
        QTimer.singleShot(1500, self._hide_overlay)

    def _mix_failed(self, msg: str):
        self._show_overlay("Fehler!", msg)

    def _show_overlay(self, title: str, details: str):
        self.overlay.setVisible(True)
        self.wait_label.setText(title)
        self.result_label.setText(details)

    def _hide_overlay(self):
        self.overlay.setVisible(False)
