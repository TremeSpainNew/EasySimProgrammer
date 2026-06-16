import json
from pathlib import Path

from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QLabel, QTableWidget,
    QTableWidgetItem
)
from PySide6.QtCore import Qt

from models.device import Device


PAGE_SELECT_MODULE = 0
PAGE_EDIT_IO = 1
PAGE_SUMMARY = 2


class SelectModulePage(QWizardPage):
    def __init__(self, modules_dir="modules"):
        super().__init__()

        self.modules_dir = Path(modules_dir)

        self.setTitle("Módulo IO")
        self.setSubTitle("Selecciona una plantilla de módulo IO.")

        self.combo = QComboBox()
        self.description = QLabel("")
        self.description.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Módulo:"))
        layout.addWidget(self.combo)
        layout.addWidget(self.description)
        layout.addStretch()
        self.setLayout(layout)

        self.combo.currentIndexChanged.connect(self.on_module_changed)

    def initializePage(self):
        self.combo.clear()

        self.modules_dir.mkdir(exist_ok=True)

        for path in sorted(self.modules_dir.glob("*.json")):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                name = data.get("name", path.stem)
                self.combo.addItem(name, str(path))

            except Exception:
                pass

        self.on_module_changed()

    def on_module_changed(self):
        path = self.current_path()

        if not path:
            self.description.setText("No hay módulos JSON disponibles.")
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.description.setText(data.get("description", ""))

        except Exception as e:
            self.description.setText(f"Error leyendo módulo: {e}")

    def current_path(self):
        if self.combo.currentIndex() < 0:
            return None

        return self.combo.currentData()

    def isComplete(self):
        return self.combo.currentIndex() >= 0

    def nextId(self):
        return PAGE_EDIT_IO


class EditIOPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Asignación de entradas/salidas")
        self.setSubTitle("Revisa o modifica los pines del módulo.")

        self.pin_base = QSpinBox()
        self.pin_base.setRange(0, 255)
        self.pin_base.setValue(0)
        self.pin_base.valueChanged.connect(self.apply_pin_base)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Tipo",
            "Nombre",
            "Pin",
            "Valor 1",
            "Valor 2"
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemChanged.connect(lambda _item: self.completeChanged.emit())

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        form = QFormLayout()
        form.addRow("Pin base:", self.pin_base)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.table)
        layout.addWidget(self.warning)
        self.setLayout(layout)

        self.raw_devices = []

    def initializePage(self):
        wizard = self.wizard()
        path = wizard.page(PAGE_SELECT_MODULE).current_path()

        self.raw_devices = []

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.raw_devices = data.get("devices", [])

        self.rebuild_table()

    def rebuild_table(self):
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.raw_devices))

        base = self.pin_base.value()

        for row, item in enumerate(self.raw_devices):
            kind = item.get("kind", "BUTTON")
            name = item.get("name", "")
            pin = item.get("pin", item.get("offset", row))
            value1 = item.get("value1", 1)
            value2 = item.get("value2", 0)

            if "offset" in item:
                pin = base + int(item["offset"])

            self.table.setItem(row, 0, QTableWidgetItem(str(kind)))
            self.table.setItem(row, 1, QTableWidgetItem(str(name)))
            self.table.setItem(row, 2, QTableWidgetItem(str(pin)))
            self.table.setItem(row, 3, QTableWidgetItem(str(value1)))
            self.table.setItem(row, 4, QTableWidgetItem(str(value2)))

        self.table.blockSignals(False)
        self.completeChanged.emit()

    def apply_pin_base(self):
        has_offsets = any("offset" in item for item in self.raw_devices)

        if has_offsets:
            self.rebuild_table()

    def get_rows(self):
        rows = []

        for row in range(self.table.rowCount()):
            kind = self.table.item(row, 0).text().strip().upper()
            name = self.table.item(row, 1).text().strip()
            pin = int(self.table.item(row, 2).text().strip())
            value1 = float(self.table.item(row, 3).text().strip())
            value2 = float(self.table.item(row, 4).text().strip())

            rows.append({
                "kind": kind,
                "name": name,
                "pin": pin,
                "value1": value1,
                "value2": value2
            })

        return rows

    def isComplete(self):
        used_pins = set()

        try:
            for row in range(self.table.rowCount()):
                kind_item = self.table.item(row, 0)
                name_item = self.table.item(row, 1)
                pin_item = self.table.item(row, 2)

                if not kind_item or not kind_item.text().strip():
                    self.warning.setText(f"Falta tipo en fila {row + 1}.")
                    return False

                if not name_item or not name_item.text().strip():
                    self.warning.setText(f"Falta nombre en fila {row + 1}.")
                    return False

                if not pin_item or not pin_item.text().strip():
                    self.warning.setText(f"Falta pin en fila {row + 1}.")
                    return False

                pin = int(pin_item.text().strip())

                if pin < 0 or pin > 255:
                    self.warning.setText(f"Pin fuera de rango en fila {row + 1}.")
                    return False

                if pin in used_pins:
                    self.warning.setText(f"Pin {pin} repetido dentro del módulo.")
                    return False

                used_pins.add(pin)

                if hasattr(self.wizard(), "is_pin_used"):
                    if self.wizard().is_pin_used(pin):
                        self.warning.setText(f"El pin {pin} ya está en uso.")
                        return False

            self.warning.setText("")
            return True

        except Exception:
            self.warning.setText("Hay valores inválidos en la tabla.")
            return False

    def nextId(self):
        return PAGE_SUMMARY


class SummaryPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Resumen")
        self.setSubTitle("Revisa el módulo antes de añadirlo.")

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setStyleSheet(
            "font-family: Consolas, monospace;"
            "font-size: 12px;"
            "padding: 10px;"
            "background: rgba(127, 127, 127, 30);"
            "border-radius: 6px;"
        )

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initializePage(self):
        rows = self.wizard().page(PAGE_EDIT_IO).get_rows()

        lines = ["Dispositivos que se añadirán:", ""]

        for item in rows:
            lines.append(
                f"{item['kind']:8} pin {item['pin']:3}  "
                f"{item['name']}  "
                f"({item['value1']:g}, {item['value2']:g})"
            )

        self.label.setText("\n".join(lines))

    def nextId(self):
        return -1


class ModuleWizard(QWizard):
    def __init__(self, devices=None, modules_dir="modules", parent=None):
        super().__init__(parent)

        self.devices = devices or []
        self.modules_dir = modules_dir

        self.setWindowTitle("Asistente de módulo IO")
        self.resize(780, 560)
        self.setMinimumSize(700, 480)

        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)
        self.setOption(QWizard.HaveHelpButton, False)

        self.setPage(PAGE_SELECT_MODULE, SelectModulePage(modules_dir))
        self.setPage(PAGE_EDIT_IO, EditIOPage())
        self.setPage(PAGE_SUMMARY, SummaryPage())

        self.setStartId(PAGE_SELECT_MODULE)

    def is_pin_used(self, pin):
        return any(str(device.pin) == str(pin) for device in self.devices)

    def get_devices(self):
        rows = self.page(PAGE_EDIT_IO).get_rows()
        devices = []

        for item in rows:
            devices.append(
                Device(
                    kind=item["kind"],
                    pin=item["pin"],
                    name=item["name"],
                    value1=item["value1"],
                    value2=item["value2"],
                )
            )

        return devices