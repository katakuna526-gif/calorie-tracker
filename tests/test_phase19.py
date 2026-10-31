import os
import tempfile
import unittest
from datetime import date

from exporter import period_csv_rows, write_csv
from stats import target_adherence


class Phase19Tests(unittest.TestCase):
    def test_target_adherence_counts_logged_days_and_tolerance(self):
        records = [
            {"day": date(2026, 10, 1), "logged": True, "calories_consumed": 2000, "exercise_calories": 0},
            {"day": date(2026, 10, 2), "logged": True, "calories_consumed": 2150, "exercise_calories": 300},
            {"day": date(2026, 10, 3), "logged": False, "calories_consumed": 0, "exercise_calories": 0},
            {"day": date(2026, 10, 4), "logged": True, "calories_consumed": 1600, "exercise_calories": 100},
        ]
        result = target_adherence(records, lambda d: 2000)
        self.assertEqual(result["days_logged"], 3)
        self.assertEqual(result["days_on_target"], 2)
        self.assertAlmostEqual(result["on_target_pct"], 66.7, places=1)
        self.assertAlmostEqual(result["average_variance"], -83.3, places=1)
        self.assertEqual(result["exercise_days"], 2)

    def test_target_adherence_empty_range_is_safe(self):
        result = target_adherence([], lambda d: 2000)
        self.assertEqual(result["days_logged"], 0)
        self.assertEqual(result["days_on_target"], 0)
        self.assertEqual(result["on_target_pct"], 0.0)

    def test_csv_rows_include_target_and_variance(self):
        records = [{
            "day": date(2026, 10, 4), "logged": True,
            "calories_consumed": 2110, "calories_burned": 2500,
            "exercise_calories": 200, "protein_g": 120,
            "carbs_g": 250, "fat_g": 70,
        }]
        rows = period_csv_rows(records, {date(2026, 10, 4): 2200})
        self.assertEqual(rows[0]["date"], "2026-10-04")
        self.assertEqual(rows[0]["calorie_target"], 2200)
        self.assertEqual(rows[0]["calorie_variance"], -90)
        self.assertEqual(rows[0]["food_logged"], "yes")

    def test_csv_export_round_trips(self):
        rows = period_csv_rows([{
            "day": date(2026, 10, 4), "logged": False,
            "calories_consumed": 0, "calories_burned": 2450,
            "exercise_calories": 0, "protein_g": 0,
            "carbs_g": 0, "fat_g": 0,
        }])
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "report.csv")
            write_csv(path, rows)
            with open(path, encoding="utf-8-sig") as fh:
                text = fh.read()
            self.assertIn("date,food_logged,calories_consumed", text)
            self.assertIn("2026-10-04,no,0", text)


if __name__ == "__main__":
    unittest.main()
