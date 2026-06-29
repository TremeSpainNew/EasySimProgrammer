import asyncio
import os
import threading

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QTextEdit,
    QVBoxLayout,
)

try:
    from bleak import BleakClient, BleakScanner
except Exception:  # pragma: no cover
    BleakClient = None
    BleakScanner = None


SERVICE_UUID = "7f1a0001-6d8f-4b93-b82e-5b3f87c5d101"
CONTROL_UUID = "7f1a0002-6d8f-4b93-b82e-5b3f87c5d101"
DATA_UUID = "7f1a0003-6d8f-4b93-b82e-5b3f87c5d101"
STATUS_UUID = "7f1a0004-6d8f-4b93-b82e-5b3f87c5d101"
DEVICE_HINTS = ("EASYSIM", "OTA")


class BluetoothOtaDialog(QDialog):
    log_signal = Signal(str)
    scan_signal = Signal(list)
    progress_signal = Signal(int, int)
    phase_signal = Signal(str)
    finished_signal = Signal(bool, str)

    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("OTA por Bluetooth")
        self.resize(720, 460)

        self._status_event = None
        self._last_status = ""

        self.device_combo = QComboBox()
        self.device_combo.setMinimumWidth(320)

        self.address_edit = QLineEdit()
        self.address_edit.setPlaceholderText("Dirección BLE o usa el desplegable")

        self.firmware_edit = QLineEdit()
        self.firmware_edit.setPlaceholderText("Selecciona un firmware .bin")

        self.btn_browse = QPushButton("Buscar bin")
        self.btn_scan = QPushButton("Escanear BLE")
        self.btn_start = QPushButton("Iniciar OTA")
        self.btn_close = QPushButton("Cerrar")

        self.phase_label = QLabel("Listo")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.log_signal.connect(self.log.append)
        self.scan_signal.connect(self._apply_scan_results)
        self.progress_signal.connect(self._update_progress)
        self.phase_signal.connect(self.phase_label.setText)
        self.finished_signal.connect(self._on_finished)

        self.btn_browse.clicked.connect(self.choose_firmware)
        self.btn_scan.clicked.connect(self.scan_devices)
        self.btn_start.clicked.connect(self.start_ota)
        self.btn_close.clicked.connect(self.close)
        self.device_combo.currentTextChanged.connect(self._sync_address_from_combo)

        form = QFormLayout()
        form.addRow("Dispositivo", self.device_combo)

        address_row = QHBoxLayout()
        address_row.addWidget(self.address_edit)
        address_row.addWidget(self.btn_scan)
        form.addRow("Dirección", address_row)

        firmware_row = QHBoxLayout()
        firmware_row.addWidget(self.firmware_edit)
        firmware_row.addWidget(self.btn_browse)
        form.addRow("Firmware", firmware_row)

        action_row = QHBoxLayout()
        action_row.addWidget(self.btn_start)
        action_row.addWidget(self.btn_close)
        action_row.addStretch()

        layout = QVBoxLayout()
        layout.addLayout(form)
        layout.addWidget(self.phase_label)
        layout.addWidget(self.progress)
        layout.addWidget(self.log)
        layout.addLayout(action_row)
        self.setLayout(layout)

        self._set_controls_enabled(True)
        self.scan_devices()

    def _set_controls_enabled(self, enabled: bool):
        self.btn_browse.setEnabled(enabled)
        self.btn_scan.setEnabled(enabled)
        self.btn_start.setEnabled(enabled)
        self.device_combo.setEnabled(enabled)
        self.address_edit.setEnabled(enabled)
        self.firmware_edit.setEnabled(enabled)

    def _log(self, text: str):
        self.log_signal.emit(text)

    def _sync_address_from_combo(self, text: str):
        if not text:
            return

        data = self.device_combo.currentData()
        if data:
            self.address_edit.setText(str(data))

    def choose_firmware(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Seleccionar firmware",
            "",
            "Firmware (*.bin)"
        )

        if path:
            self.firmware_edit.setText(path)

    def _scan_worker(self):
        async def _scan():
            if BleakScanner is None:
                raise RuntimeError("Falta la dependencia bleak. Instala requirements.txt")

            found = []
            devices = await BleakScanner.discover(timeout=5.0)

            for device in devices:
                meta_name = ""
                try:
                    meta_name = (device.metadata or {}).get("local_name", "") or ""
                except Exception:
                    meta_name = ""

                name = (device.name or meta_name or device.address or "").strip()
                upper = name.upper()
                if not any(hint in upper for hint in DEVICE_HINTS):
                    continue

                found.append((name or "Dispositivo BLE", device.address))

            return found

        try:
            devices = asyncio.run(_scan())
            self.scan_signal.emit(devices)
            self.log_signal.emit(f"Escaneo BLE completado: {len(devices)} dispositivo(s) compatibles.")
        except Exception as exc:
            self.log_signal.emit(f"Error escaneando BLE: {exc}")
            self.scan_signal.emit([])

    def scan_devices(self):
        self.phase_signal.emit("Escaneando BLE...")
        self.btn_scan.setEnabled(False)
        threading.Thread(target=self._scan_worker, daemon=True).start()

    def _apply_scan_results(self, devices):
        self.device_combo.blockSignals(True)
        self.device_combo.clear()

        if not devices:
            self.device_combo.addItem("No se encontraron dispositivos", "")
            self.address_edit.clear()
        else:
            for name, address in devices:
                self.device_combo.addItem(f"{name} - {address}", address)

        self.device_combo.blockSignals(False)

        if self.device_combo.count() > 0:
            self.device_combo.setCurrentIndex(0)

        self.btn_scan.setEnabled(True)
        self._sync_address_from_combo(self.device_combo.currentText())
        self.phase_signal.emit("Listo")

    async def _wait_for_status(self, prefix: str, timeout: float = 10.0):
        if self._status_event is None:
            self._status_event = asyncio.Event()

        prefix = prefix.upper()
        deadline = asyncio.get_running_loop().time() + timeout

        while True:
            remaining = deadline - asyncio.get_running_loop().time()
            if remaining <= 0:
                raise TimeoutError(f"No llegó respuesta BLE para {prefix}")

            self._status_event.clear()
            await asyncio.wait_for(self._status_event.wait(), timeout=remaining)

            status = (self._last_status or "").strip()
            upper = status.upper()

            if upper.startswith("ERR"):
                raise RuntimeError(status)

            if upper.startswith(prefix):
                return status

    def _ota_worker(self, address: str, firmware_path: str):
        async def _run():
            if BleakClient is None:
                raise RuntimeError("Falta la dependencia bleak. Instala requirements.txt")

            with open(firmware_path, "rb") as fp:
                firmware = fp.read()

            if not firmware:
                raise RuntimeError("El binario está vacío")

            self.phase_signal.emit("Conectando...")

            async with BleakClient(address, timeout=20.0) as client:
                self.phase_signal.emit("Conectado, iniciando notificaciones...")

                def handle_status(_sender, data):
                    text = bytes(data).decode("utf-8", errors="replace").strip()
                    self._last_status = text
                    self.log_signal.emit(f"< {text}")
                    if self._status_event is not None:
                        self._status_event.set()

                await client.start_notify(STATUS_UUID, handle_status)

                self._status_event = asyncio.Event()
                self._last_status = ""
                start_cmd = f"START {len(firmware)} {os.path.basename(firmware_path)}".encode("utf-8")
                await client.write_gatt_char(CONTROL_UUID, start_cmd, response=True)

                await self._wait_for_status("OK START", timeout=12.0)

                chunk_size = 180
                sent = 0
                total = len(firmware)

                self.phase_signal.emit("Enviando firmware...")
                for offset in range(0, total, chunk_size):
                    chunk = firmware[offset:offset + chunk_size]
                    await client.write_gatt_char(DATA_UUID, chunk, response=True)
                    sent += len(chunk)
                    self.progress_signal.emit(sent, total)

                self.phase_signal.emit("Finalizando OTA...")
                await client.write_gatt_char(CONTROL_UUID, b"END", response=True)
                await self._wait_for_status("OK END", timeout=20.0)

                self.phase_signal.emit("OTA completada")
                return True, "OTA completada. El dispositivo se reiniciará en breve."

        try:
            result = asyncio.run(_run())
            self.finished_signal.emit(result[0], result[1])
        except Exception as exc:
            self.finished_signal.emit(False, f"Error OTA BLE: {exc}")

    def start_ota(self):
        address = self.address_edit.text().strip() or self.device_combo.currentData()
        firmware_path = self.firmware_edit.text().strip()

        if not address:
            QMessageBox.warning(self, "OTA Bluetooth", "Selecciona un dispositivo BLE.")
            return

        if not firmware_path:
            QMessageBox.warning(self, "OTA Bluetooth", "Selecciona un firmware .bin.")
            return

        if not os.path.isfile(firmware_path):
            QMessageBox.warning(self, "OTA Bluetooth", "El archivo firmware no existe.")
            return

        self._set_controls_enabled(False)
        self.progress.setValue(0)
        self.log.clear()
        self._log(f"Dispositivo: {address}")
        self._log(f"Firmware: {firmware_path}")
        self.phase_signal.emit("Preparando OTA...")

        threading.Thread(
            target=self._ota_worker,
            args=(address, firmware_path),
            daemon=True,
        ).start()

    def _update_progress(self, sent: int, total: int):
        if total <= 0:
            self.progress.setValue(0)
            return

        percent = int((sent * 100) / total)
        self.progress.setValue(max(0, min(100, percent)))
        self.phase_label.setText(f"Enviados {sent}/{total} bytes")

    def _on_finished(self, ok: bool, message: str):
        self._set_controls_enabled(True)
        self.btn_scan.setEnabled(True)
        self.phase_signal.emit("Listo")

        if ok:
            QMessageBox.information(self, "OTA Bluetooth", message)
        else:
            QMessageBox.critical(self, "OTA Bluetooth", message)
