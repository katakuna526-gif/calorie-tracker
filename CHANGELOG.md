# Changelog (development notes)

A Python/Tkinter calorie and fitness tracker.

## Run

```bash
python app.py
```

## Tests

```bash
python -m unittest discover -s tests -t .
```

## Phase 18

Phase 18 focuses on daily logging usability while preserving the existing calculation and storage models:

- Previous day / Today / Next day navigation directly on the Log tab
- Clear selected-day label on the Log tab
- Historical-day progress section is labeled separately from today's progress
- Edit logged exercise entries
- Duplicate logged exercise entries
- Existing food, exercise, calendar, stats, weight and persistence features remain intact

Saved data continues to use `~/.calorie_tracker/data.json`.

## Phase 21 — Goals and personalization

- Edit profile details through the existing profile editor.
- Set an optional goal weight and see remaining weight and progress on the Weight tab.
- Override the calculated calorie target and any individual protein, carbohydrate or fat target.
- Leave custom targets blank to retain the existing calculation.
- Older JSON profiles load with the new optional fields unset; logs and calorie calculations remain unchanged unless a custom override is chosen.

## Phase 22 — Fixes
- Skipping the optional profile questions (goal weight, custom targets) no longer causes "Missing answer".
- Insights now count exercise minutes (previously always 0).
- Full test suite restored (144 tests): run `python -m unittest discover -s tests -t .`

## Phase 23 — Weight trend and week comparison
- Weight tab: cleaner trend chart (even date labels, latest value labelled) and a plain-language line comparing your weekly weight change with your plan.
- Log tab: the 7-day summary now compares days logged and average intake with the 7 days before.
- New `trends.py` and `charts.py`; 157 tests.

## Phase 24 — Calculation explanation and health disclaimer
- The Log tab shows that calorie, nutrition and exercise numbers are estimates, not medical advice.
- “How is this calculated?” explains BMR, TDEE, calorie and macro targets, exercise burn, and how food values are scaled.
- The explanation includes the current profile’s estimates and flags a custom calorie target below the usual profile minimum.
- A below-minimum custom target is also called out in the profile summary. Custom targets and saved-data format are unchanged.
- To try it: start the app, click **How is this calculated?** beside your profile, and read the explanation. If the profile has a custom calorie target below 1,500 kcal/day (male profile) or 1,200 kcal/day (female profile), confirm the notice appears in the profile summary and explanation window.
- Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .`. Real Windows layout still needs a visual check in PyCharm.

## Phase 25 — Settings and data backup
- Settings tab: choose body-weight display and entry units (kg or lb), and a light or dark appearance. Height remains cm; food and macro quantities remain grams.
- Weight is still stored in kilograms, so changing units does not alter calorie calculations or existing saved data. Profile setup, weigh-ins, weight charts, goals and exercise estimates follow the selected weight unit.
- Save a JSON backup from Settings, or restore one. A restore checks the backup first and automatically keeps a safety copy of the current data file.
- Older data files load with kg and light appearance selected by default. The preferences are stored as an additive `preferences` field.

## Phase 31 — UI polish and responsive layouts

- Added safe-area spacing for system bars, centered wider-screen layouts, consistent spacing and touch targets, readable setup forms, pinned actions, and a bottom scroll clearance for the Log tab.
- Refined Settings profile/calculation rows, circular avatar sizing, Stats weekday labels, whole-gram macro averages, exercise insight wording, and the Weight trend empty state and goal-direction label.
- Kept the existing calorie formulas and saved-data format unchanged. Light mode continues to use black highlights over pale-green surfaces.
- To try it: open the app on a phone and desktop/tablet, switch between dark and light themes, step through setup, and visit all five tabs. Follow the Phase 31 hand-off checklist in `PROJECT_CONTEXT.md`.
- Automated check: from this folder, run `python -m unittest discover -s tests -t .`.
- To try it: open **Settings**, change the weight unit to **lb** and appearance to **dark**, then click **Save settings**. Check the profile and Weight tab, then switch back to **kg** and **light** if preferred. Click **Back up data…**, choose a filename, and save. For a restore check, first change a profile detail, then choose **Restore backup…** and select the backup. Confirm; the earlier profile should return, and the confirmation names the safety copy.
- Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .` (164 tests). The fake Tkinter checks app wiring; real Windows appearance still needs a visual check in PyCharm.

## Phase 26 — Android app foundation and Log screen

- Added a separate Flet app under `flet_ui/`; the existing Tkinter app and saved data remain the desktop version.
- The Flet window has five bottom tabs, a quote strip, date navigation and a real-data Log progress screen. Calendar, Stats, Weight and Settings are reserved for later phases.
- Added centralized dark/light design palettes and plain-data viewmodels that reuse the existing calculation engine and storage.
- Flet version used: **1.0.3**. This phase is a desktop Flet preview; it does not produce an Android APK.

### Open the Flet app in PyCharm (Windows)

1. Unzip `phase26_calorie_tracker.zip` to a folder you can find.
2. In PyCharm, choose **File → Open** and select the unzipped `calorie_app` folder.
3. Check the Python interpreter shown at the bottom-right. Select your Python 3.11 interpreter if needed.
4. Open the PyCharm **Terminal** panel. It should be inside the `calorie_app` folder.
5. Enter `python -m pip install "flet[all]==1.0.3"` and press Enter. If Flet is already installed, it will report that it is satisfied.
6. Enter `python flet_ui\main.py` and press Enter.
7. A separate Calorie Tracker window should open in the dark design. It shows a quote, day arrows and, when a profile exists in the desktop app's saved data, calorie and macro progress. The four unfinished tabs show a short placeholder.

The Flet screen reads the existing `~/.calorie_tracker/data.json` data. If you have not created a profile in the desktop app yet, the Log screen explains that profile setup will arrive in a later phase. Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .` (169 tests). This checks the viewmodels and constructs the Flet controls, but does not verify the appearance on a real Windows screen or Android phone. Send a screenshot of the Flet window if anything looks different from the mockup.

## Phase 27 — Food and exercise logging in Flet

- The Log screen now has **Add food** and **Add exercise** forms, displays saved entries under the selected day, and lets you remove an entry.
- Food can be selected from the searchable built-in/custom food list, or entered by name with nutrition per 100 g. Amount is entered in grams and assigned to a meal.
- Exercise can be selected from the activity list with effort and duration for a profile-based calorie estimate. **Other** accepts a calorie value you already know.
- Entries save to the existing `~/.calorie_tracker/data.json`, so the desktop app and Flet preview share the same profile and logs. Logging food does not require a profile; exercise estimates use the profile weight, so create a profile in the desktop app first to add exercise.
- To try it: open the Flet preview with `python flet_ui\main.py`, choose **Add food**, select or type a food, enter the amount and nutrition values, choose a meal, and press **Add to day**. The entry and updated totals should appear on the Log screen. Then choose **Add exercise**, select an activity, enter effort and minutes, and press **Add to day**. Use the bin icon to remove an entry. Check the desktop app to see that these entries appear in the same saved data.
- Flet version used: **1.0.3**. Automated check: `python -m unittest discover -s tests -t .` (174 tests). The controls and saved-data flow are checked by unit tests; visual interaction on a real Windows screen and Android phone still needs your screenshot. APK packaging remains Phase 30.

## Phase 28 — Calendar and Stats screens

- Calendar now shows the selected month, marks dates with food logs and exercise-only logs, and displays the selected day's totals. Use **Open this day in Log** to review or change entries.
- Stats now opens on the most recent food-logged day so existing entries are visible on first open. It follows the supplied mockup: Day/Week/Month switch, compact eaten-versus-burned vertical bars, average macros, a short insights card and a prominent lime **Export CSV** button.
- **Export this period as CSV** saves the selected day, week or month under `Downloads\CalorieTracker`. The file contains one row per date, including logged status, intake, target, variance, burn and macros. A confirmation shows the saved file location.
- Intake averages count only days with food logged. Empty days do not get counted as zero-calorie days. All calorie and nutrition values remain estimates.
- To try it: start the app with `python flet_ui\main.py`, tap **Calendar**, move between months, select a date with a marker, then tap **Open this day in Log**. Tap **Stats**, switch between **Day**, **Week** and **Month**, and use the arrows to change the period. Stats need a profile; Calendar markers work without one. Stats open on the most recent food-logged date when there is saved history.
- Log now follows the supplied mockup more closely: a lime **+** button opens **Add food** or **Add exercise**; food entries are grouped under **Breakfast**, **Lunch**, **Snacks** or **Dinner** with a meal calorie subtotal; and the three-dot menu for each food offers **Edit**, **Duplicate** and **Delete**. **Copy yesterday** copies the previous day's foods into the selected day. **How is this calculated?** opens the plain-language explanation of targets, burn estimates and food nutrition.
- **Add food** now starts with a search list of saved foods, favorites and recent foods. Choose a food, enter its amount, pick grams or one of that food's saved serving sizes, and select a meal. The app uses the selected food's stored nutrition and shows the estimated calories before adding. The meal is suggested from the time of day but can always be changed with the meal buttons. **Custom food** opens a separate form for package nutrition per 100 g; saving it logs the food and keeps it in the list for next time.
- The Stats **Day / Week / Month** selector now uses the mockup's rounded dark pill with a lime selected period.
- To try the Log actions: click the lime **+**, choose **Add food**, type a food name, and tap a result. Enter an amount and choose a meal; if the food has saved serving sizes, you can tap one of those instead of grams. Check the calorie preview and tap **Add food · … kcal**. Use **Custom food** for a food that is not listed. Use a saved food's **⋮** menu to edit its amount or meal, duplicate it, or delete it. Select the next day and use **Copy yesterday** to bring the previous day's food entries over. Click **How is this calculated?** under Daily target to read the estimate explanation.
- Flet version used: **1.0.3**. Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .` (190 tests). Viewmodels, screen controls, food search and serving conversion, saved custom foods, meal selection, Log actions, Stats period switch and CSV contents are checked; visual interaction on your Windows screen and Android phone still needs your screenshot. Phase 29 adds Weight, Settings and profile setup; APK packaging remains Phase 30.

## Phase 29 — Weight, Settings and profile setup

- On a first launch with no saved profile, the Flet app opens with a welcome screen and walks through the existing profile questions one at a time. Optional answers can be skipped; the pace question is shown only for lose/gain goals. The plan summary shows the calculated daily calories and macros before **Start logging** saves the profile and first weigh-in.
- Weight now has a quick entry, latest weight and change, a recent trend line with a dashed goal line, goal progress, and the latest two weigh-ins. Weight input uses the selected kg/lb setting; values continue to be stored in kg and update the current profile/calorie calculations.
- Settings shows the profile, an **Edit profile** screen, kg/lb and Light/Dark choices, **Save settings**, backup/restore, and **How is this calculated?**. Editing a profile can update its weight, formula, activity, goal, pace and optional targets; saving a changed weight records today's weigh-in.
- Backups are saved to `Downloads\CalorieTracker`. **Restore backup** lists those backups, asks before replacing data, checks the backup, and keeps a safety copy of the current data.
- The calculation sheet matches the mockup: current BMR, activity-adjusted TDEE, goal adjustment, daily target and macro targets, with an optional expanded explanation. A fade transition is used between tabs and setup steps.
- To try it: open `calorie_app` in PyCharm and run `python flet_ui\main.py`. If there is no saved profile, tap **Get started**, answer the questions, and tap **Start logging**. Open **Weight** to save a weigh-in. Open **Settings** to change units/theme, edit your profile, back up data or restore a backup. The calculation sheet is available from Log and Settings.
- Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .` (199 tests). This covers first-run setup, saved profile edits, weight conversions/history, Settings, backup/restore, formula values and fade-switcher construction. The Android APK and on-device visual check remain for Phase 30.

## Phase 30 — Android app packaging and storage

- Added an Android build entry point and Flet build configuration. The APK uses an app-private persistent data folder, so saved profile, food logs, weights and settings remain available when the app is closed and updated. The Windows preview continues to use the same shared data file as the Tkinter desktop app.
- Android **Back up data**, **Restore backup** and Stats **Export CSV** use the phone's file chooser. A restored backup is checked before replacing current data, and the app keeps a safety copy.
- The Light appearance now reverses the dark theme's key colors: lime highlights/buttons become near-black, and dark surfaces become pale green. Text and button contrast are kept readable.

### Build and install the APK on Windows

1. Unzip the Phase 30 download, then open the inner `calorie_app` folder in PyCharm.
2. In the PyCharm Terminal, check that the prompt ends in `calorie_app`. Enter `flet --version` and press Enter. The project uses Flet 1.0.3.
3. Enter `flet build apk --yes --no-rich-output` and press Enter. The first build can take a while. Flet's official build process can install the needed Flutter, Java JDK 17 and Android SDK tools when they are missing. Allow it to finish and keep the computer connected to the internet.
4. When the terminal says the build completed, open `calorie_app\build\apk`. The APK file there can be copied to an Android phone and opened to install. Android may ask you to allow installing apps from that file app.
5. Launch **Calorie Tracker**. On a new install, complete the guided profile setup. To move existing Windows data to the phone, use **Settings → Back up data** in the Windows preview, transfer that JSON file to the phone, then choose **Settings → Restore backup** on Android.

If the build stops with an error, copy the last 15–20 lines of the PyCharm Terminal and send them with a screenshot. Do not share passwords or signing keys. A debug-signed APK is for personal testing; Google Play publishing needs a separate private upload key.

- Automated check: `python -m unittest discover -s tests -t .` (205 tests). Mobile picker actions, private Flet storage selection, theme colors and build configuration are checked. The APK build could not run in this restricted workspace because Flet's Flutter download needs write access to the Windows user profile; run the build command above in your PyCharm environment. The installed APK still needs a real phone check.

## Phase 32 — Fix clipped screens
- Cause: a 72 px bottom padding sat on the container *around* the scroll area, so the scroll view ended 72 px above the tab bar and cut content in half.
- Now the end space (24 px, 88 px on Log) is inside the scrolling content, and the scroll area runs down to the tab bar.
- Removed the outer ResponsiveRow wrapper (a likely second scroller); scrollbars are hidden through the theme.
- Calendar: 40 px selected circle, same-size cells, dot under logged days (lime = food, blue = exercise only).
- Stats: weekday letters share one row; insight says "No exercise logged this week."
- Settings: "Edit profile" chevron at the right edge.

## Phase 33 — Calendar touch-up and portfolio page
- Increased the selected-day circle from 40 px to 44 px. Tightened only the calendar card's inside padding so seven columns still fit on a 360 px-wide screen; the calendar row remains 56 px tall for the date and marker.
- Added a responsive project presentation page in `site/index.html` with a gallery of real app screenshots and team credits. The `site` folder is ready to host as a static site.
- No calorie formulas, saved data, or other app flows changed.
- Automated check: from the `calorie_app` folder, run `python -m unittest discover -s tests -t .`. The Phase 33 layout-token test checks the 44 px circle and row spacing. A real phone/desktop visual check and Android APK build remain unverified in this workspace.


## Phase 34 — Demo screenshots and responsive showcase
- Replaced the portfolio gallery with five supplied Android demo screens; only the Android system status/navigation bars were trimmed. Demo values are intentionally left visible.
- Refreshed the site to a light violet card style based on the supplied mobile reference and kept responsive layouts for phone, tablet, and desktop widths.
- Added an Android download call-to-action. The site links to a downloadable source ZIP. An installable APK is not currently bundled; build it with the documented Flet command before adding an APK link.
- Build an APK from this folder with `flet build apk --yes --no-rich-output`.
