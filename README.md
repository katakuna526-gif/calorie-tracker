# Calorie Tracker

A simple, private calorie and fitness tracker for Android (and Windows preview), built with Python and [Flet](https://flet.dev).

Log what you eat and the exercise you do, see your daily calories and macros against a target, and watch your weight trend over time. All data stays on your device.

## Features
- Profile setup with a daily calorie and macro target (Mifflin-St Jeor estimate, activity level, goal and pace)
- Optional goal weight and custom calorie / protein / carb / fat targets
- Food logging with per-100 g nutrition, meals, copy yesterday
- Exercise logging with MET-based calorie estimates
- Calendar, daily / weekly / monthly stats and CSV export
- Weight log with trend chart and goal progress (kg or lb)
- Light and dark theme, backup and restore
- A logging streak that rewards showing up, not hitting numbers

> All calorie and nutrition values are estimates, not medical advice.

## Install on Android
1. Open the **Releases** page of this repository and download the latest `.apk`.
2. Open the file on your phone. If asked, allow installing apps from this source.
3. Open **Calorie Tracker**.

## Run on Windows (preview)
```
pip install flet==1.0.3
python flet_ui/main.py
```

## Build the Android app yourself
```
flet build apk --yes --no-rich-output
```
The APK appears in `build/apk`. The first build downloads the Android tools and needs internet access.

## Run the tests
```
python -m unittest discover -s tests -t .
```
(The tests that touch the Flet screens need `flet` installed.)

## Project layout
- `calorie_engine.py` – all the calorie maths (no UI)
- `stats.py`, `trends.py` – daily/weekly/monthly statistics and weight trends
- `storage.py` – saved data (JSON, written safely)
- `flet_ui/` – the phone interface
- `tests/` – unit tests
- `PROJECT_CONTEXT.md` – design decisions and working agreement

## Where is my data?
On Android it is stored in the app's private folder. On Windows it is `~/.calorie_tracker/data.json`. Nothing is uploaded anywhere.

## Status
Early version. Feedback and bug reports are welcome under **Issues**.
