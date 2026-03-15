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

        # fuers styling + pressed state
        self.setProperty("role", "tile")
        self.setProperty("accent", accent)
        self.setProperty("down", False)
        self.setAttribute(Qt.WA_Hover, True)

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
        self._subtitle_label = s
        self._base_subtitle = subtitle

        text_col.addWidget(t)
        text_col.addWidget(s)

        arrow = QLabel(">")
        arrow.setObjectName("TileArrow")
        arrow.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        arrow.setFixedWidth(18)

        layout.addWidget(b, 0)
        layout.addLayout(text_col, 1)
        layout.addWidget(arrow, 0)

    def setEnabled(self, enabled: bool) -> None:
        super().setEnabled(enabled)
        self.setCursor(Qt.PointingHandCursor if enabled else Qt.ForbiddenCursor)

    def set_blocked_reason(self, reason: str | None) -> None:
        if reason:
            self.setToolTip(reason)
        else:
            self.setToolTip("")

    def _set_down(self, down: bool):
        self.setProperty("down", down)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()

    def mousePressEvent(self, event):
        if not self.isEnabled():
            event.ignore()
            return
        self._set_down(True)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if not self.isEnabled():
            event.ignore()
            return
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
        self.chip.setProperty("state", "ready")
        # Regal-Status soll visuell gleich wie der READY-Chip aussehen.
        self.regal_chip = QLabel("REGAL NICHT ERKANNT")
        self.regal_chip.setObjectName("StatusChip")
        self.regal_chip.setProperty("state", "not-ready")

        text_col.addWidget(title)
        text_col.addWidget(subtitle)
        text_col.addWidget(self.chip, 0, Qt.AlignLeft)
        text_col.addWidget(self.regal_chip, 0, Qt.AlignLeft)

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

        self.t_mix = MenuTile("MIX", "Cocktail mischen", "Rezept auswaehlen und starten", accent="teal")
        self.t_status = MenuTile("LIVE", "Status (live)", "Busy, Position, Homing, Fehler", accent="blue")
        self.t_cal = MenuTile("CAL", "Kalibrierung", "Flowrate / Pumpen einstellen", accent="purple")
        self.t_admin = MenuTile("ADMIN", "Admin", "Zutaten, Cocktails, Rezepte", accent="orange")

        self.t_mix.clicked.connect(self.go_mix.emit)
        self.t_status.clicked.connect(self.go_status.emit)
        self.t_cal.clicked.connect(self.go_calibration.emit)
        self.t_admin.clicked.connect(self.go_admin.emit)

        grid.addWidget(self.t_mix, 0, 0)
        grid.addWidget(self.t_status, 0, 1)
        grid.addWidget(self.t_cal, 1, 0)
        grid.addWidget(self.t_admin, 1, 1)

        menu_l.addLayout(grid)

        footer = QHBoxLayout()
        footer.setSpacing(12)
        """
        Hier koennte ein Copyright-Hinweis oder aehnliches hin kommen.
        hint = QLabel("Touch-optimiert  Raspberry Pi")
        hint.setObjectName("HintLabel")
        hint.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        """
        exit_btn = QPushButton("Exit")
        exit_btn.setObjectName("ExitButton")
        exit_btn.setMinimumHeight(52)
        exit_btn.clicked.connect(self.do_exit.emit)

        # footer.addWidget(hint, 1)
        footer.addWidget(exit_btn, 0)

        menu_l.addLayout(footer)

        root.addWidget(menu, 1)

    def _load_logo(self) -> None:
        assets_dir = Path(__file__).resolve().parents[1] / "assets"
        logo_path = assets_dir / "mixmateLogo by chatBIG.png"

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

    def set_ready(self, ready: bool) -> None:
        if ready:
            self.chip.setText("READY")
            self.chip.setProperty("state", "ready")
        else:
            self.chip.setText("NOT READY")
            self.chip.setProperty("state", "not-ready")

        self.chip.style().unpolish(self.chip)
        self.chip.style().polish(self.chip)
        self.chip.update()

    def set_hardware_actions_enabled(self, enabled: bool) -> None:
        self.t_mix.setEnabled(enabled)
        self.t_status.setEnabled(enabled)
        self.t_cal.setEnabled(enabled)
        # Admin bleibt immer verfuegbar (DB-/Setup-Bereich ohne I2C).
        self.t_admin.setEnabled(True)
        self.t_admin.set_blocked_reason(None)

        reason = None if enabled else "Nur mit Hardware/I2C verfuegbar"
        self.t_mix.set_blocked_reason(reason)
        self.t_status.set_blocked_reason(reason)
        self.t_cal.set_blocked_reason(reason)

    def set_regal_connected(self, connected: bool) -> None:
        if connected:
            self.regal_chip.setText("REGAL ERKANNT")
            self.regal_chip.setProperty("state", "ready")
        else:
            self.regal_chip.setText("REGAL NICHT ERKANNT")
            self.regal_chip.setProperty("state", "not-ready")
        self.regal_chip.style().unpolish(self.regal_chip)
        self.regal_chip.style().polish(self.regal_chip)
        self.regal_chip.update()
