import json
import os
import tempfile
import unittest
from datetime import date

from calorie_engine import Person, calculate_targets
from questions import QUESTIONS, person_from_answers, validate_answer
from stats import goal_weight_progress
from storage import Storage


class Phase21Tests(unittest.TestCase):
    def test_custom_targets_override_only_their_calculated_values(self):
        person = Person(
            "Test", 30, "female", 70, 165, "light", "lose", "gentle",
            goal_weight_kg=62, custom_calorie_target=1875,
            custom_protein_target=115, custom_fat_target=60,
        )
        targets = calculate_targets(person)
        self.assertEqual(targets["calories"], 1875)
        self.assertEqual(targets["protein_g"], 115)
        self.assertEqual(targets["fat_g"], 60)
        self.assertGreater(targets["carbs_g"], 0)
        self.assertFalse(targets["floor_applied"])

    def test_custom_targets_validate_ranges(self):
        with self.assertRaises(ValueError):
            Person("Test", 30, "male", 80, 180, custom_calorie_target=400)
        with self.assertRaises(ValueError):
            Person("Test", 30, "male", 80, 180, custom_protein_target=1001)

    def test_optional_target_questions_accept_blank_and_build_profile(self):
        optional = next(q for q in QUESTIONS if q["key"] == "goal_weight_kg")
        self.assertEqual(validate_answer(optional, ""), (None, None))
        answers = {
            "name": "Test", "age": 30, "sex": "male", "height_cm": 180,
            "weight_kg": 80, "activity_level": "moderate", "goal": "maintain",
            "goal_weight_kg": 70, "custom_calorie_target": 2100,
            "custom_protein_target": 140, "custom_carbs_target": None,
            "custom_fat_target": None,
        }
        person = person_from_answers(answers)
        self.assertEqual(person.goal_weight_kg, 70)
        self.assertEqual(person.custom_calorie_target, 2100)

    def test_legacy_profile_json_loads_and_keeps_existing_top_level_shape(self):
        legacy = {
            "name": "Legacy", "age": 30, "sex": "male", "weight_kg": 80,
            "height_cm": 180, "activity_level": "moderate", "goal": "lose", "pace": "gentle",
        }
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "data.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"profile": legacy, "logs": {}, "weights": {}}, fh)
            store = Storage(path)
            self.assertIsNone(store.profile.custom_calorie_target)
            self.assertIsNone(store.profile.goal_weight_kg)
            store.save()
            with open(path, encoding="utf-8") as fh:
                saved = json.load(fh)
            self.assertEqual(set(saved), {"profile", "custom_foods", "favorites", "recents", "weights", "logs", "preferences"})
            self.assertEqual(saved["profile"]["goal"], "lose")

    def test_goal_weight_progress_handles_direction_and_clamping(self):
        weights = {date(2026, 1, 1): 90.0, date(2026, 3, 1): 84.0}
        got = goal_weight_progress(weights, 80)
        self.assertEqual(got["remaining_kg"], -4.0)
        self.assertEqual(got["progress_pct"], 60.0)
        self.assertEqual(goal_weight_progress(weights, None), None)
        self.assertEqual(goal_weight_progress({}, 80), None)


if __name__ == "__main__":
    unittest.main()
