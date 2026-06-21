import random
import socket
import threading
import time

from PySide6.QtCore import QObject, Signal


class ConnectionManager(QObject):
    log = Signal(str)
    received = Signal(str)
    io_state = Signal(object, str, int)

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
        self._session_id = 0
        self._state_lock = threading.RLock()

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

    def normalize_pin(self, pin):
        text = str(pin).strip().upper()

        if text.startswith("ADS"):
            channel = text[3:]

            if not channel.isdigit():
                raise ValueError(f"Canal ADS inválido: {pin}")

            return f"ADS{int(channel)}"

        return int(text)

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

            sock = self._open_tcp_socket(ip, port)
            session_id = self._reserve_session()

            self.simulation = False
            self.connected = True
            self.mode = "TCP"
            self.sock = sock
            self.last_rx_time = time.time()

            self._start_rx_thread(session_id)
            self._start_ping_thread(session_id)

            self.log.emit(f"Conectado por TCP a {ip}:{port}")

        except Exception as e:
            self.connected = False
            self.mode = "NONE"
            self._close_socket(getattr(self, "sock", None))
            self.sock = None
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
            session_id = self._reserve_session()

            self.simulation = False
            self.connected = True
            self.mode = "SERIAL"
            self.last_rx_time = time.time()

            self._start_rx_thread(session_id)
            self.log.emit(f"Conectado por Serial a {port} @ {baud}")

        except Exception as e:
            self.connected = False
            self.serial = None
            self.mode = "NONE"
            self.log.emit(f"Error Serial: {e}")

    def disconnect(self):
        with self._state_lock:
            self._session_id += 1
            self._rx_running = False
            self.ping_running = False
            self.reconnecting = False

            sock = self.sock
            serial_conn = self.serial

            self.sock = None
            self.serial = None

        self._close_socket(sock)
        self._close_serial(serial_conn)

        if not self.simulation:
            self.connected = False
            self.mode = "NONE"

    def _reserve_session(self) -> int:
        with self._state_lock:
            self._session_id += 1
            return self._session_id

    def _open_tcp_socket(self, ip: str, port: int):
        sock = socket.create_connection((ip, port), timeout=2)

        try:
            sock.settimeout(2)
            sock.sendall(b"PING\n")

            deadline = time.time() + 2
            buffer = b""

            while time.time() < deadline:
                chunk = sock.recv(512)

                if chunk == b"":
                    raise ConnectionError("El dispositivo cerró el socket durante el handshake")

                buffer += chunk

                while b"\n" in buffer:
                    line, buffer = buffer.split(b"\n", 1)
                    text = line.decode("utf-8", errors="replace").strip()

                    if text == "PONG":
                        sock.settimeout(0.1)
                        return sock

            raise TimeoutError("No se recibió PONG tras conectar")

        except Exception:
            self._close_socket(sock)
            raise

    def _close_socket(self, sock):
        if not sock:
            return

        try:
            sock.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass

        try:
            sock.close()
        except Exception:
            pass

    def _close_serial(self, serial_conn):
        if not serial_conn:
            return

        try:
            serial_conn.close()
        except Exception:
            pass

    def _start_rx_thread(self, session_id: int):
        if self._rx_running:
            return

        self._rx_running = True
        self._rx_thread = threading.Thread(
            target=self._rx_loop,
            args=(session_id,),
            daemon=True,
        )
        self._rx_thread.start()

    def _start_ping_thread(self, session_id: int):
        if self.ping_running:
            return

        self.ping_running = True
        self.ping_thread = threading.Thread(
            target=self._ping_loop,
            args=(session_id,),
            daemon=True,
        )
        self.ping_thread.start()

    def _ping_loop(self, session_id: int):
        while self.ping_running:
            time.sleep(3)

            if session_id != self._session_id:
                break

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
                self._mark_disconnected(f"Conexión perdida: {e}", session_id)

    def _rx_loop(self, session_id: int):
        buffer = b""

        while self._rx_running:
            if session_id != self._session_id:
                break

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
                if self._rx_running and session_id == self._session_id:
                    self._mark_disconnected(f"Conexión cerrada: {e}", session_id)
                break

        if session_id == self._session_id:
            self._rx_running = False

    def _mark_disconnected(self, reason: str = "Conexión perdida", session_id: int | None = None):
        if session_id is not None and session_id != self._session_id:
            return

        if not self.connected and self.reconnecting:
            return

        self.log.emit(reason)

        self.connected = False
        self._rx_running = False
        self.ping_running = False

        sock = self.sock
        serial_conn = self.serial
        self.sock = None
        self.serial = None

        self._close_socket(sock)
        self._close_serial(serial_conn)

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

                sock = self._open_tcp_socket(self.last_ip, self.last_port)
                session_id = self._reserve_session()

                self.sock = sock
                self.connected = True
                self.mode = "TCP"
                self.last_rx_time = time.time()
                self.reconnecting = False
                self._rx_running = False

                self._start_rx_thread(session_id)
                self._start_ping_thread(session_id)

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
            pin = self.normalize_pin(parts[1])
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

    def start_pin_watch(self, pin, kind: str):
        kind = self.normalize_kind(kind)

        if self.simulation:
            return

        self.send_command(f"IO.WATCH {pin} {kind} ON")

    def stop_pin_watch(self, pin, kind: str):
        kind = self.normalize_kind(kind)

        if self.simulation:
            return

        self.send_command(f"IO.WATCH {pin} {kind} OFF")

    def read_pin(self, pin, kind: str):
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
