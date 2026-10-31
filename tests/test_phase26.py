import os
import tempfile
import unittest
from datetime import date

from calorie_engine import ExerciseEntry, FoodEntry, Person
from flet_ui.app import TAB_NAMES, build_log_screen, navigation_bar
from flet_ui.theme import DARK, LIGHT, palette_for
from flet_ui.viewmodels import log_dashboard
from storage import Storage


class Phase26ViewModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Storage(os.path.join(self.temp.name, "data.json"))
        self.day = date(2025, 4, 3)

    def test_empty_profile_is_read_only_and_has_date_quote(self):
        data = log_dashboard(self.store, self.day, today=date(2025, 4, 3))
        self.assertFalse(data["has_profile"])
        self.assertEqual(data["day_label"], "Today")
        self.assertEqual(data["quote"], __import__("stats").quote_for(self.day))
        self.assertEqual(data["target"], 0)
        self.assertEqual(self.store.logs, {})

    def test_dashboard_uses_existing_profile_food_and_exercise_math(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175, "moderate", "maintain")
        self.store.logs[self.day] = __import__("calorie_engine").DailyLog(
            log_date=self.day,
            foods=[FoodEntry("Oats", 100, 380, 13, 68, 7, "breakfast")],
            exercises=[ExerciseEntry("Walk", 30, 100)],
        )
        data = log_dashboard(self.store, self.day, today=date(2025, 4, 4))
        self.assertTrue(data["has_profile"])
        self.assertEqual(data["consumed"], 380)
        self.assertEqual(data["burned"], round(__import__("calorie_engine").calculate_daily_summary(
            self.store.profile, self.store.logs[self.day])["calories_burned"]))
        self.assertEqual(data["macros"][0]["value"], 13)
        self.assertEqual(data["macros"][0]["status"], "71 g remaining")
        self.assertEqual(data["remaining_amount"], abs(data["target"] - 380))
        self.assertEqual(data["day_label"], "Thu, 3 Apr")

    def test_over_target_copy_is_neutral(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175, "moderate", "maintain",
                                    custom_protein_target=1)
        from calorie_engine import DailyLog
        self.store.logs[self.day] = DailyLog(self.day, [FoodEntry("Food", 100, 100, 10)], [])
        data = log_dashboard(self.store, self.day, today=date(2025, 4, 4))
        self.assertEqual(data["macros"][0]["status"], "9 g over target")


class Phase26ThemeAndUiTests(unittest.TestCase):
    def test_dark_default_and_light_palette(self):
        self.assertEqual(palette_for(), DARK)
        self.assertEqual(palette_for("light"), LIGHT)
        palette = palette_for("dark")
        palette["background"] = "changed"
        self.assertEqual(palette_for()["background"], DARK["background"])

    def test_five_tab_bar_and_log_screen_construct(self):
        self.assertEqual(TAB_NAMES, ("Log", "Calendar", "Stats", "Weight", "Settings"))
        bar = navigation_bar(palette_for(), 0, lambda event: None)
        self.assertEqual(len(bar.destinations), 5)
        self.assertEqual([item.label for item in bar.destinations], list(TAB_NAMES))
        screen = build_log_screen({"day_label": "Today", "has_profile": False}, palette_for(),
                                  lambda event: None, lambda event: None)
        self.assertIsNotNone(screen)


if __name__ == "__main__":
    unittest.main()
