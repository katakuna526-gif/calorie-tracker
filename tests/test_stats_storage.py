import os
import tempfile
import unittest
from datetime import date, timedelta

from calorie_engine import Person, FoodEntry, ExerciseEntry, DailyLog
from storage import Storage
import stats


def make_logs(days_with_food, cal=200):
    logs = {}
    for d in days_with_food:
        log = DailyLog(d)
        log.foods.append(FoodEntry("Roti", 100, cal, 6, 40, 3))
        logs[d] = log
    return logs


class StorageTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "sub", "data.json")
            s = Storage(path)
            s.set_profile(Person("Alex", 25, "male", 70, 175, "light"))
            log = s.get_log(date(2026, 10, 3))
            log.foods.append(FoodEntry("Rice", 200, 130, 2.7, 28, 0.3))
            log.exercises.append(ExerciseEntry("Walk", 45, 180))
            s.save()

            s2 = Storage(path)
            self.assertEqual(s2.profile.name, "Alex")
            got = s2.logs[date(2026, 10, 3)]
            self.assertEqual(got.foods[0].name, "Rice")
            self.assertEqual(got.exercises[0].calories_burned, 180)

    def test_missing_file_is_fine(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = Storage(os.path.join(tmp, "nope.json"))
            self.assertIsNone(s.profile)
            self.assertEqual(s.logs, {})


class StatsTests(unittest.TestCase):
    def setUp(self):
        self.person = Person("Alex", 25, "male", 70, 175)
        self.today = date(2026, 10, 3)  # a Saturday

    def test_week_and_month_ranges(self):
        self.assertEqual(stats.week_range(self.today), (date(2026, 9, 28), date(2026, 10, 4)))
        self.assertEqual(stats.month_range(self.today), (date(2026, 10, 1), date(2026, 10, 31)))

    def test_week_aggregate_uses_logged_days_only(self):
        logs = make_logs([date(2026, 9, 28), date(2026, 9, 29)], cal=300)
        recs, agg = stats.period_stats(self.person, logs, "week", self.today)
        self.assertEqual(len(recs), 7)
        self.assertEqual(agg["days_logged"], 2)
        self.assertEqual(agg["consumed_total"], 600)
        self.assertEqual(agg["consumed_avg"], 300)

    def test_empty_period(self):
        _, agg = stats.period_stats(self.person, {}, "month", self.today)
        self.assertEqual(agg["days_logged"], 0)
        self.assertEqual(agg["consumed_avg"], 0)

    def test_bad_kind(self):
        with self.assertRaises(ValueError):
            stats.period_stats(self.person, {}, "year", self.today)

    def test_streak_today_logged(self):
        days = [self.today - timedelta(days=i) for i in range(3)]
        c = stats.consistency(make_logs(days), self.today)
        self.assertEqual(c["current_streak"], 3)
        self.assertEqual(c["days_logged"], 3)

    def test_streak_survives_unlogged_today(self):
        days = [self.today - timedelta(days=i) for i in (1, 2)]
        c = stats.consistency(make_logs(days), self.today)
        self.assertEqual(c["current_streak"], 2)

    def test_streak_broken(self):
        days = [self.today, self.today - timedelta(days=3)]
        c = stats.consistency(make_logs(days), self.today)
        self.assertEqual(c["current_streak"], 1)

    def test_longest_streak(self):
        days = [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3), date(2026, 9, 10)]
        c = stats.consistency(make_logs(days), self.today)
        self.assertEqual(c["longest_streak"], 3)

    def test_messages_and_quotes(self):
        self.assertIn("first meal", stats.consistency_message(
            {"window": 30, "days_logged": 0, "current_streak": 0, "longest_streak": 0}))
        self.assertTrue(stats.quote_for(self.today))
        self.assertNotEqual(stats.quote_for(self.today), stats.quote_for(self.today + timedelta(days=1)))


if __name__ == "__main__":
    unittest.main()
