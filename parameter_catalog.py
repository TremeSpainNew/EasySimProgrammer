import json


class ParameterCatalog:
    def __init__(self):
        self.parameters = []

    def load(self, filename):
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError("El catálogo debe ser una lista JSON.")

        self.parameters = data

    def names_for_kind(self, kind):
        kind = str(kind).upper()

        if kind in ("BUTTON", "SWITCH", "POT", "SELECTOR"):
            write_required = True
        elif kind == "OUTPUT":
            write_required = False
        elif kind == "CANBUS":
            write_required = None
        else:
            write_required = None

        result = []

        for item in self.parameters:
            if not isinstance(item, dict):
                continue

            if write_required is not None:
                if bool(item.get("Write", False)) != write_required:
                    continue

            name = item.get("ServerName")

            if name:
                result.append(str(name))

        result.sort()
        return result

    def find(self, name):
        for item in self.parameters:
            if isinstance(item, dict) and item.get("ServerName") == name:
                return item

        return None
