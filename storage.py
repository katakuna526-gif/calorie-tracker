"""Save and load the profile, daily logs, custom foods, favorites and recent foods as one JSON file."""

import json
import os
import shutil
from dataclasses import asdict, replace
from datetime import date
from typing import Dict, List, Optional

from calorie_engine import (
    MAX_WEIGHT_KG, MIN_WEIGHT_KG, Person, FoodEntry, ExerciseEntry, DailyLog,
)
from foods import FoodDatabase, FoodItem

DEFAULT_PATH = os.path.join(os.path.expanduser("~"), ".calorie_tracker", "data.json")
MAX_RECENTS = 10


class Storage:
    def __init__(self, path: str = DEFAULT_PATH):
        self.path = path
        self.profile: Optional[Person] = None
        self.logs: Dict[date, DailyLog] = {}
        self.favorites: List[str] = []
        self.recents: List[str] = []
        self.weights: Dict[date, float] = {}
        self.preferences = {"weight_unit": "kg", "theme": "light"}
        self.food_db = FoodDatabase()
        # Saved entries that no longer pass the checks are skipped, and counted
        # here so the app can tell the person instead of failing silently.
        self.skipped = {"foods": 0, "exercises": 0, "custom_foods": 0, "weights": 0}
        self.load()

    @property
    def skipped_total(self) -> int:
        return sum(self.skipped.values())

    # ---------- file I/O ----------
    def load(self):
        self.profile = None
        self.logs = {}
        self.favorites = []
        self.recents = []
        self.weights = {}
        self.food_db = FoodDatabase()
        self.preferences = {"weight_unit": "kg", "theme": "light"}
        self.skipped = {"foods": 0, "exercises": 0, "custom_foods": 0, "weights": 0}
        if not os.path.exists(self.path):
            return
        with open(self.path, "r", encoding="utf-8") as fh:
            raw = json.load(fh)

        if raw.get("profile"):
            self.profile = Person(**raw["profile"])

        saved_preferences = raw.get("preferences", {})
        if isinstance(saved_preferences, dict):
            if saved_preferences.get("weight_unit") in ("kg", "lb"):
                self.preferences["weight_unit"] = saved_preferences["weight_unit"]
            if saved_preferences.get("theme") in ("light", "dark"):
                self.preferences["theme"] = saved_preferences["theme"]

        for data in raw.get("custom_foods", []):
            try:
                item = FoodItem(**data)
                self.food_db.add_custom(item)
            except (ValueError, TypeError):
                self.skipped["custom_foods"] += 1

        self.favorites = [n for n in raw.get("favorites", []) if isinstance(n, str)]
        self.recents = [n for n in raw.get("recents", []) if isinstance(n, str)][:MAX_RECENTS]

        for key, kg in raw.get("weights", {}).items():
            try:
                if not (MIN_WEIGHT_KG <= float(kg) <= MAX_WEIGHT_KG):
                    raise ValueError
                self.weights[date.fromisoformat(key)] = float(kg)
            except (ValueError, TypeError):
                self.skipped["weights"] += 1

        for key, val in raw.get("logs", {}).items():
            d = date.fromisoformat(key)
            log = DailyLog(log_date=d)
            for data in val.get("foods", []):
                try:
                    log.foods.append(FoodEntry(**data))
                except (ValueError, TypeError):
                    self.skipped["foods"] += 1
            for data in val.get("exercises", []):
                try:
                    log.exercises.append(ExerciseEntry(**data))
                except (ValueError, TypeError):
                    self.skipped["exercises"] += 1
            self.logs[d] = log

    def save(self):
        folder = os.path.dirname(self.path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        raw = {
            "profile": asdict(self.profile) if self.profile else None,
            "preferences": dict(self.preferences),
            "custom_foods": [asdict(item) for item in self.food_db.custom],
            "favorites": self.favorites,
            "recents": self.recents,
            "weights": {d.isoformat(): kg for d, kg in sorted(self.weights.items())},
            "logs": {
                d.isoformat(): {
                    "foods": [asdict(f) for f in log.foods],
                    "exercises": [asdict(e) for e in log.exercises],
                }
                for d, log in self.logs.items()
                if log.foods or log.exercises
            },
        }
        tmp = self.path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(raw, fh, indent=2)
        os.replace(tmp, self.path)

    def set_preferences(self, weight_unit=None, theme=None):
        if weight_unit is not None:
            if weight_unit not in ("kg", "lb"):
                raise ValueError("Weight unit must be kg or lb.")
            self.preferences["weight_unit"] = weight_unit
        if theme is not None:
            if theme not in ("light", "dark"):
                raise ValueError("Theme must be light or dark.")
            self.preferences["theme"] = theme
        self.save()

    def restore_from(self, source_path):
        """Validate a backup and replace this file atomically, keeping a safety copy."""
        source_path = os.path.abspath(source_path)
        destination = os.path.abspath(self.path)
        if source_path == destination:
            raise ValueError("Choose a separate backup file to restore.")
        candidate = Storage(source_path)
        if candidate.skipped_total:
            raise ValueError("The selected backup contains invalid entries and was not restored.")
        folder = os.path.dirname(destination) or "."
        os.makedirs(folder, exist_ok=True)
        safety_path = destination + ".before_restore"
        if os.path.exists(destination):
            shutil.copy2(destination, safety_path)
        staging = destination + ".restore_tmp"
        try:
            shutil.copy2(source_path, staging)
            os.replace(staging, destination)
            self.load()
        finally:
            if os.path.exists(staging):
                os.remove(staging)
        return safety_path if os.path.exists(safety_path) else None

    # ---------- convenience ----------
    def set_profile(self, person: Person, today: Optional[date] = None):
        """Save the profile. If its weight differs from your latest weigh-in, that weight
        is recorded as today's weigh-in, so the weight history and the profile agree."""
        self.profile = person
        latest = self.latest_weight()
        if latest is None or latest[1] != person.weight_kg:
            self.weights[today or date.today()] = round(float(person.weight_kg), 1)
            self._sync_profile_weight()
        self.save()

    def person_on(self, d: date) -> Optional[Person]:
        """The profile with the weight you had on date d (the latest weigh-in on or before d).
        Before your first weigh-in, the earliest one is used. Keeps past days from changing
        when your weight changes later."""
        if not self.profile:
            return None
        if not self.weights:
            return self.profile
        earlier = [day for day in self.weights if day <= d]
        kg = self.weights[max(earlier) if earlier else min(self.weights)]
        return self.profile if kg == self.profile.weight_kg else replace(self.profile, weight_kg=kg)

    def get_log(self, d: date) -> DailyLog:
        if d not in self.logs:
            self.logs[d] = DailyLog(log_date=d)
        return self.logs[d]

    def add_custom_food(self, item: FoodItem):
        self.food_db.add_custom(item)  # raises ValueError if the name is taken
        self.save()

    def is_favorite(self, name: str) -> bool:
        return name in self.favorites

    def toggle_favorite(self, name: str) -> bool:
        """Returns True if the food is now a favorite."""
        if name in self.favorites:
            self.favorites.remove(name)
            now_favorite = False
        else:
            self.favorites.append(name)
            now_favorite = True
        self.save()
        return now_favorite

    def record_recent(self, name: str):
        """Most recently used first, no duplicates, newest MAX_RECENTS kept."""
        if name in self.recents:
            self.recents.remove(name)
        self.recents.insert(0, name)
        del self.recents[MAX_RECENTS:]
        self.save()

    # ---------- weight log ----------
    def latest_weight(self):
        """(date, kg) of the most recent weigh-in, or None."""
        if not self.weights:
            return None
        d = max(self.weights)
        return d, self.weights[d]

    def _sync_profile_weight(self):
        """Keep the profile's weight equal to the latest weigh-in, so BMR,
        targets and exercise estimates stay current."""
        latest = self.latest_weight()
        if self.profile and latest and self.profile.weight_kg != latest[1]:
            self.profile = replace(self.profile, weight_kg=latest[1])

    def log_weight(self, d: date, kg: float, today: Optional[date] = None):
        if d > (today or date.today()):
            raise ValueError("You can't log a weight for a future date.")
        if not (MIN_WEIGHT_KG <= kg <= MAX_WEIGHT_KG):  # also rejects nan
            raise ValueError(f"Weight must be between {MIN_WEIGHT_KG} and {MAX_WEIGHT_KG} kg.")
        self.weights[d] = round(float(kg), 1)
        self._sync_profile_weight()
        self.save()

    def remove_weight(self, d: date):
        self.weights.pop(d, None)
        self._sync_profile_weight()
        self.save()
