import json
from models.device import Device


def save_devices(path, devices):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            [device.to_dict() for device in devices],
            f,
            indent=4,
            ensure_ascii=False
        )


def load_devices(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return [Device.from_dict(item) for item in data]
