# Calorie Tracker — Project Context and Working Agreement

Paste this whole file to any AI assistant (ChatGPT/Codex or Claude) before asking it to work on the project.
Last updated at **Phase 33**.

---

## 1. Who the user is and what they want

- The user **does not code**. They run the app in **PyCharm on Windows 11** (Python 3.11.5, and a 3.14 venv in some projects) and send **screenshots** of what they see.
- They want a **simple, usable daily calorie tracker** in **Python + Tkinter**. "Basic is fine, but it must be fully functional."
- They plan their **own customisations after the app is "somewhat made"**. Do not over-engineer, and do not restyle things they will customise.
- Always **guide step by step** in plain language. Tell them exactly what to click or type, and what they should see.

### The original 9 features
1. Profile questions (configurable; the user will supply the final question list later)
2. Intake logging
3. Intake converted to calories
4. Daily totals
5. Day / week / month stats
6. Graphs
7. Motivating quotes
8. A consistency motivator
9. Nutrition per gram (food data stored per 100 g)

### Tone rules (important)
- The consistency system **rewards logging, not hitting numbers**.
- Wording is **neutral and encouraging, never shaming**. Being over a target is information, not failure.
- No red/green "good/bad" judgement on progress bars.
- Include honest limits: all numbers are **estimates**, not medical advice.

---

## 2. History: who built what

Several assistants have worked on this project, so the phase numbers are shared. **Never reuse or renumber an existing phase.**

| Phases | Built by | Content |
|---|---|---|
| 1–8 | ChatGPT | Calorie engine (maths only) with unit tests |
| 9–10 | ChatGPT | First Tkinter UI, storage |
| 11–15 | Claude | Questionnaire wizard, food search, exercise (MET) panel, weight log, day navigation, ScrollFrame, stats charts |
| 16–21 | ChatGPT/Codex | Dashboard progress bars, complete food logging, day navigation and exercise editing, reports and CSV export, progress insights, goals and personalization (goal weight, custom calorie/macro targets) |
| 22 | Claude | Fixes on top of Phase 21 (see below) |
| 23 | Claude | Weight chart, trend vs plan, week comparison |
| 24 | Codex | Calculation explanation, persistent estimate disclaimer, low custom target notice |
| 25 | Codex | Weight-unit and appearance settings, data backup and restore |
| 26 | Codex | Flet app foundation, dark/light theme tokens, Log progress preview and five tabs |
| 27 | Codex | Flet food and exercise entry forms, selected-day entry list and removal |
| 28 | Codex | Flet monthly Calendar, mockup-aligned Stats and Log, export, easy searchable food logging with meal/serving selection and estimates, custom foods, food actions, copy yesterday, calculation explanation |
| 29 | Codex | Flet Weight and Settings, Edit Profile, first-run guided profile setup from existing questions, calculation sheet, backup/restore, fade transitions |
| 30 | Codex | Flet Android build configuration, app-private persistent storage, Android file chooser for backup/restore/CSV, inverted green/black Light palette |

**Important:** Claude also built a separate Phase 16 line, but it was **dropped**. The user chose **Phase 21 (Codex's line) as the one canonical base**. Only ideas were ported from the other line (chart drawing, trend maths). Do not try to merge the old line back.

The original plan (ChatGPT's "calorie engine" plan) was: engine first, fully tested, then UI. That plan is finished and still the foundation.

---

## 3. How the code is organised

Run from inside the `calorie_app` folder: `python app.py`.
Run tests (from inside `calorie_app`): `python -m unittest discover -s tests -t .`

| File | Role |
|---|---|
| `calorie_engine.py` | **All the maths, no UI.** `Person`, `FoodEntry`, `ExerciseEntry`, `DailyLog`, BMR, TDEE, targets, exercise calories, limits |
| `stats.py` | Aggregation: daily records, week/month stats, consistency streak, quotes, adherence, insights, goal-weight progress, `weekly_summary` (rolling 7 days), `weight_trend` (points in a window) |
| `trends.py` | (Phase 23) `weight_rate` (kg/week via least-squares), `planned_kg_per_week`, `describe_trend`, `week_comparison` |
| `charts.py` | (Phase 23) Canvas drawing for the weight chart. Only uses `create_line/rectangle/oval/text` so it is testable |
| `storage.py` | JSON persistence at `~/.calorie_tracker/data.json`, atomic writes, weights, `person_on(date)` |
| `questions.py` | The profile questionnaire **as data** (`QUESTIONS` list with `only_if` and `optional`), `person_from_answers`, `answers_from_person` |
| `wizard.py` | UI that walks through `QUESTIONS` |
| `app.py` | Main window: Log, Calendar, Stats, Weight tabs |
| `food_panel.py`, `foods.py` | Food search/add, built-in food database |
| `exercise_panel.py`, `exercises.py` | Exercise list with MET values, estimate and add |
| `weight_panel.py` | Weight tab: log, list, trend chart, trend text |
| `exporter.py` | CSV export |
| `ui_helpers.py` | `ScrollFrame` (scrollable area) |
| `tests/` | `unittest` tests (157 at Phase 23) plus `fake_tk.py`, a Tkinter stand-in so UI code can be tested with no screen |

**Rule: keep logic out of the UI.** New calculations go in `calorie_engine.py`, `stats.py` or `trends.py` with tests. UI files only display and collect input.

---

## 4. Key decisions (do not silently change these)

- **BMR:** Mifflin-St Jeor. **TDEE** = BMR × activity multiplier (1.2 / 1.375 / 1.55 / 1.725 / 1.9).
- **Burn model (avoids double counting):** baseline burn = BMR × 1.2, plus logged exercise. Calorie targets are based on TDEE ± pace (gentle 250, steady 500 kcal/day). Logged exercise is **not** added to the target.
- **Safety floor:** calories never below 1500 (male) / 1200 (female) *unless the user sets a custom calorie target*.
- **Macros:** protein 1.2 g/kg (maintain) or 1.6 g/kg; fat 25% of calories; carbs = remainder. Custom targets override each one.
- **Exercise calories:** `(MET − 1) × kg × hours` (net of resting).
- **Per-100 g nutrition** for food; sanity limits stop typos (max 5000 g per entry, max 900 kcal per 100 g, protein+carbs+fat ≤ 100 g per 100 g).
- **Averages count only days with food logged.** A forgotten day is not a zero-calorie day.
- **Weights:** `Storage.person_on(d)` returns the weight on that day, so past days do not change when weight changes. Profile weight always equals the latest weigh-in.
- **Saved data:** invalid saved entries are skipped and counted in `Storage.skipped`, never crash the app. Old save files must keep loading. If a data format changes, make it backward compatible.
- **Questionnaire is data.** Optional questions have `"optional": True` and must never be required by `person_from_answers`.
- **Charts:** thin marks, hairline grid, one colour per series (`#2a78d6`), one direct label on the latest value, text in neutral ink.

---

## 5. How we work together (the working agreement)

1. **One canonical code line.** The latest zip the user has confirmed working is the base. Always start from it. Never rebuild from memory or from an older zip.
2. **Phases are sequential and small.** One phase = one focused change set = one zip the user can test.
3. **Never reuse a phase number.** The next phase is always highest number + 1. If two assistants build in parallel, the user decides which line wins, and the other only contributes ideas.
4. **Do not break existing behaviour.** Keep file names, function names and the saved-data format stable unless the phase is specifically about changing them. If you must change a function signature, update every caller and test in the same phase.
5. **Every change comes with tests.** Run the full suite before delivering and say how many tests passed. A UI change should have a smoke test using `tests/fake_tk.py`.
6. **Keep the README current.** Add a short "Phase N" section listing what changed.
7. **Deliver as a zip** with one enclosing `calorie_app` folder, named `phaseNN_calorie_tracker.zip`, without `__pycache__`.
8. **Hand-off note at the end of each phase:** what changed, how to test it (exact steps for a non-coder), and what comes next.
9. **Be honest about what was not verified.** The tests use a fake Tkinter. Nothing is checked on a real Windows screen until the user sends a screenshot or says it works.
10. **The user's confirmation ("works") is what closes a phase.** Wait for it before moving on, or at least state clearly that the next phase builds on an unconfirmed one.
11. **Do not add features that were not asked for.** Suggest them in the "next" note instead.

### Common problems already met (so nobody repeats them)
- Running the tests from the wrong folder gives "Start directory is not importable: 'tests'". The user must `cd calorie_app` first.
- The PyCharm terminal may show `<No interpreter>`. The user must select their Python in the bottom-right corner.
- `pytest` is not used. Tests use `unittest` only.
- The Log tab got cut off on small windows. This was fixed with `ScrollFrame`.
- Optional profile questions once raised "Missing answer". Fixed in Phase 22.
- Insights showed exercise minutes as 0. Fixed in Phase 22.

---

## 6. Where we are now (Phase 33) and the route ahead

Done: all 9 original features, day navigation, exercise editing, CSV export, insights, goal weight, custom targets, weight chart, trend vs plan, week-on-week comparison, calculation explanation and health disclaimer, weight-unit and appearance settings, data backup and restore. Phases 26–30 add a separate Flet app with Log progress and food/exercise input, monthly Calendar, mockup-aligned Day/Week/Month Stats, Log actions, Weight screen, Settings, Edit Profile, first-run questionnaire, calculation sheet, Android-private persistent storage, Android file picker backup/restore/CSV, and APK build configuration. The Tkinter desktop app remains intact; Windows preview data remains shared between the two desktop apps. Android app data is private to that app; use a JSON backup to move it. Stats opens on the latest food-logged date to make current saved history easy to find. Screen changes use a fade transition. Light mode uses pale green surfaces and black highlights as requested.

Phase 31 UI updates: safe-area protection and centered responsive layout, theme-aware system-bar icons, consistent spacing/touch targets, setup screen field and footer cleanup, equal-width plan macros, Settings navigation rows, Stats weekday layout and whole-gram averages, goal-direction wording, and a two-weigh-in minimum for trend charts. Existing formulas and saved-data format remain unchanged.

Next: build/install the Phase 31 APK and complete the phone checklist below. The automated checks pass, but the Android and real desktop layouts still need a visual check on the user's devices.

### Phase 31 phone and desktop check

1. Install/open the Phase 31 build in both dark and light themes; confirm the status and navigation bar icons remain readable.
2. On first launch, complete every setup question and verify the keyboard does not hide the current field or the Back/Next controls. Check kg and lb entry and optional skips.
3. Confirm the plan page has three equally sized macro cards and a working “How is this calculated?” link; tap Start logging.
4. Visit Log, Calendar, Stats, Weight and Settings. In Stats Week, confirm all seven weekday letters appear in Monday-to-Sunday order. Check Day and Month controls.
5. On Weight, confirm one weigh-in shows the “Log your weight on 2 days to see your trend” message; add a second date and confirm the chart appears. Confirm goal-progress wording for both losing and gaining goals.
6. Open Edit profile and the calculation sheet; verify the Save controls remain visible while scrolling. Test portrait/landscape and larger text settings if available.
7. On Log, scroll to the bottom and confirm Copy yesterday and the final note can be reached without the floating Add button covering them.

Phase 33 increases the selected calendar date circle to 44 px and reduces only the calendar card's inner padding to keep seven columns within a 360 px-wide screen. It adds `site/index.html`, a static portfolio presentation for the app. No calorie formulas or storage formats changed. The refreshed automated suite passed locally; the Windows desktop layout, Android layout and APK build still need a real device / Android build environment check.

The current questionnaire questions are in the `QUESTIONS` list in `questions.py`; reuse that data in both UIs and do not hard-code a second list. Current Flet preview uses Flet 1.0.3 and opens on desktop. Android packaging is configured with `pyproject.toml`; the user's Windows PyCharm environment should run `flet build apk --yes --no-rich-output`. The Flet app can log food without a profile. Exercise estimates use profile weight.

---

## 7. A starter message for another assistant

> I am continuing a Python calorie tracker with a working Tkinter desktop app and a separate Flet Android app in progress. Read `PROJECT_CONTEXT.md` fully first. Base your work on the latest phase, preserve the Tkinter app and saved-data format, add tests, update the README and PROJECT_CONTEXT.md, and deliver one zip for the next phase with exact steps for a non-coder. The Android route is Phase 26 foundation, 27 food/exercise logging, 28 Calendar/Stats, 29 Weight/Settings/profile/calculation explanation, 30 Android storage and APK.
