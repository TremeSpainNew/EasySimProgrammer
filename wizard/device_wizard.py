from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QLineEdit, QLabel,
    QDoubleSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem
)
from PySide6.QtCore import Qt

from models.device import Device
from live_pin_tester import LivePinTester


PAGE_TYPE = 0
PAGE_BASIC = 1
PAGE_TEST = 2
PAGE_OPTIONS = 3
PAGE_SELECTOR = 4
PAGE_SUMMARY = 5


class TypePage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Tipo de elemento")
        self.setSubTitle("Selecciona qué tipo de control quieres configurar.")

        self.kind = QComboBox()
        self.kind.addItems([
            "BUTTON",
            "SWITCH",
            "OUTPUT",
            "POT",
            "SELECTOR"
        ])

        label = QLabel("Tipo de elemento:")
        label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addWidget(self.kind)
        layout.addStretch()

        self.setLayout(layout)

    def nextId(self):
        return PAGE_BASIC


class BasicPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Datos básicos")
        self.setSubTitle("Introduce el pin y el nombre/parámetro.")

        self.pin = QSpinBox()
        self.pin.setRange(0, 255)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Ejemplo: PZB_ACK, SIFA_LED, REVERSER...")

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        self.pin.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.name.textChanged.connect(lambda _text: self.completeChanged.emit())

        form = QFormLayout()
        form.addRow("Pin:", self.pin)
        form.addRow("Nombre / parámetro:", self.name)
        form.addRow("", self.warning)

        self.setLayout(form)

    def initializePage(self):
        kind = self.wizard().page(PAGE_TYPE).kind.currentText()
        self.pin.setVisible(kind != "SELECTOR")

        label_item = self.layout().itemAt(0, QFormLayout.LabelRole)
        if label_item and label_item.widget():
            label_item.widget().setVisible(kind != "SELECTOR")

        self.completeChanged.emit()

    def isComplete(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).kind.currentText()

        name = self.name.text().strip()
        pin = self.pin.value()

        if not name:
            self.warning.setText("Introduce un nombre/parámetro.")
            return False

        if kind != "SELECTOR":
            if wizard and hasattr(wizard, "is_pin_used"):
                if wizard.is_pin_used(pin):
                    self.warning.setText(f"El pin {pin} ya está en uso.")
                    return False

        self.warning.setText("")
        return True

    def nextId(self):
        kind = self.wizard().page(PAGE_TYPE).kind.currentText()

        if kind == "SELECTOR":
            return PAGE_SELECTOR

        return PAGE_TEST


class TestPage(QWizardPage):
    def __init__(self, connection):
        super().__init__()

        self.setTitle("Comprobar pin")
        self.setSubTitle("Comprueba físicamente que el pin seleccionado es correcto.")

        self.tester = LivePinTester(connection)

        self.info = QLabel(
            "Pulsa el botón, cambia el interruptor, mueve el potenciómetro "
            "o activa la salida para comprobar que has elegido el pin correcto."
        )
        self.info.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.info)
        layout.addWidget(self.tester)

        self.setLayout(layout)

    def initializePage(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).kind.currentText()
        pin = wizard.page(PAGE_BASIC).pin.value()
        self.tester.set_target(pin, kind)

    def cleanupPage(self):
        self.stop_tester()

    def stop_tester(self):
        self.tester.stop()

    def get_calibration(self):
        return self.tester.get_calibration()

    def nextId(self):
        return PAGE_OPTIONS


class OptionsPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Opciones")
        self.setSubTitle("Configura los valores y comportamiento del elemento.")

        self.value1 = QDoubleSpinBox()
        self.value1.setRange(-999999, 999999)
        self.value1.setDecimals(3)
        self.value1.setValue(0)

        self.value2 = QDoubleSpinBox()
        self.value2.setRange(-999999, 999999)
        self.value2.setDecimals(3)
        self.value2.setValue(1)

        self.min_in = QSpinBox()
        self.min_in.setRange(0, 65535)
        self.min_in.setValue(0)

        self.max_in = QSpinBox()
        self.max_in.setRange(0, 65535)
        self.max_in.setValue(4095)

        self.min_out = QDoubleSpinBox()
        self.min_out.setRange(-999999, 999999)
        self.min_out.setDecimals(3)
        self.min_out.setValue(0)

        self.max_out = QDoubleSpinBox()
        self.max_out.setRange(-999999, 999999)
        self.max_out.setDecimals(3)
        self.max_out.setValue(100)

        self.smooth = QDoubleSpinBox()
        self.smooth.setRange(0, 1)
        self.smooth.setDecimals(3)
        self.smooth.setSingleStep(0.01)
        self.smooth.setValue(0.10)

        self.send_mode = QComboBox()
        self.send_mode.addItems([
            "CONTINUO",
            "CAMBIO",
            "INTERVALO",
            "MANUAL"
        ])

        self.interval = QSpinBox()
        self.interval.setRange(0, 60000)
        self.interval.setValue(200)

        self.as_integer = QCheckBox("Enviar como entero")
        self.as_integer.setChecked(True)

        self.form = QFormLayout()
        self.form.addRow("Valor 1:", self.value1)
        self.form.addRow("Valor 2:", self.value2)
        self.form.addRow("Entrada mínima:", self.min_in)
        self.form.addRow("Entrada máxima:", self.max_in)
        self.form.addRow("Salida mínima:", self.min_out)
        self.form.addRow("Salida máxima:", self.max_out)
        self.form.addRow("Suavizado:", self.smooth)
        self.form.addRow("Modo envío:", self.send_mode)
        self.form.addRow("Intervalo:", self.interval)
        self.form.addRow("", self.as_integer)

        self.setLayout(self.form)

    def initializePage(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).kind.currentText()

        is_pot = kind == "POT"

        test_page = wizard.page(PAGE_TEST)
        cal_min, cal_max = test_page.get_calibration()

        if is_pot and cal_min is not None and cal_max is not None:
            self.min_in.setValue(int(cal_min))
            self.max_in.setValue(int(cal_max))

        rows_for_pot = {
            "Entrada mínima:",
            "Entrada máxima:",
            "Salida mínima:",
            "Salida máxima:",
            "Suavizado:",
            "Modo envío:",
            "Intervalo:",
        }

        rows_for_normal = {
            "Valor 1:",
            "Valor 2:",
        }

        for i in range(self.form.rowCount()):
            label_item = self.form.itemAt(i, QFormLayout.LabelRole)
            field_item = self.form.itemAt(i, QFormLayout.FieldRole)

            label = label_item.widget() if label_item else None
            field = field_item.widget() if field_item else None

            text = label.text() if label else ""

            if text in rows_for_pot:
                if label:
                    label.setVisible(is_pot)
                if field:
                    field.setVisible(is_pot)

            elif text in rows_for_normal:
                if label:
                    label.setVisible(not is_pot)
                if field:
                    field.setVisible(not is_pot)

            else:
                if field == self.as_integer:
                    field.setVisible(is_pot)

    def nextId(self):
        return PAGE_SUMMARY


class SelectorPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Contactos del selector")
        self.setSubTitle("Define cuántos contactos tiene el selector y qué valor envía cada pin.")

        self.contact_count = QSpinBox()
        self.contact_count.setRange(2, 32)
        self.contact_count.setValue(3)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Pin", "Valor"])
        self.table.horizontalHeader().setStretchLastSection(True)

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        self.contact_count.valueChanged.connect(self.rebuild_table)
        self.table.itemChanged.connect(lambda _item: self.completeChanged.emit())

        form = QFormLayout()
        form.addRow("Número de contactos:", self.contact_count)

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.table)
        layout.addWidget(self.warning)

        self.setLayout(layout)

    def initializePage(self):
        self.rebuild_table()
        self.completeChanged.emit()

    def rebuild_table(self):
        count = self.contact_count.value()
        old = []

        for row in range(self.table.rowCount()):
            pin_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)
            old.append((
                pin_item.text() if pin_item else "",
                value_item.text() if value_item else "",
            ))

        self.table.blockSignals(True)
        self.table.setRowCount(count)

        for row in range(count):
            pin_text = old[row][0] if row < len(old) else ""
            value_text = old[row][1] if row < len(old) else str(row)

            if count == 3 and row >= len(old):
                defaults = ["-1", "0", "1"]
                value_text = defaults[row]

            self.table.setItem(row, 0, QTableWidgetItem(pin_text))
            self.table.setItem(row, 1, QTableWidgetItem(value_text))

        self.table.blockSignals(False)
        self.completeChanged.emit()

    def get_contacts(self):
        contacts = []

        for row in range(self.table.rowCount()):
            pin_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)

            pin = int(pin_item.text().strip())
            value = float(value_item.text().strip())

            contacts.append((pin, value))

        return contacts

    def isComplete(self):
        wizard = self.wizard()
        used_pins = set()

        for row in range(self.table.rowCount()):
            pin_item = self.table.item(row, 0)
            value_item = self.table.item(row, 1)

            if not pin_item or not pin_item.text().strip():
                self.warning.setText(f"Falta el pin en la fila {row + 1}.")
                return False

            if not value_item or not value_item.text().strip():
                self.warning.setText(f"Falta el valor en la fila {row + 1}.")
                return False

            try:
                pin = int(pin_item.text().strip())
                float(value_item.text().strip())
            except Exception:
                self.warning.setText(f"Pin o valor inválido en la fila {row + 1}.")
                return False

            if pin < 0 or pin > 255:
                self.warning.setText(f"Pin fuera de rango en la fila {row + 1}.")
                return False

            if pin in used_pins:
                self.warning.setText(f"El pin {pin} está repetido en el selector.")
                return False

            used_pins.add(pin)

            if wizard and hasattr(wizard, "is_pin_used"):
                if wizard.is_pin_used(pin):
                    self.warning.setText(f"El pin {pin} ya está en uso.")
                    return False

        self.warning.setText("")
        return True

    def nextId(self):
        return PAGE_SUMMARY


class SummaryPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Resumen")
        self.setSubTitle("Revisa la configuración antes de añadirla.")

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
        wizard = self.wizard()

        kind = wizard.page(PAGE_TYPE).kind.currentText()
        basic = wizard.page(PAGE_BASIC)
        options = wizard.page(PAGE_OPTIONS)

        if kind == "SELECTOR":
            contacts = wizard.page(PAGE_SELECTOR).get_contacts()

            lines = [
                f"Tipo: SELECTOR",
                f"Nombre: {basic.name.text().strip()}",
                "",
                "Contactos:"
            ]

            for pin, value in contacts:
                lines.append(f"  Pin {pin} -> {value:g}")

            self.label.setText("\n".join(lines))
            return

        if kind == "POT":
            text = (
                f"Tipo: {kind}\n"
                f"Pin: {basic.pin.value()}\n"
                f"Nombre: {basic.name.text()}\n\n"
                f"Entrada: {options.min_in.value()} - {options.max_in.value()}\n"
                f"Salida: {options.min_out.value()} - {options.max_out.value()}\n"
                f"Suavizado: {options.smooth.value()}\n"
                f"Modo envío: {options.send_mode.currentText()}\n"
                f"Intervalo: {options.interval.value()}\n"
                f"Formato: {'INT' if options.as_integer.isChecked() else 'FLOAT'}"
            )
        else:
            text = (
                f"Tipo: {kind}\n"
                f"Pin: {basic.pin.value()}\n"
                f"Nombre: {basic.name.text()}\n\n"
                f"Valor 1: {options.value1.value()}\n"
                f"Valor 2: {options.value2.value()}"
            )

        self.label.setText(text)

    def nextId(self):
        return -1


class DeviceWizard(QWizard):
    def __init__(self, connection, devices=None, parent=None):
        super().__init__(parent)

        self.connection = connection
        self.devices = devices or []

        self.setWindowTitle("Asistente EasySim")
        self.resize(600, 420)
        self.setMinimumSize(560, 380)

        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)
        self.setOption(QWizard.HaveHelpButton, False)

        self.setPage(PAGE_TYPE, TypePage())
        self.setPage(PAGE_BASIC, BasicPage())
        self.setPage(PAGE_TEST, TestPage(connection))
        self.setPage(PAGE_OPTIONS, OptionsPage())
        self.setPage(PAGE_SELECTOR, SelectorPage())
        self.setPage(PAGE_SUMMARY, SummaryPage())

        self.setStartId(PAGE_TYPE)

    def stop_test_page(self):
        page = self.page(PAGE_TEST)
        if page and hasattr(page, "stop_tester"):
            page.stop_tester()

    def accept(self):
        self.stop_test_page()
        super().accept()

    def reject(self):
        self.stop_test_page()
        super().reject()

    def closeEvent(self, event):
        self.stop_test_page()
        super().closeEvent(event)

    def is_pin_used(self, pin: int):
        return any(device.pin == pin for device in self.devices)

    def get_devices(self):
        kind = self.page(PAGE_TYPE).kind.currentText()
        basic = self.page(PAGE_BASIC)

        if kind == "SELECTOR":
            name = basic.name.text().strip()
            contacts = self.page(PAGE_SELECTOR).get_contacts()

            devices = []

            for pin, value in contacts:
                devices.append(
                    Device(
                        kind="SELECTOR",
                        pin=pin,
                        name=name,
                        value1=value,
                        value2=0,
                        min_out=value,
                        max_out=0,
                    )
                )

            return devices

        options = self.page(PAGE_OPTIONS)

        return [
            Device(
                kind=kind,
                pin=basic.pin.value(),
                name=basic.name.text().strip(),

                value1=options.value1.value(),
                value2=options.value2.value(),

                min_in=options.min_in.value(),
                max_in=options.max_in.value(),
                min_out=options.min_out.value(),
                max_out=options.max_out.value(),

                smooth=options.smooth.value(),
                send_mode=options.send_mode.currentText(),
                interval=options.interval.value(),
                as_integer=options.as_integer.isChecked(),
            )
        ]

    def get_device(self):
        devices = self.get_devices()
        return devices[0] if devices else None