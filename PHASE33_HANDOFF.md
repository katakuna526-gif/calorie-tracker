# Phase 33 hand-off

This package builds on the supplied Phase 32 archive. The earlier project notes say a phase closes when the user confirms it works, and no Phase 32 confirmation was present in this session.

## Changes
- Calendar selected-day circle: 44 px, with tighter calendar card padding and a 56 px row to retain room for the log marker.
- Added `site/index.html` and five Android demo screenshots under `site/assets/`; demo values remain visible. The responsive page includes team credits and is ready to host as a static website.
- Updated project version to 0.33.0. Calorie formulas and saved data remain unchanged.

## Run and check
1. Extract the zip and open the inner `calorie_app` folder.
2. Run the desktop preview with `python flet_ui\main.py`.
3. Run the tests with `python -m unittest discover -s tests -t .`.
4. To preview the portfolio page, open `site\index.html` in a browser. To publish it, upload the `site` folder to a static host.
5. To build an Android debug APK in an environment with the Flet Android toolchain, run `flet build apk --yes --no-rich-output` from `calorie_app`.

## Demo refresh
- The supplied screenshots replace the earlier gallery. They show demo values; no data has been blurred or hidden. Only system status/navigation bars are trimmed.
- The website uses a light violet mobile-first style. It can be placed in a static host publish directory.
- The download call-to-action downloads a ZIP of the source project. An installable APK is not bundled yet.

## Still to verify
- Final rendered page appearance at desktop and phone widths.
- Android APK build and install on a phone.
