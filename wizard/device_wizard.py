from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QLineEdit, QLabel,
    QDoubleSpinBox, QCheckBox, QTableWidget,
    QTableWidgetItem, QPushButton
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
        self.kind.addItems(["BOTON", "INTERRUPTOR", "SALIDA DIGITAL", "POTENCIOMETRO", "SELECTOR"])

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
        self.setSubTitle("Introduce el pin/canal y el nombre/parámetro.")

        self.pin_label = QLabel("Pin:")
        self.pin = QSpinBox()
        self.pin.setRange(0, 255)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Ejemplo: PZB_ACK, SIFA_LED, SPEED...")

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        self.pin.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.name.textChanged.connect(lambda _text: self.completeChanged.emit())

        form = QFormLayout()
        form.addRow(self.pin_label, self.pin)
        form.addRow("Nombre / parámetro:", self.name)
        form.addRow("", self.warning)
        self.setLayout(form)

    def initializePage(self):
        kind = self.wizard().page(PAGE_TYPE).kind.currentText()

        if kind == "POTENCIOMETRO":
            self.pin_label.setText("Canal ADS:")
            self.pin.setRange(0, 7)
            self.pin.setPrefix("ADS")
        else:
            self.pin_label.setText("Pin:")
            self.pin.setRange(0, 255)
            self.pin.setPrefix("")

        visible = kind != "SELECTOR"
        self.pin_label.setVisible(visible)
        self.pin.setVisible(visible)
        self.completeChanged.emit()

    def get_pin_token(self):
        kind = self.wizard().page(PAGE_TYPE).kind.currentText()
        if kind == "POTENCIOMETRO":
            return f"ADS{self.pin.value()}"
        return self.pin.value()

    def isComplete(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).kind.currentText()
        name = self.name.text().strip()
        pin_token = self.get_pin_token()

        if not name:
            self.warning.setText("Introduce un nombre/parámetro.")
            return False

        if kind != "SELECTOR" and hasattr(wizard, "is_pin_used"):
            if wizard.is_pin_used(pin_token):
                self.warning.setText(f"El pin/canal {pin_token} ya está en uso.")
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
        pin_token = wizard.page(PAGE_BASIC).get_pin_token()
        self.tester.set_target(pin_token, kind)

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

        self.current_pot_value = None
        self.pending_capture_row = None

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
        self.send_mode.addItems(["CONTINUO", "CAMBIO", "INTERVALO", "MANUAL"])

        self.interval = QSpinBox()
        self.interval.setRange(0, 60000)
        self.interval.setValue(200)

        self.as_integer = QCheckBox("Enviar como entero")
        self.as_integer.setChecked(True)

        self.enable_notches = QCheckBox("Usar muescas / posiciones fijas")
        self.enable_notches.setChecked(False)

        self.live_value_label = QLabel("Valor actual POT: --")

        self.notch_count = QSpinBox()
        self.notch_count.setRange(2, 32)
        self.notch_count.setValue(3)

        self.notch_table = QTableWidget()
        self.notch_table.setColumnCount(3)
        self.notch_table.setHorizontalHeaderLabels([
            "Valor POT",
            "Capturar",
            "Valor salida"
        ])
        self.notch_table.horizontalHeader().setStretchLastSection(True)

        self.notch_warning = QLabel("")
        self.notch_warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.notch_warning.setWordWrap(True)

        self.enable_notches.stateChanged.connect(self.on_notch_enabled_changed)
        self.notch_count.valueChanged.connect(self.rebuild_notch_table)
        self.notch_table.itemChanged.connect(lambda _item: self.completeChanged.emit())

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
        self.form.addRow("", self.enable_notches)
        self.form.addRow("", self.live_value_label)
        self.form.addRow("Nº muescas:", self.notch_count)
        self.form.addRow("Tabla muescas:", self.notch_table)
        self.form.addRow("", self.notch_warning)
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

        if is_pot:
            self.rebuild_notch_table()

        rows_for_pot = {
            "Entrada mínima:",
            "Entrada máxima:",
            "Salida mínima:",
            "Salida máxima:",
            "Suavizado:",
            "Modo envío:",
            "Intervalo:",
            "Nº muescas:",
            "Tabla muescas:",
        }

        rows_for_normal = {"Valor 1:", "Valor 2:"}

        for i in range(self.form.rowCount()):
            label_item = self.form.itemAt(i, QFormLayout.LabelRole)
            field_item = self.form.itemAt(i, QFormLayout.FieldRole)

            label = label_item.widget() if label_item else None
            field = field_item.widget() if field_item else None
            text = label.text() if label else ""

            if text in rows_for_pot:
                visible = is_pot

                if field in (self.notch_count, self.notch_table):
                    visible = is_pot and self.enable_notches.isChecked()

                if label:
                    label.setVisible(visible)
                if field:
                    field.setVisible(visible)

            elif text in rows_for_normal:
                if label:
                    label.setVisible(not is_pot)
                if field:
                    field.setVisible(not is_pot)

            else:
                if field == self.as_integer:
                    field.setVisible(is_pot)
                elif field == self.enable_notches:
                    field.setVisible(is_pot)
                elif field == self.live_value_label:
                    field.setVisible(is_pot and self.enable_notches.isChecked())
                elif field == self.notch_warning:
                    field.setVisible(is_pot and self.enable_notches.isChecked())

        self.completeChanged.emit()

    def on_notch_enabled_changed(self):
        self.initializePage()
        self.completeChanged.emit()

    def rebuild_notch_table(self):
        count = self.notch_count.value()

        old = []
        for row in range(self.notch_table.rowCount()):
            pot_item = self.notch_table.item(row, 0)
            out_item = self.notch_table.item(row, 2)

            old.append([
                pot_item.text() if pot_item else "",
                out_item.text() if out_item else "",
            ])

        self.notch_table.blockSignals(True)
        self.notch_table.setRowCount(count)

        in_min = self.min_in.value()
        in_max = self.max_in.value()
        out_min = self.min_out.value()
        out_max = self.max_out.value()

        span_in = max(1, in_max - in_min)
        span_out = out_max - out_min

        for row in range(count):
            if row < len(old):
                pot_text, out_text = old[row]
            else:
                if count > 1:
                    pot_value = int(in_min + (span_in * row / (count - 1)))
                    out_value = out_min + (span_out * row / (count - 1))
                else:
                    pot_value = in_min
                    out_value = out_min

                pot_text = str(pot_value)
                out_text = f"{out_value:g}"

            self.notch_table.setItem(row, 0, QTableWidgetItem(pot_text))
            self.notch_table.setItem(row, 2, QTableWidgetItem(out_text))

            btn_capture = QPushButton("Capturar")
            btn_capture.clicked.connect(lambda _=False, r=row: self.capture_notch_value(r))
            self.notch_table.setCellWidget(row, 1, btn_capture)

        self.notch_table.blockSignals(False)
        self.completeChanged.emit()

    def capture_notch_value(self, row):
        wizard = self.wizard()
        pin_token = wizard.page(PAGE_BASIC).get_pin_token()

        self.pending_capture_row = row
        self.notch_warning.setText(f"Esperando valor actual de {pin_token}...")

        wizard.connection.send_command(f"IO.READ {pin_token} POT")

    def set_live_pot_value(self, value):
        self.current_pot_value = int(value)
        self.live_value_label.setText(f"Valor actual POT: {self.current_pot_value}")

        if self.pending_capture_row is None:
            return

        row = self.pending_capture_row
        self.pending_capture_row = None

        if row < 0 or row >= self.notch_table.rowCount():
            return

        self.notch_table.setItem(
            row,
            0,
            QTableWidgetItem(str(self.current_pot_value))
        )

        self.notch_warning.setText("")
        self.completeChanged.emit()

    def get_notches(self):
        if not self.enable_notches.isChecked():
            return []

        notches = []

        for row in range(self.notch_table.rowCount()):
            pot_item = self.notch_table.item(row, 0)
            value_item = self.notch_table.item(row, 2)

            pot_value = int(pot_item.text().strip())
            out_value = float(value_item.text().strip())

            notches.append((pot_value, out_value))

        return notches

    def validate_notches(self):
        if not self.enable_notches.isChecked():
            self.notch_warning.setText("")
            return True

        used_values = set()

        for row in range(self.notch_table.rowCount()):
            pot_item = self.notch_table.item(row, 0)
            value_item = self.notch_table.item(row, 2)

            if not pot_item or not pot_item.text().strip():
                self.notch_warning.setText(f"Falta el valor POT en muesca {row + 1}.")
                return False

            if not value_item or not value_item.text().strip():
                self.notch_warning.setText(f"Falta valor de salida en muesca {row + 1}.")
                return False

            try:
                pot_value = int(pot_item.text().strip())
                float(value_item.text().strip())
            except Exception:
                self.notch_warning.setText(f"Valores inválidos en muesca {row + 1}.")
                return False

            if pot_value < 0 or pot_value > 65535:
                self.notch_warning.setText(f"Valor POT fuera de rango en muesca {row + 1}.")
                return False

            if pot_value in used_values:
                self.notch_warning.setText(f"Valor POT repetido en muesca {row + 1}.")
                return False

            used_values.add(pot_value)

        self.notch_warning.setText("")
        return True

    def isComplete(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).kind.currentText()

        if kind == "POT":
            return self.validate_notches()

        return True

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
                "Tipo: SELECTOR",
                f"Nombre: {basic.name.text().strip()}",
                "",
                "Contactos:"
            ]

            for pin, value in contacts:
                lines.append(f"  Pin {pin} -> {value:g}")

            self.label.setText("\n".join(lines))
            return

        if kind == "POT":
            lines = [
                f"Tipo: {kind}",
                f"Pin: {basic.get_pin_token()}",
                f"Nombre: {basic.name.text()}",
                "",
                f"Entrada: {options.min_in.value()} - {options.max_in.value()}",
                f"Salida: {options.min_out.value()} - {options.max_out.value()}",
                f"Suavizado: {options.smooth.value()}",
                f"Modo envío: {options.send_mode.currentText()}",
                f"Intervalo: {options.interval.value()}",
                f"Formato: {'INT' if options.as_integer.isChecked() else 'FLOAT'}",
            ]

            if options.enable_notches.isChecked():
                lines.append("")
                lines.append("Muescas:")
                for pot_value, out_value in options.get_notches():
                    lines.append(f"  POT {pot_value} -> {out_value:g}")

            self.label.setText("\n".join(lines))
            return

        text = (
            f"Tipo: {kind}\n"
            f"Pin: {basic.get_pin_token()}\n"
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
        self.resize(760, 560)
        self.setMinimumSize(680, 480)

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
        self.connection.received.connect(self.on_received)

    def on_received(self, text):
        parts = text.strip().split()

        if len(parts) < 4:
            return

        if parts[0] != "IO.STATE":
            return

        try:
            pin_token = parts[1]
            kind = parts[2].upper()
            value = int(float(parts[3]))
        except Exception:
            return

        if kind != "POT":
            return

        current_pin = str(self.page(PAGE_BASIC).get_pin_token())

        if str(pin_token) != current_pin:
            return

        options = self.page(PAGE_OPTIONS)

        if hasattr(options, "set_live_pot_value"):
            options.set_live_pot_value(value)

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

    def is_pin_used(self, pin):
        return any(str(device.pin) == str(pin) for device in self.devices)

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

        device = Device(
            kind=kind,
            pin=basic.get_pin_token(),
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

        if kind == "POT":
            device.pot_notches_enabled = options.enable_notches.isChecked()
            device.pot_notches = options.get_notches()

        return [device]

    def get_device(self):
        devices = self.get_devices()
        return devices[0] if devices else None