from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem,
    QTextEdit, QFileDialog, QTabWidget, QMessageBox,
    QLabel, QLineEdit, QSpinBox, QCheckBox, QComboBox,
    QGroupBox
)
from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction

from wizard.device_wizard import DeviceWizard
from storage import save_devices, load_devices
from commands.command_builder import build_all_commands
from connection_manager import ConnectionManager
from models.device import Device
from modbus.modbus_widget import ModbusWidget
from module_wizard import ModuleWizard
from manual_console import ManualConsole
from widgets.serial_port_combobox import SerialPortComboBox
from parameter_catalog import ParameterCatalog
from bluetooth_ota import BluetoothOtaDialog


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("EasySim Programmer")
        self.resize(1200, 780)

        self.parameter_catalog = ParameterCatalog()
        self.create_menu()

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
            ("CANBUS", "CAN bus"),
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
        self.btn_edit = QPushButton("Editar seleccionado")
        self.btn_delete = QPushButton("Eliminar seleccionado")
        self.btn_save = QPushButton("Guardar JSON")
        self.btn_load = QPushButton("Cargar JSON")
        self.btn_generate = QPushButton("Generar comandos")
        self.btn_send = QPushButton("Enviar comandos")
        self.btn_dump = QPushButton("#DUMP")
        self.btn_manual = QPushButton("Consola manual")
        self.btn_ble_ota = QPushButton("OTA Bluetooth")

        self.btn_add.clicked.connect(self.add_device)
        self.btn_add_module.clicked.connect(self.open_module_wizard)
        self.btn_edit.clicked.connect(self.edit_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_save.clicked.connect(self.save_json)
        self.btn_load.clicked.connect(self.load_json)
        self.btn_generate.clicked.connect(self.generate_commands)
        self.btn_send.clicked.connect(self.send_commands)
        self.btn_dump.clicked.connect(self.request_dump)
        self.btn_manual.clicked.connect(self.open_console)
        self.btn_ble_ota.clicked.connect(self.open_ble_ota)

        self.sim_check = QCheckBox("Simulación")
        self.sim_check.setChecked(False)
        self.sim_check.stateChanged.connect(self.on_simulation_changed)

        self.auto_reconnect_check = QCheckBox("Auto reconectar")
        self.auto_reconnect_check.setChecked(False)
        self.auto_reconnect_check.stateChanged.connect(self.on_auto_reconnect_changed)

        self.auto_reconnect_timer = QTimer(self)
        self.auto_reconnect_timer.setInterval(3000)
        self.auto_reconnect_timer.timeout.connect(self.try_auto_reconnect)

        self.connection_type = QComboBox()
        self.connection_type.addItems(["TCP", "Serial"])
        self.connection_type.setFixedWidth(80)
        self.connection_type.currentTextChanged.connect(self.on_connection_type_changed)

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
        connection_row.addWidget(self.auto_reconnect_check)

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
        button_row.addWidget(self.btn_edit)
        button_row.addWidget(self.btn_delete)
        button_row.addWidget(self.btn_manual)
        button_row.addWidget(self.btn_ble_ota)
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

        self.on_connection_type_changed(self.connection_type.currentText())
        self.setCentralWidget(root)

    def create_menu(self):
        file_menu = self.menuBar().addMenu("Archivo")

        action_open_catalog = QAction("Abrir catálogo de controles JSON...", self)
        action_open_catalog.triggered.connect(self.open_parameter_catalog)
        file_menu.addAction(action_open_catalog)

        action_ble_ota = QAction("OTA por Bluetooth...", self)
        action_ble_ota.triggered.connect(self.open_ble_ota)
        file_menu.addAction(action_ble_ota)

    def open_parameter_catalog(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Abrir catálogo de controles",
            "",
            "JSON (*.json)"
        )

        if not path:
            return

        try:
            self.parameter_catalog.load(path)
            self.add_log(
                f"Catálogo cargado correctamente: "
                f"{len(self.parameter_catalog.parameters)} controles."
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Error cargando catálogo",
                str(e)
            )

    def add_log(self, text):
        self.log.append(text)

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
            "CAN BUS": "CANBUS",
            "CANBUS": "CANBUS",
        }

        return mapping.get(kind, kind)

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
        elif device.kind == "CANBUS":
            message = (
                f"Vas a eliminar este elemento CAN:\n\n"
                f"Subtipo: {getattr(device, 'can_kind', 'BUTTON')}\n"
                f"Nombre: {device.name}\n"
                f"Canal: {device.pin}\n\n"
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

    def get_selector_group(self, device):
        if not device or device.kind != "SELECTOR":
            return []

        return [
            item for item in self.devices
            if item.kind == "SELECTOR" and item.name == device.name
        ]

    def get_table_devices(self, kind):
        if kind != "SELECTOR":
            return [device for device in self.devices if device.kind == kind]

        selector_rows = []
        seen_names = set()

        for device in self.devices:
            if device.kind != "SELECTOR" or device.name in seen_names:
                continue

            selector_rows.append(device)
            seen_names.add(device.name)

        return selector_rows

    def is_testable_output(self, device):
        if not device:
            return False

        if device.kind == "OUTPUT":
            return True

        return (
            device.kind == "CANBUS"
            and str(getattr(device, "can_kind", "")).upper() == "OUTPUT"
        )

    def send_test_output_value(self, device, value):
        value = 1 if value else 0

        if device.kind == "OUTPUT":
            if getattr(device, "name", ""):
                command = f"{device.name}={value}"
                self.connection.send_command(command)
                self.add_log(
                    f"Prueba salida {device.name} (pin {device.pin}) = {value}"
                )
            else:
                self.connection.write_output(device.pin, value)
                self.add_log(
                    f"Prueba salida directa pin {device.pin} = {value}"
                )
            return

        if device.kind == "CANBUS" and str(getattr(device, "can_kind", "")).upper() == "OUTPUT":
            command = f"{device.name}={value}"
            self.connection.send_command(command)
            self.add_log(f"Prueba salida CAN {device.name} ({device.pin}) = {value}")
            return

    def build_action_widget(self, kind, device):
        panel = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(6)

        if self.is_testable_output(device):
            btn_test = QPushButton("Test")
            btn_test.setToolTip("Mantener pulsado para activar la salida")
            btn_test.setStyleSheet(
                "background-color: #2e8b57;"
                "color: white;"
                "border-radius: 4px;"
                "padding: 2px 8px;"
                "font-weight: bold;"
            )
            btn_test.pressed.connect(lambda d=device: self.send_test_output_value(d, 1))
            btn_test.released.connect(lambda d=device: self.send_test_output_value(d, 0))
            layout.addWidget(btn_test)

        btn_delete = QPushButton("✖")
        btn_delete.setToolTip(
            "Eliminar selector completo" if kind == "SELECTOR" else "Eliminar este elemento"
        )
        btn_delete.setStyleSheet(
            "background-color: #c0392b;"
            "color: white;"
            "border-radius: 4px;"
            "padding: 2px;"
            "font-weight: bold;"
        )
        btn_delete.clicked.connect(lambda _, d=device: self.delete_device(d))
        layout.addWidget(btn_delete)
        layout.addStretch()

        panel.setLayout(layout)
        return panel

    def describe_selector_group(self, device):
        selector_devices = sorted(
            self.get_selector_group(device),
            key=lambda item: float(item.value1),
        )

        if not selector_devices:
            return "", "", ""

        pins_text = ", ".join(str(item.pin) for item in selector_devices)
        values_text = ", ".join(f"{float(item.value1):g}" for item in selector_devices)
        contacts_text = f"{len(selector_devices)} contactos"

        return pins_text, contacts_text, values_text

    def confirm_delete_selector_group(self, device):
        selector_devices = self.get_selector_group(device)
        total = len(selector_devices)

        if total <= 1:
            return self.confirm_delete_device(device)

        pins = ", ".join(str(item.pin) for item in selector_devices)
        reply = QMessageBox.question(
            self,
            "Confirmar eliminación",
            (
                f"Vas a eliminar el selector completo:\n\n"
                f"Selector: {device.name}\n"
                f"Contactos: {total}\n"
                f"Pines: {pins}\n\n"
                f"¿Quieres continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        return reply == QMessageBox.Yes

    def build_delete_command(self, device):
        if device.kind == "SELECTOR":
            return f"SEL.DELPIN {device.pin}"

        if device.kind == "CANBUS":
            return f"#DELETEPIN CAN{device.can_node}:{device.can_channel}"

        return f"#DELETEPIN {device.pin}"

    def send_delete_command(self, device):
        command = self.build_delete_command(device)

        self.connection.send_command("#CONFIG")
        self.connection.send_command(command)
        self.connection.send_command("#END")

        self.add_log(f"🗑️ Borrado enviado: {command}")

    def send_delete_selector_group(self, device):
        selector_devices = self.get_selector_group(device)

        if not selector_devices:
            return

        self.connection.send_command("#CONFIG")

        for item in selector_devices:
            command = self.build_delete_command(item)
            self.connection.send_command(command)
            self.add_log(f"🗑️ Borrado enviado: {command}")

        self.connection.send_command("#END")

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
            self.apply_runtime_cfg_feedback(line)
            return

        self.parse_dump_line(line)

    def apply_runtime_cfg_feedback(self, line: str):
        parts = line.split()
        if len(parts) < 5:
            return

        if parts[0].upper() != "OK" or parts[1].upper() != "CFG":
            return

        if parts[3].upper() != "OUTINV":
            return

        enabled = parts[4].upper() in ("ON", "TRUE", "1")
        target = parts[2].upper()
        changed = False

        if target == "ALL":
            for device in self.devices:
                if device.kind == "OUTPUT":
                    device.output_inverted = enabled
                    changed = True
                elif (
                    device.kind == "CANBUS"
                    and str(getattr(device, "can_kind", "")).upper() == "OUTPUT"
                ):
                    device.output_inverted = enabled
                    changed = True
        else:
            for device in self.devices:
                if device.kind == "OUTPUT" and str(device.pin).upper() == target:
                    device.output_inverted = enabled
                    changed = True
                elif (
                    device.kind == "CANBUS"
                    and str(getattr(device, "can_kind", "")).upper() == "OUTPUT"
                    and f"CAN{int(getattr(device, 'can_node', 0))}:{int(getattr(device, 'can_channel', 0))}" == target
                ):
                    device.output_inverted = enabled
                    changed = True

        if changed:
            self.refresh_tables()

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

        if head == "NOTCH":
            self.parse_notch_line(parts)
            return

        if head.startswith("POT.SPLIT"):
            self.parse_pot_split_line(parts)
            return

    def parse_add_line(self, parts):
        if len(parts) < 5:
            return

        kind = parts[1].upper()
        pin_text = parts[2]
        name = parts[3]

        try:
            value1 = float(parts[4])
            value2 = float(parts[5]) if len(parts) > 5 else 1
        except Exception:
            return

        try:
            if pin_text.strip().upper().startswith("CAN") and kind in ("BUTTON", "SWITCH", "OUTPUT"):
                can_node, can_channel = self.parse_can_ref(pin_text)
                pin = f"CAN{can_node}:{can_channel}"
                device = Device(
                    kind="CANBUS",
                    pin=pin,
                    name=name,
                    can_kind=kind,
                    can_node=can_node,
                    can_channel=can_channel,
                    value1=value1,
                    value2=value2,
                    min_out=value1,
                    max_out=value2,
                )
                self.dump_devices[("CANBUS", can_node, can_channel, name)] = device
                return

            pin = self.parse_pin(pin_text)
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

        if field == "OUTINV" and len(parts) >= 4:
            device = self.get_dump_output_device(pin)
            if device is None:
                return
            device.output_inverted = parts[3].upper() in ("ON", "TRUE", "1")
            return

        device = self.get_dump_pot_device(pin)
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
                device.pot_threshold = float(parts[3])

        except Exception:
            pass

    def get_dump_pot_device(self, pin):
        for dev in self.dump_devices.values():
            if dev.kind == "POT" and dev.pin == pin:
                return dev
        return None

    def get_dump_output_device(self, pin):
        for dev in self.dump_devices.values():
            if dev.kind == "OUTPUT" and dev.pin == pin:
                return dev
            if (
                dev.kind == "CANBUS"
                and str(getattr(dev, "can_kind", "")).upper() == "OUTPUT"
                and str(dev.pin) == str(pin)
            ):
                return dev
        return None

    def rebuild_dump_notches(self, device):
        values = getattr(device, "_dump_notch_values", [])
        centers = getattr(device, "_dump_notch_centers", [])

        if not values:
            device.pot_notches_enabled = False
            device.pot_notches = []
            return

        notches = []
        for index, out_value in enumerate(values):
            raw_value = centers[index] if index < len(centers) else None
            notches.append((raw_value, out_value))

        device.pot_notches_enabled = True
        device.pot_notches = notches

    def parse_notch_line(self, parts):
        if len(parts) < 3:
            return

        sub = parts[1].upper()

        try:
            pin = self.parse_pin(parts[2])
        except Exception:
            return

        device = self.get_dump_pot_device(pin)
        if device is None:
            return

        try:
            if sub == "COUNT" and len(parts) >= 4:
                count = int(parts[3])
                device.pot_notches_enabled = count > 0
                if count <= 0:
                    device.pot_notches = []
                    device._dump_notch_values = []
                    device._dump_notch_centers = []

            elif sub == "HYST" and len(parts) >= 4:
                device.pot_notch_hyst = float(parts[3])

            elif sub == "LIST.VALS" and len(parts) >= 4:
                values = [
                    float(item) for item in parts[3].split(",")
                    if item.strip()
                ]
                device._dump_notch_values = values
                self.rebuild_dump_notches(device)

            elif sub == "LIST.CENT" and len(parts) >= 4:
                centers = [
                    int(item) for item in parts[3].split(",")
                    if item.strip()
                ]
                device._dump_notch_centers = centers
                self.rebuild_dump_notches(device)

            elif sub == "PARTIAL" and len(parts) >= 4:
                device.pot_notch_partial = parts[3].upper() in ("ON", "TRUE", "1")

            elif sub == "SNAPWIN" and len(parts) >= 4:
                device.pot_notch_snapwin = float(parts[3])

        except Exception:
            pass

    def parse_pot_split_line(self, parts):
        if len(parts) < 3:
            return

        head = parts[0].upper()

        try:
            pin = self.parse_pin(parts[1])
        except Exception:
            return

        device = self.get_dump_pot_device(pin)
        if device is None:
            return

        try:
            if head == "POT.SPLIT" and len(parts) >= 3:
                device.pot_split_mode = parts[2].upper()

            elif head == "POT.SPLIT.DB" and len(parts) >= 3:
                device.pot_split_deadband = float(parts[2])

            elif head == "POT.SPLIT.CBIAS" and len(parts) >= 3:
                device.pot_split_center_bias = float(parts[2])

            elif head == "POT.SPLIT.TAG" and len(parts) >= 3:
                device.pot_split_tag = parts[2]

            elif head == "POT.SPLIT.TAGS" and len(parts) >= 4:
                device.pot_split_tag_fwd = parts[2]
                device.pot_split_tag_back = parts[3]

        except Exception:
            pass

    def parse_can_ref(self, text: str):
        raw = text.strip().upper()

        if not raw.startswith("CAN") or ":" not in raw:
            raise ValueError("Referencia CAN inválida")

        body = raw[3:]
        node_text, channel_text = body.split(":", 1)

        return int(node_text), int(channel_text)

    def parse_pin(self, text: str):
        text = text.strip().upper()

        if text.startswith("CAN"):
            return text

        if text.startswith("ADS"):
            return text

        return int(text)

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

        self.auto_reconnect_check.setVisible(is_tcp)

        if not is_tcp:
            self.auto_reconnect_timer.stop()

    def on_auto_reconnect_changed(self):
        if (
            self.auto_reconnect_check.isChecked()
            and self.connection_type.currentText() == "TCP"
            and not self.sim_check.isChecked()
        ):
            self.auto_reconnect_timer.start()
            self.add_log("Auto reconexión TCP activada.")
        else:
            self.auto_reconnect_timer.stop()
            self.add_log("Auto reconexión TCP desactivada.")

    def try_auto_reconnect(self):
        if not self.auto_reconnect_check.isChecked():
            self.auto_reconnect_timer.stop()
            return

        if self.sim_check.isChecked():
            return

        if self.connection_type.currentText() != "TCP":
            self.auto_reconnect_timer.stop()
            return

        if self.connection.connected:
            return

        ip = self.ip_edit.text().strip()
        port = self.port_spin.value()

        if not ip:
            return

        self.add_log(f"Auto reconexión TCP: intentando {ip}:{port}...")
        self.connection.connect_tcp(ip, port)

    def on_simulation_changed(self):
        self.connection.set_simulation(self.sim_check.isChecked())

        if self.sim_check.isChecked():
            self.auto_reconnect_timer.stop()
        elif self.auto_reconnect_check.isChecked() and self.connection_type.currentText() == "TCP":
            self.auto_reconnect_timer.start()

    def connect_selected(self):
        if self.sim_check.isChecked():
            self.add_log("La simulación está activada.")
            return

        mode = self.connection_type.currentText()
        self.connection.auto_reconnect = self.auto_reconnect_check.isChecked()

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

            self.connection.auto_reconnect = False
            self.connection.connect_serial(port_name, baud)

        self.sim_check.setChecked(self.connection.simulation)

    def disconnect(self):
        self.auto_reconnect_timer.stop()
        self.auto_reconnect_check.setChecked(False)
        self.connection.disconnect()
        self.add_log("Desconectado.")

    def add_device(self):
        wizard = DeviceWizard(
            self.connection,
            self.devices,
            self,
            parameter_catalog=self.parameter_catalog
        )

        if wizard.exec():
            devices = wizard.get_devices()

            if not devices:
                return

            for device in devices:
                device.kind = self.normalize_kind(device.kind)

            self.devices.extend(devices)
            self.refresh_tables()

            for device in devices:
                self.add_log(
                    f"Añadido {device.kind}: "
                    f"pin={device.pin}, name={device.name}"
                )

    def refresh_tables(self):
        for table in self.tables.values():
            table.setRowCount(0)

        for kind, _title in self.kind_titles:
            table = self.tables.get(kind)

            if not table:
                continue

            for device in self.get_table_devices(kind):
                row = table.rowCount()
                table.insertRow(row)

                if kind == "SELECTOR":
                    pins_text, contacts_text, values_text = self.describe_selector_group(device)
                    table.setItem(row, 0, QTableWidgetItem(pins_text))
                    table.setItem(row, 1, QTableWidgetItem(device.name))
                    table.setItem(row, 2, QTableWidgetItem(contacts_text))
                    table.setItem(row, 3, QTableWidgetItem(""))
                    table.setItem(row, 4, QTableWidgetItem(""))
                    table.setItem(row, 5, QTableWidgetItem(f"Posiciones: {values_text}"))
                elif kind == "CANBUS":
                    table.setItem(row, 0, QTableWidgetItem(str(device.pin)))
                    table.setItem(row, 1, QTableWidgetItem(device.name))
                    table.setItem(
                        row,
                        2,
                        QTableWidgetItem(str(getattr(device, "can_kind", "BUTTON"))),
                    )
                    table.setItem(row, 3, QTableWidgetItem(""))
                    table.setItem(row, 4, QTableWidgetItem(""))
                    table.setItem(row, 5, QTableWidgetItem(self.describe_options(device)))
                else:
                    table.setItem(row, 0, QTableWidgetItem(str(device.pin)))
                    table.setItem(row, 1, QTableWidgetItem(device.name))
                    table.setItem(row, 2, QTableWidgetItem(str(device.value1)))
                    table.setItem(row, 3, QTableWidgetItem(str(device.value2)))
                    table.setItem(row, 4, QTableWidgetItem(device.send_mode))
                    table.setItem(row, 5, QTableWidgetItem(self.describe_options(device)))

                table.setCellWidget(row, 6, self.build_action_widget(kind, device))

    def describe_options(self, device):
        if device.kind == "POT":
            text = (
                f"{device.min_in}-{device.max_in} → "
                f"{device.min_out}-{device.max_out}, "
                f"smooth={device.smooth}, "
                f"{'INT' if device.as_integer else 'FLOAT'}"
            )

            threshold = getattr(device, "pot_threshold", 0.5)
            text += f", thr={threshold:g}"

            if getattr(device, "pot_notches_enabled", False):
                notches = getattr(device, "pot_notches", [])
                text += f", muescas={len(notches)}"

            split_mode = str(getattr(device, "pot_split_mode", "OFF")).upper()
            if split_mode != "OFF":
                text += f", split={split_mode}"

            return text

        if device.kind == "SELECTOR":
            return f"Posición selector = {device.value1:g}"

        if device.kind == "CANBUS":
            text = (
                f"subtipo={getattr(device, 'can_kind', 'BUTTON')}, "
                f"nodo={getattr(device, 'can_node', 0)}, "
                f"canal={getattr(device, 'can_channel', 0)}"
            )
            if (
                str(getattr(device, "can_kind", "")).upper() == "OUTPUT"
                and getattr(device, "output_inverted", False)
            ):
                text += ", invertida=ON"
            return text

        if device.kind == "OUTPUT" and getattr(device, "output_inverted", False):
            return "invertida=ON"

        return ""

    def current_kind(self):
        index = self.tabs.currentIndex()

        if index >= len(self.kind_titles):
            return None

        return self.kind_titles[index][0]

    def get_selected_device_info(self):
        kind = self.current_kind()

        if kind is None:
            return None, None, None, None

        table = self.tables[kind]
        row = table.currentRow()

        if row < 0:
            return kind, table, None, None

        table_devices = self.get_table_devices(kind)

        if row >= len(table_devices):
            return kind, table, None, None

        device = table_devices[row]
        global_index = self.devices.index(device)
        return kind, table, global_index, device

    def replace_selector_group(self, original_device, edited_devices):
        selector_devices = self.get_selector_group(original_device)
        selector_ids = {id(device) for device in selector_devices}

        if not selector_devices:
            return

        insert_at = min(
            index for index, device in enumerate(self.devices)
            if id(device) in selector_ids
        )

        remaining = [
            device for device in self.devices
            if id(device) not in selector_ids
        ]

        self.devices = (
            remaining[:insert_at] +
            edited_devices +
            remaining[insert_at:]
        )

    def edit_selected(self):
        kind, _table, global_index, device = self.get_selected_device_info()

        if kind is None:
            QMessageBox.warning(self, "Editar", "Selecciona una tabla de controles.")
            return

        if device is None:
            QMessageBox.warning(self, "Editar", "Selecciona una fila.")
            return

        if kind == "SELECTOR":
            selector_devices = self.get_selector_group(device)
            wizard = DeviceWizard(
                self.connection,
                self.devices,
                self,
                parameter_catalog=self.parameter_catalog,
                existing_selector_devices=selector_devices,
            )
        else:
            wizard = DeviceWizard(
                self.connection,
                self.devices,
                self,
                parameter_catalog=self.parameter_catalog,
                existing_device=device,
            )

        if not wizard.exec():
            return

        edited_devices = wizard.get_devices()
        if not edited_devices:
            return

        for edited_device in edited_devices:
            edited_device.kind = self.normalize_kind(edited_device.kind)

        if kind == "SELECTOR":
            self.replace_selector_group(device, edited_devices)
            self.refresh_tables()
            self.add_log(
                f"Editado selector {edited_devices[0].name}: "
                f"{len(edited_devices)} contactos"
            )
            return

        edited_device = edited_devices[0]
        self.devices[global_index] = edited_device
        self.refresh_tables()
        self.add_log(f"Editado {edited_device.kind}: pin={edited_device.pin}, name={edited_device.name}")

    def delete_selected(self):
        kind, _table, global_index, device = self.get_selected_device_info()

        if kind is None:
            QMessageBox.warning(self, "Eliminar", "Selecciona una tabla de controles.")
            return

        if device is None:
            QMessageBox.warning(self, "Eliminar", "Selecciona una fila.")
            return

        if kind == "SELECTOR":
            if not self.confirm_delete_selector_group(device):
                return

            selector_devices = self.get_selector_group(device)
            selector_ids = {id(item) for item in selector_devices}
            self.send_delete_selector_group(device)
            self.devices = [item for item in self.devices if id(item) not in selector_ids]
            self.refresh_tables()
            self.add_log(f"Eliminado selector {device.name}: {len(selector_devices)} contactos")
            return

        if not self.confirm_delete_device(device):
            return

        self.send_delete_command(device)

        del self.devices[global_index]
        self.refresh_tables()

        self.add_log(f"Eliminado {device.kind}: {device.name} (pin {device.pin})")

    def delete_device(self, device):
        if device not in self.devices:
            return

        if device.kind == "SELECTOR":
            if not self.confirm_delete_selector_group(device):
                return

            selector_devices = self.get_selector_group(device)
            selector_ids = {id(item) for item in selector_devices}
            self.send_delete_selector_group(device)
            self.devices = [item for item in self.devices if id(item) not in selector_ids]
            self.refresh_tables()
            self.add_log(f"Eliminado selector {device.name}: {len(selector_devices)} contactos")
            return

        if not self.confirm_delete_device(device):
            return

        self.send_delete_command(device)

        self.devices.remove(device)
        self.refresh_tables()

        self.add_log(f"Eliminado {device.kind}: {device.name} (pin {device.pin})")

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
        has_pot_notches = any(
            device.kind == "POT" and (
                getattr(device, "pot_notches_enabled", False) or
                str(getattr(device, "pot_split_mode", "OFF")).upper() != "OFF"
            )
            for device in self.devices
        )

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

        if has_pot_notches:
            self.connection.send_command("NOTCH SAVEALL")

        self.connection.send_command("#SAVE")

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

            for device in devices:
                device.kind = self.normalize_kind(device.kind)

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

    def open_ble_ota(self):
        dlg = BluetoothOtaDialog(self)
        dlg.exec()

    def closeEvent(self, event):
        self.auto_reconnect_timer.stop()
        self.connection.disconnect()
        super().closeEvent(event)
