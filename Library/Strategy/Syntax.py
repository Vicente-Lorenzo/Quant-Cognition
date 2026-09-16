class SyntaxAPI:

    SEPARATOR = " · "
    SEPARATORS = ("·", ";")
    ALTERNATIVE = "|"

    @staticmethod
    def _decode_(text: str):
        part = str(text).strip()
        if part == "": return None
        for cast in (int, float):
            try: return cast(part)
            except ValueError: continue
        return part

    @staticmethod
    def numbered(body) -> bool:
        return isinstance(body, dict) and bool(body) and all(str(key).replace("-", "").strip().isdigit() for key in body)

    @staticmethod
    def format_value(value) -> str:
        if value is None: return ""
        if isinstance(value, (list, tuple)): return ", ".join("" if item is None else str(item) for item in value)
        return str(value)

    @classmethod
    def parse_value(cls, text: str) -> list:
        return [cls._decode_(part) for part in str(text).split(",")]

    @classmethod
    def format_slots(cls, value) -> str:
        if value is None: return ""
        if not isinstance(value, (list, tuple)): return str(value)
        slots = []
        for slot in value:
            options = slot if isinstance(slot, (list, tuple)) else [slot]
            slots.append(cls.ALTERNATIVE.join("" if option is None else str(option) for option in options))
        return cls.SEPARATOR.join(slots)

    @classmethod
    def parse_slots(cls, text: str) -> list:
        body = str(text).strip()
        if body == "": return []
        for symbol in cls.SEPARATORS[1:]: body = body.replace(symbol, cls.SEPARATORS[0])
        slots = []
        for part in body.split(cls.SEPARATORS[0]):
            options = [cls._decode_(option) for option in part.split(cls.ALTERNATIVE)]
            slots.append(options if len(options) > 1 else options[0])
        return slots