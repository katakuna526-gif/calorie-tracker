import unittest
from datetime import date, timedelta

import charts
import stats
import trends
from calorie_engine import DailyLog, FoodEntry, Person
from tests import fake_tk


def person(goal="lose", pace="steady"):
    return Person("A", 30, "male", 80, 180, "moderate", goal, pace)


def weights(start_kg, per_week, days, end=date(2026, 3, 1)):
    return {end - timedelta(days=days - 1 - i): start_kg + per_week * i / 7 for i in range(days)}


class TrendTests(unittest.TestCase):
    def test_needs_a_week(self):
        w = weights(80, 0, 3)
        self.assertFalse(trends.weight_rate(w, date(2026, 3, 1))["ok"])

    def test_rate_is_per_week(self):
        w = weights(80, -0.5, 15)
        r = trends.weight_rate(w, date(2026, 3, 1))
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["kg_per_week"], -0.5, places=2)

    def test_on_plan_text(self):
        p = person()
        plan = trends.planned_kg_per_week(p)
        self.assertLess(plan, 0)
        r = trends.weight_rate(weights(80, plan, 15), date(2026, 3, 1))
        self.assertEqual(trends.describe_trend(p, r)["status"], "on_plan")

    def test_opposite_direction_is_neutral(self):
        r = trends.weight_rate(weights(80, 0.4, 15), date(2026, 3, 1))
        out = trends.describe_trend(person(), r)
        self.assertEqual(out["status"], "opposite")
        self.assertNotIn("fail", out["text"].lower())

    def test_maintain_steady(self):
        r = trends.weight_rate(weights(80, 0.05, 15), date(2026, 3, 1))
        self.assertEqual(trends.describe_trend(person("maintain"), r)["status"], "steady")

    def test_no_data_text(self):
        out = trends.describe_trend(person(), trends.weight_rate({}, date(2026, 3, 1)))
        self.assertEqual(out["status"], "need_data")


class WeekCompareTests(unittest.TestCase):
    def _logs(self, days):
        ref = date(2026, 3, 14)
        return ref, {ref - timedelta(days=i): DailyLog(ref - timedelta(days=i),
                     [FoodEntry("x", 100, 100)]) for i in days}

    def test_more_days(self):
        ref, logs = self._logs([0, 1, 2, 3, 8])
        c = trends.week_comparison(person(), logs, ref)
        self.assertEqual(c["days_diff"], 3)
        self.assertIn("3 more days", trends.week_comparison_text(c))

    def test_fewer_days(self):
        ref, logs = self._logs([0, 7, 8, 9])
        self.assertIn("2 fewer days", trends.week_comparison_text(trends.week_comparison(person(), logs, ref)))

    def test_nothing_logged_is_empty(self):
        c = trends.week_comparison(person(), {}, date(2026, 3, 14))
        self.assertEqual(trends.week_comparison_text(c), "")


class ChartTests(unittest.TestCase):
    def _draw(self, pts):
        cv = fake_tk.Canvas()
        charts.draw_weight_chart(cv, 760, 190, pts)
        return cv

    def test_empty_message(self):
        self.assertTrue(any("No weigh-ins" in t for t in self._draw([]).texts()))

    def test_date_labels_even_steps(self):
        d0 = date(2026, 3, 1)
        pts = [(d0 + timedelta(days=i), 80 - i * 0.1) for i in range(11)]
        labels = [t for t in self._draw(pts).texts() if len(t) == 6 and t[:2].isdigit() and t[2] == " "]
        self.assertEqual(labels[:3], ["01 Mar", "04 Mar", "07 Mar"])   # 3-day steps, evenly spaced

    def test_latest_value_labelled(self):
        pts = [(date(2026, 3, 1), 80.0), (date(2026, 3, 8), 79.2)]
        self.assertIn("79.2 kg", self._draw(pts).texts())

    def test_tiny_range_has_no_two_decimal_ticks(self):
        ticks, dec = charts.nice_ticks(70 - 1.0, 70.2 + 1.0)
        self.assertEqual(dec, 0)


if __name__ == "__main__":
    unittest.main()
