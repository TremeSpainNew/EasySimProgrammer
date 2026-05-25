from PySide6.QtWidgets import (
    QWizard, QWizardPage, QVBoxLayout, QFormLayout,
    QComboBox, QSpinBox, QLineEdit, QLabel,
    QDoubleSpinBox, QCheckBox
)
from PySide6.QtCore import Qt

from models.device import Device
from live_pin_tester import LivePinTester


PAGE_TYPE = 0
PAGE_BASIC = 1
PAGE_TEST = 2
PAGE_OPTIONS = 3
PAGE_SUMMARY = 4


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
        self.kind.setMinimumHeight(28)

        label = QLabel("Tipo de elemento:")
        label.setAlignment(Qt.AlignCenter)

        layout = QVBoxLayout()
        layout.setContentsMargins(26, 8, 26, 8)
        layout.setSpacing(10)
        layout.addStretch(1)
        layout.addWidget(label)
        layout.addWidget(self.kind)
        layout.addStretch(1)

        self.setLayout(layout)

    def nextId(self):
        return PAGE_BASIC


class BasicPage(QWizardPage):
    def __init__(self):
        super().__init__()

        self.setTitle("Datos básicos")
        self.setSubTitle("Introduce el pin físico y el nombre/parámetro.")

        self.pin = QSpinBox()
        self.pin.setRange(0, 255)
        self.pin.setMinimumHeight(28)

        self.name = QLineEdit()
        self.name.setMinimumHeight(28)
        self.name.setPlaceholderText("Ejemplo: PZB_ACK, SIFA_LED, THROTTLE...")

        self.warning = QLabel("")
        self.warning.setStyleSheet("color: #d9534f; font-weight: bold;")
        self.warning.setWordWrap(True)

        self.pin.valueChanged.connect(lambda _value: self.completeChanged.emit())
        self.name.textChanged.connect(lambda _text: self.completeChanged.emit())

        form = QFormLayout()
        form.setContentsMargins(26, 18, 26, 8)
        form.setSpacing(10)
        form.addRow("Pin:", self.pin)
        form.addRow("Nombre / parámetro:", self.name)
        form.addRow("", self.warning)

        self.setLayout(form)

    def isComplete(self):
        wizard = self.wizard()

        name = self.name.text().strip()
        pin = self.pin.value()

        if not name:
            self.warning.setText("Introduce un nombre/parámetro.")
            return False

        if wizard and hasattr(wizard, "is_pin_used"):
            if wizard.is_pin_used(pin):
                self.warning.setText(f"El pin {pin} ya está en uso.")
                return False

        self.warning.setText("")
        return True

    def nextId(self):
        return PAGE_TEST


class TestPage(QWizardPage):
    def __init__(self, connection):
        super().__init__()

        self.setTitle("Comprobar pin")
        self.setSubTitle("Comprueba físicamente que el pin seleccionado es correcto.")

        self.connection = connection

        self.info = QLabel(
            "Pulsa el botón, cambia el interruptor, mueve el potenciómetro "
            "o activa la salida para comprobar que has elegido el pin correcto."
        )
        self.info.setWordWrap(True)

        self.tester = LivePinTester(connection)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 8, 20, 8)
        layout.setSpacing(8)
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

    def nextId(self):
        return PAGE_OPTIONS

    def get_calibration(self):
        return self.tester.get_calibration()


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

        for widget in [
            self.value1, self.value2, self.min_in, self.max_in,
            self.min_out, self.max_out, self.smooth,
            self.send_mode, self.interval
        ]:
            widget.setMinimumHeight(26)

        self.form = QFormLayout()
        self.form.setContentsMargins(26, 8, 26, 8)
        self.form.setSpacing(8)

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

        self.value1.setVisible(not is_pot)
        self.value2.setVisible(not is_pot)

        self.min_in.setVisible(is_pot)
        self.max_in.setVisible(is_pot)
        self.min_out.setVisible(is_pot)
        self.max_out.setVisible(is_pot)
        self.smooth.setVisible(is_pot)
        self.send_mode.setVisible(is_pot)
        self.interval.setVisible(is_pot)
        self.as_integer.setVisible(is_pot)

        for i in range(self.form.rowCount()):
            label_item = self.form.itemAt(i, QFormLayout.LabelRole)

            if label_item and label_item.widget():
                label = label_item.widget()
                text = label.text()

                if text in [
                    "Entrada mínima:",
                    "Entrada máxima:",
                    "Salida mínima:",
                    "Salida máxima:",
                    "Suavizado:",
                    "Modo envío:",
                    "Intervalo:",
                ]:
                    label.setVisible(is_pot)

                if text in [
                    "Valor 1:",
                    "Valor 2:",
                ]:
                    label.setVisible(not is_pot)

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
        layout.setContentsMargins(22, 12, 22, 12)
        layout.setSpacing(8)
        layout.addWidget(self.label)

        self.setLayout(layout)

    def initializePage(self):
        wizard = self.wizard()

        kind = wizard.page(PAGE_TYPE).kind.currentText()
        basic = wizard.page(PAGE_BASIC)
        options = wizard.page(PAGE_OPTIONS)

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
        self.resize(520, 330)
        self.setMinimumSize(480, 300)

        self.setWizardStyle(QWizard.ModernStyle)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setOption(QWizard.NoCancelButtonOnLastPage, True)
        self.setOption(QWizard.HaveHelpButton, False)

        self.setPage(PAGE_TYPE, TypePage())
        self.setPage(PAGE_BASIC, BasicPage())
        self.setPage(PAGE_TEST, TestPage(connection))
        self.setPage(PAGE_OPTIONS, OptionsPage())
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

    def get_device(self):
        kind = self.page(PAGE_TYPE).kind.currentText()
        basic = self.page(PAGE_BASIC)
        options = self.page(PAGE_OPTIONS)

        return Device(
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