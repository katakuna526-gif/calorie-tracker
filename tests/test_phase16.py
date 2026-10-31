import unittest
from datetime import date, timedelta

from calorie_engine import DailyLog, FoodEntry, Person, calculate_targets
import stats


class Phase16Tests(unittest.TestCase):
    def setUp(self):
        self.person = Person("Test", 30, "male", 80, 180, "moderate", "lose", "gentle")

    def test_progress_fraction_clamps(self):
        self.assertEqual(stats.progress_fraction(250, 500), 0.5)
        self.assertEqual(stats.progress_fraction(600, 500), 1.0)
        self.assertEqual(stats.progress_fraction(-10, 500), 0.0)
        self.assertEqual(stats.progress_fraction(10, 0), 0.0)

    def test_weekly_summary_only_averages_logged_food_days(self):
        today = date(2026, 10, 4)
        logs = {}
        for i, kcal in ((0, 2000), (1, 2200), (3, 1800)):
            d = today - timedelta(days=i)
            logs[d] = DailyLog(log_date=d, foods=[FoodEntry("Meal", 1000, kcal / 10, 2, 3, 1, "lunch")])
        result = stats.weekly_summary(self.person, logs, today)
        self.assertEqual(result["days_logged"], 3)
        self.assertAlmostEqual(result["consumed_avg"], 2000.0)
        self.assertAlmostEqual(result["protein_avg"], 20.0)

    def test_weight_trend_is_windowed_and_sorted(self):
        today = date(2026, 10, 4)
        weights = {today - timedelta(days=40): 90, today - timedelta(days=5): 82, today: 81}
        result = stats.weight_trend(weights, today, 30)
        self.assertEqual([x["kg"] for x in result], [82, 81])

    def test_targets_are_available_for_dashboard(self):
        target = calculate_targets(self.person)
        self.assertGreater(target["calories"], 0)
        self.assertGreater(target["protein_g"], 0)
        self.assertGreater(target["carbs_g"], 0)
        self.assertGreater(target["fat_g"], 0)


if __name__ == "__main__":
    unittest.main()
