from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox
)
from PySide6.QtCore import Qt

from modbus.modbus_model import ModbusDevice, ModbusTag


PAGE_TYPE = 0
PAGE_DEVICE = 1
PAGE_TAG = 2
PAGE_SUMMARY = 3


class ModbusTypePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Tipo Modbus")
        self.setSubTitle("Elige qué quieres crear.")

        self.mode = QComboBox()
        self.mode.addItems(["DEVICE", "TAG"])

        layout = QFormLayout()
        layout.addRow("Crear:", self.mode)
        self.setLayout(layout)

    def nextId(self):
        return PAGE_DEVICE if self.mode.currentText() == "DEVICE" else PAGE_TAG


class ModbusDevicePage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Esclavo Modbus")
        self.setSubTitle("Crea un nuevo esclavo TCP o RTU.")

        self.dev_id = QSpinBox()
        self.dev_id.setRange(0, 250)

        self.name = QLineEdit()
        self.name.setPlaceholderText("Nombre visual, ej: PLC1")

        self.bus = QComboBox()
        self.bus.addItems(["TCP", "RTU"])
        self.bus.currentTextChanged.connect(self.update_bus)

        self.ip = QLineEdit()
        self.ip.setText("192.168.1.50")

        self.port = QSpinBox()
        self.port.setRange(0, 65535)
        self.port.setValue(502)

        self.unit = QSpinBox()
        self.unit.setRange(1, 247)
        self.unit.setValue(1)

        self.period = QSpinBox()
        self.period.setRange(0, 60000)
        self.period.setValue(100)

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")

        self.name.textChanged.connect(lambda _: self.completeChanged.emit())
        self.ip.textChanged.connect(lambda _: self.completeChanged.emit())

        self.form = QFormLayout()
        self.form.addRow("ID:", self.dev_id)
        self.form.addRow("Nombre:", self.name)
        self.form.addRow("Bus:", self.bus)
        self.form.addRow("IP:", self.ip)
        self.form.addRow("Puerto:", self.port)
        self.form.addRow("Unit ID:", self.unit)
        self.form.addRow("Periodo ms:", self.period)
        self.form.addRow("", self.warning)

        self.setLayout(self.form)
        self.update_bus(self.bus.currentText())

    def update_bus(self, bus):
        tcp = bus == "TCP"

        self.ip.setVisible(tcp)
        self.port.setVisible(tcp)

        for i in range(self.form.rowCount()):
            label_item = self.form.itemAt(i, QFormLayout.LabelRole)
            field_item = self.form.itemAt(i, QFormLayout.FieldRole)

            if not label_item or not field_item:
                continue

            label = label_item.widget()
            field = field_item.widget()

            if field in (self.ip, self.port):
                label.setVisible(tcp)

        if bus == "RTU":
            self.ip.setText("0.0.0.0")
            self.port.setValue(0)
        else:
            if self.ip.text().strip() == "0.0.0.0":
                self.ip.setText("192.168.1.50")
            if self.port.value() == 0:
                self.port.setValue(502)

    def isComplete(self):
        if not self.name.text().strip():
            self.warning.setText("Introduce un nombre.")
            return False

        if self.bus.currentText() == "TCP" and not self.ip.text().strip():
            self.warning.setText("Introduce una IP.")
            return False

        self.warning.setText("")
        return True

    def nextId(self):
        return PAGE_SUMMARY


class ModbusTagPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Variable Modbus")
        self.setSubTitle("Crea una variable asociada a un esclavo.")

        self.direction = QComboBox()
        self.direction.addItems(["IN", "OUT"])
        self.direction.currentTextChanged.connect(self.update_direction)

        self.dev_id = QSpinBox()
        self.dev_id.setRange(0, 250)

        self.func = QComboBox()

        self.addr = QSpinBox()
        self.addr.setRange(0, 65535)

        self.qty = QSpinBox()
        self.qty.setRange(1, 64)
        self.qty.setValue(1)

        self.name = QLineEdit()
        self.name.setPlaceholderText("SPEED, BRAKE, LIGHT...")

        self.period = QSpinBox()
        self.period.setRange(0, 60000)
        self.period.setValue(100)

        self.scale = QDoubleSpinBox()
        self.scale.setRange(-999999, 999999)
        self.scale.setDecimals(3)
        self.scale.setValue(1.0)

        self.offset = QDoubleSpinBox()
        self.offset.setRange(-999999, 999999)
        self.offset.setDecimals(3)
        self.offset.setValue(0.0)

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")

        self.name.textChanged.connect(lambda _: self.completeChanged.emit())

        form = QFormLayout()
        form.addRow("Dirección:", self.direction)
        form.addRow("Dev ID:", self.dev_id)
        form.addRow("Función:", self.func)
        form.addRow("Dirección registro:", self.addr)
        form.addRow("Cantidad:", self.qty)
        form.addRow("Nombre tag:", self.name)
        form.addRow("Periodo ms:", self.period)
        form.addRow("Scale:", self.scale)
        form.addRow("Offset:", self.offset)
        form.addRow("", self.warning)

        self.setLayout(form)
        self.update_direction(self.direction.currentText())

    def update_direction(self, direction):
        self.func.clear()

        if direction == "OUT":
            self.func.addItems(["HREG", "COIL"])
            self.period.setValue(0)
        else:
            self.func.addItems(["HREG", "IREG", "COIL", "ISTS"])
            if self.period.value() == 0:
                self.period.setValue(100)

    def isComplete(self):
        if not self.name.text().strip():
            self.warning.setText("Introduce un nombre de tag.")
            return False

        self.warning.setText("")
        return True

    def nextId(self):
        return PAGE_SUMMARY


class ModbusSummaryPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Resumen")
        self.setSubTitle("Revisa el comando generado.")

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.label.setStyleSheet(
            "font-family: Consolas, monospace;"
            "font-size: 12px;"
            "color: white;"
            "padding: 10px;"
            "background: #1f1f1f;"
            "border-radius: 6px;"
        )

        layout = QVBoxLayout()
        layout.addWidget(self.label)
        self.setLayout(layout)

    def initializePage(self):
        self.label.setText(self.wizard().get_command())

    def nextId(self):
        return -1


class ModbusWizard(QWizard):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Asistente Modbus")
        self.resize(540, 390)
        self.setWizardStyle(QWizard.ModernStyle)

        self.setStyleSheet("""
        QWizard {
            background-color: #2b2b2b;
        }
        QLabel {
            color: white;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c;
            color: white;
            border: 1px solid #555;
            padding: 4px;
            border-radius: 4px;
        }
        QPushButton {
            background-color: #444;
            color: white;
            padding: 6px;
        }
        QPushButton:disabled {
            background-color: #333;
            color: #777;
        }
        """)

        self.setPage(PAGE_TYPE, ModbusTypePage())
        self.setPage(PAGE_DEVICE, ModbusDevicePage())
        self.setPage(PAGE_TAG, ModbusTagPage())
        self.setPage(PAGE_SUMMARY, ModbusSummaryPage())

        self.setStartId(PAGE_TYPE)

    def mode(self):
        return self.page(PAGE_TYPE).mode.currentText()

    def get_device(self):
        p = self.page(PAGE_DEVICE)

        return ModbusDevice(
            dev_id=p.dev_id.value(),
            name=p.name.text().strip(),
            ip=p.ip.text().strip(),
            port=p.port.value(),
            unit=p.unit.value(),
            period=p.period.value(),
            bus=p.bus.currentText(),
        )

    def get_tag(self):
        p = self.page(PAGE_TAG)

        return ModbusTag(
            direction=p.direction.currentText(),
            dev_id=p.dev_id.value(),
            func=p.func.currentText(),
            addr=p.addr.value(),
            qty=p.qty.value(),
            name=p.name.text().strip(),
            period=p.period.value(),
            scale=p.scale.value(),
            offset=p.offset.value(),
        )

    def get_command(self):
        if self.mode() == "DEVICE":
            d = self.get_device()

            if d.bus == "RTU":
                return f"MB.ADDDEV {d.dev_id} RTU {d.unit}"

            return f"MB.ADDDEV {d.dev_id} TCP {d.ip} {d.port} {d.unit}"

        t = self.get_tag()

        cmd = "MB.ADDOUT" if t.direction == "OUT" else "MB.ADDIN"

        return (
            f"{cmd} {t.dev_id} {t.func} {t.addr} {t.qty} "
            f"{t.name} {t.period} {t.scale:.3f} {t.offset:.3f}"
        )