from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QMessageBox, QSplitter, QGroupBox, QFormLayout
)
from PySide6.QtCore import Qt

from modbus.modbus_model import ModbusDevice, ModbusTag
from modbus.modbus_parser import parse_modbus_line
from modbus.modbus_wizard import ModbusWizard


class ModbusWidget(QWidget):
    def __init__(self, connection, parent=None):
        super().__init__(parent)

        self.connection = connection
        self.capture_active = False
        self.lines = []
        self.devices = []
        self.tags = []

        self.btn_add = QPushButton("Añadir")
        self.btn_delete = QPushButton("Eliminar")
        self.btn_dump = QPushButton("MB.DUMP")
        self.btn_save = QPushButton("MB.SAVE")
        self.btn_load = QPushButton("MB.LOAD")
        self.btn_clear = QPushButton("MB.CLEAR")
        self.btn_lsdev = QPushButton("MB.LSDEV")
        self.btn_lstag = QPushButton("MB.LSTAG")

        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(7)
        self.devices_table.setHorizontalHeaderLabels([
            "ID", "Nombre", "Bus", "IP", "Puerto", "Unit", "Periodo"
        ])
        self.devices_table.horizontalHeader().setStretchLastSection(True)
        self.devices_table.setAlternatingRowColors(True)
        self.devices_table.setSelectionBehavior(QTableWidget.SelectRows)

        self.tags_table = QTableWidget()
        self.tags_table.setColumnCount(9)
        self.tags_table.setHorizontalHeaderLabels([
            "Dir", "Dev", "Func", "Addr", "Qty",
            "Nombre", "Periodo", "Scale", "Offset"
        ])
        self.tags_table.horizontalHeader().setStretchLastSection(True)
        self.tags_table.setAlternatingRowColors(True)
        self.tags_table.setSelectionBehavior(QTableWidget.SelectRows)

        self.get_edit = QLineEdit()
        self.get_edit.setPlaceholderText("Nombre tag para MB.READ")

        self.btn_get = QPushButton("MB.READ")

        self.set_name_edit = QLineEdit()
        self.set_name_edit.setPlaceholderText("Nombre tag salida")

        self.set_value_edit = QLineEdit()
        self.set_value_edit.setPlaceholderText("Valor/es: 1 o 10 20 30")

        self.btn_set = QPushButton("MB.SET")

        tag_control = QGroupBox("Lectura / Escritura")
        tag_form = QFormLayout()
        tag_form.addRow("Leer tag:", self.get_edit)
        tag_form.addRow("", self.btn_get)
        tag_form.addRow("Escribir tag:", self.set_name_edit)
        tag_form.addRow("Valor:", self.set_value_edit)
        tag_form.addRow("", self.btn_set)
        tag_control.setLayout(tag_form)

        self.command_edit = QLineEdit()
        self.command_edit.setPlaceholderText(
            "Comando manual: MB.ADDDEV..., MODBUS.ADD..., MB.SET..."
        )

        self.btn_send_manual = QPushButton("Enviar")

        manual_row = QHBoxLayout()
        manual_row.addWidget(self.command_edit)
        manual_row.addWidget(self.btn_send_manual)

        self.status = QLabel("Modbus listo")

        top = QHBoxLayout()
        top.addWidget(self.btn_add)
        top.addWidget(self.btn_delete)
        top.addStretch()
        top.addWidget(self.btn_dump)
        top.addWidget(self.btn_save)
        top.addWidget(self.btn_load)
        top.addWidget(self.btn_clear)
        top.addWidget(self.btn_lsdev)
        top.addWidget(self.btn_lstag)

        devices_box = QGroupBox("Esclavos Modbus")
        devices_layout = QVBoxLayout()
        devices_layout.addWidget(self.devices_table)
        devices_box.setLayout(devices_layout)

        tags_box = QGroupBox("Variables / Tags")
        tags_layout = QVBoxLayout()
        tags_layout.addWidget(self.tags_table)
        tags_box.setLayout(tags_layout)

        splitter = QSplitter(Qt.Vertical)
        splitter.addWidget(devices_box)
        splitter.addWidget(tags_box)
        splitter.setSizes([230, 330])

        layout = QVBoxLayout()
        layout.addLayout(top)
        layout.addWidget(splitter)
        layout.addWidget(tag_control)
        layout.addLayout(manual_row)
        layout.addWidget(self.status)

        self.setLayout(layout)

        self.btn_add.clicked.connect(self.add_with_wizard)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_dump.clicked.connect(lambda: self.send_mb_command("MB.DUMP"))
        self.btn_save.clicked.connect(lambda: self.send_mb_command("MB.SAVE"))
        self.btn_load.clicked.connect(lambda: self.send_mb_command("MB.LOAD"))
        self.btn_clear.clicked.connect(self.confirm_clear)
        self.btn_lsdev.clicked.connect(lambda: self.send_mb_command("MB.LSDEV"))
        self.btn_lstag.clicked.connect(lambda: self.send_mb_command("MB.LSTAG"))

        self.btn_get.clicked.connect(self.send_get)
        self.btn_set.clicked.connect(self.send_set)
        self.btn_send_manual.clicked.connect(self.send_manual)

        self.connection.received.connect(self.on_received)

    def add_with_wizard(self):
        wizard = ModbusWizard(self)

        if wizard.exec():
            command = wizard.get_command()

            if wizard.mode() == "DEVICE":
                device = wizard.get_device()
                self.devices.append(device)
                self.refresh_devices_table()
            else:
                tag = wizard.get_tag()
                self.tags.append(tag)
                self.refresh_tags_table()

            self.connection.send_command(command)
            self.connection.send_command("MB.SAVE")
            self.status.setText(f"Enviado: {command}")

    def refresh_devices_table(self):
        self.devices_table.setRowCount(0)

        for dev in self.devices:
            row = self.devices_table.rowCount()
            self.devices_table.insertRow(row)

            self.devices_table.setItem(row, 0, QTableWidgetItem(str(dev.dev_id)))
            self.devices_table.setItem(row, 1, QTableWidgetItem(dev.name))
            self.devices_table.setItem(row, 2, QTableWidgetItem(dev.bus))
            self.devices_table.setItem(row, 3, QTableWidgetItem(dev.ip))
            self.devices_table.setItem(row, 4, QTableWidgetItem(str(dev.port)))
            self.devices_table.setItem(row, 5, QTableWidgetItem(str(dev.unit)))
            self.devices_table.setItem(row, 6, QTableWidgetItem(str(dev.period)))

    def refresh_tags_table(self):
        self.tags_table.setRowCount(0)

        for tag in self.tags:
            row = self.tags_table.rowCount()
            self.tags_table.insertRow(row)

            self.tags_table.setItem(row, 0, QTableWidgetItem(tag.direction))
            self.tags_table.setItem(row, 1, QTableWidgetItem(str(tag.dev_id)))
            self.tags_table.setItem(row, 2, QTableWidgetItem(tag.func))
            self.tags_table.setItem(row, 3, QTableWidgetItem(str(tag.addr)))
            self.tags_table.setItem(row, 4, QTableWidgetItem(str(tag.qty)))
            self.tags_table.setItem(row, 5, QTableWidgetItem(tag.name))
            self.tags_table.setItem(row, 6, QTableWidgetItem(str(tag.period)))
            self.tags_table.setItem(row, 7, QTableWidgetItem(f"{tag.scale:.3f}"))
            self.tags_table.setItem(row, 8, QTableWidgetItem(f"{tag.offset:.3f}"))

    def delete_selected(self):
        tag_row = self.tags_table.currentRow()
        dev_row = self.devices_table.currentRow()

        if tag_row >= 0 and self.tags_table.hasFocus():
            self.delete_tag(tag_row)
            return

        if dev_row >= 0 and self.devices_table.hasFocus():
            self.delete_device(dev_row)
            return

        if tag_row >= 0:
            self.delete_tag(tag_row)
            return

        if dev_row >= 0:
            self.delete_device(dev_row)
            return

        QMessageBox.warning(self, "Eliminar", "Selecciona un esclavo o una variable.")

    def delete_device(self, row):
        if row < 0 or row >= len(self.devices):
            return

        dev = self.devices[row]

        reply = QMessageBox.question(
            self,
            "Eliminar esclavo",
            (
                f"Vas a eliminar el esclavo Modbus:\n\n"
                f"ID: {dev.dev_id}\n"
                f"Nombre: {dev.name}\n\n"
                f"También se eliminarán sus tags en el ESP32.\n\n"
                f"¿Continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        command = f"MB.DELDEV {dev.dev_id}"
        self.connection.send_command(command)
        self.connection.send_command("MB.SAVE")

        self.devices.pop(row)
        self.tags = [t for t in self.tags if t.dev_id != dev.dev_id]

        self.refresh_devices_table()
        self.refresh_tags_table()

        self.status.setText(f"Eliminado esclavo: {dev.name}")

    def delete_tag(self, row):
        if row < 0 or row >= len(self.tags):
            return

        tag = self.tags[row]

        reply = QMessageBox.question(
            self,
            "Eliminar tag",
            (
                f"Vas a eliminar el tag Modbus:\n\n"
                f"Nombre: {tag.name}\n"
                f"Dev: {tag.dev_id}\n"
                f"Func: {tag.func}\n\n"
                f"¿Continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        command = f"MB.DELTAG {tag.name}"
        self.connection.send_command(command)
        self.connection.send_command("MB.SAVE")

        self.tags.pop(row)
        self.refresh_tags_table()

        self.status.setText(f"Eliminado tag: {tag.name}")

    def send_get(self):
        name = self.get_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "MB.READ", "Introduce el nombre del tag.")
            return

        self.connection.send_command(f"MB.READ {name}")
        self.status.setText(f"Enviado: MB.READ {name}")

    def send_set(self):
        name = self.set_name_edit.text().strip()
        value = self.set_value_edit.text().strip()

        if not name:
            QMessageBox.warning(self, "MB.SET", "Introduce el nombre del tag.")
            return

        if not value:
            QMessageBox.warning(self, "MB.SET", "Introduce el valor.")
            return

        command = f"MB.SET {name} {value}"
        self.connection.send_command(command)
        self.status.setText(f"Enviado: {command}")

    def send_mb_command(self, command: str):
        self.connection.send_command(command)
        self.status.setText(f"Enviado: {command}")

    def confirm_clear(self):
        reply = QMessageBox.question(
            self,
            "Confirmar MB.CLEAR",
            (
                "Vas a borrar la configuración Modbus guardada.\n\n"
                "¿Quieres continuar?"
            ),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply != QMessageBox.Yes:
            return

        self.connection.send_command("MB.CLEAR")
        self.devices = []
        self.tags = []
        self.refresh_devices_table()
        self.refresh_tags_table()
        self.status.setText("Enviado: MB.CLEAR")

    def send_manual(self):
        command = self.command_edit.text().strip()

        if not command:
            return

        upper = command.upper()

        if not upper.startswith("MB.") and not upper.startswith("MODBUS."):
            command = "MB." + command

        self.connection.send_command(command)
        self.command_edit.clear()
        self.status.setText(f"Enviado: {command}")

    def on_received(self, text: str):
        line = text.strip()

        if line == "BEGIN MB":
            self.capture_active = True
            self.lines = []
            self.devices = []
            self.tags = []
            self.status.setText("Leyendo Modbus...")
            return

        if line == "END MB":
            self.capture_active = False
            self.refresh_devices_table()
            self.refresh_tags_table()
            self.status.setText(
                f"Modbus leído: {len(self.devices)} esclavos, {len(self.tags)} tags"
            )
            return

        if self.capture_active:
            self.parse_dump_line(line)
            return

        if line.startswith("MB.VAL "):
            self.status.setText(line)
            return

        if line.startswith("MB.READ "):
            self.status.setText(line)
            return

        if line.startswith("MB.SET"):
            self.status.setText(line)
            return

        if line.startswith("✅") or line.startswith("⚠️") or line.startswith("❌"):
            self.status.setText(line)
            return

    def parse_dump_line(self, line: str):
        self.lines.append(parse_modbus_line(line))

        if line.startswith("MB.DEV "):
            self.parse_device_line(line)
            return

        if line.startswith("MB.TAG "):
            self.parse_tag_line(line)
            return

    def parse_device_line(self, line: str):
        # Firmware actual:
        # MB.DEV <id> <ip> <unit>
        parts = line.split()

        if len(parts) < 4:
            return

        try:
            dev_id = int(parts[1])
            ip = parts[2]
            unit = int(parts[3])

            dev = ModbusDevice(
                dev_id=dev_id,
                name=f"DEV{dev_id}",
                ip=ip,
                port=502,
                unit=unit,
                period=0,
                bus="TCP",
            )

            self.devices.append(dev)
        except Exception:
            pass

    def parse_tag_line(self, line: str):
        # MB.TAG <OUT|IN> <devId> <func> <addr> <qty> <name> <period> <scale> <offset>
        parts = line.split()

        if len(parts) < 10:
            return

        try:
            tag = ModbusTag(
                direction=parts[1].upper(),
                dev_id=int(parts[2]),
                func=parts[3].upper(),
                addr=int(parts[4]),
                qty=int(parts[5]),
                name=parts[6],
                period=int(parts[7]),
                scale=float(parts[8]),
                offset=float(parts[9]),
            )
            self.tags.append(tag)
        except Exception:
            pass