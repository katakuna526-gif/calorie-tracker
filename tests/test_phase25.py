import json
import os
import tempfile
import unittest
from datetime import date

from calorie_engine import Person
from storage import Storage
from units import from_kg, to_kg


class SettingsAndBackupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.current = os.path.join(self.temp.name, "data.json")
        self.backup = os.path.join(self.temp.name, "backup.json")

    def test_preferences_are_saved_and_old_files_get_defaults(self):
        with open(self.current, "w", encoding="utf-8") as file:
            json.dump({"profile": None, "logs": {}}, file)
        store = Storage(self.current)
        self.assertEqual(store.preferences, {"weight_unit": "kg", "theme": "light"})
        store.set_preferences("lb", "dark")
        loaded = Storage(self.current)
        self.assertEqual(loaded.preferences, {"weight_unit": "lb", "theme": "dark"})

    def test_backup_restore_recovers_tracker_and_keeps_safety_copy(self):
        original = Storage(self.current)
        original.set_profile(Person("Alex", 25, "male", 70, 175, "moderate", "lose", "steady"))
        original.set_preferences("lb", "dark")
        with open(self.current, "rb") as source, open(self.backup, "wb") as target:
            target.write(source.read())

        original.set_profile(Person("Sam", 35, "female", 62, 165, "light", "maintain"))
        safety = original.restore_from(self.backup)
        self.assertEqual(original.profile.name, "Alex")
        self.assertEqual(original.preferences["theme"], "dark")
        self.assertTrue(os.path.isfile(safety))
        self.assertEqual(Storage(self.current).profile.name, "Alex")

    def test_invalid_backup_is_refused_without_changing_data(self):
        store = Storage(self.current)
        store.set_profile(Person("Alex", 25, "male", 70, 175, "moderate", "maintain"))
        with open(self.backup, "w", encoding="utf-8") as file:
            file.write("not json")
        with open(self.current, "rb") as file:
            before = file.read()
        with self.assertRaises((ValueError, json.JSONDecodeError)):
            store.restore_from(self.backup)
        with open(self.current, "rb") as file:
            self.assertEqual(file.read(), before)

    def test_weight_conversion_round_trip(self):
        pounds = from_kg(70, "lb")
        self.assertAlmostEqual(pounds, 154.3236, places=3)
        self.assertAlmostEqual(to_kg(pounds, "lb"), 70, places=6)


if __name__ == "__main__":
    unittest.main()
