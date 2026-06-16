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
from modbus.modbus_widget import ModbusWidget
from module_wizard import ModuleWizard
from manual_console import ManualConsole
from widgets.serial_port_combobox import SerialPortComboBox

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EasySim Programmer")
        self.resize(1200, 780)

        self.connection = ConnectionManager()
        self.connection.log.connect(self.add_log)
        self.connection.received.connect(self.on_received)

        self.devices = []

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
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels([
                "Pin", "Nombre", "Valor 1", "Valor 2",
                "Modo", "Opciones", "Acción"
            ])
            table.horizontalHeader().setStretchLastSection(True)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setAlternatingRowColors(True)

            self.tables[kind] = table
            self.tabs.addTab(table, title)
        self.modbus_widget = ModbusWidget(self.connection)
        self.tabs.addTab(self.modbus_widget, "Modbus")

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)

        self.btn_add = QPushButton("Añadir con asistente")
        self.btn_add_module = QPushButton("Añadir módulo IO")
        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_save = QPushButton("Guardar JSON")
        self.btn_load = QPushButton("Cargar JSON")
        self.btn_generate = QPushButton("Generar comandos")
        self.btn_send = QPushButton("Enviar comandos")
        self.btn_dump = QPushButton("#DUMP")
        self.btn_manual = QPushButton("Consola manual")

        self.btn_add.clicked.connect(self.add_device)
        self.btn_add_module.clicked.connect(self.open_module_wizard)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_save.clicked.connect(self.save_json)
        self.btn_load.clicked.connect(self.load_json)
        self.btn_generate.clicked.connect(self.generate_commands)
        self.btn_send.clicked.connect(self.send_commands)
        self.btn_dump.clicked.connect(self.request_dump)
        self.btn_manual.clicked.connect(self.open_console)

        self.sim_check = QCheckBox("Simulación")
        self.sim_check.setChecked(False)
        self.sim_check.stateChanged.connect(self.on_simulation_changed)

        self.connection_type = QComboBox()
        self.connection_type.addItems(["TCP", "Serial"])
        self.connection_type.setFixedWidth(80)
        self.connection_type.currentTextChanged.connect(
            self.on_connection_type_changed
        )

        self.ip_edit = QLineEdit()
        self.ip_edit.setPlaceholderText("IP dispositivo")
        self.ip_edit.setText("192.168.1.177")
        self.ip_edit.setFixedWidth(130)

        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(5000)
        self.port_spin.setFixedWidth(90)

        self.serial_port_edit = SerialPortComboBox()
        self.serial_port_edit.setFixedWidth(140)

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
        self.lbl_ip = QLabel("IP:")
        self.lbl_port = QLabel("Puerto:")
        self.lbl_serial = QLabel("Serial:")
        self.lbl_baud = QLabel("Baud:")

        connection_row.addWidget(self.lbl_ip)
        connection_row.addWidget(self.ip_edit)

        connection_row.addWidget(self.lbl_port)
        connection_row.addWidget(self.port_spin)

        connection_row.addWidget(self.lbl_serial)
        connection_row.addWidget(self.serial_port_edit)

        connection_row.addWidget(self.lbl_baud)
        connection_row.addWidget(self.baud_spin)
        connection_row.addWidget(self.btn_connect)
        connection_row.addWidget(self.btn_disconnect)
        connection_row.addStretch()
        connection_box.setLayout(connection_row)

        button_row = QHBoxLayout()
        button_row.setContentsMargins(0, 0, 0, 0)
        button_row.setSpacing(8)
        button_row.addWidget(self.btn_add)
        button_row.addWidget(self.btn_add_module)
        button_row.addWidget(self.btn_delete)
        button_row.addWidget(self.btn_manual)
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
        self.on_connection_type_changed(
            self.connection_type.currentText()
        )
        self.setCentralWidget(root)

    def add_log(self, text):
        self.log.append(text)

    # ==========================================================
    # CONFIRMACIONES / BORRADO REAL
    # ==========================================================

    def confirm_delete_device(self, device):
        title = "Confirmar eliminación"

        if device.kind == "SELECTOR":
            message = (
                f"Vas a eliminar este contacto del selector:\n\n"
                f"Selector: {device.name}\n"
                f"Pin: {device.pin}\n"
                f"Valor: {device.value1:g}\n\n"
                f"¿Quieres continuar?"
            )
        else:
            message = (
                f"Vas a eliminar este elemento:\n\n"
                f"Tipo: {device.kind}\n"
                f"Nombre: {device.name}\n"
                f"Pin: {device.pin}\n\n"
                f"¿Quieres continuar?"
            )

        reply = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def build_delete_command(self, device):
        if device.kind == "SELECTOR":
            return f"SEL.DELPIN {device.pin}"

        return f"#DELETEPIN {device.pin}"

    def send_delete_command(self, device):
        command = self.build_delete_command(device)

        self.connection.send_command("#CONFIG")
        self.connection.send_command(command)
        self.connection.send_command("#END")

        self.add_log(f"🗑️ Borrado enviado: {command}")

    def confirm_replace_from_dump(self):
        if not self.devices:
            return True

        reply = QMessageBox.question(
            self,
            "Importar configuración",
            (
                "El #DUMP recibido sustituirá la configuración actual de las tablas.\n\n"
                "¿Quieres continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

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
            if not self.confirm_replace_from_dump():
                self.dump_active = False
                self.dump_devices = {}
                self.add_log("Importación cancelada por el usuario.")
                return

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
    def on_connection_type_changed(self, mode):
        is_tcp = mode == "TCP"

        self.lbl_ip.setVisible(is_tcp)
        self.ip_edit.setVisible(is_tcp)

        self.lbl_port.setVisible(is_tcp)
        self.port_spin.setVisible(is_tcp)

        self.lbl_serial.setVisible(not is_tcp)
        self.serial_port_edit.setVisible(not is_tcp)

        self.lbl_baud.setVisible(not is_tcp)
        self.baud_spin.setVisible(not is_tcp)


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
            port_name = self.serial_port_edit.currentPort()
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
            devices = wizard.get_devices()

            if not devices:
                return

            self.devices.extend(devices)
            self.refresh_tables()

            for device in devices:
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

            btn_delete = QPushButton("✖")
            btn_delete.setToolTip("Eliminar este elemento")
            btn_delete.setStyleSheet(
                "background-color: #c0392b;"
                "color: white;"
                "border-radius: 4px;"
                "padding: 2px;"
                "font-weight: bold;"
            )
            btn_delete.clicked.connect(lambda _, d=device: self.delete_device(d))

            table.setCellWidget(row, 6, btn_delete)

    def describe_options(self, device):
        if device.kind == "POT":
            return (
                f"{device.min_in}-{device.max_in} → "
                f"{device.min_out}-{device.max_out}, "
                f"smooth={device.smooth}, "
                f"{'INT' if device.as_integer else 'FLOAT'}"
            )

        if device.kind == "SELECTOR":
            return f"Posición selector = {device.value1:g}"

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

        if not self.confirm_delete_device(device):
            return

        self.send_delete_command(device)

        self.devices.remove(device)
        self.refresh_tables()

        self.add_log(f"Eliminado {device.kind}: {device.name} (pin {device.pin})")

    def delete_device(self, device):
        if device not in self.devices:
            return

        if not self.confirm_delete_device(device):
            return

        self.send_delete_command(device)

        self.devices.remove(device)
        self.refresh_tables()

        self.add_log(f"Eliminado {device.kind}: {device.name} (pin {device.pin})")

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
        normal_commands = build_all_commands(self.devices)

        modbus_commands = []
        if hasattr(self, "modbus_widget"):
            modbus_commands = self.modbus_widget.build_all_commands()

        if not normal_commands and not modbus_commands:
            self.add_log("No hay comandos para enviar.")
            return

        self.add_log("Enviando configuración completa...")

        self.connection.send_command("#CONFIG")

        for command in normal_commands:
            self.connection.send_command(command)

        self.connection.send_command("#SAVE")

        # Modbus: limpiar siempre antes de reenviar
        if hasattr(self, "modbus_widget"):
            self.connection.send_command("MB.CLEAR")

            for command in modbus_commands:
                self.connection.send_command(command)

            self.connection.send_command("MB.SAVE")

        self.connection.send_command("#END")

        self.add_log("Configuración completa enviada.")
    
    def open_module_wizard(self):
        wizard = ModuleWizard(devices=self.devices, parent=self)
    
        if wizard.exec():
            devices = wizard.get_devices()
    
            if not devices:
                return
    
            self.devices.extend(devices)
            self.refresh_tables()
    
            for device in devices:
                self.add_log(
                    f"Añadido desde módulo {device.kind}: "
                    f"pin={device.pin}, name={device.name}"
                )
    
    def open_console(self):
        dlg = ManualConsole(self.connection, self)
        dlg.exec()

    def closeEvent(self, event):
        self.connection.disconnect()
        super().closeEvent(event)