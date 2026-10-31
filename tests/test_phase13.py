import json
import os
import tempfile
import unittest

import questions as Q
from calorie_engine import Person, calculate_targets
from storage import Storage


def q(key):
    return next(x for x in Q.QUESTIONS if x["key"] == key)


FULL_ANSWERS = {
    "name": "Alex", "age": 25, "sex": "male", "height_cm": 175.0, "weight_kg": 70.0,
    "activity_level": "moderate", "goal": "lose", "pace": "steady",
}


class ValidationTests(unittest.TestCase):
    def test_valid_number(self):
        self.assertEqual(Q.validate_answer(q("age"), " 25 "), (25, None))
        self.assertEqual(Q.validate_answer(q("weight_kg"), "70.5"), (70.5, None))

    def test_bad_numbers(self):
        for raw in ("", "abc", "nan", "inf", "17", "101", "-5"):
            value, problem = Q.validate_answer(q("age"), raw)
            self.assertIsNone(value, raw)
            self.assertTrue(problem, raw)

    def test_whole_number_required(self):
        self.assertIsNone(Q.validate_answer(q("age"), "25.5")[0])

    def test_choice(self):
        self.assertEqual(Q.validate_answer(q("sex"), "female"), ("female", None))
        self.assertIsNone(Q.validate_answer(q("sex"), "")[0])
        self.assertIsNone(Q.validate_answer(q("sex"), "other")[0])

    def test_text_default(self):
        self.assertEqual(Q.validate_answer(q("name"), "  ")[0], "Me")
        self.assertEqual(Q.validate_answer(q("name"), "Priya")[0], "Priya")


class FlowTests(unittest.TestCase):
    def test_pace_hidden_when_maintaining(self):
        keys = [x["key"] for x in Q.visible_questions({"goal": "maintain"})]
        self.assertNotIn("pace", keys)
        keys = [x["key"] for x in Q.visible_questions({"goal": "lose"})]
        self.assertIn("pace", keys)

    def test_person_from_answers_round_trip(self):
        person = Q.person_from_answers(FULL_ANSWERS)
        self.assertEqual(person.goal, "lose")
        expected = dict(FULL_ANSWERS, goal_weight_kg=None, custom_calorie_target=None,
                        custom_protein_target=None, custom_carbs_target=None,
                        custom_fat_target=None)
        self.assertEqual(Q.answers_from_person(person), expected)

    def test_maintain_needs_no_pace(self):
        answers = dict(FULL_ANSWERS, goal="maintain")
        del answers["pace"]
        self.assertEqual(Q.person_from_answers(answers).goal, "maintain")

    def test_missing_answer(self):
        answers = dict(FULL_ANSWERS)
        del answers["weight_kg"]
        with self.assertRaises(ValueError):
            Q.person_from_answers(answers)


class TargetTests(unittest.TestCase):
    def test_lose_steady(self):
        t = calculate_targets(Person("A", 25, "male", 70, 175, "moderate", "lose", "steady"))
        self.assertEqual(t["calories"], 2094)
        self.assertEqual(t["adjustment"], -500)
        self.assertEqual(t["protein_g"], 112)
        self.assertFalse(t["floor_applied"])

    def test_gain_gentle_and_maintain(self):
        base = Person("A", 25, "male", 70, 175, "moderate", "maintain")
        gain = Person("A", 25, "male", 70, 175, "moderate", "gain", "gentle")
        self.assertEqual(calculate_targets(gain)["calories"] - calculate_targets(base)["calories"], 250)
        self.assertEqual(calculate_targets(base)["adjustment"], 0)

    def test_calorie_floor(self):
        t = calculate_targets(Person("S", 40, "female", 45, 150, "sedentary", "lose", "steady"))
        self.assertEqual(t["calories"], 1200)
        self.assertTrue(t["floor_applied"])

    def test_macros_add_up_roughly(self):
        t = calculate_targets(Person("A", 25, "male", 70, 175, "moderate", "lose", "steady"))
        kcal = t["protein_g"] * 4 + t["carbs_g"] * 4 + t["fat_g"] * 9
        self.assertAlmostEqual(kcal, t["calories"], delta=10)

    def test_bad_goal_or_pace(self):
        with self.assertRaises(ValueError):
            Person("A", 25, "male", 70, 175, "moderate", "bulk")
        with self.assertRaises(ValueError):
            Person("A", 25, "male", 70, 175, "moderate", "lose", "extreme")


class OldDataTests(unittest.TestCase):
    def test_phase12_save_file_still_loads(self):
        """A profile saved before goals existed must load with sensible defaults."""
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            with open(path, "w") as fh:
                json.dump({"profile": {"name": "Old", "age": 30, "sex": "female", "weight_kg": 60.0,
                                       "height_cm": 165.0, "activity_level": "light"},
                           "logs": {}}, fh)
            store = Storage(path)
            self.assertEqual(store.profile.goal, "maintain")
            self.assertEqual(store.profile.pace, "gentle")

    def test_new_profile_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            store = Storage(path)
            store.set_profile(Q.person_from_answers(FULL_ANSWERS))
            self.assertEqual(Storage(path).profile.goal, "lose")


if __name__ == "__main__":
    unittest.main()
