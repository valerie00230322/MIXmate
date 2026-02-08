from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QFrame, QPushButton, QSizePolicy
)


class MenuTile(QFrame):
    clicked = Signal()

    def __init__(self, badge: str, title: str, subtitle: str, accent: str):
        super().__init__()

        # damit QSS background auf QFrame greift
        self.setAttribute(Qt.WA_StyledBackground, True)

        # fürs styling + pressed state
        self.setProperty("role", "tile")
        self.setProperty("accent", accent)
        self.setProperty("down", False)

        self.setCursor(Qt.PointingHandCursor)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(14)

        b = QLabel(badge)
        b.setObjectName("TileBadge")
        b.setAlignment(Qt.AlignCenter)
        b.setFixedSize(54, 54)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        t = QLabel(title)
        t.setObjectName("TileTitle")

        s = QLabel(subtitle)
        s.setObjectName("TileSubtitle")
        s.setWordWrap(True)

        text_col.addWidget(t)
        text_col.addWidget(s)

        arrow = QLabel(">")
        arrow.setObjectName("TileArrow")
        arrow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        arrow.setFixedWidth(18)

        layout.addWidget(b, 0)
        layout.addLayout(text_col, 1)
        layout.addWidget(arrow, 0)

    def _set_down(self, down: bool):
        self.setProperty("down", down)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        self._set_down(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        was_down = bool(self.property("down"))
        self._set_down(False)
        if was_down and self.rect().contains(event.pos()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class HomeScreen(QWidget):
    go_mix = Signal()
    go_status = Signal()
    go_calibration = Signal()
    go_admin = Signal()
    do_exit = Signal()

    def __init__(self):
        super().__init__()
        self.setObjectName("HomeScreen")
        self.setAttribute(Qt.WA_StyledBackground, True)

        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        hero = QFrame()
        hero.setObjectName("HeroCard")
        hero.setAttribute(Qt.WA_StyledBackground, True)

        hero_l = QHBoxLayout(hero)
        hero_l.setContentsMargins(18, 16, 18, 16)
        hero_l.setSpacing(16)

        self.logo = QLabel()
        self.logo.setObjectName("HeroLogo")
        self.logo.setFixedSize(92, 92)
        self.logo.setAlignment(Qt.AlignCenter)
        self._load_logo()

        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        title = QLabel("MIXmate")
        title.setObjectName("HomeTitle")

        subtitle = QLabel("die automatische Schankanlage")
        subtitle.setObjectName("HomeSubtitle")

        self.chip = QLabel("READY")
        self.chip.setObjectName("StatusChip")

        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        text_col.addWidget(self.chip, 0, Qt.AlignLeft)

        hero_l.addWidget(self.logo, 0)
        hero_l.addLayout(text_col, 1)

        root.addWidget(hero, 0)

        menu = QFrame()
        menu.setObjectName("MenuCard")
        menu.setAttribute(Qt.WA_StyledBackground, True)

        menu_l = QVBoxLayout(menu)
        menu_l.setContentsMargins(18, 16, 18, 16)
        menu_l.setSpacing(12)

        menu_title = QLabel("Menü")
        menu_title.setObjectName("SectionTitle")
        menu_l.addWidget(menu_title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(12)

        t_mix = MenuTile("MIX", "Cocktail mischen", "Rezept auswählen und starten", accent="teal")
        t_status = MenuTile("LIVE", "Status (live)", "Busy, Position, Homing, Fehler", accent="blue")
        t_cal = MenuTile("CAL", "Kalibrierung", "Flowrate / Pumpen einstellen", accent="purple")
        t_admin = MenuTile("ADMIN", "Admin", "Zutaten, Cocktails, Rezepte", accent="orange")

        t_mix.clicked.connect(self.go_mix.emit)
        t_status.clicked.connect(self.go_status.emit)
        t_cal.clicked.connect(self.go_calibration.emit)
        t_admin.clicked.connect(self.go_admin.emit)

        grid.addWidget(t_mix, 0, 0)
        grid.addWidget(t_status, 0, 1)
        grid.addWidget(t_cal, 1, 0)
        grid.addWidget(t_admin, 1, 1)

        menu_l.addLayout(grid)

        footer = QHBoxLayout()
        footer.setSpacing(12)

        hint = QLabel("Touch-optimiert  Raspberry Pi")
        hint.setObjectName("HintLabel")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        exit_btn = QPushButton("Exit")
        exit_btn.setObjectName("ExitButton")
        exit_btn.setMinimumHeight(52)
        exit_btn.clicked.connect(self.do_exit.emit)

        footer.addWidget(hint, 1)
        footer.addWidget(exit_btn, 0)

        menu_l.addLayout(footer)

        root.addWidget(menu, 1)

    def _load_logo(self) -> None:
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "mixmateLogo by chat.png"

        if logo_path.exists():
            pix = QPixmap(str(logo_path))
            if not pix.isNull():
                self.logo.setPixmap(
                    pix.scaled(
                        self.logo.width(),
                        self.logo.height(),
                        Qt.KeepAspectRatio,
                        Qt.SmoothTransformation,
                    )
                )
                return

        self.logo.setText("MIX\nmate")
        self.logo.setObjectName("LogoFallback")
