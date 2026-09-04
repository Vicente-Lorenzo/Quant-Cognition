STRIDE = 86400

def tabulate(payload: dict, name: str, column: str = None) -> dict:
    sheet = next((entry for entry in payload.get("sheets") or [] if entry.get("name") == name), None)
    if sheet is None: return {}
    names = [entry.get("name") for entry in sheet.get("columns") or []]
    index = names.index(column) if column in names else len(names) - 1
    return {row[0]: row[index] for row in sheet.get("rows") or [] if row and len(row) > index}

def transpose(payload: dict, name: str, skip: str = "Strategy") -> dict:
    sheet = next((entry for entry in payload.get("sheets") or [] if entry.get("name") == name), None)
    if sheet is None: return {}
    names = [entry.get("name") for entry in sheet.get("columns") or []]
    row = next((entry for entry in sheet.get("rows") or [] if entry and entry[0] != skip), None)
    if row is None: return {}
    return {label: value for label, value in zip(names[1:], row[1:])}

def trace(payload: dict, pane: str, key: str) -> list:
    frame = next((entry for entry in payload.get("panes") or [] if entry.get("id") == pane), None)
    if frame is None: return []
    series = next((entry for entry in frame.get("series") or [] if entry.get("key") == key), None)
    return (series or {}).get("data") or []

def diurnal(points: list) -> list:
    buckets = {}
    for point in points:
        if point.get("value") is None: continue
        buckets[int(point["time"]) // 86400] = point["value"]
    return [{"time": day * 86400, "value": value} for day, value in sorted(buckets.items())]

def stitch(folds: list) -> tuple[list, list]:
    curve, marks, level = [], [], 100.0
    for record in folds:
        equity = record.get("Equity") or []
        if not equity: continue
        opening = equity[0][1]
        if not opening: continue
        marks.append({"Fold": record.get("Fold"), "Parameters": record.get("Parameters"),
                      "Start": str(record.get("Start"))[:10], "Stop": str(record.get("Stop"))[:10],
                      "Training": record.get("Training"), "Validation": record.get("Validation"),
                      "Opening": round(level, 4),
                      "Return (%)": round((equity[-1][1] / opening - 1.0) * 100.0, 4)})
        curve.extend((stamp, level * value / opening) for stamp, value in equity)
        level = level * equity[-1][1] / opening
    return curve, marks

def tick(index: int) -> int:
    return index * STRIDE

def ordinal(values: list) -> list:
    return [{"time": tick(index), "value": None if value is None else float(value)} for index, value in enumerate(values, start=1)]

def grouped(journal: list, *keys: str) -> dict:
    buckets = {}
    for record in journal:
        buckets.setdefault(tuple(record.get(key) for key in keys), []).append(record)
    return buckets

def searched(journal: list) -> list:
    reserved = {"Fold", "Stage", "Round", "Candidate", "Fitness", "Seed", "Episode", "Train", "Validation", "Return", "Eligible"}
    names = []
    for record in journal:
        for name in record:
            if name not in reserved and name not in names: names.append(name)
    return names

def winners(journal: list, *keys: str) -> list:
    scored = [record for record in journal if record.get("Fitness") is not None]
    names = searched(scored)
    marks = []
    for coordinates, records in grouped(scored, *keys).items():
        best = max(records, key=lambda record: record["Fitness"])
        marks.append({**dict(zip(keys, coordinates)), "Trials": len(records), "Fitness": round(best["Fitness"], 6),
                      "Candidate": best.get("Candidate"), **{name: best.get(name) for name in names}})
    return sorted(marks, key=lambda mark: tuple((mark.get(key) is None, mark.get(key)) for key in keys))

__all__ = ["STRIDE", "tabulate", "transpose", "trace", "diurnal", "stitch", "tick", "ordinal", "grouped", "searched", "winners"]