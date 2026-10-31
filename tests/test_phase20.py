import unittest
from datetime import date

from stats import progress_insights, weight_goal_insight


class Phase20Tests(unittest.TestCase):
    def test_progress_insights_ignore_unlogged_days(self):
        records = [
            {"day": date(2026, 10, 1), "logged": True, "calories_consumed": 1980, "exercise_calories": 300},
            {"day": date(2026, 10, 2), "logged": False, "calories_consumed": 0, "exercise_calories": 0},
            {"day": date(2026, 10, 3), "logged": True, "calories_consumed": 2400, "exercise_calories": 0},
        ]
        got = progress_insights(records, lambda d: 2000)
        self.assertEqual(got["days_logged"], 2)
        self.assertEqual(got["exercise_days"], 1)
        self.assertEqual(got["exercise_calories"], 300)
        self.assertEqual(got["best_day"]["date"], date(2026, 10, 1))
        self.assertEqual(got["highest_day"]["date"], date(2026, 10, 3))

    def test_progress_insights_empty(self):
        got = progress_insights([], lambda d: 2000)
        self.assertEqual(got["days_logged"], 0)
        self.assertIsNone(got["best_day"])

    def test_weight_goal_direction(self):
        weights = {date(2026, 9, 1): 90.0, date(2026, 10, 1): 88.4}
        got = weight_goal_insight(weights, "lose")
        self.assertEqual(got["status"], "aligned")
        self.assertEqual(got["change"], -1.6)

        got = weight_goal_insight(weights, "gain")
        self.assertEqual(got["status"], "opposite")

    def test_weight_goal_needs_two_entries(self):
        got = weight_goal_insight({date(2026, 10, 1): 90.0}, "lose")
        self.assertEqual(got["status"], "not_enough_data")
        self.assertIsNone(got["change"])


if __name__ == "__main__":
    unittest.main()
