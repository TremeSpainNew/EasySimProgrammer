def pin_to_text(pin):
    return str(pin)


def build_add_command(device):
    pin = pin_to_text(device.pin)

    if device.kind == "BOTON":
        return f"ADD BUTTON {pin} {device.name} {device.value1:g} {device.value2:g}"

    if device.kind == "INTERRUPTOR":
        return f"ADD SWITCH {pin} {device.name} {device.value1:g} {device.value2:g}"

    if device.kind == "SALIDA DIGITAL":
        return f"ADD OUTPUT {pin} {device.name} {device.value1:g} {device.value2:g}"

    if device.kind == "POTENCIOMETRO":
        return f"ADD POT {pin} {device.name} {device.min_out:g} {device.max_out:g}"

    if device.kind == "SELECTOR":
        return f"SEL.ADD {device.name} {pin} {device.value1:g}"

    return ""


def build_extra_commands(device):
    commands = []

    if device.kind == "POTENCIOMETRO":
        pin = pin_to_text(device.pin)

        commands.append(
            f"CFG {pin} SCALE {device.min_in} {device.max_in} "
            f"{device.min_out:g} {device.max_out:g}"
        )

        commands.append(f"CFG {pin} SMOOTH {device.smooth:g}")

        if device.send_mode == "INTERVALO":
            commands.append(f"CFG {pin} MODE INTERVALO {device.interval}")
        else:
            commands.append(f"CFG {pin} MODE {device.send_mode}")

        commands.append(f"CFG {pin} FORMAT {'INT' if device.as_integer else 'FLOAT'}")

    return commands


def build_all_commands(devices):
    commands = []

    for device in devices:
        add_command = build_add_command(device)

        if add_command:
            commands.append(add_command)

        commands.extend(build_extra_commands(device))

    return commands
