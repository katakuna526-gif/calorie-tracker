import json
import os
import tempfile
import unittest
from datetime import date, timedelta

import stats
from calorie_engine import (
    DailyLog, FoodEntry, Person, calculate_daily_summary, calculate_exercise_calories,
    is_unusually_high_burn,
)
from exercises import EXERCISES, INTENSITIES, estimate_calories, get_exercise
from storage import Storage

TODAY = date(2026, 10, 4)


class ExerciseListTests(unittest.TestCase):
    def test_names_unique_and_levels_make_sense(self):
        names = [e.name.lower() for e in EXERCISES]
        self.assertEqual(len(names), len(set(names)))
        for e in EXERCISES:
            self.assertTrue(1 <= e.light <= e.moderate <= e.vigorous <= 20, e.name)
            self.assertTrue(e.note, e.name)

    def test_lookup_is_case_insensitive(self):
        self.assertEqual(get_exercise("  running ").name, "Running")
        self.assertIsNone(get_exercise("Underwater basket weaving"))
        self.assertIsNone(get_exercise(""))

    def test_includes_common_activities(self):
        for name in ("Walking", "Running", "Yoga", "Weight training", "Badminton", "Cricket", "Swimming"):
            self.assertIsNotNone(get_exercise(name), name)


class EstimateTests(unittest.TestCase):
    def test_known_values(self):
        # (MET - 1) x kg x hours
        self.assertAlmostEqual(estimate_calories("Running", "moderate", 89, 15), 162.4, places=1)
        self.assertAlmostEqual(estimate_calories("Walking", "vigorous", 70, 45), 210.0, places=1)

    def test_harder_effort_burns_more(self):
        results = [estimate_calories("Cycling (outdoor)", level, 70, 30) for level in INTENSITIES]
        self.assertEqual(results, sorted(results))
        self.assertLess(results[0], results[-1])

    def test_heavier_and_longer_burn_more(self):
        self.assertGreater(estimate_calories("Running", "moderate", 90, 30), estimate_calories("Running", "moderate", 60, 30))
        self.assertGreater(estimate_calories("Running", "moderate", 70, 60), estimate_calories("Running", "moderate", 70, 30))

    def test_resting_met_burns_nothing_extra(self):
        self.assertEqual(calculate_exercise_calories(1.0, 70, 60), 0)

    def test_bad_inputs(self):
        bad_calls = [
            lambda: estimate_calories("Nope", "moderate", 70, 30),
            lambda: estimate_calories("Running", "extreme", 70, 30),
            lambda: estimate_calories("Running", "moderate", 70, 0),
            lambda: estimate_calories("Running", "moderate", 70, 1441),
            lambda: estimate_calories("Running", "moderate", 70, float("nan")),
            lambda: estimate_calories("Running", "moderate", 0, 30),
            lambda: estimate_calories("Running", "moderate", 500, 30),
            lambda: calculate_exercise_calories(0.5, 70, 30),
        ]
        for call in bad_calls:
            with self.assertRaises(ValueError):
                call()

    def test_unusually_high_burn_warning(self):
        self.assertFalse(is_unusually_high_burn(60, 1000))   # exactly 1000 kcal/hour is allowed quietly
        self.assertTrue(is_unusually_high_burn(60, 1001))
        self.assertTrue(is_unusually_high_burn(234, 4553))   # the junk entry from the screenshot
        self.assertFalse(is_unusually_high_burn(45, 500))
        self.assertFalse(is_unusually_high_burn(0, 100))


class WeightLogTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "data.json")
        self.store = Storage(self.path)
        self.store.set_profile(Person("Alex", 25, "male", 70, 175, "moderate"), today=TODAY - timedelta(days=30))

    def test_profile_weight_is_recorded_as_first_weigh_in(self):
        self.assertEqual(self.store.weights, {TODAY - timedelta(days=30): 70.0})

    def test_log_updates_profile_and_persists(self):
        self.store.log_weight(TODAY, 68.46, today=TODAY)
        self.assertEqual(self.store.weights[TODAY], 68.5)
        self.assertEqual(self.store.profile.weight_kg, 68.5)
        again = Storage(self.path)
        self.assertEqual(again.weights[TODAY], 68.5)
        self.assertEqual(again.profile.weight_kg, 68.5)

    def test_older_weigh_in_does_not_change_current_weight(self):
        self.store.log_weight(TODAY, 68.0, today=TODAY)
        self.store.log_weight(TODAY - timedelta(days=10), 72.0, today=TODAY)
        self.assertEqual(self.store.profile.weight_kg, 68.0)

    def test_removing_latest_goes_back_to_previous(self):
        self.store.log_weight(TODAY - timedelta(days=5), 69.0, today=TODAY)
        self.store.log_weight(TODAY, 67.0, today=TODAY)
        self.store.remove_weight(TODAY)
        self.assertEqual(self.store.profile.weight_kg, 69.0)

    def test_removing_everything_keeps_the_profile_weight(self):
        self.store.remove_weight(TODAY - timedelta(days=30))
        self.assertEqual(self.store.weights, {})
        self.assertEqual(self.store.profile.weight_kg, 70.0)

    def test_remove_unknown_date_is_harmless(self):
        self.store.remove_weight(date(2020, 1, 1))
        self.assertEqual(len(self.store.weights), 1)

    def test_rejects_bad_weights(self):
        for kg in (0, -5, 29.9, 300.1, float("nan"), float("inf")):
            with self.assertRaises(ValueError, msg=str(kg)):
                self.store.log_weight(TODAY, kg, today=TODAY)
        self.assertNotIn(TODAY, self.store.weights)

    def test_rejects_future_dates(self):
        with self.assertRaises(ValueError):
            self.store.log_weight(TODAY + timedelta(days=1), 70, today=TODAY)
        self.assertEqual(self.store.profile.weight_kg, 70.0)

    def test_editing_profile_with_new_weight_adds_a_weigh_in(self):
        self.store.set_profile(Person("Alex", 25, "male", 72.4, 175, "moderate"), today=TODAY)
        self.assertEqual(self.store.weights[TODAY], 72.4)
        self.assertEqual(self.store.profile.weight_kg, 72.4)

    def test_editing_profile_without_weight_change_adds_nothing(self):
        self.store.set_profile(Person("Alex", 25, "male", 70, 175, "high", "lose", "gentle"), today=TODAY)
        self.assertEqual(len(self.store.weights), 1)
        self.assertEqual(self.store.profile.goal, "lose")

    def test_bad_weights_in_file_are_skipped_and_counted(self):
        with open(self.path, "w") as fh:
            json.dump({"profile": None, "logs": {},
                       "weights": {"2026-10-01": 70, "2026-10-02": 5, "2026-10-03": "heavy", "not-a-date": 70}}, fh)
        store = Storage(self.path)
        self.assertEqual(store.weights, {date(2026, 10, 1): 70.0})
        self.assertEqual(store.skipped["weights"], 3)

    def test_old_file_without_weights_loads(self):
        with open(self.path, "w") as fh:
            json.dump({"profile": {"name": "A", "age": 30, "sex": "male", "weight_kg": 70.0,
                                   "height_cm": 175.0, "activity_level": "light"}, "logs": {}}, fh)
        store = Storage(self.path)
        self.assertEqual(store.weights, {})
        self.assertEqual(store.person_on(TODAY).weight_kg, 70.0)


class PersonOnTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = Storage(os.path.join(self.tmp.name, "data.json"))
        self.store.set_profile(Person("Alex", 25, "male", 80, 175, "moderate"), today=date(2026, 9, 1))
        self.store.log_weight(date(2026, 9, 20), 75.0, today=TODAY)
        self.store.log_weight(date(2026, 10, 3), 72.0, today=TODAY)

    def kg(self, d):
        return self.store.person_on(d).weight_kg

    def test_weight_follows_the_dates(self):
        self.assertEqual(self.kg(date(2026, 8, 1)), 80)    # before the first weigh-in: the earliest one
        self.assertEqual(self.kg(date(2026, 9, 1)), 80)
        self.assertEqual(self.kg(date(2026, 9, 19)), 80)
        self.assertEqual(self.kg(date(2026, 9, 20)), 75)
        self.assertEqual(self.kg(date(2026, 10, 2)), 75)
        self.assertEqual(self.kg(date(2026, 10, 3)), 72)
        self.assertEqual(self.kg(date(2026, 12, 25)), 72)  # later days use the latest weigh-in

    def test_only_weight_changes(self):
        p = self.store.person_on(date(2026, 9, 1))
        self.assertEqual((p.name, p.age, p.height_cm, p.goal), ("Alex", 25, 175, "maintain"))

    def test_no_profile(self):
        self.assertIsNone(Storage(os.path.join(self.tmp.name, "other.json")).person_on(TODAY))

    def test_changing_weight_does_not_rewrite_past_burn(self):
        """A day's burned calories must stay the same after you weigh in at a new weight."""
        old_day = date(2026, 9, 10)
        logs = {old_day: DailyLog(old_day, foods=[FoodEntry("Roti", 100, 297)])}
        before = stats.daily_records(self.store.profile, logs, old_day, old_day, person_on=self.store.person_on)[0]
        self.store.log_weight(TODAY, 60.0, today=TODAY)   # a big change afterwards
        after = stats.daily_records(self.store.profile, logs, old_day, old_day, person_on=self.store.person_on)[0]
        self.assertEqual(before["calories_burned"], after["calories_burned"])
        # 80 kg: BMR = 800 + 1093.75 - 125 + 5 = 1773.75; baseline = BMR x 1.2
        self.assertEqual(before["baseline_burn"], round(1773.75 * 1.2, 2))

    def test_without_person_on_the_current_weight_is_used(self):
        old_day = date(2026, 9, 10)
        rec = stats.daily_records(self.store.profile, {}, old_day, old_day)[0]
        self.assertEqual(rec["baseline_burn"], calculate_daily_summary(self.store.profile, DailyLog(old_day))["baseline_burn"])

    def test_period_stats_accepts_person_on(self):
        recs, agg = stats.period_stats(self.store.profile, {}, "week", date(2026, 9, 10), person_on=self.store.person_on)
        self.assertEqual(len(recs), 7)
        self.assertEqual(agg["days_logged"], 0)


class WeightSummaryTests(unittest.TestCase):
    def test_empty(self):
        info = stats.weight_summary({})
        self.assertEqual(info["entries"], [])
        self.assertIsNone(info["latest"])
        self.assertEqual(info["days"], 0)

    def test_single(self):
        info = stats.weight_summary({date(2026, 10, 1): 70.0})
        self.assertEqual(info["change"], 0)
        self.assertIsNone(info["entries"][0]["change"])

    def test_changes_newest_first(self):
        info = stats.weight_summary({date(2026, 10, 1): 70.0, date(2026, 10, 8): 69.2, date(2026, 10, 4): 69.8})
        self.assertEqual([e["date"].day for e in info["entries"]], [8, 4, 1])
        self.assertEqual([e["change"] for e in info["entries"]], [-0.6, -0.2, None])
        self.assertEqual(info["change"], -0.8)
        self.assertEqual(info["days"], 7)
        self.assertEqual(info["latest"], (date(2026, 10, 8), 69.2))
        self.assertEqual(info["first"], (date(2026, 10, 1), 70.0))


if __name__ == "__main__":
    unittest.main()
