"""Builds the real App and its panels on the stand-in toolkit and clicks through them.

This checks the wiring (the right functions are called with the right data and the labels
show the right numbers). It cannot check how the window looks; that needs a real screen.
"""

import os
import sys
import tempfile
import unittest
from collections import namedtuple
from datetime import date, timedelta
from unittest import mock

from tests import fake_tk

_patcher = None
app_module = ui_helpers = None
Person = Storage = None
OTHER = ""
Event = namedtuple("Event", "num delta x_root y_root")


def setUpModule():
    global _patcher, app_module, ui_helpers, Person, Storage, OTHER
    _patcher = mock.patch.dict(sys.modules, fake_tk.install())
    _patcher.start()
    for name in ("app", "food_panel", "exercise_panel", "weight_panel", "ui_helpers", "wizard"):
        sys.modules.pop(name, None)
    import app as app_module_
    import exercise_panel
    import ui_helpers as ui_helpers_
    from calorie_engine import Person as Person_
    from storage import Storage as Storage_
    app_module, ui_helpers, Person, Storage = app_module_, ui_helpers_, Person_, Storage_
    OTHER = exercise_panel.OTHER


def tearDownModule():
    _patcher.stop()  # also removes the stand-in-bound modules from sys.modules


def text_of(widget):
    return widget.opts.get("text", "")


class AppTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Storage(os.path.join(self.tmp.name, "data.json"))
        self.store.set_profile(Person("Alex", 25, "male", 70, 175, "moderate", "lose", "steady"))
        self.app = app_module.App(self.store)
        for fn in (app_module.messagebox.showerror, app_module.messagebox.showinfo):
            fn.reset_mock()

    # ---- opening
    def test_opens_with_profile_and_summary(self):
        self.assertIn("Daily target", text_of(self.app.profile_text))
        self.assertIn("kcal", text_of(self.app.progress_text))
        self.assertIn("Target", text_of(self.app.summary))
        self.assertEqual(len(self.app.tabs._children), 5)  # Log, Calendar, Stats, Weight, Settings

    def test_settings_save_theme_and_weight_unit(self):
        self.app.weight_unit_var.set("lb")
        self.app.theme_var.set("dark")
        self.app.save_settings()
        self.assertEqual(self.store.preferences, {"weight_unit": "lb", "theme": "dark"})
        self.assertIn("154.3 lb", text_of(self.app.profile_text))
        self.assertEqual(self.app.style.current_theme, "clam")
        self.assertEqual(self.app.weight_panel.weight_label.cget("text"), "Weight (lb)")
        self.app.weight_panel.kg.set("150")
        self.app.weight_panel._save()
        self.assertAlmostEqual(self.store.profile.weight_kg, 68.0, places=1)

    def test_opens_without_profile(self):
        empty = Storage(os.path.join(self.tmp.name, "empty.json"))
        app = app_module.App(empty)
        self.assertIn("No profile yet", text_of(app.profile_text))

    def test_calculation_explanation_includes_estimates_and_disclaimer(self):
        self.assertIn("not medical advice", text_of(self.app.disclaimer))
        window = self.app.show_calculations()
        explanation = text_of(self.app.calculation_text)
        self.assertIn("Mifflin", explanation)
        self.assertIn("TDEE", explanation)
        self.assertIn("not medical advice", explanation)
        self.assertIsNotNone(window)

    def test_custom_target_below_usual_minimum_is_clearly_flagged(self):
        below_floor = Person("Alex", 25, "male", 70, 175, "moderate", "lose", "steady",
                             custom_calorie_target=1300)
        self.store.set_profile(below_floor)
        self.app.refresh_all()
        self.assertIn("below the usual 1500 kcal/day minimum", text_of(self.app.profile_text))
        self.app.show_calculations()
        explanation = text_of(self.app.calculation_text)
        self.assertIn("custom calorie target (1300 kcal/day)", explanation)
        self.assertIn("cannot assess whether a target is appropriate", explanation)

    # ---- food
    def test_search_pick_and_add_food(self):
        panel = self.app.food_panel
        panel.query.set("roti")
        panel.result_list.selection_set(0)
        panel._select()
        self.assertEqual(panel.unit.get().split(" (")[0], "1 roti")
        panel.qty.set("2")
        panel._add()
        food = self.app.log.foods[0]
        self.assertAlmostEqual(food.grams, 80)
        self.assertIn("kcal", panel.entries.items[0])
        self.assertIn("238", text_of(self.app.progress_text))   # 80 g of roti is about 238 kcal

    def test_add_food_without_choosing_one(self):
        self.app.food_panel._add()
        app_module.messagebox.showinfo.assert_called()
        self.assertEqual(self.app.log.foods, [])

    # ---- exercise
    def test_exercise_estimate_and_add(self):
        panel = self.app.exercise_panel
        panel.activity.set("Running")
        panel.intensity.set("moderate")
        panel.minutes.set("15")
        self.assertIn("128 kcal", text_of(panel.estimate))   # (8.3 - 1) x 70 kg x 0.25 h
        panel._add()
        entry = self.app.log.exercises[0]
        self.assertAlmostEqual(entry.calories_burned, 127.75, delta=0.1)
        self.assertEqual(entry.name, "Running (moderate)")
        self.assertIn("128", panel.entries.items[0])

    def test_exercise_other_uses_typed_calories(self):
        panel = self.app.exercise_panel
        panel.activity.set(OTHER)
        panel.name.set("Padel")
        panel.minutes.set("60")
        panel.calories.set("400")
        panel._add()
        self.assertEqual(self.app.log.exercises[0].name, "Padel")
        self.assertEqual(self.app.log.exercises[0].calories_burned, 400)

    def test_exercise_bad_minutes_is_reported_not_raised(self):
        panel = self.app.exercise_panel
        panel.minutes.set("abc")
        panel._add()
        app_module.messagebox.showerror.assert_called()
        self.assertEqual(self.app.log.exercises, [])

    # ---- weight
    def test_logging_weight_updates_profile_and_targets(self):
        before = text_of(self.app.profile_text)
        self.app.weight_panel.kg.set("66.5")
        self.app.weight_panel._save()
        self.assertEqual(self.store.profile.weight_kg, 66.5)
        self.assertIn("66.5 kg", text_of(self.app.profile_text))
        self.assertNotEqual(before, text_of(self.app.profile_text))
        self.assertIn("66.5", self.app.weight_panel.listbox.items[0])

    def test_future_weight_is_rejected_with_a_message(self):
        self.app.selected = date.today() + timedelta(days=3)
        self.app.weight_panel.kg.set("70")
        self.app.weight_panel._save()
        app_module.messagebox.showerror.assert_called()
        self.assertEqual(self.store.weights.get(self.app.selected), None)

    def test_bad_weight_text(self):
        self.app.weight_panel.kg.set("heavy")
        self.app.weight_panel._save()
        app_module.messagebox.showerror.assert_called()

    def test_past_day_uses_the_weight_from_that_day(self):
        old_day = date.today() - timedelta(days=40)
        self.store.log_weight(old_day, 80.0)
        self.store.log_weight(date.today(), 70.0)
        self.app.selected = old_day
        self.app.refresh_all()
        self.assertEqual(self.app._weight_for_exercise(), 80.0)
        self.app.selected = date.today()
        self.assertEqual(self.app._weight_for_exercise(), 70.0)

    # ---- every screen refreshes without error for every period
    def test_all_screens_refresh(self):
        self.app.food_panel.query.set("rice")
        self.app.food_panel.result_list.selection_set(0)
        self.app.food_panel._select()
        self.app.food_panel._add()
        for kind in ("day", "week", "month"):
            self.app.stat_kind.set(kind)
            self.app.refresh_all()
            self.assertIn("days logged", text_of(self.app.stat_text))


class ScrollFrameTests(unittest.TestCase):
    def setUp(self):
        self.sf = ui_helpers.ScrollFrame(None)
        self.sf.winfo_viewable = lambda: True
        self.sf.inner.winfo_reqheight = lambda: 2000   # content taller than the window
        self.sf.canvas.winfo_height = lambda: 500
        self.sf.canvas.yview_scroll = mock.Mock()
        self.child = fake_tk.Widget(self.sf.inner)

    def wheel(self, over, delta=-120, num="??"):
        self.sf.winfo_containing = lambda x, y: over
        self.sf._on_wheel(Event(num, delta, 0, 0))

    def test_scrolls_down_when_over_the_page(self):
        self.wheel(self.child, delta=-120)
        self.sf.canvas.yview_scroll.assert_called_once_with(3, "units")

    def test_scrolls_up(self):
        self.wheel(self.child, delta=120)
        self.sf.canvas.yview_scroll.assert_called_once_with(-3, "units")

    def test_linux_buttons(self):
        self.wheel(self.child, delta=0, num=5)
        self.sf.canvas.yview_scroll.assert_called_once_with(3, "units")

    def test_ignored_over_a_list_or_dropdown(self):
        for cls in ("Listbox", "TCombobox"):
            box = fake_tk.Widget(self.sf.inner)
            box.winfo_class = lambda cls=cls: cls
            self.wheel(box)
        self.sf.canvas.yview_scroll.assert_not_called()

    def test_ignored_when_pointer_is_elsewhere(self):
        self.wheel(fake_tk.Widget(None))   # a widget in another window
        self.wheel(None)
        self.sf.canvas.yview_scroll.assert_not_called()

    def test_ignored_when_everything_fits(self):
        self.sf.inner.winfo_reqheight = lambda: 300
        self.wheel(self.child)
        self.sf.canvas.yview_scroll.assert_not_called()

    def test_ignored_when_tab_is_hidden(self):
        self.sf.winfo_viewable = lambda: False
        self.wheel(self.child)
        self.sf.canvas.yview_scroll.assert_not_called()


if __name__ == "__main__":
    unittest.main()
