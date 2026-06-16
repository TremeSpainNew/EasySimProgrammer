from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QProgressBar, QFrame, QHBoxLayout
)
from PySide6.QtCore import QTimer, Qt


class LivePinTester(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)

        self.connection = connection

        self.pin = 0
        self.kind = "BUTTON"
        self.output_state = 0
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

    def set_target(self, pin: int, kind: str):
        self.stop_watch()

        self.pin = pin
        self.kind = self.normalize_kind(kind)
        self.output_state = 0

        self.calibrating = False
        self.cal_min = None
        self.cal_max = None
        self.calibrate_button.setText("Calibrar rango POT")

        self.title.setText(f"Esperando {self.kind} en pin {pin}")
        self.status.setText("Esperando estado del ESP32...")

        is_pot = self.kind == "POT"
        is_output = self.kind == "OUTPUT"

        self.bar.setVisible(is_pot)
        self.calibrate_button.setVisible(is_pot)
        self.toggle_button.setVisible(is_output)
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

    def on_io_state(self, pin: int, kind: str, value: int):
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
            active = bool(value)
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
        self.connection.write_output(self.pin, self.output_state)

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