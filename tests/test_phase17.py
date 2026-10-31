import json
import os
import tempfile
import unittest
from datetime import date, timedelta

from calorie_engine import DailyLog, FoodEntry
from foods import FoodDatabase, FoodItem
from storage import Storage


class Phase17Tests(unittest.TestCase):
    def test_favorites_and_recents_are_ordered_and_deduplicated(self):
        with tempfile.TemporaryDirectory() as td:
            store = Storage(os.path.join(td, "data.json"))
            store.toggle_favorite("Rice, white, cooked")
            store.toggle_favorite("Banana")
            store.record_recent("Rice, white, cooked")
            store.record_recent("Banana")
            store.record_recent("Rice, white, cooked")
            self.assertEqual(store.recents[:2], ["Rice, white, cooked", "Banana"])
            self.assertEqual(store.favorites, ["Rice, white, cooked", "Banana"])

    def test_serving_converts_to_expected_grams(self):
        db = FoodDatabase()
        rice = db.get("Rice, white, cooked")
        self.assertIsNotNone(rice)
        entry = rice.to_entry(rice.servings["1 cup"], "lunch")
        self.assertEqual(entry.grams, 158)
        self.assertAlmostEqual(entry.calories, 205.4, places=1)

    def test_edit_and_duplicate_style_operations_preserve_nutrition(self):
        original = FoodEntry("Banana", 118, 89, 1.1, 22.8, 0.3, "breakfast")
        duplicate = FoodEntry(**original.__dict__)
        edited = FoodEntry(**{**original.__dict__, "grams": 177, "meal": "snacks"})
        self.assertEqual(duplicate.__dict__, original.__dict__)
        self.assertEqual(edited.name, original.name)
        self.assertEqual(edited.meal, "snacks")
        self.assertGreater(edited.calories, original.calories)

    def test_copy_yesterday_data_can_round_trip_through_storage(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "data.json")
            store = Storage(path)
            yesterday = date(2026, 10, 3)
            today = date(2026, 10, 4)
            store.logs[yesterday] = DailyLog(
                log_date=yesterday,
                foods=[FoodEntry("Rice, white, cooked", 158, 130, 2.7, 28.2, 0.3, "lunch")],
            )
            store.save()
            loaded = Storage(path)
            source = loaded.logs[yesterday]
            loaded.logs[today] = DailyLog(log_date=today, foods=[FoodEntry(**f.__dict__) for f in source.foods])
            loaded.save()
            again = Storage(path)
            self.assertEqual(len(again.logs[today].foods), 1)
            self.assertEqual(again.logs[today].foods[0].meal, "lunch")

    def test_new_food_data_does_not_change_existing_json_shape(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "data.json")
            store = Storage(path)
            store.food_db.add_custom(FoodItem("Test food", 100, 10, 10, 2, {"1 serving": 50}, custom=True))
            store.save()
            with open(path, encoding="utf-8") as fh:
                raw = json.load(fh)
            self.assertIn("custom_foods", raw)
            self.assertIn("favorites", raw)
            self.assertIn("recents", raw)
            self.assertIn("logs", raw)
            self.assertEqual(raw["custom_foods"][0]["name"], "Test food")


if __name__ == "__main__":
    unittest.main()
