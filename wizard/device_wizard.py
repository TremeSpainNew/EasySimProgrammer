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

KIND_LABELS = {
    "BUTTON": "Pulsador",
    "SWITCH": "Interruptor",
    "OUTPUT": "Salida Digital",
    "POT": "Potenciometro",
    "SELECTOR": "Selector",
    "CANBUS": "CAN bus",
}


def kind_label(kind: str) -> str:
    return KIND_LABELS.get(str(kind).upper(), str(kind))


class TypePage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Tipo de elemento")
        self.setSubTitle("Selecciona qué tipo de control quieres configurar.")

        self.kind = QComboBox()
        self.kind.addItem(kind_label("BUTTON"), "BUTTON")
        self.kind.addItem(kind_label("SWITCH"), "SWITCH")
        self.kind.addItem(kind_label("OUTPUT"), "OUTPUT")
        self.kind.addItem(kind_label("POT"), "POT")
        self.kind.addItem(kind_label("SELECTOR"), "SELECTOR")
        self.kind.addItem(kind_label("CANBUS"), "CANBUS")

        label = QLabel("Tipo de elemento:")
        label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.addStretch()
        layout.addWidget(label)
        layout.addWidget(self.kind)
        layout.addStretch()

        self.setLayout(layout)

    def current_kind(self):
        return self.kind.currentData() or self.kind.currentText()

    def initializePage(self):
        wizard = self.wizard()
        device = getattr(wizard, "existing_device", None)

        if not device:
            self.kind.setEnabled(True)
            return

        index = self.kind.findData(str(device.kind).upper())
        if index >= 0:
            self.kind.setCurrentIndex(index)

        self.kind.setEnabled(False)

    def nextId(self):
        return PAGE_BASIC


class BasicPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Datos básicos")
        self.setSubTitle("Introduce el pin/canal y el parámetro.")

        self.pin_label = QLabel("Pin:")

        self.pin = QSpinBox()
        self.pin.setRange(0, 255)

        self.can_kind = QComboBox()
        self.can_kind.addItem(kind_label("BUTTON"), "BUTTON")
        self.can_kind.addItem(kind_label("SWITCH"), "SWITCH")
        self.can_kind.addItem(kind_label("OUTPUT"), "OUTPUT")

        self.can_node = QSpinBox()
        self.can_node.setRange(0, 255)

        self.can_channel = QSpinBox()
        self.can_channel.setRange(0, 255)

        self.name = QComboBox()
        self.name.setEditable(True)
        self.name.setInsertPolicy(QComboBox.NoInsert)
        self.name.lineEdit().setPlaceholderText(
            "Ejemplo: controller::throttle, asfa::reconocer..."
        )

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        self.pin.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.can_kind.currentTextChanged.connect(self.on_can_kind_changed)
        self.can_node.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.can_channel.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.name.currentTextChanged.connect(lambda _text: self.completeChanged.emit())
        self.name.lineEdit().textChanged.connect(lambda _text: self.completeChanged.emit())

        self.form = QFormLayout()
        self.form.addRow(self.pin_label, self.pin)
        self.form.addRow("Tipo CAN:", self.can_kind)
        self.form.addRow("Nodo CAN:", self.can_node)
        self.form.addRow("Canal CAN:", self.can_channel)
        self.form.addRow("Parámetro:", self.name)
        self.form.addRow("", self.warning)

        self.setLayout(self.form)
        self._prefilled = False

    def current_parameter_kind(self):
        kind = self.wizard().page(PAGE_TYPE).current_kind()

        if kind != "CANBUS":
            return kind

        return self.can_kind.currentData() or self.can_kind.currentText()

    def refresh_catalog(self):
        catalog = getattr(self.wizard(), "parameter_catalog", None)

        if not catalog:
            return

        current = self.name.currentText().strip()

        self.name.blockSignals(True)
        self.name.clear()
        self.name.addItems(catalog.names_for_kind(self.current_parameter_kind()))

        if current:
            self.name.setCurrentText(current)

        self.name.blockSignals(False)

    def on_can_kind_changed(self, _text):
        self.refresh_catalog()
        self.completeChanged.emit()

    def initializePage(self):
        kind = self.wizard().page(PAGE_TYPE).current_kind()
        is_can = kind == "CANBUS"

        if kind == "POT":
            self.pin_label.setText("Canal ADS:")
            self.pin.setRange(0, 7)
            self.pin.setPrefix("ADS")
        else:
            self.pin_label.setText("Pin:")
            self.pin.setRange(0, 255)
            self.pin.setPrefix("")

        visible = kind not in ("SELECTOR", "CANBUS")
        self.pin_label.setVisible(visible)
        self.pin.setVisible(visible)
        self.can_kind.setVisible(is_can)
        self.can_node.setVisible(is_can)
        self.can_channel.setVisible(is_can)
        self.form.labelForField(self.can_kind).setVisible(is_can)
        self.form.labelForField(self.can_node).setVisible(is_can)
        self.form.labelForField(self.can_channel).setVisible(is_can)

        self.refresh_catalog()

        device = getattr(self.wizard(), "existing_device", None)
        if device and not self._prefilled and str(device.kind).upper() == kind:
            if kind == "POT" and str(device.pin).upper().startswith("ADS"):
                self.pin.setValue(int(str(device.pin).upper()[3:]))
            elif kind == "CANBUS":
                can_kind = str(getattr(device, "can_kind", "BUTTON")).upper()
                index = self.can_kind.findData(can_kind)
                if index >= 0:
                    self.can_kind.setCurrentIndex(index)
                self.can_node.setValue(int(getattr(device, "can_node", 0)))
                self.can_channel.setValue(int(getattr(device, "can_channel", 0)))
            elif kind != "SELECTOR":
                self.pin.setValue(int(device.pin))

            self.name.setCurrentText(str(device.name))
            self._prefilled = True

        self.completeChanged.emit()

    def get_pin_token(self):
        kind = self.wizard().page(PAGE_TYPE).current_kind()

        if kind == "POT":
            return f"ADS{self.pin.value()}"

        if kind == "CANBUS":
            return f"CAN{self.can_node.value()}:{self.can_channel.value()}"

        return self.pin.value()

    def get_can_kind(self):
        return self.can_kind.currentData() or self.can_kind.currentText()

    def get_name(self):
        return self.name.currentText().strip()

    def isComplete(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).current_kind()

        name = self.get_name()
        pin_token = self.get_pin_token()

        if not name:
            self.warning.setText("Introduce o selecciona un parámetro.")
            return False

        if kind == "SELECTOR":
            if wizard and hasattr(wizard, "is_selector_name_used"):
                if wizard.is_selector_name_used(name):
                    self.warning.setText("Ya existe otro selector con ese nombre.")
                    return False
        elif kind == "CANBUS":
            if wizard and hasattr(wizard, "is_can_used"):
                if wizard.is_can_used(self.can_node.value(), self.can_channel.value()):
                    self.warning.setText(
                        f"El CAN{self.can_node.value()}:{self.can_channel.value()} ya está en uso."
                    )
                    return False
        else:
            if wizard and hasattr(wizard, "is_pin_used"):
                if wizard.is_pin_used(pin_token):
                    self.warning.setText(f"El pin/canal {pin_token} ya está en uso.")
                    return False

        self.warning.setText("")
        return True

    def nextId(self):
        kind = self.wizard().page(PAGE_TYPE).current_kind()

        if kind == "SELECTOR":
            return PAGE_SELECTOR

        if kind == "CANBUS":
            return PAGE_SUMMARY

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
        kind = wizard.page(PAGE_TYPE).current_kind()
        pin_token = wizard.page(PAGE_BASIC).get_pin_token()

        if kind == "CANBUS":
            self.tester.stop()
            return

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

        self.threshold = QDoubleSpinBox()
        self.threshold.setRange(0, 1)
        self.threshold.setDecimals(4)
        self.threshold.setSingleStep(0.01)
        self.threshold.setValue(0.50)

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

        self.notch_hyst = QDoubleSpinBox()
        self.notch_hyst.setRange(0, 0.3)
        self.notch_hyst.setDecimals(3)
        self.notch_hyst.setSingleStep(0.01)
        self.notch_hyst.setValue(0.05)

        self.notch_partial = QCheckBox("Activar muescas parciales")
        self.notch_partial.setChecked(False)

        self.notch_snapwin = QDoubleSpinBox()
        self.notch_snapwin.setRange(0, 0.3)
        self.notch_snapwin.setDecimals(3)
        self.notch_snapwin.setSingleStep(0.01)
        self.notch_snapwin.setValue(0.03)

        self.split_mode = QComboBox()
        self.split_mode.addItems(["OFF", "DUAL", "SIGNED", "CENTERED"])

        self.split_deadband = QDoubleSpinBox()
        self.split_deadband.setRange(0, 0.3)
        self.split_deadband.setDecimals(3)
        self.split_deadband.setSingleStep(0.01)
        self.split_deadband.setValue(0.02)

        self.split_center_bias = QDoubleSpinBox()
        self.split_center_bias.setRange(0, 1)
        self.split_center_bias.setDecimals(3)
        self.split_center_bias.setSingleStep(0.01)
        self.split_center_bias.setValue(0.5)

        self.split_tag = QLineEdit()
        self.split_tag.setPlaceholderText("Tag unico opcional")

        self.split_tag_fwd = QLineEdit()
        self.split_tag_fwd.setPlaceholderText("Tag forward")

        self.split_tag_back = QLineEdit()
        self.split_tag_back.setPlaceholderText("Tag backward")

        self.enable_notches.stateChanged.connect(self.on_notch_enabled_changed)
        self.notch_count.valueChanged.connect(self.rebuild_notch_table)
        self.notch_table.itemChanged.connect(lambda _item: self.completeChanged.emit())
        self.split_mode.currentTextChanged.connect(self.on_split_mode_changed)

        self.form = QFormLayout()
        self.form.addRow("Valor 1:", self.value1)
        self.form.addRow("Valor 2:", self.value2)
        self.form.addRow("Entrada mínima:", self.min_in)
        self.form.addRow("Entrada máxima:", self.max_in)
        self.form.addRow("Salida mínima:", self.min_out)
        self.form.addRow("Salida máxima:", self.max_out)
        self.form.addRow("Suavizado:", self.smooth)
        self.form.addRow("Umbral cambio:", self.threshold)
        self.form.addRow("Modo envío:", self.send_mode)
        self.form.addRow("Intervalo:", self.interval)
        self.form.addRow("", self.as_integer)
        self.form.addRow("", self.enable_notches)
        self.form.addRow("", self.live_value_label)
        self.form.addRow("Nº muescas:", self.notch_count)
        self.form.addRow("Tabla muescas:", self.notch_table)
        self.form.addRow("Histéresis muescas:", self.notch_hyst)
        self.form.addRow("", self.notch_partial)
        self.form.addRow("Ventana snap:", self.notch_snapwin)
        self.form.addRow("", self.notch_warning)
        self.form.addRow("Modo split:", self.split_mode)
        self.form.addRow("Deadband split:", self.split_deadband)
        self.form.addRow("Bias centro split:", self.split_center_bias)
        self.form.addRow("Tag split:", self.split_tag)
        self.form.addRow("Tag forward:", self.split_tag_fwd)
        self.form.addRow("Tag backward:", self.split_tag_back)

        self.setLayout(self.form)
        self._prefilled = False

    def initializePage(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).current_kind()

        is_pot = kind == "POT"
        device = getattr(wizard, "existing_device", None)

        if is_pot and device and not self._prefilled and str(device.kind).upper() == "POT":
            self.min_in.setValue(int(device.min_in))
            self.max_in.setValue(int(device.max_in))
            self.min_out.setValue(float(device.min_out))
            self.max_out.setValue(float(device.max_out))
            self.smooth.setValue(float(device.smooth))
            self.threshold.setValue(float(getattr(device, "pot_threshold", 0.5)))
            self.send_mode.setCurrentText(str(device.send_mode))
            self.interval.setValue(int(device.interval))
            self.as_integer.setChecked(bool(device.as_integer))

            self.enable_notches.setChecked(bool(getattr(device, "pot_notches_enabled", False)))
            notches = list(getattr(device, "pot_notches", []))
            self.notch_count.setValue(max(2, len(notches) or 2))
            self.notch_hyst.setValue(float(getattr(device, "pot_notch_hyst", 0.05)))
            self.notch_partial.setChecked(bool(getattr(device, "pot_notch_partial", False)))
            self.notch_snapwin.setValue(float(getattr(device, "pot_notch_snapwin", 0.03)))

            self.split_mode.setCurrentText(str(getattr(device, "pot_split_mode", "OFF")).upper())
            self.split_deadband.setValue(float(getattr(device, "pot_split_deadband", 0.02)))
            self.split_center_bias.setValue(float(getattr(device, "pot_split_center_bias", 0.5)))
            self.split_tag.setText(str(getattr(device, "pot_split_tag", "")))
            self.split_tag_fwd.setText(str(getattr(device, "pot_split_tag_fwd", "")))
            self.split_tag_back.setText(str(getattr(device, "pot_split_tag_back", "")))

            self.rebuild_notch_table()
            for row, (raw_value, out_value) in enumerate(notches):
                if row >= self.notch_table.rowCount():
                    break
                self.notch_table.setItem(
                    row,
                    0,
                    QTableWidgetItem("" if raw_value is None else str(raw_value))
                )
                self.notch_table.setItem(row, 2, QTableWidgetItem(f"{out_value:g}"))

            self._prefilled = True

        test_page = wizard.page(PAGE_TEST)
        cal_min, cal_max = test_page.get_calibration()

        if is_pot and cal_min is not None and cal_max is not None and not self._prefilled:
            self.min_in.setValue(int(cal_min))
            self.max_in.setValue(int(cal_max))

        if is_pot and not self._prefilled:
            self.rebuild_notch_table()

        rows_for_pot = {
            "Entrada mínima:",
            "Entrada máxima:",
            "Salida mínima:",
            "Salida máxima:",
            "Suavizado:",
            "Umbral cambio:",
            "Modo envío:",
            "Intervalo:",
            "Nº muescas:",
            "Tabla muescas:",
            "Histéresis muescas:",
            "Ventana snap:",
            "Modo split:",
            "Deadband split:",
            "Bias centro split:",
            "Tag split:",
            "Tag forward:",
            "Tag backward:",
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
                visible = is_pot

                if field in (self.notch_count, self.notch_table, self.notch_hyst, self.notch_snapwin):
                    visible = is_pot and self.enable_notches.isChecked()

                if field in (self.split_deadband, self.split_center_bias, self.split_tag):
                    visible = is_pot and self.split_mode.currentText() != "OFF"

                if field in (self.split_tag_fwd, self.split_tag_back):
                    visible = is_pot and self.split_mode.currentText() == "DUAL"

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

                elif field == self.notch_partial:
                    field.setVisible(is_pot and self.enable_notches.isChecked())

                elif field == self.notch_warning:
                    field.setVisible(is_pot and self.enable_notches.isChecked())

        self.completeChanged.emit()

    def on_notch_enabled_changed(self):
        self.initializePage()
        self.completeChanged.emit()

    def on_split_mode_changed(self):
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

            pot_text = pot_item.text().strip()
            pot_value = None if pot_text == "" else int(pot_text)
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
                pot_text = pot_item.text().strip()
                pot_value = int(pot_text) if pot_text else None
                float(value_item.text().strip())
            except Exception:
                self.notch_warning.setText(f"Valores inválidos en muesca {row + 1}.")
                return False

            if pot_value is not None and (pot_value < 0 or pot_value > 65535):
                self.notch_warning.setText(f"Valor POT fuera de rango en muesca {row + 1}.")
                return False

            if pot_value is not None and pot_value in used_values:
                self.notch_warning.setText(f"Valor POT repetido en muesca {row + 1}.")
                return False

            if pot_value is not None:
                used_values.add(pot_value)

        self.notch_warning.setText("")
        return True

    def isComplete(self):
        wizard = self.wizard()
        kind = wizard.page(PAGE_TYPE).current_kind()

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
        self._prefilled = False

    def initializePage(self):
        wizard = self.wizard()
        selector_devices = getattr(wizard, "existing_selector_devices", None)

        if selector_devices and not self._prefilled:
            ordered = sorted(selector_devices, key=lambda device: float(device.value1))

            self.contact_count.setValue(max(2, len(ordered)))
            self.rebuild_table()

            for row, device in enumerate(ordered):
                if row >= self.table.rowCount():
                    break

                self.table.setItem(row, 0, QTableWidgetItem(str(device.pin)))
                self.table.setItem(row, 1, QTableWidgetItem(f"{float(device.value1):g}"))

            self._prefilled = True
        else:
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

        kind = wizard.page(PAGE_TYPE).current_kind()
        basic = wizard.page(PAGE_BASIC)
        options = wizard.page(PAGE_OPTIONS)

        if kind == "SELECTOR":
            contacts = wizard.page(PAGE_SELECTOR).get_contacts()

            lines = [
                f"Tipo: {kind_label(kind)}",
                f"Nombre: {basic.get_name()}",
                "",
                "Contactos:"
            ]

            for pin, value in contacts:
                lines.append(f"  Pin {pin} -> {value:g}")

            self.label.setText("\n".join(lines))
            return

        if kind == "CANBUS":
            lines = [
                f"Tipo: {kind_label(kind)}",
                f"Subtipo: {kind_label(basic.get_can_kind())}",
                f"Referencia: {basic.get_pin_token()}",
                f"Nombre: {basic.get_name()}",
            ]

            self.label.setText("\n".join(lines))
            return

        if kind == "POT":
            lines = [
                f"Tipo: {kind_label(kind)}",
                f"Pin: {basic.get_pin_token()}",
                f"Nombre: {basic.get_name()}",
                "",
                f"Entrada: {options.min_in.value()} - {options.max_in.value()}",
                f"Salida: {options.min_out.value()} - {options.max_out.value()}",
                f"Suavizado: {options.smooth.value()}",
                f"Umbral cambio: {options.threshold.value()}",
                f"Modo envío: {options.send_mode.currentText()}",
                f"Intervalo: {options.interval.value()}",
                f"Formato: {'INT' if options.as_integer.isChecked() else 'FLOAT'}",
            ]

            if options.enable_notches.isChecked():
                lines.append("")
                lines.append("Muescas:")

                lines.append(f"Histéresis: {options.notch_hyst.value()}")
                lines.append(f"Parciales: {'ON' if options.notch_partial.isChecked() else 'OFF'}")
                lines.append(f"Snap window: {options.notch_snapwin.value()}")

                for pot_value, out_value in options.get_notches():
                    left = "AUTO" if pot_value is None else str(pot_value)
                    lines.append(f"  POT {left} -> {out_value:g}")

            if options.split_mode.currentText() != "OFF":
                lines.append("")
                lines.append(f"Split: {options.split_mode.currentText()}")
                lines.append(f"Deadband: {options.split_deadband.value()}")
                lines.append(f"Bias centro: {options.split_center_bias.value()}")
                if options.split_tag.text().strip():
                    lines.append(f"Tag split: {options.split_tag.text().strip()}")
                if options.split_mode.currentText() == "DUAL":
                    if options.split_tag_fwd.text().strip():
                        lines.append(f"Tag forward: {options.split_tag_fwd.text().strip()}")
                    if options.split_tag_back.text().strip():
                        lines.append(f"Tag backward: {options.split_tag_back.text().strip()}")

            self.label.setText("\n".join(lines))
            return

        text = (
            f"Tipo: {kind_label(kind)}\n"
            f"Pin: {basic.get_pin_token()}\n"
            f"Nombre: {basic.get_name()}\n\n"
            f"Valor 1: {options.value1.value()}\n"
            f"Valor 2: {options.value2.value()}"
        )

        self.label.setText(text)

    def nextId(self):
        return -1


class DeviceWizard(QWizard):
    def __init__(
        self,
        connection,
        devices=None,
        parent=None,
        parameter_catalog=None,
        existing_device=None,
        existing_selector_devices=None,
    ):
        super().__init__(parent)

        self.connection = connection
        self.devices = devices or []
        self.parameter_catalog = parameter_catalog
        self.existing_device = existing_device
        self.existing_selector_devices = existing_selector_devices or []

        if self.existing_device is None and self.existing_selector_devices:
            self.existing_device = self.existing_selector_devices[0]

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
        for device in self.devices:
            if device is self.existing_device:
                continue
            if device in self.existing_selector_devices:
                continue
            if str(device.pin) == str(pin):
                return True
        return False

    def is_selector_name_used(self, name):
        selector_name = str(name).strip()

        if not selector_name:
            return False

        for device in self.devices:
            if device.kind != "SELECTOR":
                continue
            if device in self.existing_selector_devices:
                continue
            if str(device.name).strip() == selector_name:
                return True

        return False

    def is_can_used(self, node, channel):
        for device in self.devices:
            if device is self.existing_device:
                continue
            if device in self.existing_selector_devices:
                continue
            if str(device.kind).upper() != "CANBUS":
                continue
            if int(getattr(device, "can_node", -1)) == int(node) and int(
                getattr(device, "can_channel", -1)
            ) == int(channel):
                return True
        return False

    def get_devices(self):
        kind = self.page(PAGE_TYPE).current_kind()
        basic = self.page(PAGE_BASIC)

        if kind == "SELECTOR":
            name = basic.get_name()
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

        if kind == "CANBUS":
            return [
                Device(
                    kind="CANBUS",
                    pin=basic.get_pin_token(),
                    name=basic.get_name(),
                    can_kind=basic.get_can_kind(),
                    can_node=basic.can_node.value(),
                    can_channel=basic.can_channel.value(),
                    value1=0,
                    value2=1,
                )
            ]

        options = self.page(PAGE_OPTIONS)

        device = Device(
            kind=kind,
            pin=basic.get_pin_token(),
            name=basic.get_name(),

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
            pot_threshold=options.threshold.value(),
            pot_notches_enabled=options.enable_notches.isChecked() if kind == "POT" else False,
            pot_notches=options.get_notches() if kind == "POT" else [],
            pot_notch_hyst=options.notch_hyst.value() if kind == "POT" else 0.05,
            pot_notch_partial=options.notch_partial.isChecked() if kind == "POT" else False,
            pot_notch_snapwin=options.notch_snapwin.value() if kind == "POT" else 0.03,
            pot_split_mode=options.split_mode.currentText() if kind == "POT" else "OFF",
            pot_split_deadband=options.split_deadband.value() if kind == "POT" else 0.02,
            pot_split_center_bias=options.split_center_bias.value() if kind == "POT" else 0.5,
            pot_split_tag=options.split_tag.text().strip() if kind == "POT" else "",
            pot_split_tag_fwd=options.split_tag_fwd.text().strip() if kind == "POT" else "",
            pot_split_tag_back=options.split_tag_back.text().strip() if kind == "POT" else "",
        )

        return [device]

    def get_device(self):
        devices = self.get_devices()
        return devices[0] if devices else None
