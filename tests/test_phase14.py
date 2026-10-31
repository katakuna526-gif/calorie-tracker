import json
import os
import tempfile
import unittest
from datetime import datetime

import foods
from calorie_engine import (
    DailyLog, ExerciseEntry, FoodEntry, calculate_meal_totals, check_nutrition_values,
)
from foods import BUILTIN_FOODS, FoodDatabase, FoodItem, default_meal, grams_for
from storage import MAX_RECENTS, Storage


class SanityLimitTests(unittest.TestCase):
    def test_screenshot_values_are_rejected(self):
        """45 g protein + 45 g carbs + 35 g fat in 100 g of food cannot exist."""
        with self.assertRaises(ValueError):
            FoodEntry("fh", 4434, 43, 45, 45, 35)

    def test_each_limit(self):
        bad = [
            dict(name="x", grams=5001, calories_per_100g=100),      # too much food in one entry
            dict(name="x", grams=100, calories_per_100g=901),       # denser than pure fat
            dict(name="x", grams=100, calories_per_100g=100, protein_per_100g=101),
            dict(name="x", grams=100, calories_per_100g=100, protein_per_100g=60, carbs_per_100g=50),
            dict(name="x", grams=100, calories_per_100g=float("nan")),
            dict(name="x", grams=100, calories_per_100g=100, meal="brunch"),
        ]
        for kwargs in bad:
            with self.assertRaises(ValueError, msg=str(kwargs)):
                FoodEntry(**kwargs)

    def test_real_foods_pass(self):
        FoodEntry("Olive oil", 100, 884, 0, 0, 100)    # pure fat is allowed
        FoodEntry("Sugar", 100, 387, 0, 100, 0)
        FoodEntry("Meal", 5000, 100)

    def test_exercise_limits(self):
        for minutes, kcal in ((0, 100), (1441, 100), (30, -1), (30, 10001)):
            with self.assertRaises(ValueError):
                ExerciseEntry("x", minutes, kcal)
        ExerciseEntry("Marathon", 240, 2800)

    def test_meal_defaults_to_snacks(self):
        self.assertEqual(FoodEntry("x", 100, 100).meal, "snacks")

    def test_meal_totals(self):
        log = DailyLog()
        log.foods += [FoodEntry("a", 100, 200, meal="breakfast"),
                      FoodEntry("b", 100, 300, meal="lunch"),
                      FoodEntry("c", 50, 100, meal="lunch")]
        totals = calculate_meal_totals(log)
        self.assertEqual(totals["breakfast"], 200)
        self.assertEqual(totals["lunch"], 350)
        self.assertEqual(totals["dinner"], 0)


class BuiltinFoodTests(unittest.TestCase):
    def test_names_are_unique(self):
        names = [f.name.lower() for f in BUILTIN_FOODS]
        self.assertEqual(len(names), len(set(names)))

    def test_calories_match_macros(self):
        """4/4/9 kcal per gram of protein/carbs/fat should roughly explain the calories.
        Catches typos such as a swapped or missing digit."""
        for f in BUILTIN_FOODS:
            estimate = 4 * f.protein_per_100g + 4 * f.carbs_per_100g + 9 * f.fat_per_100g
            allowed = 0.25 * f.calories_per_100g + 15
            self.assertLessEqual(abs(estimate - f.calories_per_100g), allowed, f.name)

    def test_includes_common_indian_staples(self):
        db = FoodDatabase()
        for query in ("roti", "dal", "paneer", "idli", "rajma", "ghee"):
            self.assertTrue(db.search(query), query)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.db = FoodDatabase()

    def names(self, query):
        return [i.name for i in self.db.search(query)]

    def test_aliases(self):
        self.assertIn("Roti / chapati (whole wheat)", self.names("chapati"))
        self.assertIn("Yogurt / curd, plain", self.names("curd"))
        self.assertIn("Egg, whole, boiled", self.names("anda"))

    def test_prefix_and_case(self):
        names = self.names("CHICK")
        self.assertIn("Chicken breast, cooked", names)
        self.assertIn("Chickpeas, boiled", names)

    def test_order_follows_list_for_ties(self):
        names = self.names("rice")
        self.assertLess(names.index("Rice, white, cooked"), names.index("Rice, brown, cooked"))

    def test_multi_word(self):
        self.assertEqual(self.names("breast chicken")[0], "Chicken breast, cooked")

    def test_empty_and_no_match(self):
        self.assertEqual(self.db.search(""), [])
        self.assertEqual(self.db.search("   "), [])
        self.assertEqual(self.db.search("zzzzz"), [])

    def test_limit(self):
        self.assertLessEqual(len(self.db.search("a", limit=5)), 5)

    def test_custom_food_found_and_ranked_first_on_tie(self):
        self.db.add_custom(FoodItem("Rice, mom's special", 150, 3, 30, 1))
        self.assertEqual(self.names("rice")[0], "Rice, mom's special")

    def test_duplicate_names_rejected(self):
        with self.assertRaises(ValueError):
            self.db.add_custom(FoodItem("banana", 90, 1, 23, 0.3))
        self.db.add_custom(FoodItem("My shake", 120, 10, 12, 3))
        with self.assertRaises(ValueError):
            self.db.add_custom(FoodItem("MY SHAKE", 120, 10, 12, 3))

    def test_suggestions(self):
        got = [i.name for i in self.db.suggestions(["Banana"], ["Apple", "Banana", "Nonexistent"])]
        self.assertEqual(got, ["Banana", "Apple"])


class ServingTests(unittest.TestCase):
    def test_roti_servings(self):
        roti = FoodDatabase().search("roti")[0]
        grams = grams_for(2, roti.servings["1 roti"])
        self.assertEqual(grams, 80)
        entry = roti.to_entry(grams, "lunch")
        self.assertAlmostEqual(entry.calories, 237.6)
        self.assertEqual(entry.meal, "lunch")

    def test_bad_amounts(self):
        for bad in (0, -1, float("nan")):
            with self.assertRaises(ValueError):
                grams_for(bad)

    def test_bad_custom_items(self):
        with self.assertRaises(ValueError):
            FoodItem("", 100)
        with self.assertRaises(ValueError):
            FoodItem("x", 100, servings={"1 piece": 0})
        with self.assertRaises(ValueError):
            FoodItem("x", 100, protein_per_100g=80, carbs_per_100g=80)

    def test_default_meal(self):
        def at(hour):
            return default_meal(datetime(2026, 10, 3, hour, 0))
        self.assertEqual(
            [at(8), at(10), at(11), at(15), at(16), at(20), at(21), at(23)],
            ["breakfast", "breakfast", "lunch", "lunch", "dinner", "dinner", "snacks", "snacks"],
        )


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = os.path.join(self.tmp.name, "data.json")

    def tearDown(self):
        self.tmp.cleanup()

    def test_round_trip_custom_favorites_recents_and_meals(self):
        s = Storage(self.path)
        s.add_custom_food(FoodItem("My shake", 120, 10, 12, 3, {"1 glass": 300}))
        self.assertTrue(s.toggle_favorite("My shake"))
        s.record_recent("Banana")
        s.get_log(datetime(2026, 10, 3).date()).foods.append(FoodEntry("Banana", 118, 89, meal="breakfast"))
        s.save()

        s2 = Storage(self.path)
        self.assertEqual(s2.food_db.get("my shake").servings, {"1 glass": 300})
        self.assertTrue(s2.food_db.get("my shake").custom)
        self.assertEqual(s2.favorites, ["My shake"])
        self.assertEqual(s2.recents, ["Banana"])
        self.assertEqual(s2.logs[datetime(2026, 10, 3).date()].foods[0].meal, "breakfast")

    def test_toggle_favorite_twice(self):
        s = Storage(self.path)
        s.toggle_favorite("Banana")
        self.assertFalse(s.toggle_favorite("Banana"))
        self.assertEqual(s.favorites, [])

    def test_recents_order_dedupe_and_cap(self):
        s = Storage(self.path)
        for i in range(MAX_RECENTS + 5):
            s.record_recent(f"Food {i}")
        s.record_recent("Food 7")
        self.assertEqual(len(s.recents), MAX_RECENTS)
        self.assertEqual(s.recents[0], "Food 7")
        self.assertEqual(len(set(s.recents)), MAX_RECENTS)

    def test_old_entries_without_meal_load_as_snacks(self):
        with open(self.path, "w") as fh:
            json.dump({"profile": None, "logs": {"2026-10-03": {"foods": [
                {"name": "Roti", "grams": 100, "calories_per_100g": 200, "protein_per_100g": 6,
                 "carbs_per_100g": 40, "fat_per_100g": 3}], "exercises": []}}}, fh)
        s = Storage(self.path)
        self.assertEqual(s.logs[datetime(2026, 10, 3).date()].foods[0].meal, "snacks")
        self.assertEqual(s.skipped_total, 0)

    def test_impossible_saved_entries_are_skipped_and_counted(self):
        """The junk test values from the Phase 13 screenshot must not crash the app."""
        with open(self.path, "w") as fh:
            json.dump({"profile": None, "logs": {"2026-10-03": {
                "foods": [
                    {"name": "roti", "grams": 100, "calories_per_100g": 96, "protein_per_100g": 23,
                     "carbs_per_100g": 34, "fat_per_100g": 23},
                    {"name": "fh", "grams": 4434, "calories_per_100g": 43, "protein_per_100g": 45,
                     "carbs_per_100g": 45, "fat_per_100g": 35}],
                "exercises": [{"name": "dgr", "duration_minutes": 234, "calories_burned": 99999}]}}}, fh)
        s = Storage(self.path)
        log = s.logs[datetime(2026, 10, 3).date()]
        self.assertEqual([f.name for f in log.foods], ["roti"])
        self.assertEqual(log.exercises, [])
        self.assertEqual(s.skipped, {"foods": 1, "exercises": 1, "custom_foods": 0, "weights": 0})

    def test_bad_custom_food_in_file_is_skipped(self):
        with open(self.path, "w") as fh:
            json.dump({"profile": None, "logs": {}, "custom_foods": [
                {"name": "Bad", "calories_per_100g": 5000},
                {"name": "Good", "calories_per_100g": 100}]}, fh)
        s = Storage(self.path)
        self.assertIsNotNone(s.food_db.get("Good"))
        self.assertIsNone(s.food_db.get("Bad"))
        self.assertEqual(s.skipped["custom_foods"], 1)

    def test_phase13_file_still_loads(self):
        with open(self.path, "w") as fh:
            json.dump({"profile": {"name": "A", "age": 30, "sex": "male", "weight_kg": 70.0,
                                   "height_cm": 175.0, "activity_level": "light",
                                   "goal": "lose", "pace": "steady"}, "logs": {}}, fh)
        s = Storage(self.path)
        self.assertEqual(s.profile.goal, "lose")
        self.assertEqual(s.favorites, [])


if __name__ == "__main__":
    unittest.main()
