import os
import tempfile
import unittest
from datetime import date, timedelta
from types import SimpleNamespace

import flet as ft

from calorie_engine import Person
from flet_ui.app import FletTrackerApp, build_settings_screen, build_weight_screen
from flet_ui.theme import palette_for
from questions import visible_questions
from storage import Storage


class FakePage:
    def __init__(self):
        self.controls = []
        self.dialogs = []

    def add(self, control):
        self.controls.append(control)

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


def descendants(control):
    yield control
    for child in getattr(control, "controls", []) or []:
        yield from descendants(child)
    content = getattr(control, "content", None)
    if content is not None and content is not control:
        yield from descendants(content)


class Phase29FletTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Storage(os.path.join(self.temp.name, "data.json"))
        self.page = FakePage()

    def app(self):
        return FletTrackerApp(self.page, self.store)

    def test_first_launch_shows_welcome_and_guides_through_all_13_questions(self):
        app = self.app()
        self.assertTrue(app.setup_mode)
        self.assertEqual(app.setup_stage, "welcome")
        self.assertIsNone(self.page.navigation_bar)
        self.assertTrue(any(getattr(control, "content", None) == "Get started"
                            for control in descendants(app._switcher.content)))

        app._start_setup()
        self.assertIn("Step 1 / 13", [getattr(control, "value", None)
                                     for control in descendants(app._switcher.content)])
        answers = {
            "name": "Alex", "age": "25", "sex": "male", "height_cm": "173",
            "weight_kg": "85", "activity_level": "light", "goal": "lose",
            "pace": "steady", "goal_weight_kg": "75", "custom_calorie_target": "",
            "custom_protein_target": "", "custom_carbs_target": "", "custom_fat_target": "",
        }
        count = 0
        while app.setup_stage == "questions":
            question = visible_questions(app.setup_answers)[app.setup_index]
            key = question["key"]
            if question["type"] == "choice":
                app.setup_draft[key] = answers[key]
            else:
                app.setup_inputs[key].value = answers[key]
            app._next_setup()
            count += 1

        self.assertEqual(count, 13)
        self.assertEqual(app.setup_stage, "summary")
        self.assertEqual(app.setup_person.name, "Alex")
        self.assertEqual(app.setup_person.goal_weight_kg, 75)
        self.assertIsNone(self.store.profile)
        app._complete_setup()
        self.assertEqual(self.store.profile.name, "Alex")
        self.assertAlmostEqual(self.store.profile.weight_kg, 85)
        self.assertIn(date.today(), self.store.weights)
        self.assertFalse(app.setup_mode)
        self.assertEqual(self.page.navigation_bar.selected_index, 0)

    def test_questionnaire_skips_pace_when_goal_is_maintain(self):
        app = self.app()
        app.setup_answers = {"goal": "maintain"}
        keys = [question["key"] for question in visible_questions(app.setup_answers)]
        self.assertNotIn("pace", keys)
        self.assertEqual(len(keys), 12)

    def test_weight_screen_uses_units_trend_goal_and_recent_entries(self):
        day1, day2 = date.today() - timedelta(days=1), date.today()
        self.store.set_profile(Person("Alex", 25, "male", 85, 173,
                                      goal="lose", goal_weight_kg=75))
        self.store.log_weight(day1, 85.5)
        self.store.log_weight(day2, 85)
        app = self.app()
        app.pending_weight_unit = "kg"
        screen = app._weight_screen()
        controls = list(descendants(screen))
        self.assertTrue(any(getattr(control, "label", "") == "Weight (kg)" for control in controls))
        self.assertTrue(any(isinstance(control, ft.Stack) for control in controls))
        self.assertTrue(any(getattr(control, "value", None) == "Goal 75 kg" for control in controls))
        self.assertTrue(any(getattr(control, "value", None) == "85.0 kg" for control in controls))

    def test_saving_weight_in_pounds_updates_kg_profile_and_history(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173))
        app = self.app()
        app.pending_weight_unit = "lb"
        app._save_weight("200")
        self.assertAlmostEqual(self.store.profile.weight_kg, 90.7, places=1)
        self.assertAlmostEqual(self.store.weights[date.today()], 90.7, places=1)

    def test_settings_screen_has_profile_edit_units_appearance_and_backup_actions(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173, activity_level="light"))
        screen = build_settings_screen(
            {"profile": self.store.profile, "weight_unit": "kg", "theme": "dark"},
            palette_for("dark"), lambda value: None, lambda value: None,
            lambda event: None, lambda event: None, lambda event: None,
            lambda event: None, lambda event: None,
        )
        labels = [getattr(control, "value", None) for control in descendants(screen)]
        self.assertIn("Edit profile", [getattr(control, "value", None)
                                      for control in descendants(screen)])
        self.assertIn("Body weight units", labels)
        self.assertIn("Appearance", labels)
        self.assertIn("Save settings", [getattr(control, "content", None)
                                        for control in descendants(screen)])
        self.assertIn("How is this calculated?", [getattr(control, "value", None)
                                                  for control in descendants(screen)])

    def test_settings_changes_are_saved_and_profile_editor_updates_profile(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173,
                                      activity_level="light", goal="lose", pace="gentle"))
        app = self.app()
        app._set_pending_weight_unit("lb")
        app._set_pending_theme("dark")
        app._save_settings()
        self.assertEqual(self.store.preferences["weight_unit"], "lb")
        self.assertEqual(self.store.preferences["theme"], "dark")

        app._open_profile_editor()
        app.profile_fields["name"].value = "Alex Updated"
        app.profile_fields["weight"].value = "190"
        app.profile_fields["goal_weight"].value = "165"
        app._open_activity_picker()
        activity_choices = self.page.dialogs[-1].content.content.controls
        activity_choices[3].on_click(None)  # Light activity, after the title and hint.
        app._set_editor_sex("female")
        goal = ft.Dropdown(value="lose")
        pace = ft.Dropdown(value="steady")
        app._save_profile_editor(goal, pace)
        self.assertEqual(self.store.profile.name, "Alex Updated")
        self.assertEqual(self.store.profile.sex, "female")
        self.assertEqual(self.store.profile.activity_level, "light")
        self.assertAlmostEqual(self.store.profile.weight_kg, 86.2, places=1)
        self.assertAlmostEqual(self.store.profile.goal_weight_kg, 74.8, places=1)
        self.assertEqual(self.store.profile.pace, "steady")

    def test_calculation_sheet_matches_mockup_and_shows_live_profile_values(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173,
                                      activity_level="light", goal="lose", pace="steady"))
        app = self.app()
        app._open_calculations()
        sheet = self.page.dialogs[-1]
        self.assertIsInstance(sheet, ft.BottomSheet)
        labels = [getattr(control, "value", None) for control in descendants(sheet)]
        self.assertIn("How is this calculated?", labels)
        self.assertTrue(any(isinstance(label, str) and label.startswith("1. BMR (at rest)")
                            for label in labels))
        self.assertTrue(any(isinstance(label, str) and label.startswith("Daily target")
                            for label in labels))
        self.assertIn("Estimates only. Not medical advice.", labels)

    def test_tab_content_switches_with_fade_animation(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173))
        app = self.app()
        switcher = app._switcher
        self.assertIsInstance(switcher, ft.AnimatedSwitcher)
        self.assertEqual(switcher.duration, 240)
        app._on_tab_change(SimpleNamespace(control=SimpleNamespace(selected_index=3)))
        self.assertIs(app._switcher, switcher)
        self.assertEqual(self.page.navigation_bar.selected_index, 3)
        self.assertTrue(any(isinstance(control, ft.TextField)
                            and control.label == "Weight (kg)"
                            for control in descendants(app._switcher.content)))

    def test_backup_and_restore_from_settings_keep_safety_copy(self):
        self.store.set_profile(Person("Alex", 25, "male", 85, 173))
        app = self.app()
        app.backup_directory = os.path.join(self.temp.name, "backups")
        app._backup_data()
        backups = [name for name in os.listdir(app.backup_directory) if name.endswith(".json")]
        self.assertEqual(len(backups), 1)
        self.store.profile.name = "Changed"
        self.store.save()
        app._restore_backup()
        file_list = self.page.dialogs[-1]
        first_backup = file_list.content.controls[1]
        first_backup.on_click(None)
        confirm = self.page.dialogs[-1]
        confirm.actions[1].on_click(None)
        self.assertEqual(self.store.profile.name, "Alex")
        self.assertTrue(os.path.exists(self.store.path + ".before_restore"))


if __name__ == "__main__":
    unittest.main()
