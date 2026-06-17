import random
import socket
import threading
import time

from PySide6.QtCore import QObject, Signal


class ConnectionManager(QObject):
    log = Signal(str)
    received = Signal(str)
    io_state = Signal(int, str, int)

    def __init__(self):
        super().__init__()

        self.simulation = False
        self.connected = False
        self.mode = "SIM"

        self.sock = None
        self.serial = None

        self.output_states = {}
        self.last_values = {}

        self._rx_thread = None
        self._rx_running = False

        self.auto_reconnect = False
        self.last_ip = ""
        self.last_port = 5000

        self.last_rx_time = 0
        self.ping_thread = None
        self.ping_running = False
        self.reconnecting = False

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

    def set_simulation(self, enabled: bool):
        self.disconnect()

        self.simulation = enabled
        self.connected = enabled
        self.mode = "SIM" if enabled else "NONE"

        self.log.emit(f"Modo simulación: {'ON' if enabled else 'OFF'}")

    def connect_tcp(self, ip: str, port: int = 5000):
        try:
            self.disconnect()

            self.last_ip = ip
            self.last_port = port

            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(2)
            self.sock.connect((ip, port))
            self.sock.settimeout(0.1)

            self.simulation = False
            self.connected = True
            self.mode = "TCP"
            self.last_rx_time = time.time()

            self._start_rx_thread()
            self._start_ping_thread()

            self.log.emit(f"Conectado por TCP a {ip}:{port}")

        except Exception as e:
            self.connected = False
            self.sock = None
            self.mode = "NONE"
            self.log.emit(f"Error TCP: {e}")

    def connect_serial(self, port: str, baud: int = 115200):
        try:
            import serial
        except Exception:
            self.log.emit("pyserial no está instalado. Ejecuta: pip install pyserial")
            return

        try:
            self.disconnect()

            self.serial = serial.Serial(port, baudrate=baud, timeout=0.1)

            self.simulation = False
            self.connected = True
            self.mode = "SERIAL"
            self.last_rx_time = time.time()

            self._start_rx_thread()
            self.log.emit(f"Conectado por Serial a {port} @ {baud}")

        except Exception as e:
            self.connected = False
            self.serial = None
            self.mode = "NONE"
            self.log.emit(f"Error Serial: {e}")

    def disconnect(self):
        self._rx_running = False
        self.ping_running = False
        self.reconnecting = False

        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass

        self.sock = None
        self.serial = None

        if not self.simulation:
            self.connected = False
            self.mode = "NONE"

    def _start_rx_thread(self):
        if self._rx_running:
            return

        self._rx_running = True
        self._rx_thread = threading.Thread(target=self._rx_loop, daemon=True)
        self._rx_thread.start()

    def _start_ping_thread(self):
        if self.ping_running:
            return

        self.ping_running = True
        self.ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.ping_thread.start()

    def _ping_loop(self):
        while self.ping_running:
            time.sleep(3)

            if self.simulation:
                continue

            if self.mode != "TCP":
                continue

            if not self.connected:
                if self.auto_reconnect:
                    self._start_reconnect_thread()
                continue

            try:
                self.send_command("PING")

                if time.time() - self.last_rx_time > 10:
                    raise ConnectionError("Timeout esperando PONG")

            except Exception as e:
                self._mark_disconnected(f"Conexión perdida: {e}")

    def _rx_loop(self):
        buffer = b""

        while self._rx_running:
            try:
                chunk = b""

                if self.mode == "TCP" and self.sock:
                    try:
                        chunk = self.sock.recv(512)

                        if chunk == b"":
                            raise ConnectionError("Socket cerrado por remoto")

                    except socket.timeout:
                        chunk = b""

                elif self.mode == "SERIAL" and self.serial:
                    chunk = self.serial.read(512)

                if chunk:
                    buffer += chunk

                    while b"\n" in buffer:
                        line, buffer = buffer.split(b"\n", 1)
                        text = line.decode("utf-8", errors="replace").strip()

                        if text:
                            self.last_rx_time = time.time()
                            self.received.emit(text)
                            self.log.emit(f"< {text}")
                            self._parse_line(text)

            except Exception as e:
                if self._rx_running:
                    self._mark_disconnected(f"Conexión cerrada: {e}")
                break

        self._rx_running = False

    def _mark_disconnected(self, reason: str = "Conexión perdida"):
        if not self.connected and self.reconnecting:
            return

        self.log.emit(reason)

        self.connected = False

        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass

        self.sock = None

        if self.mode == "TCP":
            self.mode = "TCP"
            if self.auto_reconnect:
                self._start_reconnect_thread()
        else:
            self.mode = "NONE"

    def _start_reconnect_thread(self):
        if self.reconnecting:
            return

        self.reconnecting = True
        thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        thread.start()

    def _reconnect_loop(self):
        while self.auto_reconnect and not self.simulation:
            if not self.last_ip:
                break

            try:
                self.log.emit(f"Reconectando a {self.last_ip}:{self.last_port}...")

                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                sock.connect((self.last_ip, self.last_port))
                sock.settimeout(0.1)

                self.sock = sock
                self.connected = True
                self.mode = "TCP"
                self.last_rx_time = time.time()
                self.reconnecting = False
                self._rx_running = False

                self._start_rx_thread()
                self._start_ping_thread()

                self.log.emit("Reconectado correctamente")

                self.send_command("#DUMP")

                return

            except Exception:
                time.sleep(3)

        self.reconnecting = False

    def _parse_line(self, line: str):
        if not line.startswith("IO.STATE"):
            return

        parts = line.split()

        if len(parts) < 4:
            return

        try:
            pin = int(parts[1])
            kind = self.normalize_kind(parts[2])
            value = int(parts[3])

            self.last_values[(pin, kind)] = value
            self.io_state.emit(pin, kind, value)

        except Exception:
            pass

    def send_command(self, command: str):
        if self.simulation:
            self.log.emit(f"SIM > {command}")
            return

        if not self.connected:
            self.log.emit("No hay conexión activa.")
            return

        data = (command + "\n").encode("utf-8")

        try:
            if self.mode == "TCP" and self.sock:
                self.sock.sendall(data)

            elif self.mode == "SERIAL" and self.serial:
                self.serial.write(data)
                self.serial.flush()

            else:
                self.log.emit("Modo de conexión no válido.")
                return

            self.log.emit(f"> {command}")

        except Exception as e:
            self._mark_disconnected(f"Error enviando comando: {e}")

    def start_pin_watch(self, pin: int, kind: str):
        kind = self.normalize_kind(kind)

        if self.simulation:
            return

        self.send_command(f"IO.WATCH {pin} {kind} ON")

    def stop_pin_watch(self, pin: int, kind: str):
        kind = self.normalize_kind(kind)

        if self.simulation:
            return

        self.send_command(f"IO.WATCH {pin} {kind} OFF")

    def read_pin(self, pin: int, kind: str):
        kind = self.normalize_kind(kind)

        if self.simulation:
            if kind in ("BUTTON", "SWITCH", "SELECTOR"):
                value = random.choice([0, 0, 0, 1])
            elif kind == "POT":
                value = random.randint(0, 4095)
            elif kind == "OUTPUT":
                value = self.output_states.get(pin, 0)
            else:
                value = 0

            self.last_values[(pin, kind)] = value
            self.io_state.emit(pin, kind, value)
            return value

        return self.last_values.get((pin, kind), 0)

    def write_output(self, pin: int, value: int):
        value = 1 if value else 0

        if self.simulation:
            self.output_states[pin] = value
            self.last_values[(pin, "OUTPUT")] = value
            self.io_state.emit(pin, "OUTPUT", value)
            self.log.emit(f"SIM OUT pin {pin} = {value}")
            return

        self.send_command(f"IO.WRITE {pin} {value}")