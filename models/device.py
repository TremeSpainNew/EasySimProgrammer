from dataclasses import dataclass, asdict, field
from typing import Union


PinValue = Union[int, str]


def parse_can_ref(pin) -> tuple[int, int] | None:
    if not isinstance(pin, str):
        return None

    text = pin.strip().upper()

    if not text.startswith("CAN"):
        return None

    body = text[3:]

    if ":" not in body:
        raise ValueError(f"Referencia CAN invalida: {pin}")

    node_text, channel_text = body.split(":", 1)

    if not node_text.isdigit() or not channel_text.isdigit():
        raise ValueError(f"Referencia CAN invalida: {pin}")

    return int(node_text), int(channel_text)


def parse_pin_value(pin) -> PinValue:
    if isinstance(pin, str):
        text = pin.strip().upper()

        can_ref = parse_can_ref(text)
        if can_ref is not None:
            node, channel = can_ref
            return f"CAN{node}:{channel}"

        if text.startswith("ADS"):
            channel = text[3:]

            if not channel.isdigit():
                raise ValueError(f"Canal ADS inválido: {pin}")

            return f"ADS{int(channel)}"

        return int(text)

    return int(pin)


def parse_pot_notches(notches):
    result = []

    if not isinstance(notches, list):
        return result

    for item in notches:
        if isinstance(item, (list, tuple)) and len(item) >= 2:
            raw_value, out_value = item[0], item[1]
        elif isinstance(item, dict):
            raw_value = item.get("raw", item.get("pot_value"))
            out_value = item.get("value", item.get("out_value"))
        else:
            continue

        try:
            raw = None if raw_value in (None, "") else int(raw_value)
            result.append((raw, float(out_value)))
        except (TypeError, ValueError):
            continue

    return result


@dataclass
class Device:
    kind: str
    pin: PinValue
    name: str
    can_kind: str = "BUTTON"
    can_node: int = 0
    can_channel: int = 0
    output_inverted: bool = False

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
    pot_threshold: float = 0.5
    pot_notches_enabled: bool = False
    pot_notches: list[tuple[int, float]] = field(default_factory=list)
    pot_notch_hyst: float = 0.05
    pot_notch_partial: bool = False
    pot_notch_snapwin: float = 0.03
    pot_split_mode: str = "OFF"
    pot_split_deadband: float = 0.02
    pot_split_center_bias: float = 0.5
    pot_split_tag: str = ""
    pot_split_tag_fwd: str = ""
    pot_split_tag_back: str = ""

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(data):
        kind = str(data.get("kind", "BUTTON")).upper()
        pin = parse_pin_value(data.get("pin", 0))

        can_kind = str(data.get("can_kind", "BUTTON")).upper()
        can_node = int(data.get("can_node", 0))
        can_channel = int(data.get("can_channel", 0))

        if kind == "CANBUS":
            can_ref = parse_can_ref(pin)
            if can_ref is not None:
                can_node, can_channel = can_ref

        return Device(
            kind=kind,
            pin=pin,
            name=data.get("name", ""),
            can_kind=can_kind,
            can_node=can_node,
            can_channel=can_channel,
            output_inverted=bool(data.get("output_inverted", False)),

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
            pot_threshold=float(data.get("pot_threshold", 0.5)),
            pot_notches_enabled=bool(data.get("pot_notches_enabled", False)),
            pot_notches=parse_pot_notches(data.get("pot_notches", [])),
            pot_notch_hyst=float(data.get("pot_notch_hyst", 0.05)),
            pot_notch_partial=bool(data.get("pot_notch_partial", False)),
            pot_notch_snapwin=float(data.get("pot_notch_snapwin", 0.03)),
            pot_split_mode=str(data.get("pot_split_mode", "OFF")).upper(),
            pot_split_deadband=float(data.get("pot_split_deadband", 0.02)),
            pot_split_center_bias=float(data.get("pot_split_center_bias", 0.5)),
            pot_split_tag=str(data.get("pot_split_tag", "")),
            pot_split_tag_fwd=str(data.get("pot_split_tag_fwd", "")),
            pot_split_tag_back=str(data.get("pot_split_tag_back", "")),
        )
