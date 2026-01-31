# Inhalt der Hauptseite
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame, QSizePolicy
)

#ist wie consoleview aufgebaut-Navigation über Signale
class HomeScreen(QWidget):
    #ist zm navigieren da
    go_mix = Signal()
    go_status = Signal()
    go_calibration = Signal()
    go_admin = Signal()
    do_exit = Signal()

    def __init__(self):
        super().__init__()

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 28, 28, 28)
        root.setSpacing(18)

        #Lögo und Titel
        header = QFrame()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(18, 18, 18, 18)
        header_layout.setSpacing(18)

        self.logo_label = QLabel()
        self.logo_label.setFixedSize(140, 140)
        self.logo_label.setAlignment(Qt.AlignCenter)
        self._load_logo()

        title_box = QVBoxLayout()
        title_box.setSpacing(6)

        title = QLabel("MIXmate")
        title.setObjectName("TitleLabel")
        title.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        subtitle = QLabel("die automatische Schankanlage")
        subtitle.setObjectName("SubtitleLabel")
        subtitle.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        title_box.addWidget(title)
        title_box.addWidget(subtitle)

        header_layout.addWidget(self.logo_label, 0)
        header_layout.addLayout(title_box, 1)

        root.addWidget(header)

        # Menü
        menu_card = QFrame()
        menu_card.setObjectName("Card")
        menu_layout = QVBoxLayout(menu_card)
        menu_layout.setContentsMargins(18, 18, 18, 18)
        menu_layout.setSpacing(14)

        menu_title = QLabel("Menü")
        menu_title.setObjectName("SectionTitle")
        menu_layout.addWidget(menu_title)

        # Buttons 
        menu_layout.addWidget(self._menu_button("Cocktail mischen", self.go_mix.emit))
        menu_layout.addWidget(self._menu_button("Cocktail-Status (live)", self.go_status.emit))
        menu_layout.addWidget(self._menu_button(" Kalibrierung", self.go_calibration.emit))
        menu_layout.addWidget(self._menu_button("Admin", self.go_admin.emit))

        
        spacer = QFrame()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        menu_layout.addWidget(spacer)

        # Exit-Button unten
        exit_btn = self._menu_button("Exit", self.do_exit.emit)
        exit_btn.setObjectName("DangerButton")
        menu_layout.addWidget(exit_btn)

        root.addWidget(menu_card, 1)

        
        hint = QLabel("Tipp: Große Buttons für Touch • Fullscreen im Mixer-Betrieb")
        hint.setObjectName("HintLabel")
        hint.setAlignment(Qt.AlignCenter)
        root.addWidget(hint)

    def _menu_button(self, text: str, on_click) -> QPushButton:
        btn = QPushButton(text)
        btn.setMinimumHeight(84)  # große Buttons für Touchbedienung
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(on_click)
        btn.setObjectName("MenuButton")
        return btn

    def _load_logo(self) -> None:
        #TODO:Logo aus assets laden bzw designen zuerst
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "mixmate_logo.png"

        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                pix = pix.scaled(
                    self.logo_label.width(),
                    self.logo_label.height(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self.logo_label.setPixmap(pix)
                self.logo_label.setText("")
                self.logo_label.setObjectName("Logo")
                return

        # Fallback, falls Logo nicht lädt: Text-Logo
        self.logo_label.setText("MIX\nmate")
        self.logo_label.setObjectName("LogoFallback")
