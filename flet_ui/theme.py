"""Visual tokens for the Flet interface. Keep all palette values here."""

DARK = {
    "background": "#0E0F10",
    "card": "#16181A",
    "surface": "#1B1D1F",
    "track": "#25272A",
    "accent": "#C6F135",
    "accent_text": "#16200A",
    "quote_strip": "#1E2610",
    "series_secondary": "#8AB4FF",
    "muted": "#8C9094",
    "text": "#F6F7F2",
    "grid": "#303336",
}

LIGHT = {
    # In light mode, invert the dark theme's signature pair: the lime surfaces
    # become soft greens, while lime buttons/highlights become near-black.
    "background": "#F0F7D5",
    "card": "#E4F0B9",
    "surface": "#D9E99A",
    "track": "#C8D58F",
    "accent": "#11140D",
    "accent_text": "#FFFFFF",
    "quote_strip": "#DBEBA3",
    "series_secondary": "#8AB4FF",
    "muted": "#666B70",
    "text": "#14160F",
    "grid": "#B5C47D",
}

PALETTES = {"dark": DARK, "light": LIGHT}

FONT_FAMILY = "Roboto"
FONT_SIZES = {"title": 20, "question": 26, "section": 16, "body": 14, "small": 12}
SPACING = {"page": 20, "card": 16, "tight": 8, "section": 12, "xs": 4,
           "sm": 8, "md": 12, "lg": 16, "xl": 20, "xxl": 24}
RADIUS = {"card": 16, "chip": 12, "button": 12, "sheet_top": 24, "pill": 24}
BOTTOM_SPACE = 24          # empty space at the end of every scrolling screen (inside the scroll)
FAB_CLEARANCE = 88         # extra end space on Log so the + button never covers content
CALENDAR_DAY_SIZE = 44     # diameter of the selected-day circle
CALENDAR_DOT_SIZE = 6
CALENDAR_CELL_HEIGHT = 56
CHART_BAR_AREA = 76        # fixed height of the bar area in the stats chart
TOUCH_TARGET = 48
PRIMARY_BUTTON_HEIGHT = 52
TEXT_FIELD_HEIGHT = 56
CONTENT_MAX_WIDTH = 480


def palette_for(name: str = "dark") -> dict:
    """Return a copy of a named palette, defaulting safely to the dark design."""
    return dict(PALETTES.get(name, DARK))
