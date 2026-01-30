# Navigation der Hauptfenster-Screens
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget
from PySide6.QtGui import QPalette, QColor
from View.qt.screens.home_screen import HomeScreen

self.home = HomeScreen()
self.home.go_mix.connect(self.show_cocktails)          # Mix-Screen
self.home.go_status.connect(self.show_status)          # Status-Screen
self.home.go_calibration.connect(self.show_calibration)
self.home.go_admin.connect(self.show_admin)
self.home.do_exit.connect(self.close)                  

self.stack.addWidget(self.home)
