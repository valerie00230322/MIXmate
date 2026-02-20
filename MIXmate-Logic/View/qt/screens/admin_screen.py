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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QTableWidget, QTableWidgetItem, QMessageBox,
    QInputDialog, QDialog, QDialogButtonBox, QFormLayout, QLineEdit
)


def _msg_error(parent: QWidget, text: str):
    QMessageBox.critical(parent, "Fehler", text)


def _msg_info(parent: QWidget, text: str):
    QMessageBox.information(parent, "Info", text)


def _confirm(parent: QWidget, title: str, text: str) -> bool:
    return QMessageBox.question(parent, title, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes


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

        self.stack.addWidget(self.page_menu)
        self.stack.addWidget(self.page_ingredients)
        self.stack.addWidget(self.page_cocktails)
        self.stack.addWidget(self.page_pumps)

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

    def _card(self) -> QFrame:
        c = QFrame()
        c.setObjectName("Card")
        return c

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

        for b in (btn_ing, btn_cock, btn_pumps):
            b.setProperty("role", "cocktail")   # reused style: großer button
            b.setMinimumHeight(70)

        btn_ing.clicked.connect(self.show_ingredients)
        btn_cock.clicked.connect(self.show_cocktails)
        btn_pumps.clicked.connect(self.show_pumps)

        c.addWidget(btn_ing)
        c.addWidget(btn_cock)
        c.addWidget(btn_pumps)
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
        self.tbl_ingredients.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_ingredients.setEditTriggers(QTableWidget.NoEditTriggers)
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
        self.tbl_cocktails.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_cocktails.setEditTriggers(QTableWidget.NoEditTriggers)
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

        for b in (btn_refresh, btn_add, btn_delete, btn_assign):
            b.setProperty("role", "nav")

        top.addWidget(title)
        top.addStretch(1)
        top.addWidget(btn_refresh)
        top.addWidget(btn_add)
        top.addWidget(btn_delete)
        top.addWidget(btn_assign)
        top.addWidget(btn_back)

        c.addLayout(top)

        self.tbl_pumps = QTableWidget(0, 4)
        self.tbl_pumps.setHorizontalHeaderLabels(["pump_number", "ingredient_id", "flow_rate_ml_s", "position_steps"])
        self.tbl_pumps.setSelectionBehavior(QTableWidget.SelectRows)
        self.tbl_pumps.setEditTriggers(QTableWidget.NoEditTriggers)
        c.addWidget(self.tbl_pumps, 1)

        lay.addWidget(card, 1)

        btn_refresh.clicked.connect(self.refresh_pumps)
        btn_add.clicked.connect(self.add_pump)
        btn_delete.clicked.connect(self.delete_pump)
        btn_assign.clicked.connect(self.assign_ingredient)

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
        pump_number, ok = QInputDialog.getInt(self, "Neue Pumpe", "pump_number:", 1, 1, 9999, 1)
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
