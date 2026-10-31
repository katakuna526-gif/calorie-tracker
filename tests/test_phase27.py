import os
import tempfile
import unittest
from datetime import date

import flet as ft
from calorie_engine import Person
from flet_ui.app import FletTrackerApp
from flet_ui.entry_viewmodels import make_exercise_entry, make_food_entry
from flet_ui.app import build_log_screen
from flet_ui.theme import palette_for
from storage import Storage


class Phase27EntryTests(unittest.TestCase):
    def test_food_form_values_use_existing_entry_validation(self):
        food = make_food_entry("  Banana ", "118", "89", "1.1", "22.8", "0.3", "breakfast")
        self.assertEqual(food.name, "Banana")
        self.assertEqual(food.grams, 118)
        self.assertAlmostEqual(food.calories, 105.02)
        with self.assertRaises(ValueError):
            make_food_entry("", "-2", "901", "0", "0", "0", "lunch")

    def test_exercise_form_estimate_and_manual_calories(self):
        walking = make_exercise_entry("Walking", "30", 70, "moderate")
        self.assertEqual(walking.duration_minutes, 30)
        self.assertGreater(walking.calories_burned, 0)
        known = make_exercise_entry("Other", "20", 70, manual_calories="90")
        self.assertEqual(known.calories_burned, 90)
        with self.assertRaises(ValueError):
            make_exercise_entry("Other", "20", 70, manual_calories="-1")

    def test_food_and_exercise_write_to_shared_storage_for_selected_day(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "data.json")
            store = Storage(path)
            store.profile = Person("Alex", 30, "male", 70, 175)
            day = date(2025, 5, 12)
            store.get_log(day).foods.append(make_food_entry("Apple", 100, 52, 0.3, 13.8, 0.2, "snacks"))
            store.get_log(day).exercises.append(make_exercise_entry("Walking", 30, 70))
            store.save()
            loaded = Storage(path)
            self.assertEqual(loaded.logs[day].foods[0].name, "Apple")
            self.assertEqual(loaded.logs[day].exercises[0].name, "Walking")

    def test_log_screen_has_entry_actions_and_lists_saved_food(self):
        from calorie_engine import DailyLog, FoodEntry
        log = DailyLog(log_date=date.today(), foods=[
            FoodEntry("Apple", 100, 52, 0.3, 13.8, 0.2, "snacks")
        ])
        calls = []
        screen = build_log_screen(
            {"day_label": "Today", "has_profile": False}, palette_for(),
            lambda event: None, lambda event: None, log=log,
            on_remove_food=lambda index: calls.append(index),
            on_remove_exercise=lambda index: calls.append(index),
            on_edit_food=lambda index: calls.append(index),
            on_duplicate_food=lambda index: calls.append(index),
            on_copy_yesterday=lambda event: None,
        )
        self.assertIsNotNone(screen)
        def descendants(control):
            yield control
            for child in getattr(control, "controls", []) or []:
                yield from descendants(child)
            child = getattr(control, "content", None)
            if child is not None:
                yield from descendants(child)
        self.assertTrue(any(isinstance(control, ft.Text) and "Apple" in (control.value or "")
                            for control in descendants(screen)))

    def test_food_and_exercise_dialogs_construct_with_flet_controls(self):
        class FakePage:
            def __init__(self):
                self.dialogs = []

            def show_dialog(self, dialog):
                self.dialogs.append(dialog)

            def update(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            store = Storage(os.path.join(folder, "data.json"))
            store.profile = Person("Alex", 30, "male", 70, 175)
            app = object.__new__(FletTrackerApp)
            app.page = FakePage()
            app.storage = store
            app.selected_date = date.today()
            app.palette = palette_for()
            app._add_food_dialog()
            app._add_exercise_dialog()
            self.assertEqual(len(app.page.dialogs), 2)
            self.assertIsInstance(app.page.dialogs[0], ft.BottomSheet)
            self.assertEqual(app.page.dialogs[1].title, "Add exercise")
            food_controls = app.page.dialogs[0].content.content.controls
            self.assertTrue(any(isinstance(control, ft.TextField)
                                and control.hint_text == "Search food" for control in food_controls))


if __name__ == "__main__":
    unittest.main()
