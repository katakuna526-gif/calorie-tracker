# Phase 32 hand-off

Changes: clipping fix and calendar/stats/settings tidy-ups (see README, Phase 32).
Not verified on a device: the build environment had no Flet, so only the logic tests and a mock-based construction check were run.

## Run
1. Extract the zip, open the `calorie_app` folder in PyCharm.
2. Terminal: `python flet_ui\main.py` (Windows preview) or `flet build apk --yes --no-rich-output` (phone).
3. Tests: `python -m unittest discover -s tests -t .`

## What you should see (Log, Calendar, Stats, Weight, Settings)
- Scroll to the very bottom: the last item is fully visible just above the tab bar, no dead black gap.
- No scrollbar on top of any card.
- Log: "Tue, 6 Oct" fully visible under the quote strip; the + button floats just above the tab bar and never hides content (scroll to the end).
- Calendar: selected day is a neat lime circle; 5 Oct and 6 Oct show a small dot (the selected day's dot is dark).
- Stats: weekday letters all on one line; insight says "No exercise logged this week."
- Settings: chevron on "Edit profile" at the far right.
- Repeat in landscape, largest font size and the light theme.

## Known, not done
- Tab bar active pill still close to the screen edge on the first/last tab (needs a custom bar).
- Calendar circle is 40 px, not 44 px, so seven columns fit on a 360 px-wide phone.
- Desktop preview window now fills its width instead of a centred column.
