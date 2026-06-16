from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QLineEdit,
    QPushButton
)

class ManualConsole(QDialog):
    def __init__(self, connection, parent=None):
        super().__init__(parent)

        self.connection = connection

        self.setWindowTitle("Consola manual")
        self.resize(700, 400)

        self.log = QTextEdit()
        self.log.setReadOnly(True)

        self.command = QLineEdit()
        self.command.returnPressed.connect(self.send_command)

        self.send_button = QPushButton("Enviar")
        self.send_button.clicked.connect(self.send_command)

        row = QHBoxLayout()
        row.addWidget(self.command)
        row.addWidget(self.send_button)

        layout = QVBoxLayout()
        layout.addWidget(self.log)
        layout.addLayout(row)

        self.setLayout(layout)

        self.connection.received.connect(self.on_received)

    def send_command(self):
        cmd = self.command.text().strip()

        if not cmd:
            return

        self.connection.send_command(cmd)

        self.log.append(f"> {cmd}")

        self.command.clear()

    def on_received(self, text):
        self.log.append(f"< {text}")

    def closeEvent(self, event):
        try:
            self.connection.received.disconnect(self.on_received)
        except:
            pass

        super().closeEvent(event)