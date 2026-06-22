def pin_to_text(pin):
    return str(pin)


def normalize_kind(kind: str) -> str:
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
        "CAN BUS": "CANBUS",
        "CANBUS": "CANBUS",
    }

    return mapping.get(kind, kind)


def build_add_command(device):
    kind = normalize_kind(device.kind)
    pin = pin_to_text(device.pin)

    if kind == "BUTTON":
        return f"ADD BUTTON {pin} {device.name} {device.value1:g} {device.value2:g}"

    if kind == "SWITCH":
        return f"ADD SWITCH {pin} {device.name} {device.value1:g} {device.value2:g}"

    if kind == "OUTPUT":
        return f"ADD OUTPUT {pin} {device.name} {device.value1:g} {device.value2:g}"

    if kind == "POT":
        return f"ADD POT {pin} {device.name} {device.min_out:g} {device.max_out:g}"

    if kind == "SELECTOR":
        return f"SEL.ADD {device.name} {pin} {device.value1:g}"

    if kind == "CANBUS":
        can_kind = normalize_kind(getattr(device, "can_kind", "BUTTON"))
        can_node = int(getattr(device, "can_node", 0))
        can_channel = int(getattr(device, "can_channel", 0))
        return (
            f"ADD {can_kind} CAN{can_node}:{can_channel} "
            f"{device.name} {device.value1:g} {device.value2:g}"
        )

    return ""


def build_extra_commands(device):
    commands = []
    kind = normalize_kind(device.kind)

    if kind == "POT":
        pin = pin_to_text(device.pin)

        commands.append(
            f"CFG {pin} SCALE {device.min_in} {device.max_in} "
            f"{device.min_out:g} {device.max_out:g}"
        )

        commands.append(f"CFG {pin} SMOOTH {device.smooth:g}")
        commands.append(f"CFG {pin} THRESH {getattr(device, 'pot_threshold', 0.5):g}")

        if device.send_mode == "INTERVALO":
            commands.append(f"CFG {pin} MODE INTERVALO {device.interval}")
        else:
            commands.append(f"CFG {pin} MODE {device.send_mode}")

        commands.append(f"CFG {pin} FORMAT {'INT' if device.as_integer else 'FLOAT'}")

        if getattr(device, "pot_notches_enabled", False):
            commands.append(f"NOTCH CLEAR {pin}")

            for index, (raw_value, out_value) in enumerate(getattr(device, "pot_notches", [])):
                commands.append(f"NOTCH ADD {pin} {out_value:g}")
                if raw_value is not None:
                    commands.append(f"NOTCH CENT {pin} {index} {raw_value}")

            commands.append(f"NOTCH HYST {pin} {getattr(device, 'pot_notch_hyst', 0.05):g}")
            commands.append(
                f"NOTCH PARTIAL {pin} {'ON' if getattr(device, 'pot_notch_partial', False) else 'OFF'}"
            )
            commands.append(f"NOTCH SNAPWIN {pin} {getattr(device, 'pot_notch_snapwin', 0.03):g}")

        split_mode = str(getattr(device, "pot_split_mode", "OFF")).upper()
        if split_mode != "OFF":
            commands.append(f"POT.SPLIT {pin} {split_mode}")
            commands.append(f"POT.SPLIT.DB {pin} {getattr(device, 'pot_split_deadband', 0.02):g}")
            commands.append(
                f"POT.SPLIT.CBIAS {pin} {getattr(device, 'pot_split_center_bias', 0.5):g}"
            )

            tag_fwd = str(getattr(device, "pot_split_tag_fwd", "")).strip()
            tag_back = str(getattr(device, "pot_split_tag_back", "")).strip()
            tag_single = str(getattr(device, "pot_split_tag", "")).strip()

            if split_mode == "DUAL" and tag_fwd and tag_back:
                commands.append(f"POT.SPLIT.TAGS {pin} {tag_fwd} {tag_back}")

            if tag_single:
                commands.append(f"POT.SPLIT.TAG {pin} {tag_single}")

    return commands


def build_all_commands(devices):
    commands = []

    for device in devices:
        add_command = build_add_command(device)

        if add_command:
            commands.append(add_command)

        commands.extend(build_extra_commands(device))

    return commands
