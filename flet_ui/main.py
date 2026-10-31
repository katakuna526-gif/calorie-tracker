"""Run the Android-style Flet preview on Windows from the calorie_app folder."""

import sys
import os
from pathlib import Path

import flet as ft

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from flet_ui.app import FletTrackerApp
from storage import DEFAULT_PATH, Storage


def make_storage():
    """Use Flet's durable, private app folder when packaged; keep desktop data shared."""
    app_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if app_data:
        data_dir = Path(app_data)
        data_dir.mkdir(parents=True, exist_ok=True)
        return Storage(str(data_dir / "calorie_tracker.json"))
    return Storage(DEFAULT_PATH)


def main(page: ft.Page):
    FletTrackerApp(page, make_storage())


if __name__ == "__main__":
    ft.run(main)
