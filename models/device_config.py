from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any


DEVICE_SWITCH = "SWITCH"
DEVICE_BUTTON = "BUTTON"
DEVICE_OUTPUT = "OUTPUT"
DEVICE_POT = "POT"
DEVICE_SELECTOR = "SELECTOR"

SEND_CONTINUO = "CONTINUO"
SEND_CAMBIO = "CAMBIO"
SEND_INTERVALO = "INTERVALO"
SEND_MANUAL = "MANUAL"


@dataclass
class SelectorPosition:
    pin: str = "0"
    value: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "SelectorPosition":
        return SelectorPosition(
            pin=str(data.get("pin", "0")),
            value=float(data.get("value", 0.0)),
        )


@dataclass
class DeviceConfig:
    device_type: str = DEVICE_BUTTON
    pin: str = "0"                 # admite 0..127, A0, ADS0..ADS3
    param: str = ""                # nombre/tag que usa el firmware
    value_1: float = 1.0            # minOut / valor ON / valor pulsado
    value_2: float = 0.0            # maxOut / valor OFF / valor soltado

    # POT
    min_in: int = 0
    max_in: int = 4095
    min_out: float = 0.0
    max_out: float = 100.0
    smooth: float = 0.10
    send_mode: str = SEND_CONTINUO
    interval: int = 200
    integer_format: bool = True
    threshold: float = 0.01

    # SELECTOR
    selector_positions: List[SelectorPosition] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["selector_positions"] = [p.to_dict() for p in self.selector_positions]
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "DeviceConfig":
        cfg = DeviceConfig(
            device_type=data.get("device_type", DEVICE_BUTTON),
            pin=str(data.get("pin", "0")),
            param=data.get("param", ""),
            value_1=float(data.get("value_1", 1.0)),
            value_2=float(data.get("value_2", 0.0)),
            min_in=int(data.get("min_in", 0)),
            max_in=int(data.get("max_in", 4095)),
            min_out=float(data.get("min_out", 0.0)),
            max_out=float(data.get("max_out", 100.0)),
            smooth=float(data.get("smooth", 0.10)),
            send_mode=data.get("send_mode", SEND_CONTINUO),
            interval=int(data.get("interval", 200)),
            integer_format=bool(data.get("integer_format", True)),
            threshold=float(data.get("threshold", 0.01)),
        )
        cfg.selector_positions = [
            SelectorPosition.from_dict(p) for p in data.get("selector_positions", [])
        ]
        return cfg
