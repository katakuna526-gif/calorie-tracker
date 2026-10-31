import json
import os
import tempfile
import tomllib
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from calorie_engine import Person
from flet_ui.app import FletTrackerApp
from flet_ui.main import make_storage
from flet_ui.theme import DARK, LIGHT, palette_for
from storage import Storage


class FakePage:
    def __init__(self, platform=ft.PagePlatform.ANDROID):
        self.platform = platform
        self.services = []
        self.dialogs = []
        self.controls = []

    def add(self, control):
        pass

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialogs.append(dialog)

    def pop_dialog(self):
        if self.dialogs:
            self.dialogs.pop()


class FakePicker:
    def __init__(self, selected=None):
        self.selected = selected
        self.saved = None

    async def save_file(self, **kwargs):
        self.saved = kwargs
        return "selected-location"

    async def pick_files(self, **kwargs):
        return [self.selected] if self.selected else []


class Phase30Tests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def test_light_theme_inverts_lime_accents_and_dark_surfaces(self):
        self.assertEqual(palette_for("dark"), DARK)
        self.assertEqual(LIGHT["accent"], "#11140D")
        self.assertEqual(LIGHT["accent_text"], "#FFFFFF")
        self.assertNotEqual(LIGHT["background"], DARK["background"])
        self.assertNotEqual(LIGHT["card"], DARK["card"])
        self.assertEqual(palette_for("light"), LIGHT)

    def test_packaged_flet_data_uses_private_durable_storage_path(self):
        data_dir = Path(self.temp.name) / "flet-data"
        with patch.dict(os.environ, {"FLET_APP_STORAGE_DATA": str(data_dir)}):
            store = make_storage()
        self.assertEqual(Path(store.path), data_dir / "calorie_tracker.json")
        self.assertTrue(data_dir.is_dir())

    def test_without_flet_runtime_environment_desktop_keeps_shared_legacy_file(self):
        with patch.dict(os.environ, {}, clear=True):
            store = make_storage()
        from storage import DEFAULT_PATH
        self.assertEqual(store.path, DEFAULT_PATH)

    def test_android_build_configuration_uses_root_entry_and_pinned_flet(self):
        config_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
        with config_path.open("rb") as source:
            config = tomllib.load(source)
        self.assertIn("flet==1.0.3", config["project"]["dependencies"])
        self.assertEqual(config["tool"]["flet"]["app"]["module"], "main.py")
        self.assertEqual(config["tool"]["flet"]["org"], "com.calorietracker")

    async def test_android_backup_uses_file_picker_and_exports_saved_json(self):
        path = str(Path(self.temp.name) / "data.json")
        store = Storage(path)
        store.set_profile(Person("Alex", 25, "male", 85, 173))
        page = FakePage()
        app = FletTrackerApp(page, store)
        picker = FakePicker()
        app.file_picker = picker

        await app._backup_action()

        self.assertEqual(picker.saved["file_type"], ft.FilePickerFileType.CUSTOM)
        self.assertEqual(picker.saved["allowed_extensions"], ["json"])
        exported = json.loads(picker.saved["src_bytes"].decode("utf-8"))
        self.assertEqual(exported["profile"]["name"], "Alex")
        self.assertTrue(page.dialogs)

    async def test_android_restore_picks_json_and_keeps_safety_copy(self):
        old_path = Path(self.temp.name) / "old.json"
        old_store = Storage(str(old_path))
        old_store.set_profile(Person("Saved Alex", 25, "male", 85, 173))
        backup = old_path.read_bytes()

        current = Storage(str(Path(self.temp.name) / "current.json"))
        current.set_profile(Person("Current", 32, "female", 70, 165))
        app = FletTrackerApp(FakePage(), current)
        picker = FakePicker(SimpleNamespace(bytes=backup, path=None, name="my_backup.json"))
        app.file_picker = picker

        await app._restore_action()
        dialog = app.page.dialogs[-1]
        self.assertIn("my_backup.json", dialog.title)
        dialog.actions[1].on_click(None)

        self.assertEqual(current.profile.name, "Saved Alex")
        self.assertTrue(Path(current.path + ".before_restore").exists())
        self.assertFalse(Path(current.path + ".picked_backup").exists())

    async def test_android_csv_export_passes_report_bytes_to_file_picker(self):
        store = Storage(str(Path(self.temp.name) / "csv.json"))
        store.set_profile(Person("Alex", 25, "male", 85, 173))
        app = FletTrackerApp(FakePage(), store)
        picker = FakePicker()
        app.file_picker = picker

        await app._export_stats_csv_action()

        self.assertTrue(picker.saved["file_name"].endswith(".csv"))
        self.assertIn(b"date,food_logged,calories_consumed", picker.saved["src_bytes"])


if __name__ == "__main__":
    unittest.main()
