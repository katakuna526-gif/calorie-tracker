# Phase 31 hand-off

The app is in the `calorie_app` folder. This phase updates the Flet UI and keeps the existing calculation formulas and saved-data format.

## Open the project in PyCharm

1. Extract `phase31_calorie_tracker.zip`.
2. In PyCharm, choose **File → Open** and select the extracted `calorie_app` folder.
3. Open the PyCharm Terminal and confirm its location ends in `calorie_app`.
4. Run `python flet_ui\main.py` to preview the app on Windows.
5. Run `python -m unittest discover -s tests -t .` to check the app logic and screen construction. The Phase 31 copy passed all 210 tests here.

## Build an Android APK

When you are ready, run `flet build apk --yes --no-rich-output` from that same `calorie_app` folder. This workspace has not built or visually inspected the APK. If the build fails, share the final 15–20 terminal lines.

## Visual check list

1. Confirm status-bar text/icons are readable in both themes.
2. On first launch, move through all setup questions, test optional skips and kg/lb selection, and check the keyboard does not cover the active input or footer.
3. On the plan summary, check the three macro cards fit evenly, then open the calculation explanation and start logging.
4. Visit Log, Calendar, Stats, Weight and Settings in both portrait and landscape. Confirm screen changes fade smoothly.
5. In Stats Week, check the weekday sequence is M T W T F S S; switch to Day and Month too.
6. In Weight, check the one-entry trend prompt, then add a second weigh-in on another date and make sure the chart appears. Check goal wording for lose and gain profiles.
7. Scroll to the bottom of Log and Settings. Confirm Copy yesterday and bottom actions remain reachable and the Add button does not cover content.
8. Increase phone text size if available and check labels and buttons remain readable.
