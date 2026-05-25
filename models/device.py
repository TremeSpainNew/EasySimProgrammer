from dataclasses import dataclass, asdict


@dataclass
class Device:
    kind: str
    pin: int
    name: str

    value1: float = 0
    value2: float = 1

    min_in: int = 0
    max_in: int = 4095
    min_out: float = 0
    max_out: float = 100

    smooth: float = 0.10
    send_mode: str = "CAMBIO"
    interval: int = 200
    as_integer: bool = True

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        return Device(
            kind=data.get("kind", "BUTTON"),
            pin=int(data.get("pin", 0)),
            name=data.get("name", ""),

            value1=float(data.get("value1", 0)),
            value2=float(data.get("value2", 1)),

            min_in=int(data.get("min_in", 0)),
            max_in=int(data.get("max_in", 4095)),
            min_out=float(data.get("min_out", 0)),
            max_out=float(data.get("max_out", 100)),

            smooth=float(data.get("smooth", 0.10)),
            send_mode=data.get("send_mode", "CAMBIO"),
            interval=int(data.get("interval", 200)),
            as_integer=bool(data.get("as_integer", True)),
        )
