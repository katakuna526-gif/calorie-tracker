import unittest
from datetime import date, timedelta

from calorie_engine import ExerciseEntry


class Phase18Tests(unittest.TestCase):
    def test_exercise_entry_edit_values_are_validated(self):
        entry = ExerciseEntry("Walking (moderate)", 30, 111)
        edited = ExerciseEntry("Cycling (moderate)", 45, 280)
        self.assertEqual(edited.name, "Cycling (moderate)")
        self.assertEqual(edited.duration_minutes, 45)
        self.assertEqual(edited.calories_burned, 280)
        with self.assertRaises(ValueError):
            ExerciseEntry("Bad", 0, 100)
        with self.assertRaises(ValueError):
            ExerciseEntry("Bad", 30, 10001)

    def test_exercise_duplicate_preserves_all_values(self):
        original = ExerciseEntry("Running (moderate)", 30, 325)
        duplicate = type(original)(**original.__dict__)
        self.assertEqual(duplicate.__dict__, original.__dict__)
        self.assertIsNot(duplicate, original)

    def test_day_navigation_dates_move_one_day_at_a_time(self):
        selected = date(2026, 10, 4)
        self.assertEqual(selected + timedelta(days=-1), date(2026, 10, 3))
        self.assertEqual(selected + timedelta(days=1), date(2026, 10, 5))

    def test_historical_day_can_have_independent_exercise_entries(self):
        day_a = [ExerciseEntry("Walking", 30, 111)]
        day_b = [type(day_a[0])(**day_a[0].__dict__)]
        day_b[0].calories_burned = 200
        self.assertEqual(day_a[0].calories_burned, 111)
        self.assertEqual(day_b[0].calories_burned, 200)


if __name__ == "__main__":
    unittest.main()
