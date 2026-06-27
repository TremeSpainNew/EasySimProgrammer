from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QHBoxLayout, QCheckBox
)
from PySide6.QtCore import QTimer, Qt


class LivePinTester(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)

        self.connection = connection

        self.pin = 0
        self.kind = "BUTTON"
        self.output_name = ""
        self.output_state = 0
        self.output_inverted = False
        self.last_output_raw_value = 0
        self.watch_active = False

        self.calibrating = False
        self.cal_min = None
        self.cal_max = None

        self.title = QLabel("Prueba del pin")
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet("font-size: 14px; font-weight: bold;")

        self.status = QLabel("Esperando estado del ESP32...")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size: 16px; font-weight: bold;")

        self.indicator = QFrame()
        self.indicator.setFixedSize(56, 56)
        self.set_indicator(False)

        self.bar = QProgressBar()
        self.bar.setRange(0, 4095)
        self.bar.setValue(0)
        self.bar.setTextVisible(True)

        self.toggle_button = QPushButton("Probar salida ON/OFF")
        self.toggle_button.clicked.connect(self.toggle_output)

        self.invert_output_check = QCheckBox("Invertir salida en la prueba")
        self.invert_output_check.toggled.connect(self.on_output_inversion_changed)

        self.calibrate_button = QPushButton("Calibrar rango POT")
        self.calibrate_button.clicked.connect(self.toggle_calibration)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self.toggle_button)
        button_row.addWidget(self.calibrate_button)

        layout = QVBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        layout.addWidget(self.title)
        layout.addWidget(self.status)
        layout.addWidget(self.indicator, alignment=Qt.AlignCenter)
        layout.addWidget(self.bar)
        layout.addWidget(self.invert_output_check)
        layout.addLayout(button_row)

        self.setLayout(layout)

        self.connection.io_state.connect(self.on_io_state)

        self.sim_timer = QTimer(self)
        self.sim_timer.timeout.connect(self.poll_simulation)
    
    def normalize_kind(self, kind: str) -> str:
        kind = str(kind).upper()

        mapping = {
            "BOTON": "BUTTON",
            "BOTÓN": "BUTTON",
            "BUTTON": "BUTTON",

            "INTERRUPTOR": "SWITCH",
            "SWITCH": "SWITCH",

            "SALIDA DIGITAL": "OUTPUT",
            "OUTPUT": "OUTPUT",

            "POTENCIOMETRO": "POT",
            "POTENCIÓMETRO": "POT",
            "POT": "POT",

            "SELECTOR": "SELECTOR",
        }

        return mapping.get(kind, kind)

    def display_kind(self, kind: str) -> str:
        labels = {
            "BUTTON": "pulsador",
            "SWITCH": "interruptor",
            "OUTPUT": "salida",
            "POT": "potenciometro",
            "SELECTOR": "selector",
        }
        return labels.get(self.normalize_kind(kind), str(kind).lower())

    def set_target(self, pin, kind: str, output_name: str = ""):
        self.stop_watch()

        self.pin = pin
        self.kind = self.normalize_kind(kind)
        self.output_name = str(output_name or "").strip()
        self.output_state = 0
        self.last_output_raw_value = 0
        self.set_output_inverted(False)

        self.calibrating = False
        self.cal_min = None
        self.cal_max = None
        self.calibrate_button.setText("Calibrar rango POT")

        self.title.setText(f"Esperando {self.display_kind(self.kind)} en pin {pin}")
        self.status.setText("Esperando estado del ESP32...")

        is_pot = self.kind == "POT"
        is_output = self.kind == "OUTPUT"

        self.bar.setVisible(is_pot)
        self.calibrate_button.setVisible(is_pot)
        self.toggle_button.setVisible(is_output)
        self.invert_output_check.setVisible(is_output)
        self.indicator.setVisible(not is_pot)

        if self.connection.simulation:
            self.sim_timer.start(250)
        else:
            self.sim_timer.stop()
            self.start_watch()

            value = self.connection.read_pin(self.pin, self.kind)
            self.update_display(value)

    def start_watch(self):
        if self.watch_active:
            return

        self.connection.start_pin_watch(self.pin, self.kind)
        self.watch_active = True

    def stop_watch(self):
        if not self.watch_active:
            return

        self.connection.stop_pin_watch(self.pin, self.kind)
        self.watch_active = False

    def stop(self):
        self.sim_timer.stop()
        self.stop_watch()

    def poll_simulation(self):
        value = self.connection.read_pin(self.pin, self.kind)
        self.update_display(value)

    def on_io_state(self, pin, kind: str, value: int):
        kind = self.normalize_kind(kind)

        if pin != self.pin:
            return

        if kind != self.kind:
            return

        self.update_display(value)

    def update_display(self, value: int):
        if self.kind == "POT":
            value = int(value)
            self.bar.setValue(value)

            if self.calibrating:
                if self.cal_min is None or value < self.cal_min:
                    self.cal_min = value

                if self.cal_max is None or value > self.cal_max:
                    self.cal_max = value

                self.status.setText(
                    f"Calibrando... Valor: {value} | Min: {self.cal_min} | Max: {self.cal_max}"
                )
            else:
                self.status.setText(f"Valor actual: {value}")

            return

        if self.kind == "OUTPUT":
            self.last_output_raw_value = 1 if value else 0
            active = bool(self.physical_to_logical_output(value))
            self.output_state = 1 if active else 0
            self.status.setText("Salida ON" if active else "Salida OFF")
            self.set_indicator(active)
            return

        active = bool(value)

        if self.kind == "BUTTON":
            self.status.setText("PULSADO" if active else "Sin pulsar")

        elif self.kind == "SWITCH":
            self.status.setText("ACTIVO" if active else "INACTIVO")

        elif self.kind == "SELECTOR":
            self.status.setText("SELECCIONADO" if active else "Sin seleccionar")

        else:
            self.status.setText(str(value))

        self.set_indicator(active)

    def set_indicator(self, active: bool):
        if active:
            self.indicator.setStyleSheet(
                "background-color: #18c964;"
                "border-radius: 28px;"
                "border: 2px solid white;"
            )
        else:
            self.indicator.setStyleSheet(
                "background-color: #333333;"
                "border-radius: 28px;"
                "border: 2px solid #777777;"
            )

    def toggle_output(self):
        self.output_state = 0 if self.output_state else 1

        if self.kind == "OUTPUT" and self.output_name:
            self.connection.send_command(f"{self.output_name}={self.output_state}")
            return

        self.connection.write_output(
            self.pin,
            self.logical_to_physical_output(self.output_state)
        )

    def logical_to_physical_output(self, value: int) -> int:
        value = 1 if value else 0
        return 1 - value if self.output_inverted else value

    def physical_to_logical_output(self, value: int) -> int:
        value = 1 if value else 0
        return 1 - value if self.output_inverted else value

    def on_output_inversion_changed(self, checked: bool):
        self.output_inverted = bool(checked)

        if self.kind == "OUTPUT":
            self.update_display(self.last_output_raw_value)

    def set_output_inverted(self, enabled: bool):
        self.output_inverted = bool(enabled)
        self.invert_output_check.blockSignals(True)
        self.invert_output_check.setChecked(self.output_inverted)
        self.invert_output_check.blockSignals(False)

        if self.kind == "OUTPUT":
            self.update_display(self.last_output_raw_value)

    def get_output_inverted(self) -> bool:
        return bool(self.output_inverted)

    def toggle_calibration(self):
        self.calibrating = not self.calibrating

        if self.calibrating:
            self.cal_min = None
            self.cal_max = None
            self.calibrate_button.setText("Finalizar calibración")
        else:
            self.calibrate_button.setText("Calibrar rango POT")

    def get_calibration(self):
        return self.cal_min, self.cal_max
