"""CSV reporting helpers. No UI and no changes to the app's saved JSON format."""

import csv
import io
from pathlib import Path


def period_csv_rows(records, targets_by_date=None):
    """Return CSV-ready rows for daily records.

    ``records`` are the dictionaries produced by stats.daily_records().
    ``targets_by_date`` optionally maps dates to calorie targets so the export
    can show target and variance without changing the stored log format.
    """
    targets_by_date = targets_by_date or {}
    rows = []
    for r in records:
        d = r["day"]
        target = targets_by_date.get(d, "")
        variance = ""
        if target != "":
            variance = round(r["calories_consumed"] - target, 2)
        rows.append({
            "date": d.isoformat(),
            "food_logged": "yes" if r["logged"] else "no",
            "calories_consumed": round(r["calories_consumed"], 2),
            "calorie_target": target,
            "calorie_variance": variance,
            "calories_burned": round(r["calories_burned"], 2),
            "exercise_calories": round(r["exercise_calories"], 2),
            "protein_g": round(r["protein_g"], 2),
            "carbs_g": round(r["carbs_g"], 2),
            "fat_g": round(r["fat_g"], 2),
        })
    return rows


FIELDNAMES = [
    "date", "food_logged", "calories_consumed", "calorie_target",
    "calorie_variance", "calories_burned", "exercise_calories",
    "protein_g", "carbs_g", "fat_g",
]


def period_csv_bytes(records, targets_by_date=None):
    """Build a UTF-8-with-BOM CSV payload for file pickers that accept bytes."""
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=FIELDNAMES)
    writer.writeheader()
    writer.writerows(period_csv_rows(records, targets_by_date))
    return ("\ufeff" + output.getvalue()).encode("utf-8")


def write_csv(path, rows):
    """Write report rows to ``path`` and return the Path used."""
    path = Path(path)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)
    return path
