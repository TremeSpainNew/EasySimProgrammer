from modbus.modbus_model import ModbusLine


def parse_modbus_line(line: str) -> ModbusLine:
    text = line.strip()

    if not text:
        return ModbusLine(raw=line, kind="EMPTY")

    parts = text.split()

    if text.startswith("MB.WINDOW"):
        return ModbusLine(raw=text, kind="WINDOW", name="MB.WINDOW", value=text)

    if text.startswith("MB.AUTOLOAD"):
        return ModbusLine(raw=text, kind="AUTOLOAD", name="MB.AUTOLOAD", value=text)

    if parts[0].startswith("MB."):
        name = parts[0]
        value = " ".join(parts[1:]) if len(parts) > 1 else ""
        return ModbusLine(raw=text, kind="MB", name=name, value=value)

    return ModbusLine(raw=text, kind="RAW", name=parts[0], value=" ".join(parts[1:]))