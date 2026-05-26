from dataclasses import dataclass


@dataclass
class ModbusDevice:
    dev_id: int
    name: str
    ip: str = "0.0.0.0"
    port: int = 502
    unit: int = 1
    period: int = 100
    bus: str = "TCP"   # TCP / RTU


@dataclass
class ModbusTag:
    direction: str      # IN / OUT
    dev_id: int
    func: str           # HREG / IREG / COIL / ISTS
    addr: int
    qty: int
    name: str
    period: int = 100
    scale: float = 1.0
    offset: float = 0.0


@dataclass
class ModbusLine:
    raw: str
    kind: str = ""
    name: str = ""
    value: str = ""