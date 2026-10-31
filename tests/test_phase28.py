import csv
import io
import os
import tempfile
import unittest
from datetime import date

import flet as ft

from calorie_engine import DailyLog, ExerciseEntry, FoodEntry, Person
from flet_ui.app import (FletTrackerApp, build_calendar_screen, build_log_screen,
                         build_stats_screen)
from exporter import period_csv_bytes
from flet_ui.theme import palette_for
from flet_ui.viewmodels import calculation_explanation, calendar_month, stats_dashboard
from storage import Storage


class Phase28ViewModelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = Storage(os.path.join(self.temp.name, "data.json"))

    def test_calendar_marks_logged_dates_and_does_not_create_empty_log(self):
        from calorie_engine import DailyLog
        day = date(2025, 2, 3)
        self.store.logs[day] = DailyLog(
            log_date=day,
            foods=[FoodEntry("Apple", 100, 52, 0.3, 13.8, 0.2, "snacks")],
            exercises=[ExerciseEntry("Walk", 20, 60)],
        )
        view = calendar_month(self.store, date(2025, 2, 1), day, today=date(2025, 2, 3))
        selected = [cell for week in view["weeks"] for cell in week if cell and cell["selected"]]
        self.assertEqual(len(selected), 1)
        self.assertTrue(selected[0]["has_food"])
        self.assertTrue(selected[0]["has_exercise"])
        self.assertEqual(view["food_count"], 1)
        self.assertEqual(view["food_calories"], 52)
        self.assertEqual(len(self.store.logs), 1)

    def test_calendar_month_grid_has_seven_columns_and_selected_day_summary(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175)
        day = date(2025, 4, 3)
        from calorie_engine import DailyLog
        self.store.logs[day] = DailyLog(day, [FoodEntry("Oats", 100, 380, 13, 66, 7)], [])
        view = calendar_month(self.store, date(2025, 4, 1), day, today=day)
        self.assertTrue(all(len(week) == 7 for week in view["weeks"]))
        self.assertEqual(view["consumed"], 380)
        self.assertIsNotNone(view["burned"])

    def test_stats_use_existing_period_aggregation_and_only_logged_food_days(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175)
        from calorie_engine import DailyLog
        self.store.logs[date(2025, 7, 1)] = DailyLog(
            date(2025, 7, 1), [FoodEntry("Rice", 100, 130)], [])
        self.store.logs[date(2025, 7, 3)] = DailyLog(
            date(2025, 7, 3), [FoodEntry("Rice", 200, 130)], [])
        view = stats_dashboard(self.store, date(2025, 7, 3), "week")
        self.assertEqual(view["days_logged"], 2)
        self.assertEqual(view["days_in_range"], 7)
        self.assertEqual(view["consumed_total"], 390)
        self.assertEqual(view["consumed_avg"], 195)
        self.assertEqual(len(view["records"]), 7)
        self.assertEqual(sum(record["logged"] for record in view["records"]), 2)
        self.assertTrue(all("target_fraction" in record for record in view["records"]))

    def test_stats_without_profile_return_a_plain_setup_state(self):
        view = stats_dashboard(self.store, date(2025, 7, 3), "month")
        self.assertFalse(view["has_profile"])
        self.assertEqual(view["days_in_range"], 31)
        self.assertEqual(view["records"], [])

    def test_stats_provide_average_macro_targets_for_logged_days(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175)
        from calorie_engine import DailyLog
        self.store.logs[date(2025, 7, 3)] = DailyLog(
            date(2025, 7, 3), [FoodEntry("Oats", 100, 380, 13, 66, 7)], [])
        view = stats_dashboard(self.store, date(2025, 7, 3), "day")
        self.assertGreater(view["macro_targets"]["protein"], 0)
        self.assertEqual(view["protein_avg"], 13)

    def test_stats_default_date_prefers_latest_food_logged_day(self):
        from calorie_engine import DailyLog
        self.store.logs[date(2025, 7, 2)] = DailyLog(
            date(2025, 7, 2), [FoodEntry("Apple", 100, 52)], [])
        self.store.logs[date(2025, 7, 5)] = DailyLog(
            date(2025, 7, 5), [FoodEntry("Rice", 100, 130)], [])
        from flet_ui.viewmodels import latest_food_log_date
        self.assertEqual(latest_food_log_date(self.store), date(2025, 7, 5))

    def test_csv_payload_contains_period_records_and_is_excel_friendly(self):
        self.store.profile = Person("Alex", 30, "male", 70, 175)
        from calorie_engine import DailyLog
        day = date(2025, 7, 3)
        self.store.logs[day] = DailyLog(day, [FoodEntry("Rice", 100, 130)], [])
        view = stats_dashboard(self.store, day, "day")
        payload = period_csv_bytes(view["records"], {day: view["records"][0]["target"]})
        rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["food_logged"], "yes")
        self.assertEqual(rows[0]["calories_consumed"], "130.0")


class Phase28ControlConstructionTests(unittest.TestCase):
    def test_calendar_and_stats_screens_construct(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Storage(os.path.join(folder, "data.json"))
            store.profile = Person("Alex", 30, "male", 70, 175)
            calendar_data = calendar_month(store, date(2025, 4, 1), date(2025, 4, 3))
            calendar_screen = build_calendar_screen(
                calendar_data, palette_for(), lambda event: None, lambda event: None,
                lambda day: None, lambda event: None,
            )
            stats_data = stats_dashboard(store, date(2025, 4, 3), "week")
            stats_screen = build_stats_screen(
                stats_data, palette_for(), "week", lambda event: None,
                lambda event: None, lambda event: None,
            )
            self.assertTrue(calendar_screen.controls)
            self.assertTrue(stats_screen.controls)

    def test_stats_screen_has_calorie_chart_and_export_action(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Storage(os.path.join(folder, "data.json"))
            store.profile = Person("Alex", 30, "male", 70, 175)
            from calorie_engine import DailyLog
            day = date.today()
            store.logs[day] = DailyLog(day, [FoodEntry("Apple", 100, 52)], [])
            data = stats_dashboard(store, day, "week")
            screen = build_stats_screen(data, palette_for(), "week", lambda event: None,
                                        lambda event: None, lambda event: None,
                                        on_export=lambda event: None)
            def descendants(control):
                yield control
                for child in getattr(control, "controls", []) or []:
                    yield from descendants(child)
                content = getattr(control, "content", None)
                if content is not None:
                    yield from descendants(content)
            controls = list(descendants(screen))
            self.assertTrue(any(getattr(control, "value", None) == "Average macros"
                                for control in controls))
            self.assertTrue(any(getattr(control, "value", None) == "eaten"
                                for control in controls))
            self.assertTrue(any(getattr(control, "value", None) == "burned"
                                for control in controls))
            self.assertTrue(any(getattr(control, "content", None) == "Export CSV"
                                and control.on_click is not None for control in controls))

    def test_export_handler_writes_csv_to_configured_download_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Storage(os.path.join(folder, "data.json"))
            store.profile = Person("Alex", 30, "male", 70, 175)
            day = date.today()
            from calorie_engine import DailyLog
            store.logs[day] = DailyLog(day, [FoodEntry("Apple", 100, 52)], [])
            app = object.__new__(FletTrackerApp)
            app.storage = store
            app.stats_reference_date = day
            app.stat_kind = "week"
            app.export_directory = folder
            app.page = object()
            app.palette = palette_for()
            app.messages = []
            app._info_dialog = lambda title, message: app.messages.append((title, message))
            app._export_stats_csv()
            saved = [name for name in os.listdir(folder) if name.endswith(".csv")]
            self.assertEqual(len(saved), 1)
            with open(os.path.join(folder, saved[0]), encoding="utf-8-sig", newline="") as file:
                rows = list(csv.DictReader(file))
            self.assertIn("calorie_tracker_week_", saved[0])
            self.assertEqual(len(rows), 7)
            today_row = next(row for row in rows if row["date"] == day.isoformat())
            self.assertEqual(today_row["food_logged"], "yes")
            self.assertIn("saved to", app.messages[0][1])


class Phase28LogScreenTests(unittest.TestCase):
    @staticmethod
    def descendants(control):
        yield control
        for child in getattr(control, "controls", []) or []:
            yield from Phase28LogScreenTests.descendants(child)
        content = getattr(control, "content", None)
        if content is not None and content is not control:
            yield from Phase28LogScreenTests.descendants(content)

    def test_log_screen_has_copy_yesterday_meal_sections_and_food_menu(self):
        log = DailyLog(date.today(), [
            FoodEntry("Oats", 100, 380, 13, 66, 7, "breakfast"),
            FoodEntry("Apple", 150, 78, 0, 21, 0, "snacks"),
        ], [])
        data = {"day_label": "Today", "has_profile": False, "quote": "Keep going"}
        screen = build_log_screen(data, palette_for(), lambda event: None,
                                  lambda event: None, log=log,
                                  on_remove_food=lambda index: None,
                                  on_remove_exercise=lambda index: None,
                                  on_edit_food=lambda index: None,
                                  on_duplicate_food=lambda index: None,
                                  on_copy_yesterday=lambda event: None)
        controls = list(self.descendants(screen))
        labels = [getattr(control, "value", None) for control in controls]
        self.assertTrue(any(getattr(control, "content", None) == "Copy yesterday"
                            for control in controls))
        self.assertIn("Breakfast", labels)
        self.assertIn("Snacks", labels)
        menus = [control for control in controls if isinstance(control, ft.PopupMenuButton)]
        self.assertEqual(len(menus), 2)
        self.assertEqual([item.content for item in menus[0].items], ["Edit", "Duplicate", "Delete"])

    def test_calculation_explanation_covers_target_and_food_estimates(self):
        person = Person("Alex", 30, "male", 70, 175)
        explanation = " ".join(calculation_explanation(person))
        self.assertIn("Mifflin", explanation)
        self.assertIn("TDEE", explanation)
        self.assertIn("(MET − 1)", explanation)
        self.assertIn("per 100 g", explanation)
        self.assertIn("not medical advice", explanation)

    def test_copy_yesterday_and_duplicate_food_keep_meal_and_nutrition(self):
        with tempfile.TemporaryDirectory() as folder:
            store = Storage(os.path.join(folder, "data.json"))
            yesterday, today = date(2025, 7, 2), date(2025, 7, 3)
            store.logs[yesterday] = DailyLog(
                yesterday, [FoodEntry("Oats", 100, 380, 13, 66, 7, "breakfast")], [])
            app = object.__new__(FletTrackerApp)
            app.storage, app.selected_date = store, today
            app.render = lambda: None
            app._copy_yesterday()
            copied = store.logs[today].foods[0]
            app._duplicate_food(0)
            self.assertEqual(len(store.logs[today].foods), 2)
            self.assertEqual(store.logs[today].foods[1].meal, "breakfast")
            self.assertEqual(store.logs[today].foods[1].calories, copied.calories)

    def test_add_food_search_uses_saved_servings_meal_and_calorie_preview(self):
        class Page:
            def __init__(self):
                self.dialogs = []

            def show_dialog(self, dialog):
                self.dialogs.append(dialog)

            def pop_dialog(self):
                self.dialogs.pop()

            def update(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            app = object.__new__(FletTrackerApp)
            app.storage = Storage(os.path.join(folder, "data.json"))
            app.selected_date = date.today()
            app.palette = palette_for()
            app.page = Page()
            app.render = lambda: None
            app._add_food_dialog()
            controls = app.page.dialogs[0].content.content.controls
            search, results = controls[:2]
            self.assertEqual(search.hint_text, "Search food")
            search.value = "Pasta"
            search.on_change(None)
            pasta = next(row for row in results.controls
                         if any(getattr(item, "value", None) == "Pasta, cooked"
                                for item in self.descendants(row)))
            pasta.on_click(None)
            amount_row = controls[3]
            amount, units = amount_row.controls
            self.assertEqual(amount.width, 96)
            units.controls[1].on_click(None)
            self.assertEqual(amount.value, "1")
            meals = controls[5]
            meals.controls[1].on_click(None)
            self.assertEqual(controls[6].value, "About 221 kcal · 140 g")
            self.assertEqual(controls[8].content, "Add food · 221 kcal")
            controls[8].on_click(None)
            entry = app.storage.logs[app.selected_date].foods[0]
            self.assertEqual(entry.name, "Pasta, cooked")
            self.assertEqual(entry.grams, 140)
            self.assertEqual(entry.meal, "lunch")

    def test_stats_period_switch_uses_lime_selected_pill_and_changes_period(self):
        data = {"has_profile": False, "start": date(2025, 7, 1),
                "title": "July 2025", "days_logged": 1, "days_in_range": 7}
        selected = []
        screen = build_stats_screen(data, palette_for(), "week", selected.append,
                                    lambda event: None, lambda event: None)
        periods = screen.controls[0]
        pills = periods.content.controls
        self.assertEqual(len(pills), 3)
        self.assertEqual(pills[1].bgcolor, palette_for()["accent"])
        self.assertEqual(pills[0].bgcolor, palette_for()["surface"])
        pills[2].on_click(None)
        self.assertEqual(selected, ["month"])

    def test_custom_food_form_saves_package_values_and_logs_selected_meal(self):
        class Page:
            def __init__(self):
                self.dialogs = []

            def show_dialog(self, dialog):
                self.dialogs.append(dialog)

            def pop_dialog(self):
                self.dialogs.pop()

            def update(self):
                pass

        with tempfile.TemporaryDirectory() as folder:
            app = object.__new__(FletTrackerApp)
            app.storage = Storage(os.path.join(folder, "data.json"))
            app.selected_date = date(2025, 7, 3)
            app.palette = palette_for()
            app.page = Page()
            app.render = lambda: None
            app._custom_food_dialog()
            controls = app.page.dialogs[0].content.content.controls
            controls[1].value = "Homemade soup"
            controls[2].value = "250"
            controls[3].value = "dinner"
            controls[4].value = "80"
            controls[5].value = "4"
            controls[6].value = "10"
            controls[7].value = "2"
            controls[9].on_click(None)
            entry = app.storage.logs[app.selected_date].foods[0]
            saved_food = app.storage.food_db.get("Homemade soup")
            self.assertEqual((entry.grams, entry.meal, entry.calories), (250, "dinner", 200))
            self.assertTrue(saved_food.custom)
            self.assertEqual(saved_food.protein_per_100g, 4)

if __name__ == "__main__":
    unittest.main()
