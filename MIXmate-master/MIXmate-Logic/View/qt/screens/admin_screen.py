""" Console Features
        ("\n=== ADMIN ===")
            print("1) Zutaten verwalten")
            print("2) Cocktails verwalten")
            print("3) Pumpen verwalten")
            print("4) Zurück")
            

            1)Zutaten

            print("\n--- Zutaten ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Umbenennen")
            print("4) Zurück")

            2) Cocktails
            print("\n--- Cocktails ---")
            print("1) Anzeigen")
            print("2) Hinzufügen")
            print("3) Löschen")
            print("4) Rezept bearbeiten")
            print("5) Zurück")

            3) Pumpen
            print(f"\n--- Rezept bearbeiten (cocktail_id={cocktail_id}) ---")
            print("1) Rezept anzeigen")
            print("2) Zutat hinzufügen")
            print("3) Zutat ändern (ml / order_index)")
            print("4) Zutat entfernen")
            print("5) Zurück")
            """
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QTableWidget, QTableWidgetItem, QMessageBox,
    QInputDialog, QDialog, QDialogButtonBox, QTextEdit
)
from Services.simulation_trace_service import get_simulation_trace_service


def _msg_error(parent: QWidget, text: str):
    QMessageBox.critical(parent, "Fehler", text)


def _msg_info(parent: QWidget, text: str):
    QMessageBox.information(parent, "Info", text)


def _confirm(parent: QWidget, title: str, text: str) -> bool:
    return QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes


class SimulationTraceDialog(QDialog):
    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setWindowTitle("Simulation I2C Monitor")
        self.resize(820, 480)
        self.trace_service = get_simulation_trace_service()
        self.last_id = 0

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        self.text = QTextEdit(self)
        self.text.setReadOnly(True)
        root.addWidget(self.text, 1)

        actions = QHBoxLayout()
        btn_clear = QPushButton("Leeren", self)
        btn_close = QPushButton("Schließen", self)
        actions.addStretch(1)
        actions.addWidget(btn_clear)
        actions.addWidget(btn_close)
        root.addLayout(actions)

        btn_clear.clicked.connect(self._clear)
        btn_close.clicked.connect(self.accept)

        self.timer = QTimer(self)
        self.timer.setInterval(300)
        self.timer.timeout.connect(self._poll)
        self.timer.start()
        self._poll()

    def _clear(self):
        self.trace_service.clear()
        self.last_id = 0
        self.text.clear()

    def _poll(self):
        items = self.trace_service.get_entries_since(self.last_id)
        if not items:
            return
        for item in items:
            self.text.append(f"[{item['ts']}] {item['message']}")
            self.last_id = int(item["id"])
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())

    def closeEvent(self, event):
        self.timer.stop()
        super().closeEvent(event)


class RecipeEditorDialog(QDialog):
    def __init__(self, parent: QWidget, admin_controller, cocktail_id: int, cocktail_name: str):
        super().__init__(parent)
        self.admin_controller = admin_controller
        self.cocktail_id = cocktail_id

        self.setWindowTitle(f"Rezept bearbeiten: {cocktail_name} (ID {cocktail_id})")
        self.resize(720, 520)

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(12)

        level_row = QHBoxLayout()
        level_row.setSpacing(10)
        self.level_info = QLabel("")
        self.level_info.setObjectName("InfoLabel")
        self.btn_set_level = QPushButton("Glas-Ebene setzen")
        self.btn_set_level.setProperty("role", "nav")
        self.btn_set_level.clicked.connect(self.set_glass_level)
        level_row.addWidget(self.level_info, 1)
        level_row.addWidget(self.btn_set_level)
        root.addLayout(level_row)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["order_index", "ingredient_id", "Zutat", "ml"])
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        root.addWidget(self.table, 1)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self.btn_refresh = QPushButton("Aktualisieren")
        self.btn_add = QPushButton("Hinzufügen")
        self.btn_update = QPushButton("Ändern")
        self.btn_delete = QPushButton("Entfernen")

        btn_row.addWidget(self.btn_refresh)
        btn_row.addWidget(self.btn_add)
        btn_row.addWidget(self.btn_update)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch(1)

        root.addLayout(btn_row)

        box = QDialogButtonBox(QDialogButtonBox.Close)
        box.rejected.connect(self.reject)
        root.addWidget(box)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_add.clicked.connect(self.add_item)
        self.btn_update.clicked.connect(self.update_item)
        self.btn_delete.clicked.connect(self.delete_item)

        self.refresh()

    def _refresh_glass_level_info(self):
        try:
            level = self.admin_controller.get_cocktail_source_level(self.cocktail_id)
        except Exception as e:
            self.level_info.setText(f"Fehler bei Glasebene: {e}")
            return

        if level is None:
            self.level_info.setText("Glasquelle: keine Ebene gesetzt")
        else:
            self.level_info.setText(f"Glasquelle: Ebene {level}")

    def refresh(self):
        try:
            recipe = self.admin_controller.get_recipe(self.cocktail_id)
        except Exception as e:
            _msg_error(self, str(e))
            return

        self.table.setRowCount(0)
        for r in recipe:
            row = self.table.rowCount()
            self.table.insertRow(row)

            self.table.setItem(row, 0, QTableWidgetItem(str(r["order_index"])))
            self.table.setItem(row, 1, QTableWidgetItem(str(r["ingredient_id"])))
            self.table.setItem(row, 2, QTableWidgetItem(str(r["ingredient_name"])))
            self.table.setItem(row, 3, QTableWidgetItem(str(r["amount_ml"])))

        self.table.resizeColumnsToContents()
        self._refresh_glass_level_info()

    def set_glass_level(self):
        try:
            levels = self.admin_controller.list_levels()
        except Exception as e:
            _msg_error(self, str(e))
            return

        if levels:
            options = [str(int(x["levelnumber"])) for x in levels]
            chosen, ok = QInputDialog.getItem(self, "Glas-Ebene", "Ebene:", options, 0, False)
            if not ok:
                return
            levelnumber = int(chosen)
        else:
            levelnumber, ok = QInputDialog.getInt(
                self, "Glas-Ebene", "Ebene (Ganzzahl):", 1, 1, 9999, 1
            )
            if not ok:
                return

        try:
            self.admin_controller.set_cocktail_source_level(self.cocktail_id, levelnumber)
            self._refresh_glass_level_info()
        except Exception as e:
            _msg_error(self, str(e))

    def _selected_row_values(self):
        idx = self.table.currentRow()
        if idx < 0:
            return None
        order_index = int(self.table.item(idx, 0).text())
        ingredient_id = int(self.table.item(idx, 1).text())
        amount_ml = float(self.table.item(idx, 3).text())
        return ingredient_id, amount_ml, order_index

    def add_item(self):
        try:
            ingredients = self.admin_controller.list_ingredients()
        except Exception as e:
            _msg_error(self, str(e))
            return

        if not ingredients:
            _msg_info(self, "Keine Zutaten vorhanden.")
            return

        options = [f"{i['ingredient_id']}: {i['name']}" for i in ingredients]
        chosen, ok = QInputDialog.getItem(self, "Zutat wählen", "Zutat:", options, 0, False)
        if not ok:
            return

        ingredient_id = int(chosen.split(":")[0].strip())

        ml, ok = QInputDialog.getDouble(self, "Menge", "Menge in ml:", 10.0, 0.1, 9999.0, 1)
        if not ok:
            return

        order_index, ok = QInputDialog.getInt(self, "Reihenfolge", "order_index:", 1, 1, 9999, 1)
        if not ok:
            return

        try:
            self.admin_controller.add_recipe_item(self.cocktail_id, ingredient_id, ml, order_index)
            self.refresh()
        except Exception as e:
            _msg_error(self, str(e))

    def update_item(self):
        selected = self._selected_row_values()
        if not selected:
            _msg_info(self, "Bitte zuerst eine Zeile auswählen.")
            return

        ingredient_id, old_ml, old_order = selected

        ml, ok = QInputDialog.getDouble(self, "Menge ändern", "Neue Menge in ml:", old_ml, 0.1, 9999.0, 1)
        if not ok:
            return

        order_index, ok = QInputDialog.getInt(self, "Reihenfolge ändern", "Neuer order_index:", old_order, 1, 9999, 1)
        if not ok:
            return

        try:
            self.admin_controller.update_recipe_item(self.cocktail_id, ingredient_id, ml, order_index)
            self.refresh()
        except Exception as e:
            _msg_error(self, str(e))

    def delete_item(self):
        selected = self._selected_row_values()
        if not selected:
            _msg_info(self, "Bitte zuerst eine Zeile auswählen.")
            return

        ingredient_id, _, _ = selected

        if not _confirm(self, "Entfernen", f"Zutat (ingredient_id={ingredient_id}) wirklich entfernen?"):
            return

        try:
            self.admin_controller.delete_recipe_item(self.cocktail_id, ingredient_id)
            self.refresh()
        except Exception as e:
            _msg_error(self, str(e))


class AdminScreen(QWidget):
    def __init__(self, admin_controller, pump_controller, on_back):
        super().__init__()
        self.setObjectName("AdminScreen")

        self.admin_controller = admin_controller
        self.pump_controller = pump_controller
        self.on_back = on_back
        self.sim_trace_dialog = None

        # Eine zentrale Stack-Navigation statt vieler einzelner Dialoge.
        self.stack = QStackedWidget()

        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(14)

        header = QHBoxLayout()
        header.setSpacing(12)

        back = QPushButton("Zurück")
        back.setProperty("role", "nav")
        back.setMinimumHeight(52)
        back.clicked.connect(self.on_back)

        title = QLabel("Admin")
        title.setObjectName("ScreenTitle")
        title.setAlignment(Qt.AlignCenter)

        header.addWidget(back)
        header.addWidget(title, 1)
        header.addSpacing(back.sizeHint().width())

        root.addLayout(header)
        root.addWidget(self.stack, 1)

        self.page_menu = self._build_menu_page()
        self.page_ingredients = self._build_ingredients_page()
        self.page_cocktails = self._build_cocktails_page()
        self.page_pumps = self._build_pumps_page()
        self.page_setup = self._build_setup_page()
        self.page_mixer_settings = self._build_mixer_settings_page()
        self.page_level_settings = self._build_level_settings_page()

        self.stack.addWidget(self.page_menu)
        self.stack.addWidget(self.page_ingredients)
        self.stack.addWidget(self.page_cocktails)
        self.stack.addWidget(self.page_pumps)
        self.stack.addWidget(self.page_setup)
        self.stack.addWidget(self.page_mixer_settings)
        self.stack.addWidget(self.page_level_settings)

        self.show_menu()

    def show_menu(self):
        self.stack.setCurrentWidget(self.page_menu)

    def show_ingredients(self):
        self.refresh_ingredients()
        self.stack.setCurrentWidget(self.page_ingredients)

    def show_cocktails(self):
        self.refresh_cocktails()
        self.stack.setCurrentWidget(self.page_cocktails)

    def show_pumps(self):
        self.refresh_pumps()
        self.stack.setCurrentWidget(self.page_pumps)

    def show_setup(self):
        self.refresh_setup()
        self.stack.setCurrentWidget(self.page_setup)

    def show_mixer_settings(self):
        # Vor dem Anzeigen immer frisch aus der DB laden.
        self.refresh_setup()
        self.stack.setCurrentWidget(self.page_mixer_settings)

    def show_level_settings(self):
        # Vor dem Anzeigen immer frisch aus der DB laden.
        self.refresh_setup()
        self.stack.setCurrentWidget(self.page_level_settings)

    def _card(self) -> QFrame:
        c = QFrame()
        c.setObjectName("Card")
        return c

    def _style_table(self, table: QTableWidget):
        table.setObjectName("AdminTable")
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setSelectionMode(QTableWidget.SingleSelection)
        table.setWordWrap(False)
        table.setCornerButtonEnabled(False)
        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(40)
        table.horizontalHeader().setStretchLastSection(True)
        table.horizontalHeader().setDefaultAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def _build_menu_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        info = QLabel("Was willst du verwalten?")
        info.setObjectName("InfoLabel")
        c.addWidget(info)

        btn_ing = QPushButton("Zutaten verwalten")
        btn_cock = QPushButton("Cocktails verwalten")
        btn_pumps = QPushButton("Pumpen verwalten")
        btn_setup = QPushButton("System-Setup")

        for b in (btn_ing, btn_cock, btn_pumps, btn_setup):
            b.setProperty("role", "cocktail")   # reused style: großer button
            b.setMinimumHeight(70)

        btn_ing.clicked.connect(self.show_ingredients)
        btn_cock.clicked.connect(self.show_cocktails)
        btn_pumps.clicked.connect(self.show_pumps)
        btn_setup.clicked.connect(self.show_setup)

        c.addWidget(btn_ing)
        c.addWidget(btn_cock)
        c.addWidget(btn_pumps)
        c.addWidget(btn_setup)
        c.addStretch(1)

        lay.addWidget(card, 1)
        return w

    def _build_ingredients_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        title = QLabel("Zutaten")
        title.setObjectName("SectionTitle")

        btn_back = QPushButton("Menü")
        btn_back.setProperty("role", "nav")
        btn_back.clicked.connect(self.show_menu)

        btn_refresh = QPushButton("Aktualisieren")
        btn_add = QPushButton("Hinzufügen")
        btn_rename = QPushButton("Umbenennen")

        for b in (btn_refresh, btn_add, btn_rename):
            b.setProperty("role", "nav")

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_add)
        top.addWidget(btn_rename)
        top.addWidget(btn_back)

        c.addLayout(top)

        self.tbl_ingredients = QTableWidget(0, 2)
        self.tbl_ingredients.setHorizontalHeaderLabels(["ingredient_id", "name"])
        self.tbl_ingredients.setEditTriggers(QTableWidget.NoEditTriggers)
        self._style_table(self.tbl_ingredients)
        c.addWidget(self.tbl_ingredients, 1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_ingredients)
        btn_add.clicked.connect(self.add_ingredient)
        btn_rename.clicked.connect(self.rename_ingredient)

        return w

    def refresh_ingredients(self):
        try:
            items = self.admin_controller.list_ingredients()
        except Exception as e:
            _msg_error(self, str(e))
            return

        self.tbl_ingredients.setRowCount(0)
        for ing in items:
            row = self.tbl_ingredients.rowCount()
            self.tbl_ingredients.insertRow(row)
            self.tbl_ingredients.setItem(row, 0, QTableWidgetItem(str(ing["ingredient_id"])))
            self.tbl_ingredients.setItem(row, 1, QTableWidgetItem(str(ing["name"])))

        self.tbl_ingredients.resizeColumnsToContents()

    def _selected_ingredient_id(self):
        r = self.tbl_ingredients.currentRow()
        if r < 0:
            return None
        return int(self.tbl_ingredients.item(r, 0).text())

    def add_ingredient(self):
        name, ok = QInputDialog.getText(self, "Zutat hinzufügen", "Zutatenname:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return

        try:
            self.admin_controller.add_ingredient(name)
            self.refresh_ingredients()
        except Exception as e:
            _msg_error(self, str(e))

    def rename_ingredient(self):
        ingredient_id = self._selected_ingredient_id()
        if ingredient_id is None:
            _msg_info(self, "Bitte zuerst eine Zutat auswählen.")
            return

        new_name, ok = QInputDialog.getText(self, "Umbenennen", "Neuer Name:")
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name:
            return

        try:
            self.admin_controller.rename_ingredient(ingredient_id, new_name)
            self.refresh_ingredients()
        except Exception as e:
            _msg_error(self, str(e))

    def _build_cocktails_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        title = QLabel("Cocktails")
        title.setObjectName("SectionTitle")

        btn_back = QPushButton("Menü")
        btn_back.setProperty("role", "nav")
        btn_back.clicked.connect(self.show_menu)

        btn_refresh = QPushButton("Aktualisieren")
        btn_add = QPushButton("Hinzufügen")
        btn_delete = QPushButton("Löschen")
        btn_recipe = QPushButton("Rezept bearbeiten")

        for b in (btn_refresh, btn_add, btn_delete, btn_recipe):
            b.setProperty("role", "nav")

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_add)
        top.addWidget(btn_delete)
        top.addWidget(btn_recipe)
        top.addWidget(btn_back)

        c.addLayout(top)

        self.tbl_cocktails = QTableWidget(0, 2)
        self.tbl_cocktails.setHorizontalHeaderLabels(["cocktail_id", "cocktail_name"])
        self.tbl_cocktails.setEditTriggers(QTableWidget.NoEditTriggers)
        self._style_table(self.tbl_cocktails)
        c.addWidget(self.tbl_cocktails, 1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_cocktails)
        btn_add.clicked.connect(self.add_cocktail)
        btn_delete.clicked.connect(self.delete_cocktail)
        btn_recipe.clicked.connect(self.edit_recipe)

        return w

    def refresh_cocktails(self):
        try:
            items = self.admin_controller.list_cocktails()
        except Exception as e:
            _msg_error(self, str(e))
            return

        self.tbl_cocktails.setRowCount(0)
        for co in items:
            row = self.tbl_cocktails.rowCount()
            self.tbl_cocktails.insertRow(row)
            self.tbl_cocktails.setItem(row, 0, QTableWidgetItem(str(co["cocktail_id"])))
            self.tbl_cocktails.setItem(row, 1, QTableWidgetItem(str(co["cocktail_name"])))

        self.tbl_cocktails.resizeColumnsToContents()

    def _selected_cocktail(self):
        r = self.tbl_cocktails.currentRow()
        if r < 0:
            return None
        cid = int(self.tbl_cocktails.item(r, 0).text())
        name = str(self.tbl_cocktails.item(r, 1).text())
        return cid, name

    def add_cocktail(self):
        name, ok = QInputDialog.getText(self, "Cocktail hinzufügen", "Cocktailname:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return

        try:
            new_id = self.admin_controller.add_cocktail(name)
            self.refresh_cocktails()
            if new_id is not None:
                _msg_info(self, f"Gespeichert. Neue cocktail_id: {new_id}")
        except Exception as e:
            _msg_error(self, str(e))

    def delete_cocktail(self):
        sel = self._selected_cocktail()
        if not sel:
            _msg_info(self, "Bitte zuerst einen Cocktail auswählen.")
            return

        cocktail_id, cocktail_name = sel
        if not _confirm(self, "Löschen", f"'{cocktail_name}' wirklich löschen?"):
            return

        try:
            self.admin_controller.delete_cocktail(cocktail_id)
            self.refresh_cocktails()
        except Exception as e:
            _msg_error(self, str(e))

    def edit_recipe(self):
        sel = self._selected_cocktail()
        if not sel:
            _msg_info(self, "Bitte zuerst einen Cocktail auswählen.")
            return

        cocktail_id, cocktail_name = sel
        dlg = RecipeEditorDialog(self, self.admin_controller, cocktail_id, cocktail_name)
        dlg.exec()

    def _build_pumps_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        title = QLabel("Pumpen")
        title.setObjectName("SectionTitle")

        btn_back = QPushButton("Menü")
        btn_back.setProperty("role", "nav")
        btn_back.clicked.connect(self.show_menu)

        btn_refresh = QPushButton("Aktualisieren")
        btn_add = QPushButton("Neue Pumpe")
        btn_delete = QPushButton("Pumpe löschen")
        btn_assign = QPushButton("Zutat zuweisen")
        btn_distance = QPushButton("Abstand setzen")

        for b in (btn_refresh, btn_add, btn_delete, btn_assign, btn_distance):
            b.setProperty("role", "nav")

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_add)
        top.addWidget(btn_delete)
        top.addWidget(btn_assign)
        top.addWidget(btn_distance)
        top.addWidget(btn_back)

        c.addLayout(top)

        self.tbl_pumps = QTableWidget(0, 4)
        self.tbl_pumps.setHorizontalHeaderLabels(["pump_number", "ingredient_id", "flow_rate_ml_s", "position_steps"])
        self.tbl_pumps.setEditTriggers(QTableWidget.NoEditTriggers)
        self._style_table(self.tbl_pumps)
        c.addWidget(self.tbl_pumps, 1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_pumps)
        btn_add.clicked.connect(self.add_pump)
        btn_delete.clicked.connect(self.delete_pump)
        btn_assign.clicked.connect(self.assign_ingredient)
        btn_distance.clicked.connect(self.set_pump_distance)

        return w

    def refresh_pumps(self):
        try:
            pumps = self.pump_controller.list_pumps()
        except Exception as e:
            _msg_error(self, str(e))
            return

        self.tbl_pumps.setRowCount(0)
        for p in pumps:
            row = self.tbl_pumps.rowCount()
            self.tbl_pumps.insertRow(row)
            self.tbl_pumps.setItem(row, 0, QTableWidgetItem(str(p["pump_number"])))
            self.tbl_pumps.setItem(row, 1, QTableWidgetItem(str(p["ingredient_id"])))
            self.tbl_pumps.setItem(row, 2, QTableWidgetItem(str(p["flow_rate_ml_s"])))
            self.tbl_pumps.setItem(row, 3, QTableWidgetItem(str(p["position_steps"])))

        self.tbl_pumps.resizeColumnsToContents()

    def _selected_pump_number(self):
        r = self.tbl_pumps.currentRow()
        if r < 0:
            return None
        return int(self.tbl_pumps.item(r, 0).text())

    def add_pump(self):
        pump_number, ok = QInputDialog.getInt(self, "Neue Pumpe", "pump_number (1-10):", 1, 1, 10, 1)
        if not ok:
            return

        try:
            self.admin_controller.add_pump(pump_number)
            self.refresh_pumps()
            _msg_info(self, "Pumpe angelegt. Position/Flow-Rate machst du dann in der Kalibrierung.")
        except Exception as e:
            _msg_error(self, str(e))

    def delete_pump(self):
        pump_number = self._selected_pump_number()
        if pump_number is None:
            _msg_info(self, "Bitte zuerst eine Pumpe auswählen.")
            return

        if not _confirm(self, "Löschen", f"Pumpe {pump_number} wirklich löschen?"):
            return

        try:
            self.admin_controller.delete_pump(pump_number)
            self.refresh_pumps()
        except Exception as e:
            _msg_error(self, str(e))

    def assign_ingredient(self):
        pump_number = self._selected_pump_number()
        if pump_number is None:
            _msg_info(self, "Bitte zuerst eine Pumpe auswählen.")
            return

        try:
            ingredients = self.admin_controller.list_ingredients()
        except Exception as e:
            _msg_error(self, str(e))
            return

        if not ingredients:
            _msg_info(self, "Keine Zutaten vorhanden.")
            return

        options = [f"{i['ingredient_id']}: {i['name']}" for i in ingredients]
        chosen, ok = QInputDialog.getItem(self, "Zutat zuweisen", "Zutat:", options, 0, False)
        if not ok:
            return

        ingredient_id = int(chosen.split(":")[0].strip())

        try:
            self.pump_controller.assign_ingredient(pump_number, ingredient_id)
            self.refresh_pumps()
            _msg_info(self, "Gespeichert.")
        except Exception as e:
            _msg_error(self, str(e))

    def set_pump_distance(self):
        pump_number = self._selected_pump_number()
        if pump_number is None:
            _msg_info(self, "Bitte zuerst eine Pumpe auswählen.")
            return

        current_steps = 0
        row = self.tbl_pumps.currentRow()
        if row >= 0 and self.tbl_pumps.item(row, 3) is not None:
            try:
                current_steps = int(float(self.tbl_pumps.item(row, 3).text()))
            except Exception:
                current_steps = 0

        new_steps, ok = QInputDialog.getInt(
            self,
            "Pumpenabstand",
            f"Neue Position (steps) für Pumpe {pump_number}:",
            current_steps,
            0,
            1000000,
            1,
        )
        if not ok:
            return

        try:
            self.admin_controller.set_pump_distance(pump_number, int(new_steps))
            self.refresh_pumps()
            _msg_info(self, "Pumpenabstand gespeichert.")
        except Exception as e:
            _msg_error(self, str(e))

    def _build_setup_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)

        title = QLabel("System-Setup")
        title.setObjectName("SectionTitle")

        btn_back = QPushButton("Menü")
        btn_back.setProperty("role", "nav")
        btn_back.clicked.connect(self.show_menu)

        btn_refresh = QPushButton("Aktualisieren")
        btn_mixer = QPushButton("Mixer")
        btn_levels = QPushButton("Ebenen")
        btn_toggle_sim = QPushButton("Simulation EIN/AUS")
        btn_show_sim = QPushButton("Simulation-Monitor")

        for b in (btn_refresh, btn_toggle_sim, btn_show_sim):
            b.setProperty("role", "nav")
        for b in (btn_mixer, btn_levels):
            b.setProperty("role", "cocktail")
            b.setMinimumHeight(84)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_back)
        c.addLayout(top)

        info = QLabel("Wähle einen Bereich:")
        info.setObjectName("InfoLabel")
        c.addWidget(info)

        # Zentrale Einstiege: von hier geht es in die Detailseiten.
        c.addWidget(btn_mixer)
        c.addWidget(btn_levels)

        sim_row = QHBoxLayout()
        sim_row.setSpacing(10)
        sim_row.addWidget(btn_toggle_sim)
        sim_row.addWidget(btn_show_sim)
        sim_row.addStretch(1)
        c.addLayout(sim_row)

        self.lbl_sim_mode = QLabel("-")
        self.lbl_sim_mode.setObjectName("InfoLabel")
        c.addWidget(self.lbl_sim_mode)
        c.addStretch(1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_setup)
        btn_mixer.clicked.connect(self.show_mixer_settings)
        btn_levels.clicked.connect(self.show_level_settings)
        btn_toggle_sim.clicked.connect(self.toggle_simulation_mode)
        btn_show_sim.clicked.connect(self.open_simulation_monitor)

        return w

    def _build_mixer_settings_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        title = QLabel("Mixer-Einstellungen")
        title.setObjectName("SectionTitle")

        btn_back_setup = QPushButton("Zur Setup-Auswahl")
        btn_back_setup.setProperty("role", "nav")
        btn_back_setup.clicked.connect(self.show_setup)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_back_setup)
        c.addLayout(top)

        # Alle Mixer-Parameter auf einer Seite gesammelt.
        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)

        btn_set_mixer = QPushButton("Mixerhöhe setzen")
        btn_set_mixer_ausschub = QPushButton("Mixer-Ausschub setzen")
        btn_set_mixer_direction = QPushButton("Mixer-Richtung setzen")
        btn_set_wait = QPushButton("Warteposition setzen")
        btn_set_safe_home = QPushButton("Sichere Homing-Höhe setzen")
        btn_set_load_unload = QPushButton("Beladen/Entladen-Position setzen")
        btn_refresh = QPushButton("Aktualisieren")
        for b in (
            btn_set_mixer,
            btn_set_mixer_ausschub,
            btn_set_mixer_direction,
            btn_set_wait,
            btn_set_safe_home,
            btn_set_load_unload,
            btn_refresh,
        ):
            b.setProperty("role", "nav")

        action_buttons = [
            btn_set_mixer,
            btn_set_mixer_ausschub,
            btn_set_mixer_direction,
            btn_set_wait,
            btn_set_safe_home,
            btn_set_load_unload,
            btn_refresh,
        ]
        for i, b in enumerate(action_buttons):
            actions.addWidget(b, i // 3, i % 3)
        c.addLayout(actions)

        self.lbl_mixer_height = QLabel("-")
        self.lbl_mixer_ausschub = QLabel("-")
        self.lbl_mixer_direction = QLabel("-")
        self.lbl_waiting_position = QLabel("-")
        self.lbl_homing_safe_height = QLabel("-")
        self.lbl_load_unload_position = QLabel("-")
        for lbl in (
            self.lbl_mixer_height,
            self.lbl_mixer_ausschub,
            self.lbl_mixer_direction,
            self.lbl_waiting_position,
            self.lbl_homing_safe_height,
            self.lbl_load_unload_position,
        ):
            lbl.setObjectName("InfoLabel")
            c.addWidget(lbl)

        c.addStretch(1)
        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_setup)
        btn_set_mixer.clicked.connect(self.set_mixer_height)
        btn_set_mixer_ausschub.clicked.connect(self.set_mixer_ausschub_distance)
        btn_set_mixer_direction.clicked.connect(self.set_mixer_direction)
        btn_set_wait.clicked.connect(self.set_waiting_position)
        btn_set_safe_home.clicked.connect(self.set_homing_safe_height)
        btn_set_load_unload.clicked.connect(self.set_load_unload_position)

        return w

    def _build_level_settings_page(self) -> QWidget:
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(12)

        card = self._card()
        c = QVBoxLayout(card)
        c.setContentsMargins(18, 18, 18, 18)
        c.setSpacing(12)

        top = QHBoxLayout()
        top.setSpacing(10)
        title = QLabel("Ebenen-Einstellungen")
        title.setObjectName("SectionTitle")

        btn_back_setup = QPushButton("Zur Setup-Auswahl")
        btn_back_setup.setProperty("role", "nav")
        btn_back_setup.clicked.connect(self.show_setup)

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_back_setup)
        c.addLayout(top)

        # Ebenen-Verwaltung inklusive Tabelle und Aktionen.
        actions = QGridLayout()
        actions.setHorizontalSpacing(10)
        actions.setVerticalSpacing(10)

        btn_set_level_ausschub = QPushButton("Ebenen-Ausschub setzen")
        btn_set_level_direction = QPushButton("Ebenenrichtung setzen")
        btn_set_level_height = QPushButton("Ebenenhöhe setzen")
        btn_add_level = QPushButton("Ebene hinzufügen")
        btn_delete_level = QPushButton("Ebene löschen")
        btn_refresh = QPushButton("Aktualisieren")
        for b in (
            btn_set_level_ausschub,
            btn_set_level_direction,
            btn_set_level_height,
            btn_add_level,
            btn_delete_level,
            btn_refresh,
        ):
            b.setProperty("role", "nav")

        level_buttons = [
            btn_set_level_ausschub,
            btn_set_level_direction,
            btn_set_level_height,
            btn_add_level,
            btn_delete_level,
            btn_refresh,
        ]
        for i, b in enumerate(level_buttons):
            actions.addWidget(b, i // 3, i % 3)
        c.addLayout(actions)

        self.tbl_level_heights = QTableWidget(0, 4)
        self.tbl_level_heights.setHorizontalHeaderLabels(["levelnumber", "height_mm", "ausschub_mm", "richtung"])
        self.tbl_level_heights.setEditTriggers(QTableWidget.NoEditTriggers)
        self._style_table(self.tbl_level_heights)
        c.addWidget(self.tbl_level_heights, 1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_setup)
        btn_set_level_ausschub.clicked.connect(self.set_level_ausschub_distance)
        btn_set_level_height.clicked.connect(self.set_level_height)
        btn_set_level_direction.clicked.connect(self.set_level_direction)
        btn_add_level.clicked.connect(self.add_level)
        btn_delete_level.clicked.connect(self.delete_level)

        return w

    def refresh_setup(self):
        try:
            mixer_h = self.admin_controller.get_mixer_height()
            mixer_ausschub = self.admin_controller.get_mixer_ausschub_distance()
            mixer_direction = self.admin_controller.get_mixer_direction()
            wait_pos = self.admin_controller.get_waiting_position()
            homing_safe_h = self.admin_controller.get_homing_safe_height()
            load_unload_pos = self.admin_controller.get_load_unload_position()
            sim_mode = self.admin_controller.get_simulation_mode()
            levels = self.admin_controller.list_levels()
        except Exception as e:
            _msg_error(self, str(e))
            return

        # Ein Refresh befuellt beide Unterseiten (Mixer + Ebenen) gleichzeitig.
        self.lbl_mixer_height.setText(
            f"Mixerhöhe: {'-' if mixer_h is None else f'{float(mixer_h):.2f} mm'}"
        )
        self.lbl_mixer_ausschub.setText(
            f"Mixer-Ausschub: {'-' if mixer_ausschub is None else f'{float(mixer_ausschub):.2f} mm'}"
        )
        self.lbl_mixer_direction.setText(
            f"Mixer-Richtung: {'links' if bool(mixer_direction) else 'rechts'}"
            if mixer_direction is not None
            else "Mixer-Richtung: -"
        )
        self.lbl_waiting_position.setText(
            f"Warteposition: {'-' if wait_pos is None else f'{float(wait_pos):.2f} mm'}"
        )
        self.lbl_homing_safe_height.setText(
            f"Sichere Homing-Höhe: {'-' if homing_safe_h is None else f'{float(homing_safe_h):.2f} mm'}"
        )
        self.lbl_load_unload_position.setText(
            f"Beladen/Entladen-Position: {'-' if load_unload_pos is None else f'{float(load_unload_pos):.2f} mm'}"
        )
        self.lbl_sim_mode.setText(
            f"Simulation: {'AKTIV' if sim_mode else 'INAKTIV'}"
        )
        self.tbl_level_heights.setRowCount(0)
        for lv in levels:
            levelnumber = int(lv["levelnumber"])
            height = self.admin_controller.get_level_height(levelnumber)
            level_ausschub = self.admin_controller.get_level_ausschub_distance(levelnumber)
            level_direction = self.admin_controller.get_level_direction(levelnumber)
            if level_direction is None:
                level_direction = True

            row = self.tbl_level_heights.rowCount()
            self.tbl_level_heights.insertRow(row)
            self.tbl_level_heights.setItem(row, 0, QTableWidgetItem(str(levelnumber)))
            self.tbl_level_heights.setItem(
                row, 1, QTableWidgetItem("-" if height is None else f"{float(height):.2f}")
            )
            self.tbl_level_heights.setItem(
                row, 2, QTableWidgetItem("-" if level_ausschub is None else f"{float(level_ausschub):.2f}")
            )
            self.tbl_level_heights.setItem(
                row, 3, QTableWidgetItem("links" if bool(level_direction) else "rechts")
            )

        self.tbl_level_heights.resizeColumnsToContents()

    def set_mixer_height(self):
        current = self.admin_controller.get_mixer_height()
        val, ok = QInputDialog.getDouble(
            self, "Mixerhöhe", "Mixerhöhe in mm:", 0.0 if current is None else float(current), 0.0, 99999.0, 2
        )
        if not ok:
            return
        try:
            self.admin_controller.set_mixer_height(float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_mixer_ausschub_distance(self):
        current = self.admin_controller.get_mixer_ausschub_distance()
        val, ok = QInputDialog.getDouble(
            self,
            "Mixer-Ausschub",
            "Ausschubdistanz in mm:",
            0.0 if current is None else float(current),
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_mixer_ausschub_distance(float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_mixer_direction(self):
        current = self.admin_controller.get_mixer_direction()
        if current is None:
            current = True
        options = ["links", "rechts"]
        default_idx = 0 if bool(current) else 1
        chosen, ok = QInputDialog.getItem(
            self,
            "Mixer-Richtung",
            "Richtung:",
            options,
            default_idx,
            False,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_mixer_direction(chosen == "links")
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_waiting_position(self):
        current = self.admin_controller.get_waiting_position()
        val, ok = QInputDialog.getDouble(
            self, "Warteposition", "Warteposition in mm:", 0.0 if current is None else float(current), 0.0, 99999.0, 2
        )
        if not ok:
            return
        try:
            self.admin_controller.set_waiting_position(float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_homing_safe_height(self):
        current = self.admin_controller.get_homing_safe_height()
        val, ok = QInputDialog.getDouble(
            self,
            "Sichere Homing-Höhe",
            "Höhe in mm:",
            0.0 if current is None else float(current),
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_homing_safe_height(float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_load_unload_position(self):
        current = self.admin_controller.get_load_unload_position()
        val, ok = QInputDialog.getDouble(
            self,
            "Beladen/Entladen-Position",
            "Position in mm:",
            0.0 if current is None else float(current),
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_load_unload_position(float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_level_ausschub_distance(self):
        row = self.tbl_level_heights.currentRow()
        if row < 0:
            _msg_info(self, "Bitte zuerst eine Ebene auswählen.")
            return

        levelnumber = int(self.tbl_level_heights.item(row, 0).text())
        current = self.admin_controller.get_level_ausschub_distance(levelnumber)
        val, ok = QInputDialog.getDouble(
            self,
            "Ebene-Ausschubdistanz",
            f"Ausschubdistanz für Ebene {levelnumber} in mm:",
            0.0 if current is None else float(current),
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_level_ausschub_distance(levelnumber, float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_level_height(self):
        row = self.tbl_level_heights.currentRow()
        if row < 0:
            _msg_info(self, "Bitte zuerst eine Ebene auswählen.")
            return

        levelnumber = int(self.tbl_level_heights.item(row, 0).text())
        current = self.admin_controller.get_level_height(levelnumber)
        val, ok = QInputDialog.getDouble(
            self,
            "Ebenenhöhe",
            f"Höhe für Ebene {levelnumber} in mm:",
            0.0 if current is None else float(current),
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return
        try:
            self.admin_controller.set_level_height(levelnumber, float(val))
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def set_level_direction(self):
        row = self.tbl_level_heights.currentRow()
        if row < 0:
            _msg_info(self, "Bitte zuerst eine Ebene auswählen.")
            return

        levelnumber = int(self.tbl_level_heights.item(row, 0).text())
        current = self.admin_controller.get_level_direction(levelnumber)
        if current is None:
            current = True

        options = ["links", "rechts"]
        default_idx = 0 if bool(current) else 1
        chosen, ok = QInputDialog.getItem(
            self,
            "Ebenenrichtung",
            f"Richtung für Ebene {levelnumber}:",
            options,
            default_idx,
            False,
        )
        if not ok:
            return

        try:
            self.admin_controller.set_level_direction(levelnumber, chosen == "links")
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def delete_level(self):
        row = self.tbl_level_heights.currentRow()
        if row < 0:
            _msg_info(self, "Bitte zuerst eine Ebene auswählen.")
            return

        levelnumber = int(self.tbl_level_heights.item(row, 0).text())
        if not _confirm(self, "Ebene löschen", f"Ebene {levelnumber} wirklich löschen?"):
            return

        try:
            self.admin_controller.delete_level(levelnumber)
            self.refresh_setup()
        except Exception as e:
            _msg_error(self, str(e))

    def add_level(self):
        ext_mm, ok = QInputDialog.getDouble(
            self,
            "Ebene hinzufügen",
            "Extension-Distanz (mm):",
            0.0,
            0.0,
            99999.0,
            2,
        )
        if not ok:
            return

        try:
            new_level = self.admin_controller.add_level(float(ext_mm))
            self.refresh_setup()
            _msg_info(self, f"Ebene {new_level} wurde angelegt.")
        except Exception as e:
            _msg_error(self, str(e))

    def toggle_simulation_mode(self):
        try:
            current = bool(self.admin_controller.get_simulation_mode())
            new_state = not current
            self.admin_controller.set_simulation_mode(new_state)
            self.refresh_setup()
            _msg_info(self, f"Simulation ist jetzt {'AKTIV' if new_state else 'INAKTIV'}.")
        except Exception as e:
            _msg_error(self, str(e))

    def open_simulation_monitor(self):
        if self.sim_trace_dialog is None or not self.sim_trace_dialog.isVisible():
            self.sim_trace_dialog = SimulationTraceDialog(self)
            self.sim_trace_dialog.show()
            self.sim_trace_dialog.raise_()
            self.sim_trace_dialog.activateWindow()
            return
        self.sim_trace_dialog.raise_()
        self.sim_trace_dialog.activateWindow()



