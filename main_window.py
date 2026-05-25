from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QFileDialog, QTabWidget, QMessageBox,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QGroupBox
)

from wizard.device_wizard import DeviceWizard
from storage import save_devices, load_devices
from commands.command_builder import build_all_commands
from connection_manager import ConnectionManager
from models.device import Device


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EasySim Programmer")
        self.resize(1200, 780)

        self.connection = ConnectionManager()
        self.connection.log.connect(self.add_log)
        self.connection.received.connect(self.on_received)

        self.devices = []

        # DUMP parser
        self.dump_active = False
        self.dump_devices = {}

        self.tabs = QTabWidget()
        self.tables = {}

        self.kind_titles = [
            ("BUTTON", "Pulsadores"),
            ("SWITCH", "Interruptores"),
            ("OUTPUT", "Salidas / LEDs"),
            ("POT", "Potenciómetros"),
            ("SELECTOR", "Selectores"),
        ]

        for kind, title in self.kind_titles:
            table = QTableWidget()
            table.setColumnCount(6)
            table.setHorizontalHeaderLabels([
                "Pin",
                "Nombre",
                "Valor 1",
                "Valor 2",
                "Modo",
                "Opciones"
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)

            self.tables[kind] = table
            self.tabs.addTab(table, title)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)

        self.btn_add = QPushButton("Añadir con asistente")
        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_save = QPushButton("Guardar JSON")
        self.btn_load = QPushButton("Cargar JSON")
        self.btn_generate = QPushButton("Generar comandos")
        self.btn_send = QPushButton("Enviar comandos")
        self.btn_dump = QPushButton("#DUMP")

        self.btn_add.clicked.connect(self.add_device)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_save.clicked.connect(self.save_json)
        self.btn_load.clicked.connect(self.load_json)
        self.btn_generate.clicked.connect(self.generate_commands)
        self.btn_send.clicked.connect(self.send_commands)
        self.btn_dump.clicked.connect(self.request_dump)

        self.sim_check = QCheckBox("Simulación")
        self.sim_check.setChecked(True)
        self.sim_check.stateChanged.connect(self.on_simulation_changed)

        self.connection_type = QComboBox()
        self.connection_type.addItems(["TCP", "Serial"])
        self.connection_type.setFixedWidth(80)

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP dispositivo")
        self.ip_edit.setText("192.168.1.177")
        self.ip_edit.setFixedWidth(130)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)
        self.port_spin.setFixedWidth(90)

        self.serial_port_edit = QLineEdit()
        self.serial_port_edit.setPlaceholderText("COM3")
        self.serial_port_edit.setText("COM3")
        self.serial_port_edit.setFixedWidth(90)

        self.baud_spin = QSpinBox()
        self.baud_spin.setRange(1200, 1000000)
        self.baud_spin.setValue(115200)
        self.baud_spin.setFixedWidth(100)

        self.btn_connect = QPushButton("Conectar")
        self.btn_connect.clicked.connect(self.connect_selected)

        self.btn_disconnect = QPushButton("Desconectar")
        self.btn_disconnect.clicked.connect(self.disconnect)

        connection_box = QGroupBox("Conexión")
        connection_row = QHBoxLayout()
        connection_row.setContentsMargins(8, 6, 8, 6)
        connection_row.setSpacing(8)
        connection_row.addWidget(self.sim_check)
        connection_row.addWidget(self.connection_type)
        connection_row.addWidget(QLabel("IP:"))
        connection_row.addWidget(self.ip_edit)
        connection_row.addWidget(QLabel("Puerto:"))
        connection_row.addWidget(self.port_spin)
        connection_row.addWidget(QLabel("Serial:"))
        connection_row.addWidget(self.serial_port_edit)
        connection_row.addWidget(QLabel("Baud:"))
        connection_row.addWidget(self.baud_spin)
        connection_row.addWidget(self.btn_connect)
        connection_row.addWidget(self.btn_disconnect)
        connection_row.addStretch()
        connection_box.setLayout(connection_row)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self.btn_add)
        button_row.addWidget(self.btn_delete)
        button_row.addStretch()
        button_row.addWidget(self.btn_dump)
        button_row.addWidget(self.btn_load)
        button_row.addWidget(self.btn_save)
        button_row.addWidget(self.btn_generate)
        button_row.addWidget(self.btn_send)

        top_widget = QWidget()
        top_layout = QVBoxLayout()
        top_layout.setContentsMargins(8, 8, 8, 4)
        top_layout.setSpacing(8)
        top_layout.addWidget(connection_box)
        top_layout.addLayout(button_row)
        top_widget.setLayout(top_layout)

        content = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(8, 4, 8, 8)
        content_layout.setSpacing(6)
        content_layout.addWidget(self.tabs)
        content_layout.addWidget(QLabel("Log"))
        content_layout.addWidget(self.log)
        content.setLayout(content_layout)

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(top_widget)
        layout.addWidget(content)

        root = QWidget()
        root.setLayout(layout)
        self.setCentralWidget(root)

    def add_log(self, text):
        self.log.append(text)

    # ==========================================================
    # DUMP PARSER
    # ==========================================================

    def request_dump(self):
        self.dump_active = False
        self.dump_devices = {}
        self.connection.send_command("#DUMP")

    def on_received(self, text):
        line = text.strip()

        if line == "BEGIN CONFIG":
            self.dump_active = True
            self.dump_devices = {}
            self.add_log("Leyendo configuración del dispositivo...")
            return

        if line == "#END" and self.dump_active:
            self.dump_active = False
            self.devices = list(self.dump_devices.values())
            self.refresh_tables()
            self.add_log(f"Configuración importada: {len(self.devices)} elementos.")
            return

        if not self.dump_active:
            return

        self.parse_dump_line(line)

    def parse_dump_line(self, line: str):
        parts = line.split()

        if not parts:
            return

        head = parts[0].upper()

        if head == "ADD":
            self.parse_add_line(parts)
            return

        if head == "SEL.ADD":
            self.parse_selector_line(parts)
            return

        if head == "CFG":
            self.parse_cfg_line(parts)
            return

    def parse_add_line(self, parts):
        if len(parts) < 5:
            return

        kind = parts[1].upper()
        pin_text = parts[2]
        name = parts[3]

        try:
            pin = self.parse_pin(pin_text)
            value1 = float(parts[4])
            value2 = float(parts[5]) if len(parts) > 5 else 1
        except Exception:
            return

        if kind not in ("BUTTON", "SWITCH", "OUTPUT", "POT"):
            return

        device = Device(
            kind=kind,
            pin=pin,
            name=name,
            value1=value1,
            value2=value2,
            min_out=value1,
            max_out=value2,
        )

        self.dump_devices[(kind, pin, name)] = device

    def parse_selector_line(self, parts):
        if len(parts) < 4:
            return

        try:
            name = parts[1]
            pin = self.parse_pin(parts[2])
            value = float(parts[3])
        except Exception:
            return

        device = Device(
            kind="SELECTOR",
            pin=pin,
            name=name,
            value1=value,
            value2=0,
            min_out=value,
            max_out=0,
        )

        self.dump_devices[("SELECTOR", pin, name)] = device

    def parse_cfg_line(self, parts):
        if len(parts) < 4:
            return

        try:
            pin = self.parse_pin(parts[1])
        except Exception:
            return

        field = parts[2].upper()

        device = None
        for dev in self.dump_devices.values():
            if dev.kind == "POT" and dev.pin == pin:
                device = dev
                break

        if device is None:
            return

        try:
            if field == "SCALE" and len(parts) >= 7:
                device.min_in = int(float(parts[3]))
                device.max_in = int(float(parts[4]))
                device.min_out = float(parts[5])
                device.max_out = float(parts[6])

            elif field == "FORMAT" and len(parts) >= 4:
                device.as_integer = parts[3].upper() == "INT"

            elif field == "SMOOTH" and len(parts) >= 4:
                device.smooth = float(parts[3])

            elif field == "MODE" and len(parts) >= 4:
                device.send_mode = parts[3].upper()

                if device.send_mode == "INTERVALO" and len(parts) >= 5:
                    device.interval = int(float(parts[4]))

            elif field == "THRESH" and len(parts) >= 4:
                pass

        except Exception:
            pass

    def parse_pin(self, text: str) -> int:
        text = text.strip().upper()

        if text.startswith("ADS"):
            return 128 + int(text[3:])

        return int(text)

    # ==========================================================
    # CONNECTION
    # ==========================================================

    def on_simulation_changed(self):
        self.connection.set_simulation(self.sim_check.isChecked())

    def connect_selected(self):
        if self.sim_check.isChecked():
            self.add_log("La simulación está activada.")
            return

        mode = self.connection_type.currentText()

        if mode == "TCP":
            ip = self.ip_edit.text().strip()
            port = self.port_spin.value()

            if not ip:
                QMessageBox.warning(self, "TCP", "Introduce una IP.")
                return

            self.connection.connect_tcp(ip, port)

        else:
            port_name = self.serial_port_edit.text().strip()
            baud = self.baud_spin.value()

            if not port_name:
                QMessageBox.warning(self, "Serial", "Introduce un puerto Serial.")
                return

            self.connection.connect_serial(port_name, baud)

        self.sim_check.setChecked(self.connection.simulation)

    def disconnect(self):
        self.connection.disconnect()
        self.add_log("Desconectado.")

    # ==========================================================
    # DEVICES
    # ==========================================================

    def add_device(self):
        wizard = DeviceWizard(self.connection, self.devices, self)

        if wizard.exec():
            device = wizard.get_device()
            self.devices.append(device)
            self.refresh_tables()
            self.add_log(f"Añadido {device.kind}: pin={device.pin}, name={device.name}")

    def refresh_tables(self):
        for table in self.tables.values():
            table.setRowCount(0)

        for device in self.devices:
            table = self.tables.get(device.kind)

            if not table:
                continue

            row = table.rowCount()
            table.insertRow(row)

            table.setItem(row, 0, QTableWidgetItem(str(device.pin)))
            table.setItem(row, 1, QTableWidgetItem(device.name))
            table.setItem(row, 2, QTableWidgetItem(str(device.value1)))
            table.setItem(row, 3, QTableWidgetItem(str(device.value2)))
            table.setItem(row, 4, QTableWidgetItem(device.send_mode))
            table.setItem(row, 5, QTableWidgetItem(self.describe_options(device)))

    def describe_options(self, device):
        if device.kind == "POT":
            return (
                f"{device.min_in}-{device.max_in} → "
                f"{device.min_out}-{device.max_out}, "
                f"smooth={device.smooth}, "
                f"{'INT' if device.as_integer else 'FLOAT'}"
            )

        if device.kind == "SELECTOR":
            return f"Posición selector = {device.value1}"

        return ""

    def current_kind(self):
        index = self.tabs.currentIndex()
        return self.kind_titles[index][0]

    def delete_selected(self):
        kind = self.current_kind()
        table = self.tables[kind]
        row = table.currentRow()

        if row < 0:
            QMessageBox.warning(self, "Eliminar", "Selecciona una fila.")
            return

        filtered = [device for device in self.devices if device.kind == kind]

        if row >= len(filtered):
            return

        device = filtered[row]
        self.devices.remove(device)

        self.refresh_tables()
        self.add_log(f"Eliminado {device.kind}: {device.name}")

    # ==========================================================
    # FILES / COMMANDS
    # ==========================================================

    def save_json(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Guardar configuración",
            "",
            "JSON (*.json)"
        )

        if not path:
            return

        save_devices(path, self.devices)
        self.add_log(f"Guardado: {path}")

    def load_json(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Cargar configuración",
            "",
            "JSON (*.json)"
        )

        if not path:
            return

        self.devices = load_devices(path)
        self.refresh_tables()
        self.add_log(f"Cargado: {path}")

    def generate_commands(self):
        self.add_log("---- COMANDOS ----")

        for command in build_all_commands(self.devices):
            self.add_log(command)

        self.add_log("------------------")

    def send_commands(self):
        commands = build_all_commands(self.devices)
    
        if not commands:
            self.add_log("No hay comandos para enviar.")
            return
    
        self.add_log("Enviando configuración...")
    
        self.connection.send_command("#CONFIG")
    
        for command in commands:
            self.connection.send_command(command)
    
        self.connection.send_command("#SAVE")
        self.connection.send_command("#END")
    
        self.add_log("Configuración enviada.")

    def closeEvent(self, event):
        self.connection.disconnect()
        super().closeEvent(event)