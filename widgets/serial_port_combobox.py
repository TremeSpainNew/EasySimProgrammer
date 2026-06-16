from PySide6.QtWidgets import QComboBox
from serial.tools import list_ports

class SerialPortComboBox(QComboBox):
    def showPopup(self):
        current = self.currentText()

        self.clear()

        for port in list_ports.comports():
            self.addItem(
                f"{port.device} - {port.description}",
                port.device
            )

        if self.count() == 0:
            self.addItem("Sin puertos")

        idx = self.findText(current)

        if idx >= 0:
            self.setCurrentIndex(idx)

        super().showPopup()

    def currentPort(self):
        return self.currentData()