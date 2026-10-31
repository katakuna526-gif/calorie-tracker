import unittest
from datetime import date

from calorie_engine import DailyLog, ExerciseEntry, FoodEntry
from flet_ui import theme
from flet_ui.viewmodels import calendar_month, day_marker, exercise_insight_text
from storage import Storage
import os
import tempfile


class Phase32Tests(unittest.TestCase):
    def test_day_marker(self):
        d = date(2026, 10, 5)
        self.assertIsNone(day_marker(None))
        self.assertIsNone(day_marker(DailyLog(d)))
        self.assertEqual(day_marker(DailyLog(d, [FoodEntry("x", 100, 95)])), "food")
        self.assertEqual(day_marker(DailyLog(d, [], [ExerciseEntry("walk", 20, 80)])), "exercise")
        self.assertEqual(day_marker(DailyLog(d, [FoodEntry("x", 100, 95)], [ExerciseEntry("walk", 20, 80)])), "food")

    def test_calendar_cells_carry_markers(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = Storage(os.path.join(tmp, "d.json"))
            store.logs[date(2026, 10, 5)] = DailyLog(date(2026, 10, 5), [FoodEntry("x", 95, 100)])
            store.logs[date(2026, 10, 7)] = DailyLog(date(2026, 10, 7), [], [ExerciseEntry("walk", 20, 80)])
            data = calendar_month(store, date(2026, 10, 1), date(2026, 10, 6), today=date(2026, 10, 6))
        cells = {c["day"]: c for w in data["weeks"] for c in w if c}
        self.assertEqual(cells[5]["marker"], "food")
        self.assertIsNone(cells[6]["marker"])
        self.assertEqual(cells[7]["marker"], "exercise")

    def test_exercise_insight_wording(self):
        self.assertEqual(exercise_insight_text(0, "week"), "No exercise logged this week.")
        self.assertEqual(exercise_insight_text(0, "month"), "No exercise logged this month.")
        self.assertEqual(exercise_insight_text(1, "week"), "Exercise on 1 day.")
        self.assertEqual(exercise_insight_text(3, "month"), "Exercise on 3 days.")

    def test_layout_tokens(self):
        self.assertEqual(theme.BOTTOM_SPACE, 24)
        self.assertEqual(theme.FAB_CLEARANCE, 88)
        self.assertEqual(theme.CALENDAR_DAY_SIZE, 44)
        self.assertGreater(theme.CALENDAR_CELL_HEIGHT, theme.CALENDAR_DAY_SIZE + theme.CALENDAR_DOT_SIZE)


if __name__ == "__main__":
    unittest.main()
