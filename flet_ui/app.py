"""Phase 26 Flet shell and real-data Log progress screen."""

import calendar
import math
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import flet as ft

import stats
from calorie_engine import (
    ACTIVITY_LEVELS, MEALS, PACE_ADJUSTMENT, DailyLog, Person,
    calculate_bmr, calculate_targets, calculate_tdee,
)
from exercises import EXERCISES, INTENSITIES
from foods import FoodItem, default_meal, grams_for
from flet_ui.entry_viewmodels import make_exercise_entry, make_food_entry
from flet_ui.theme import (
    BOTTOM_SPACE, CALENDAR_CELL_HEIGHT, CALENDAR_DAY_SIZE, CALENDAR_DOT_SIZE, CHART_BAR_AREA,
    CONTENT_MAX_WIDTH, FAB_CLEARANCE, FONT_FAMILY, FONT_SIZES, PRIMARY_BUTTON_HEIGHT, RADIUS,
    SPACING, TEXT_FIELD_HEIGHT, TOUCH_TARGET, palette_for,
)
from questions import (
    QUESTIONS, answers_from_person, person_from_answers, validate_answer, visible_questions,
)
from units import from_kg, to_kg, weight_unit_label
from flet_ui.viewmodels import (
    calculation_explanation, calendar_month, exercise_insight_text, goal_weight_progress_label, latest_food_log_date,
    log_dashboard, stats_dashboard,
)
from exporter import period_csv_bytes, period_csv_rows, write_csv

TAB_NAMES = ("Log", "Calendar", "Stats", "Weight", "Settings")
TAB_ICONS = (
    ft.Icons.RECEIPT_LONG,
    ft.Icons.CALENDAR_MONTH,
    ft.Icons.BAR_CHART,
    ft.Icons.MONITOR_WEIGHT,
    ft.Icons.SETTINGS,
)


def _app_theme(palette: dict, is_dark: bool) -> ft.Theme:
    icon_brightness = ft.Brightness.LIGHT if is_dark else ft.Brightness.DARK
    overlay = ft.SystemOverlayStyle(
        status_bar_color=palette["background"],
        system_navigation_bar_color=palette["background"],
        status_bar_icon_brightness=icon_brightness,
        system_navigation_bar_icon_brightness=icon_brightness,
    )
    base = dict(color_scheme_seed=palette["accent"], font_family=FONT_FAMILY,
                system_overlay_style=overlay)
    try:  # hide scrollbars so none can sit on top of a card
        return ft.Theme(scrollbar_theme=ft.ScrollbarTheme(
            thumb_visibility=False, track_visibility=False, thickness=0), **base)
    except Exception:
        return ft.Theme(**base)


def quote_strip(quote: str, palette: dict) -> ft.Control:
    return ft.Container(
        content=ft.Text(quote, size=FONT_SIZES["body"], italic=True,
                        color=palette["accent"], font_family=FONT_FAMILY,
                        max_lines=2, overflow=ft.TextOverflow.ELLIPSIS),
        bgcolor=palette["quote_strip"],
        padding=SPACING["card"], alignment=ft.Alignment.CENTER_LEFT,
        border_radius=RADIUS["card"],
        margin=ft.Margin(SPACING["page"], SPACING["section"], SPACING["page"], SPACING["tight"]),
    )


def _card(content: ft.Control, palette: dict, padding: int = SPACING["card"],
          expand: bool = False) -> ft.Container:
    return ft.Container(content=content, bgcolor=palette["card"], padding=padding,
                        border_radius=RADIUS["card"], expand=expand)


def _txt(value: str, palette: dict, size: int = 14, muted: bool = False, weight=None, color=None) -> ft.Text:
    return ft.Text(value, size=size, color=color or (palette["muted"] if muted else palette["text"]),
                   weight=weight, font_family=FONT_FAMILY)


def macro_card(macros: list[dict], palette: dict) -> ft.Container:
    rows = []
    for item in macros:
        rows.extend([
            ft.Row(
                controls=[
                    _txt(item["label"], palette, size=FONT_SIZES["body"]),
                    _txt(item["value_text"], palette, size=FONT_SIZES["small"], muted=True),
                ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.ProgressBar(value=item["fraction"], color=palette["accent"],
                           bgcolor=palette["track"], bar_height=8, border_radius=8),
            _txt(item["status"], palette, size=FONT_SIZES["small"], muted=True),
        ])
    return _card(ft.Column(controls=rows, spacing=SPACING["xs"]), palette)


def _progress_card(data: dict, palette: dict) -> ft.Container:
    ring = ft.Stack(
        controls=[
            ft.ProgressRing(value=data["calorie_fraction"], width=132, height=132,
                            stroke_width=10, color=palette["accent"], bgcolor=palette["track"]),
            ft.Column(
                controls=[
                    _txt(f"{data['consumed']:,}", palette, size=FONT_SIZES["section"], weight=ft.FontWeight.W_500),
                    _txt("kcal", palette, size=FONT_SIZES["small"], muted=True),
                ], alignment=ft.MainAxisAlignment.CENTER,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=0,
            ),
        ], width=132, height=132, alignment=ft.Alignment.CENTER,
    )
    details = ft.Column(
        controls=[
            _txt(data["remaining_label"], palette, muted=True),
            _txt(f"{data['remaining_amount']:,}", palette, size=FONT_SIZES["title"], weight=ft.FontWeight.W_500),
            _txt("Burned", palette, muted=True),
            _txt(f"{data['burned']:,} kcal", palette),
            _txt("Balance", palette, muted=True),
            _txt(f"{data['balance']:+,} kcal", palette),
        ], spacing=SPACING["xs"], expand=True,
    )
    return _card(ft.Row(controls=[ring, details], spacing=SPACING["md"],
                        vertical_alignment=ft.CrossAxisAlignment.CENTER), palette)


def target_card(data: dict, palette: dict, on_calculations=None) -> ft.Container:
    content = ft.Column(spacing=SPACING["tight"], controls=[
        ft.Row(controls=[
            _txt("Daily target", palette, size=FONT_SIZES["section"]),
            _txt(f"{data['target']:,} kcal", palette, size=FONT_SIZES["section"],
                 color=palette["accent"]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.Row(controls=[
            _txt(data["goal_label"], palette, muted=True),
            _txt("Estimates only", palette, size=FONT_SIZES["small"], muted=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        ft.TextButton("How is this calculated?", on_click=on_calculations,
                      style=ft.ButtonStyle(color=palette["muted"])),
    ])
    return _card(content, palette)


def build_log_screen(data: dict, palette: dict, on_previous, on_next, log=None,
                     on_remove_food=None, on_remove_exercise=None,
                     on_edit_food=None, on_duplicate_food=None, on_copy_yesterday=None,
                     on_calculations=None) -> ft.Control:
    day_switcher = ft.Row(
        controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Previous day", width=48, height=48,
                          icon_color=palette["muted"], on_click=on_previous),
            ft.Text(data["day_label"], size=FONT_SIZES["section"], color=palette["text"],
                    font_family=FONT_FAMILY, expand=True, text_align=ft.TextAlign.CENTER),
            ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Next day", width=48, height=48,
                          icon_color=palette["muted"], on_click=on_next),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER,
    )
    if not data["has_profile"]:
        progress = _card(ft.Column(spacing=SPACING["tight"], controls=[
            _txt("Your daily progress", palette, size=FONT_SIZES["section"]),
            _txt("Food can be logged now. Set up a profile in the desktop app to see progress and log exercise.",
                 palette, muted=True),
        ]), palette)
        content = [day_switcher, progress]
    else:
        progress = _progress_card(data, palette)
        content = [day_switcher, progress, macro_card(data["macros"], palette),
                   target_card(data, palette, on_calculations)]

    content.extend(_logged_entries(log, palette, on_remove_food, on_remove_exercise,
                                   on_edit_food, on_duplicate_food, on_copy_yesterday))
    if not log or not (log.foods or log.exercises):
        content.append(_card(_txt("Nothing logged for this day yet.", palette, muted=True), palette))

    content.append(_txt("Nutrition and activity values are estimates, not medical advice.",
                         palette, size=FONT_SIZES["small"], muted=True))
    return ft.Column(controls=content, spacing=SPACING["section"], scroll=ft.ScrollMode.HIDDEN,
                    expand=True, horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def _logged_entries(log, palette, on_remove_food, on_remove_exercise,
                    on_edit_food=None, on_duplicate_food=None, on_copy_yesterday=None):
    log = log or DailyLog()
    sections = [ft.Row(controls=[
        _txt("Food", palette, size=FONT_SIZES["section"]),
        ft.TextButton("Copy yesterday", on_click=on_copy_yesterday,
                      style=ft.ButtonStyle(color=palette["accent"])),
    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
    meal_labels = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner", "snacks": "Snacks"}
    for meal in MEALS:
        entries = [(index, food) for index, food in enumerate(log.foods) if food.meal == meal]
        if not entries:
            continue
        meal_total = round(sum(food.calories for _, food in entries))
        rows = [ft.Row(controls=[
            _txt(meal_labels[meal], palette, size=FONT_SIZES["section"]),
            _txt(f"{meal_total:,} kcal", palette, size=FONT_SIZES["small"], muted=True),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)]
        for index, food in entries:
            menu = ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT, tooltip=f"Options for {food.name}",
                icon_color=palette["muted"], width=48, height=48,
                items=[
                    ft.PopupMenuItem(content="Edit", on_click=lambda event, i=index: on_edit_food(i)),
                    ft.PopupMenuItem(content="Duplicate", on_click=lambda event, i=index: on_duplicate_food(i)),
                    ft.PopupMenuItem(content="Delete", on_click=lambda event, i=index: on_remove_food(i)),
                ],
            )
            rows.append(ft.Row(controls=[
                ft.Column(controls=[
                    _txt(f"{food.name} · {food.grams:g} g", palette),
                    _txt(f"{round(food.calories):,} kcal", palette, size=FONT_SIZES["small"], muted=True),
                ], spacing=SPACING["xs"], expand=True), menu,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
        sections.append(_card(ft.Column(controls=rows, spacing=SPACING["xs"]), palette))

    if log.exercises:
        rows = [_txt("Exercise", palette, size=FONT_SIZES["section"])]
        for index, exercise in enumerate(log.exercises):
            remove = ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip=f"Remove {exercise.name}",
                                   width=48, height=48, icon_color=palette["muted"],
                                   on_click=lambda event, i=index: on_remove_exercise(i))
            rows.append(ft.Row(controls=[
                ft.Column(controls=[
                    _txt(f"{exercise.name} · {exercise.duration_minutes:g} min", palette),
                    _txt(f"{round(exercise.calories_burned):,} kcal estimated", palette,
                         size=FONT_SIZES["small"], muted=True),
                ], spacing=SPACING["xs"], expand=True), remove,
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
        sections.append(_card(ft.Column(controls=rows, spacing=SPACING["xs"]), palette))
    return sections


def build_calendar_screen(data: dict, palette: dict, on_previous, on_next,
                         on_select_day, on_open_log) -> ft.Control:
    month_header = ft.Row(controls=[
        ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Previous month", width=48, height=48,
                      icon_color=palette["muted"], on_click=on_previous),
        ft.Text(data["title"], size=FONT_SIZES["section"], color=palette["text"],
                expand=True, text_align=ft.TextAlign.CENTER),
        ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Next month", width=48, height=48,
                      icon_color=palette["muted"], on_click=on_next),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    weekday_header = ft.Row(controls=[
        ft.Container(content=_txt(day, palette, size=FONT_SIZES["small"], muted=True),
                     expand=True, alignment=ft.Alignment.CENTER)
        for day in ("M", "T", "W", "T", "F", "S", "S")
    ], spacing=0)

    week_rows = []
    for week in data["weeks"]:
        cells = []
        for item in week:
            if item is None:
                cells.append(ft.Container(expand=True, height=CALENDAR_CELL_HEIGHT))
                continue
            is_selected = item["selected"]
            marker = item.get("marker")
            if marker is None:
                dot_color = "transparent"
            elif is_selected:
                dot_color = palette["accent_text"]
            else:
                dot_color = palette["accent"] if marker == "food" else palette["series_secondary"]
            number = ft.Container(
                content=_txt(str(item["day"]), palette, size=FONT_SIZES["body"],
                             color=palette["accent_text"] if is_selected else palette["text"]),
                width=CALENDAR_DAY_SIZE, height=CALENDAR_DAY_SIZE,
                alignment=ft.Alignment.CENTER, border_radius=CALENDAR_DAY_SIZE,
                bgcolor=palette["accent"] if is_selected else None,
            )
            dot = ft.Container(width=CALENDAR_DOT_SIZE, height=CALENDAR_DOT_SIZE,
                               bgcolor=dot_color, border_radius=CALENDAR_DOT_SIZE)
            cells.append(ft.Container(
                content=ft.Column(controls=[number, dot], spacing=SPACING["xs"] // 2,
                                  horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                  alignment=ft.MainAxisAlignment.START),
                expand=True, height=CALENDAR_CELL_HEIGHT, alignment=ft.Alignment.TOP_CENTER,
                on_click=lambda event, d=item["date"]: on_select_day(d),
            ))
        week_rows.append(ft.Row(controls=cells, spacing=0))

    calendar_card = _card(ft.Column(controls=[weekday_header, *week_rows], spacing=SPACING["xs"]),
                          palette, padding=SPACING["xs"])
    if data["has_profile"]:
        detail_lines = [
            ft.Row(controls=[_txt("Consumed", palette, muted=True),
                             _txt(f"{data['consumed']:,} kcal", palette)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(controls=[_txt("Burned", palette, muted=True),
                             _txt(f"{data['burned']:,} kcal", palette)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.Row(controls=[_txt("Balance", palette, muted=True),
                             _txt(f"{data['balance']:+,} kcal", palette)],
                   alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            _txt(f"Protein {data['protein']} g  ·  Carbs {data['carbs']} g  ·  Fat {data['fat']} g",
                 palette, size=FONT_SIZES["small"], muted=True),
        ]
    else:
        detail_lines = [_txt("Set up a profile in the desktop app to see calorie burn and balance.",
                             palette, muted=True)]
    detail_lines.insert(0, _txt(data["selected_label"], palette, size=FONT_SIZES["section"]))
    detail_lines.append(_txt(
        f"{data['food_count']} food entr{'y' if data['food_count'] == 1 else 'ies'} · "
        f"{data['exercise_count']} exercise entr{'y' if data['exercise_count'] == 1 else 'ies'}",
        palette, size=FONT_SIZES["small"], muted=True,
    ))
    detail_lines.append(ft.FilledButton(
        "Open this day in Log", icon=ft.Icons.RECEIPT_LONG, on_click=on_open_log,
        bgcolor=palette["accent"], color=palette["accent_text"],
    ))
    details = _card(ft.Column(controls=detail_lines, spacing=SPACING["sm"]), palette)
    legend = ft.Row(controls=[
        ft.Container(width=6, height=6, bgcolor=palette["accent"], border_radius=6),
        _txt("Food logged", palette, size=FONT_SIZES["small"], muted=True),
        ft.Container(width=6, height=6, bgcolor=palette["series_secondary"], border_radius=6),
        _txt("Exercise only", palette, size=FONT_SIZES["small"], muted=True),
    ], spacing=SPACING["sm"])
    return ft.Column(controls=[month_header, calendar_card, legend, details],
                     spacing=SPACING["section"], scroll=ft.ScrollMode.HIDDEN, expand=True)


def build_stats_screen(data: dict, palette: dict, kind: str,
                       on_kind_change, on_previous, on_next, on_export=None) -> ft.Control:
    period_buttons = []
    for value, label in (("day", "Day"), ("week", "Week"), ("month", "Month")):
        selected = value == kind
        period_buttons.append(ft.Container(
            content=_txt(label, palette, size=FONT_SIZES["small"],
                         color=palette["accent_text"] if selected else palette["text"],
                         weight=ft.FontWeight.W_500),
            expand=True, height=TOUCH_TARGET, alignment=ft.Alignment.CENTER,
            bgcolor=palette["accent"] if selected else palette["surface"],
            border_radius=RADIUS["pill"],
            on_click=lambda event, selected_kind=value: on_kind_change(selected_kind),
        ))
    periods = ft.Container(
        content=ft.Row(controls=period_buttons, spacing=0),
        bgcolor=palette["surface"], border_radius=RADIUS["pill"], padding=SPACING["xs"],
    )
    period_name = (f"Week of {data['start'].day} {data['start'].strftime('%b')}"
                   if kind == "week" else data["title"])
    period_heading = ft.Column(controls=[
        _txt(period_name, palette, size=FONT_SIZES["body"]),
        _txt(f"{data['days_logged']}/{data['days_in_range']} logged", palette,
             size=FONT_SIZES["small"], color=palette["accent"]),
    ], spacing=SPACING["xs"], expand=True, horizontal_alignment=ft.CrossAxisAlignment.CENTER)
    date_nav = ft.Row(controls=[
        ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Previous period", width=48, height=48,
                      icon_color=palette["muted"], on_click=on_previous),
        period_heading,
        ft.IconButton(icon=ft.Icons.CHEVRON_RIGHT, tooltip="Next period", width=48, height=48,
                      icon_color=palette["muted"], on_click=on_next),
    ], vertical_alignment=ft.CrossAxisAlignment.CENTER)
    if not data["has_profile"]:
        return ft.Column(controls=[periods, date_nav, _card(ft.Column(controls=[
            _txt("Your stats", palette, size=FONT_SIZES["section"]),
            _txt("Set up a profile in the desktop app to see calorie and nutrition summaries. Logged days will still appear in Calendar.",
                 palette, muted=True),
            ft.OutlinedButton("Export CSV", icon=ft.Icons.DOWNLOAD,
                              on_click=on_export, disabled=True),
        ], spacing=SPACING["tight"]), palette)], spacing=SPACING["section"], expand=True)

    days_logged = data["days_logged"]
    all_records = data["records"]
    logged_records = [record for record in all_records if record["logged"]]
    if kind == "month":
        logged_records = logged_records[-7:]
    chart_records = all_records if kind == "week" else logged_records
    scale = max([max(record["calories_consumed"], record["calories_burned"])
                 for record in chart_records] + [1])
    bars = []
    labels = []
    for record in chart_records:
        if kind == "week":
            bar_label = record["day"].strftime("%a")[0]
        else:
            bar_label = record["day"].strftime("%d")
        eaten_height = (max(3, round(CHART_BAR_AREA * record["calories_consumed"] / scale))
                        if record["logged"] else 0)
        burned_height = (max(3, round(CHART_BAR_AREA * record["calories_burned"] / scale))
                         if record["logged"] else 0)
        bars.append(ft.Container(
            content=ft.Row(controls=[
                ft.Container(width=10, height=eaten_height, bgcolor=palette["accent"], border_radius=3),
                ft.Container(width=10, height=burned_height, bgcolor=palette["series_secondary"], border_radius=3),
            ], spacing=SPACING["xs"], vertical_alignment=ft.CrossAxisAlignment.END,
               alignment=ft.MainAxisAlignment.CENTER),
            expand=True, height=CHART_BAR_AREA, alignment=ft.Alignment.BOTTOM_CENTER))
        labels.append(ft.Container(
            content=_txt(bar_label, palette, size=FONT_SIZES["small"], muted=True),
            expand=True, alignment=ft.Alignment.CENTER))
    if not bars:
        bars_content = _txt("Log food to see the calorie chart for this period.", palette, muted=True)
    else:
        bars_content = ft.Column(controls=[
            ft.Row(controls=bars, spacing=0, vertical_alignment=ft.CrossAxisAlignment.END),
            ft.Row(controls=labels, spacing=0),   # all labels share one row, so one baseline
        ], spacing=SPACING["xs"])
    chart = _card(ft.Column(controls=[
        bars_content,
        ft.Row(controls=[
            ft.Container(width=8, height=8, bgcolor=palette["accent"], border_radius=8),
            _txt("eaten", palette, size=FONT_SIZES["small"], muted=True),
            ft.Container(width=8, height=8, bgcolor=palette["series_secondary"], border_radius=8),
            _txt("burned", palette, size=FONT_SIZES["small"], muted=True),
        ], spacing=SPACING["sm"]),
    ], spacing=SPACING["xs"]), palette)

    macro_rows = [
        _txt("Average macros", palette, size=FONT_SIZES["body"], muted=True),
        _txt(f"P {data['protein_avg']:g}g   C {data['carbs_avg']:g}g   F {data['fat_avg']:g}g",
             palette, size=FONT_SIZES["body"]),
    ]
    macros = _card(ft.Column(controls=macro_rows, spacing=SPACING["sm"]), palette)

    adherence = data["adherence"]
    if adherence and adherence["days_logged"]:
        insights = data["insights"]
        variance = insights["average_variance"]
        direction = "over" if variance > 0 else "under" if variance < 0 else "at"
        insight_text = (f"Average {abs(variance):,.0f} kcal {direction} target. "
                        + exercise_insight_text(insights["exercise_days"], kind))
    else:
        insight_text = "Log food to build personalized insights."
    notes = _card(ft.Column(controls=[
        _txt("Insights", palette, size=FONT_SIZES["body"], muted=True),
        _txt(insight_text, palette, size=FONT_SIZES["body"]),
    ], spacing=SPACING["xs"]), palette)
    disclaimer = _txt("All calorie and nutrition values are estimates.", palette,
                      size=FONT_SIZES["small"], muted=True)
    export_button = ft.FilledButton("Export CSV", icon=ft.Icons.DOWNLOAD,
                                    on_click=on_export, bgcolor=palette["accent"],
                                    color=palette["accent_text"], expand=True)
    return ft.Column(controls=[
        periods, date_nav, chart, macros, notes, export_button, disclaimer,
    ], spacing=SPACING["section"], scroll=ft.ScrollMode.HIDDEN, expand=True,
       horizontal_alignment=ft.CrossAxisAlignment.STRETCH)


def navigation_bar(palette: dict, selected_index: int, on_change) -> ft.NavigationBar:
    return ft.NavigationBar(
        destinations=[ft.NavigationBarDestination(icon=icon, label=label)
                      for icon, label in zip(TAB_ICONS, TAB_NAMES)],
        selected_index=selected_index,
        bgcolor=palette["surface"],
        indicator_color=palette["track"],
        label_behavior=ft.NavigationBarLabelBehavior.ALWAYS_SHOW,
        on_change=on_change,
    )


def _choice_pill(label: str, selected: bool, palette: dict, on_click,
                 expand: bool = True) -> ft.Container:
    return ft.Container(
        content=_txt(label, palette, size=FONT_SIZES["body"],
                     color=palette["accent_text"] if selected else palette["text"]),
        expand=expand, height=TOUCH_TARGET, alignment=ft.Alignment.CENTER,
        bgcolor=palette["accent"] if selected else palette["track"],
        border_radius=RADIUS["pill"], on_click=on_click,
    )


def _weight_chart(weights: dict, goal_kg: float | None, unit: str,
                  palette: dict, end: date | None = None) -> ft.Control:
    end = end or date.today()
    entries = stats.weight_trend(weights, end, 30)
    if not entries:
        return _card(_txt("Your weight trend will appear here after you log a weigh-in.",
                          palette, muted=True), palette)
    if len(entries) < 2:
        return _card(_txt("Log your weight on 2 days to see your trend", palette, muted=True), palette)

    width, height, padding = 300, 118, 12
    values = [item["kg"] for item in entries]
    if goal_kg is not None:
        values.append(goal_kg)
    low, high = min(values), max(values)
    if high - low < 0.5:
        low -= 0.5
        high += 0.5
    else:
        margin = (high - low) * 0.12
        low -= margin
        high += margin

    def y_for(kg):
        return padding + (high - kg) / (high - low) * (height - 2 * padding)

    controls = []
    if goal_kg is not None:
        y = y_for(goal_kg)
        for x in range(padding, width - padding, 18):
            controls.append(ft.Container(left=x, top=y, width=10, height=2,
                                         bgcolor=palette["muted"], border_radius=2))

    points = []
    for index, item in enumerate(entries):
        x = padding if len(entries) == 1 else padding + index * (width - 2 * padding) / (len(entries) - 1)
        points.append((x, y_for(item["kg"])))
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        dx, dy = x2 - x1, y2 - y1
        controls.append(ft.Container(
            left=(x1 + x2) / 2 - math.hypot(dx, dy) / 2,
            top=(y1 + y2) / 2 - 1.5,
            width=math.hypot(dx, dy), height=3,
            bgcolor=palette["accent"], border_radius=3,
            rotate=ft.Rotate(angle=math.atan2(dy, dx)),
        ))
    for x, y in points:
        controls.append(ft.Container(left=x - 5, top=y - 5, width=10, height=10,
                                     bgcolor=palette["accent"], border_radius=10))

    chart = ft.Stack(controls=controls, width=width, height=height,
                     clip_behavior=ft.ClipBehavior.HARD_EDGE)
    return _card(chart, palette, padding=8)


def build_weight_screen(data: dict, palette: dict, unit: str, on_save) -> ft.Control:
    field = ft.TextField(label=f"Weight ({weight_unit_label(unit)})",
                         keyboard_type=ft.KeyboardType.NUMBER,
                         border_radius=RADIUS["button"], expand=True)
    save = ft.FilledButton("Save", on_click=lambda event: on_save(field.value),
                           bgcolor=palette["accent"], color=palette["accent_text"])
    entry = ft.Row(controls=[field, save], spacing=SPACING["sm"],
                   vertical_alignment=ft.CrossAxisAlignment.CENTER)

    latest = data["latest"]
    if latest:
        delta = data["change"]
        summary = _card(ft.Column(controls=[
            ft.Row(controls=[
                _txt(f"{from_kg(latest[1], unit):.1f} {weight_unit_label(unit)}",
                     palette, size=FONT_SIZES["title"] + 4),
                _txt(f"{from_kg(delta, unit):+.1f} {weight_unit_label(unit)}" if delta is not None else "",
                     palette, color=palette["accent"]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            _weight_chart(data["weights"], data["goal_kg"], unit, palette, data["today"]),
        ], spacing=SPACING["sm"]), palette)
    else:
        summary = _card(ft.Column(controls=[
            _txt("No weigh-ins yet", palette, size=FONT_SIZES["section"]),
            _txt("Your latest weight and trend will show here after you save your first entry.",
                 palette, muted=True),
        ], spacing=SPACING["sm"]), palette)

    day_note = _txt("Saving for " + data.get("selected_date", data["today"]).strftime("%a, %d %b")
                    + " (change the day on the Log tab)", palette, size=FONT_SIZES["small"], muted=True)
    sections = [day_note, entry, summary]
    progress = data["goal_progress"]
    if progress:
        progress_label = goal_weight_progress_label(
            progress["remaining_kg"], data.get("goal", "lose"), unit,
        )
        sections.append(_card(ft.Column(controls=[
            ft.Row(controls=[
                _txt(f"Goal {from_kg(progress['goal_kg'], unit):g} {weight_unit_label(unit)}",
                     palette, muted=True),
                _txt(progress_label,
                     palette, color=palette["accent"]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            ft.ProgressBar(value=progress["progress_pct"] / 100,
                           color=palette["accent"], bgcolor=palette["track"],
                           bar_height=7, border_radius=8),
        ], spacing=SPACING["sm"]), palette))

    history = []
    for item in data["entries"][:2]:
        history.append(_card(ft.Row(controls=[
            _txt(f"{item['date'].day} {item['date'].strftime('%b')}"
                 if hasattr(item["date"], "strftime") else str(item["date"]),
                 palette, muted=True),
            _txt(f"{from_kg(item['kg'], unit):.1f} {weight_unit_label(unit)}", palette),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), palette, padding=SPACING["sm"]))
    sections.extend(history)
    if data["trend_note"]:
        sections.append(_txt(data["trend_note"], palette, size=FONT_SIZES["small"], muted=True))
    return ft.Column(controls=sections, spacing=SPACING["section"],
                     scroll=ft.ScrollMode.HIDDEN, expand=True)


def build_settings_screen(data: dict, palette: dict, on_weight_unit, on_theme,
                          on_save, on_edit_profile, on_backup, on_restore,
                          on_calculations, backup_help=None) -> ft.Control:
    person = data["profile"]
    if person:
        goal = person.goal.replace("_", " ").title()
        if person.goal != "maintain":
            goal += f", {person.pace}"
        details = (f"{from_kg(person.weight_kg, data['weight_unit']):g} {weight_unit_label(data['weight_unit'])}"
                   f" · {person.height_cm:g} cm · {person.activity_level.replace('_', ' ').title()}\n"
                   f"Goal: {goal}")
        profile_card = _card(ft.Row(controls=[
            ft.Container(content=_txt(person.name[:1].upper(), palette, size=FONT_SIZES["title"],
                                      color=palette["accent_text"]),
                         width=48, height=48, alignment=ft.Alignment.CENTER,
                         bgcolor=palette["accent"], border_radius=RADIUS["pill"]),
            ft.Column(controls=[
                _txt(person.name, palette, size=FONT_SIZES["title"]),
                _txt(details, palette, muted=True),
            ], spacing=SPACING["xs"], expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=palette["muted"]),
        ], spacing=SPACING["md"], vertical_alignment=ft.CrossAxisAlignment.CENTER), palette)
        profile_card.on_click = on_edit_profile
    else:
        profile_card = _card(ft.Column(controls=[
            _txt("Profile not set up", palette, size=FONT_SIZES["section"]),
            _txt("Create your profile to get calorie and macro estimates.", palette, muted=True),
        ]), palette)
        profile_card.on_click = on_edit_profile

    unit_group = ft.Row(controls=[
        _choice_pill("kg", data["weight_unit"] == "kg", palette,
                     lambda event: on_weight_unit("kg")),
        _choice_pill("lb", data["weight_unit"] == "lb", palette,
                     lambda event: on_weight_unit("lb")),
    ], spacing=SPACING["xs"])
    theme_group = ft.Row(controls=[
        _choice_pill("Light", data["theme"] == "light", palette,
                     lambda event: on_theme("light")),
        _choice_pill("Dark", data["theme"] == "dark", palette,
                     lambda event: on_theme("dark")),
    ], spacing=SPACING["xs"])

    controls = [
        profile_card,
        ft.Container(content=ft.Row(controls=[
            ft.Icon(ft.Icons.PERSON_OUTLINE, color=palette["accent"]),
            ft.Container(content=_txt("Edit profile", palette, size=FONT_SIZES["body"]), expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=palette["muted"]),
        ], spacing=SPACING["sm"]), bgcolor=palette["card"], padding=SPACING["card"],
            border_radius=RADIUS["card"], on_click=on_edit_profile),
        _card(ft.Column(controls=[
            _txt("DISPLAY", palette, size=FONT_SIZES["small"], muted=True),
            _txt("Body weight units", palette, muted=True), unit_group,
        ], spacing=SPACING["sm"]), palette),
        _card(ft.Column(controls=[
            _txt("Appearance", palette, muted=True), theme_group,
        ], spacing=SPACING["sm"]), palette),
        ft.Row(controls=[ft.FilledButton("Save settings", on_click=on_save,
                        bgcolor=palette["accent"], color=palette["accent_text"],
                        height=PRIMARY_BUTTON_HEIGHT, expand=True)]),
        ft.Row(controls=[ft.OutlinedButton("Back up data", icon=ft.Icons.DOWNLOAD, on_click=on_backup,
                          style=ft.ButtonStyle(color=palette["text"]), expand=True)]),
        ft.Row(controls=[ft.OutlinedButton("Restore backup", icon=ft.Icons.UPLOAD, on_click=on_restore,
                          style=ft.ButtonStyle(color=palette["text"]), expand=True)]),
        ft.Container(content=ft.Row(controls=[
            _txt("How is this calculated?", palette),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=palette["muted"]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), bgcolor=palette["card"],
            padding=SPACING["card"], border_radius=RADIUS["card"], on_click=on_calculations),
        _txt(backup_help or
             "Height stays in cm; food amounts stay in grams. Backups are saved in Downloads/CalorieTracker. "
             "Numbers are estimates, not medical advice.",
             palette, size=FONT_SIZES["small"], muted=True),
    ]
    return ft.Column(controls=controls, spacing=SPACING["tight"],
                     scroll=ft.ScrollMode.HIDDEN, expand=True)


class FletTrackerApp:
    def __init__(self, page: ft.Page, storage):
        self.page = page
        self.storage = storage
        self.selected_date = date.today()
        self.calendar_month_ref = self.selected_date.replace(day=1)
        self.stats_reference_date = latest_food_log_date(storage, self.selected_date)
        self.stat_kind = "week"
        self.selected_tab = 0
        self.setup_mode = storage.profile is None
        self.setup_stage = "welcome" if self.setup_mode else "questions"
        self.setup_answers = {}
        self.setup_draft = {}
        self.setup_inputs = {}
        self.setup_index = 0
        self.setup_weight_unit = storage.preferences.get("weight_unit", "kg")
        self.setup_error = ""
        self.setup_person = None
        self.profile_editing = False
        self.pending_weight_unit = storage.preferences.get("weight_unit", "kg")
        self.pending_theme = ("dark" if self.setup_mode
                              else storage.preferences.get("theme", "dark"))
        self.palette = palette_for(self.pending_theme)
        self.is_android = getattr(page, "platform", None) in (
            ft.PagePlatform.ANDROID, ft.PagePlatform.ANDROID_TV,
        )
        self.file_picker = ft.FilePicker() if self.is_android else None
        if self.file_picker is not None and hasattr(page, "services"):
            page.services.append(self.file_picker)
        self._switcher = None
        self._screen_serial = 0

        page.title = "Calorie Tracker"
        page.theme_mode = ft.ThemeMode.DARK if self.pending_theme == "dark" else ft.ThemeMode.LIGHT
        page.theme = _app_theme(self.palette, self.pending_theme == "dark")
        page.dark_theme = _app_theme(palette_for("dark"), True)
        page.light_theme = _app_theme(palette_for("light"), False)
        page.bgcolor = self.palette["background"]
        page.padding = 0
        page.spacing = 0
        if hasattr(page, "window"):
            page.window.width = 430
            page.window.height = 850
            page.window.min_width = 360
            page.window.min_height = 640
        self.render()

    def _welcome_screen(self):
        ring = ft.Stack(controls=[
            ft.ProgressRing(value=0.76, width=142, height=142, stroke_width=9,
                            color=self.palette["accent"], bgcolor=self.palette["track"]),
            ft.Container(content=ft.Icon(ft.Icons.CHECK, size=48,
                                         color=self.palette["accent"]),
                         width=82, height=82, alignment=ft.Alignment.CENTER,
                         bgcolor=self.palette["quote_strip"], border_radius=44),
        ], width=142, height=142, alignment=ft.Alignment.CENTER)
        copy = ft.Column(controls=[
            _txt("Let's set up your plan", self.palette, size=FONT_SIZES["title"] + 12,
                 weight=ft.FontWeight.W_600),
            _txt("13 quick questions, about 2 minutes. You can change any answer later.",
                 self.palette, size=FONT_SIZES["body"], muted=True),
            _txt("Numbers are estimates, not medical advice.", self.palette,
                 size=FONT_SIZES["small"], muted=True),
        ], spacing=SPACING["section"], horizontal_alignment=ft.CrossAxisAlignment.CENTER)
        for copy_item in copy.controls:
            if isinstance(copy_item, ft.Text):
                copy_item.text_align = ft.TextAlign.CENTER
        return ft.Column(controls=[
            ft.Container(expand=True),
            ring, copy,
            ft.Container(expand=True),
            ft.Row(controls=[ft.FilledButton(
                "Get started", on_click=self._start_setup,
                bgcolor=self.palette["accent"], color=self.palette["accent_text"],
                height=PRIMARY_BUTTON_HEIGHT, expand=True,
            )]),
        ], spacing=SPACING["section"], expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER)

    def _question_screen(self):
        questions = visible_questions(self.setup_answers)
        if not questions:
            return self._welcome_screen()
        index = min(self.setup_index, len(questions) - 1)
        question = questions[index]
        key = question["key"]
        saved = self.setup_answers.get(key)
        draft = self.setup_draft.get(key, saved)
        total_steps = len(QUESTIONS) if "goal" not in self.setup_answers else len(questions)
        header = ft.Row(controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Back",
                          icon_color=self.palette["muted"], on_click=self._back_setup),
            ft.Container(content=_txt(f"Step {index + 1} / {total_steps}", self.palette,
                                      color=self.palette["accent"]),
                         bgcolor=self.palette["quote_strip"], padding=ft.Padding(14, 8, 14, 8),
                         border_radius=RADIUS["pill"]),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        progress = ft.ProgressBar(value=(index + 1) / total_steps,
                                  color=self.palette["accent"], bgcolor=self.palette["track"],
                                  bar_height=8, border_radius=8)
        prompt = _txt(question["prompt"], self.palette, size=FONT_SIZES["question"],
                      weight=ft.FontWeight.W_600)
        prompt.max_lines = 3
        prompt.overflow = ft.TextOverflow.ELLIPSIS
        input_controls = []
        if question["type"] == "choice":
            choices = []
            for value, label in question["choices"]:
                if ":" in label:
                    title, subtitle = label.split(":", 1)
                else:
                    title, subtitle = label, ""
                is_selected = value == draft
                choices.append(ft.Container(
                    content=ft.Column(controls=[
                        _txt(title.strip(), self.palette,
                             color=self.palette["accent"] if is_selected else self.palette["text"],
                             weight=ft.FontWeight.W_500),
                        *([_txt(subtitle.strip(), self.palette, muted=True)] if subtitle else []),
                    ], spacing=SPACING["xs"]),
                    bgcolor=self.palette["quote_strip"] if is_selected else self.palette["card"],
                    border=ft.Border.all(1, self.palette["accent"] if is_selected else self.palette["track"]),
                    border_radius=RADIUS["card"], padding=SPACING["card"],
                    on_click=lambda event, chosen=value, qkey=key: self._choose_setup_answer(qkey, chosen),
                ))
            input_controls.append(ft.Column(controls=choices, spacing=SPACING["sm"],
                                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH))
        else:
            unit = question.get("unit", "")
            if key in ("weight_kg", "goal_weight_kg"):
                unit_buttons = ft.Row(controls=[
                    _choice_pill("kg", self.setup_weight_unit == "kg", self.palette,
                                 lambda event: self._change_setup_unit("kg"), expand=True),
                    _choice_pill("lb", self.setup_weight_unit == "lb", self.palette,
                                 lambda event: self._change_setup_unit("lb"), expand=True),
                ], spacing=SPACING["xs"])
                unit = unit_buttons
            display_value = "" if draft is None else str(draft)
            if key in ("weight_kg", "goal_weight_kg") and saved is not None and key not in self.setup_draft:
                display_value = f"{from_kg(saved, self.setup_weight_unit):g}"
            field = ft.TextField(
                value=display_value,
                hint_text=question.get("default", "Enter a number"),
                keyboard_type=ft.KeyboardType.NUMBER if question["type"] == "number" else ft.KeyboardType.TEXT,
                text_size=FONT_SIZES["title"],
                height=TEXT_FIELD_HEIGHT,
                border_radius=RADIUS["card"],
                border_color=self.palette["accent"],
                suffix=(None if isinstance(unit, ft.Control) else (unit or None)),
                on_change=lambda event, qkey=key: self.setup_draft.__setitem__(qkey, event.control.value),
            )
            self.setup_inputs[key] = field
            input_controls.append(field)
            if isinstance(unit, ft.Control):
                input_controls.append(unit)

        help_text = question.get("help")
        body_controls = [prompt]
        if help_text:
            body_controls.append(_txt(help_text, self.palette, size=FONT_SIZES["body"], muted=True))
        body_controls.extend(input_controls)
        if self.setup_error:
            body_controls.append(_txt(self.setup_error, self.palette, color="#E57373"))
        skip = []
        if question.get("optional"):
            skip = [ft.TextButton("Skip this question", on_click=self._skip_setup_question,
                                  style=ft.ButtonStyle(color=self.palette["accent"]))]
        body = ft.Column(controls=body_controls, spacing=SPACING["section"],
                         scroll=ft.ScrollMode.HIDDEN, expand=True,
                         horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        footer = ft.Column(controls=[*skip, ft.Row(controls=[
            ft.FilledButton("Back", on_click=self._back_setup,
                            bgcolor=self.palette["track"], color=self.palette["text"], expand=1),
            ft.FilledButton("Next", on_click=self._next_setup,
                            bgcolor=self.palette["accent"], color=self.palette["accent_text"], expand=2),
        ], spacing=SPACING["sm"])], spacing=SPACING["xs"],
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        if skip:
            footer.controls[0] = ft.Row(controls=skip, alignment=ft.MainAxisAlignment.CENTER)
        return ft.Column(controls=[header, progress, body, footer],
                         spacing=SPACING["section"], expand=True)

    def _plan_summary_screen(self):
        person = self.setup_person
        target = calculate_targets(person)
        ring = ft.Stack(controls=[
            ft.ProgressRing(value=0.76, width=70, height=70, stroke_width=6,
                            color=self.palette["accent"], bgcolor=self.palette["track"]),
            ft.Container(width=52, height=52, alignment=ft.Alignment.CENTER,
                         content=ft.Icon(ft.Icons.CHECK, color=self.palette["accent"], size=24)),
        ], width=70, height=70, alignment=ft.Alignment.CENTER)
        macros = ft.Row(controls=[
            _card(ft.Column(controls=[_txt(f"{target['protein_g']:g} g", self.palette,
                                           size=FONT_SIZES["section"]),
                            _txt("Protein", self.palette, muted=True)],
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER), self.palette, padding=SPACING["sm"], expand=True),
            _card(ft.Column(controls=[_txt(f"{target['carbs_g']:g} g", self.palette,
                                           size=FONT_SIZES["section"]),
                            _txt("Carbs", self.palette, muted=True)],
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER), self.palette, padding=SPACING["sm"], expand=True),
            _card(ft.Column(controls=[_txt(f"{target['fat_g']:g} g", self.palette,
                                           size=FONT_SIZES["section"]),
                            _txt("Fat", self.palette, muted=True)],
                           horizontal_alignment=ft.CrossAxisAlignment.CENTER), self.palette, padding=SPACING["sm"], expand=True),
        ], spacing=SPACING["sm"])
        goal = person.goal.replace("_", " ")
        if person.goal != "maintain":
            goal += f", {person.pace} pace"
        if person.goal_weight_kg is not None:
            goal += f", goal weight {from_kg(person.goal_weight_kg, self.pending_weight_unit):g} {weight_unit_label(self.pending_weight_unit)}"
        return ft.Column(controls=[
            ft.Container(expand=True),
            ft.Row(controls=[ring, ft.Column(controls=[
                _txt(f"{target['calories']:,}", self.palette, size=FONT_SIZES["title"] + 8,
                     color=self.palette["accent"]),
                _txt("kcal a day", self.palette, muted=True),
            ], spacing=0)], spacing=SPACING["md"], alignment=ft.MainAxisAlignment.CENTER),
            _txt("Your daily plan", self.palette, size=FONT_SIZES["title"] + 5,
                 weight=ft.FontWeight.W_600),
            macros,
            _txt(f"Goal: {goal}", self.palette, muted=True),
            _txt("Estimates only. Not medical advice.", self.palette,
                 size=FONT_SIZES["small"], muted=True),
            ft.TextButton("How is this calculated?", on_click=self._open_calculations,
                          style=ft.ButtonStyle(color=self.palette["accent"])),
            ft.Container(expand=True),
            ft.Row(controls=[ft.FilledButton(
                "Start logging", on_click=self._complete_setup,
                bgcolor=self.palette["accent"], color=self.palette["accent_text"],
                height=PRIMARY_BUTTON_HEIGHT, expand=True,
            )]),
        ], spacing=SPACING["section"], expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH)

    def _start_setup(self, event=None):
        self.setup_stage = "questions"
        self.setup_index = 0
        self.setup_error = ""
        self.setup_inputs = {}
        self.render()

    def _choose_setup_answer(self, key, value):
        self.setup_draft[key] = value
        self.setup_error = ""
        self.render()

    def _change_setup_unit(self, unit):
        question = visible_questions(self.setup_answers)[self.setup_index]
        key = question["key"]
        field = getattr(self, "setup_inputs", {}).get(key)
        old_unit = self.setup_weight_unit
        if field and field.value:
            try:
                kg = to_kg(float(field.value), old_unit)
                self.setup_draft[key] = f"{from_kg(kg, unit):g}"
            except (ValueError, TypeError):
                self.setup_draft[key] = field.value
        self.setup_weight_unit = unit
        self.render()

    def _next_setup(self, event=None):
        questions = visible_questions(self.setup_answers)
        question = questions[self.setup_index]
        key = question["key"]
        raw = self.setup_draft.get(key)
        if question["type"] != "choice":
            field = getattr(self, "setup_inputs", {}).get(key)
            if field is not None:
                raw = field.value
        if key in ("weight_kg", "goal_weight_kg") and self.setup_weight_unit == "lb" and raw not in (None, ""):
            try:
                raw = str(to_kg(float(raw), "lb"))
            except (ValueError, TypeError):
                pass
        value, error = validate_answer(question, raw)
        if error:
            self.setup_error = error
            self.render()
            return
        self.setup_answers[key] = value
        updated = visible_questions(self.setup_answers)
        next_index = next(i for i, item in enumerate(updated) if item["key"] == key) + 1
        self.setup_error = ""
        if next_index >= len(updated):
            try:
                self.setup_person = person_from_answers(self.setup_answers)
                self.setup_stage = "summary"
            except ValueError as exc:
                self.setup_error = str(exc)
                self.setup_index = max(0, len(updated) - 1)
        else:
            self.setup_index = next_index
        self.render()

    def _skip_setup_question(self, event=None):
        questions = visible_questions(self.setup_answers)
        question = questions[self.setup_index]
        self.setup_answers[question["key"]] = None
        self.setup_draft[question["key"]] = ""
        field = getattr(self, "setup_inputs", {}).get(question["key"])
        if field is not None:
            field.value = ""
        self._next_setup(event)

    def _back_setup(self, event=None):
        if self.setup_stage == "summary":
            self.setup_stage = "questions"
            self.setup_index = len(visible_questions(self.setup_answers)) - 1
        elif self.setup_index == 0:
            self.setup_stage = "welcome"
        else:
            self.setup_index -= 1
        self.setup_error = ""
        self.render()

    def _complete_setup(self, event=None):
        if self.setup_person is None:
            return
        self.storage.set_profile(self.setup_person)
        self.pending_weight_unit = self.setup_weight_unit
        self.storage.set_preferences(weight_unit=self.pending_weight_unit,
                                     theme=self.pending_theme)
        self.setup_mode = False
        self.selected_tab = 0
        self.render()

    def _weight_screen(self):
        summary = stats.weight_summary(self.storage.weights)
        goal_kg = self.storage.profile.goal_weight_kg if self.storage.profile else None
        progress = stats.goal_weight_progress(self.storage.weights, goal_kg) if goal_kg is not None else None
        return build_weight_screen({
            "weights": self.storage.weights,
            "latest": summary["latest"],
            "change": summary["change"] if len(summary["entries"]) > 1 else None,
            "entries": summary["entries"],
            "goal_kg": goal_kg,
            "goal_progress": progress,
            "today": date.today(),
            "selected_date": self.selected_date,
            "trend_note": "",
        }, self.palette, self.pending_weight_unit, self._save_weight)

    def _save_weight(self, raw):
        try:
            entered = float(raw)
            kg = to_kg(entered, self.pending_weight_unit)
            self.storage.log_weight(self.selected_date, kg)
        except (ValueError, TypeError) as exc:
            self._info_dialog("Weight", str(exc) or "Enter your weight as a number.")
            return
        self.render()

    def _set_pending_weight_unit(self, unit):
        self.pending_weight_unit = unit
        self.render()

    def _set_pending_theme(self, theme):
        self.pending_theme = theme
        self.render()

    def _save_settings(self, event=None):
        try:
            self.storage.set_preferences(weight_unit=self.pending_weight_unit,
                                         theme=self.pending_theme)
        except ValueError as exc:
            self._info_dialog("Settings", str(exc))
            return
        self.palette = palette_for(self.pending_theme)
        self.page.theme_mode = ft.ThemeMode.DARK if self.pending_theme == "dark" else ft.ThemeMode.LIGHT
        self.page.theme = _app_theme(self.palette, self.pending_theme == "dark")
        self.page.dark_theme = _app_theme(palette_for("dark"), True)
        self.page.light_theme = _app_theme(palette_for("light"), False)
        self.page.bgcolor = self.palette["background"]
        self.render()

    def _profile_editor_screen(self):
        p = self.storage.profile
        unit = self.pending_weight_unit
        self.profile_fields = {
            "name": self._field("Name", p.name),
            "age": self._field("Age", str(p.age), ft.KeyboardType.NUMBER),
            "height": self._field("Height (cm)", f"{p.height_cm:g}", ft.KeyboardType.NUMBER),
            "weight": self._field("Weight", f"{from_kg(p.weight_kg, unit):g}", ft.KeyboardType.NUMBER),
            "goal_weight": self._field("Goal weight (optional)",
                                        "" if p.goal_weight_kg is None else f"{from_kg(p.goal_weight_kg, unit):g}",
                                        ft.KeyboardType.NUMBER),
            "calories": self._field("Calories (optional)",
                                     "" if p.custom_calorie_target is None else f"{p.custom_calorie_target:g}",
                                     ft.KeyboardType.NUMBER),
            "protein": self._field("Protein (optional)",
                                    "" if p.custom_protein_target is None else f"{p.custom_protein_target:g}",
                                    ft.KeyboardType.NUMBER),
            "carbs": self._field("Carbs (optional)",
                                  "" if p.custom_carbs_target is None else f"{p.custom_carbs_target:g}",
                                  ft.KeyboardType.NUMBER),
            "fat": self._field("Fat (optional)",
                                "" if p.custom_fat_target is None else f"{p.custom_fat_target:g}",
                                ft.KeyboardType.NUMBER),
        }
        self.profile_sex_choice = p.sex.lower()
        self.profile_activity_choice = p.activity_level.lower()
        sex_pills = []
        for value, label in (("male", "Male"), ("female", "Female")):
            pill = _choice_pill(label, value == self.profile_sex_choice, self.palette,
                                lambda event, choice=value: self._set_editor_sex(choice), expand=True)
            sex_pills.append((value, pill))
        self.profile_sex_pills = sex_pills
        sex = _card(ft.Column(controls=[
            _txt("Calorie formula", self.palette, muted=True),
            ft.Row(controls=[pill for _, pill in sex_pills], spacing=SPACING["xs"]),
            _txt("The standard formulas use these categories to estimate resting calories.",
                 self.palette, size=FONT_SIZES["small"], muted=True),
        ], spacing=SPACING["sm"]), self.palette)
        goal = ft.Dropdown(label="Goal", value=p.goal, options=[
            ft.DropdownOption(key="lose", text="Lose weight"),
            ft.DropdownOption(key="maintain", text="Maintain weight"),
            ft.DropdownOption(key="gain", text="Gain weight"),
        ])
        pace = ft.Dropdown(label="Pace", value=p.pace, options=[
            ft.DropdownOption(key="gentle", text="Gentle · about 250 kcal/day"),
            ft.DropdownOption(key="steady", text="Steady · about 500 kcal/day"),
        ])
        pace_container = _card(ft.Column(controls=[pace,
            _txt("Shown only for lose or gain goals.", self.palette, size=FONT_SIZES["small"], muted=True)],
            spacing=SPACING["xs"]), self.palette)
        pace_container.visible = goal.value in ("lose", "gain")
        goal.on_select = lambda event: self._set_pace_visibility(pace_container, goal.value)
        self.profile_activity_text = _txt(
            next(label.split(":", 1)[0] for value, label in
                 next(q for q in QUESTIONS if q["key"] == "activity_level")["choices"]
                 if value == self.profile_activity_choice),
            self.palette, size=FONT_SIZES["body"])
        self.profile_activity_hint = _txt(
            next(label.split(":", 1)[1].strip() for value, label in
                 next(q for q in QUESTIONS if q["key"] == "activity_level")["choices"]
                 if value == self.profile_activity_choice),
            self.palette, size=FONT_SIZES["small"], muted=True)
        activity_control = _card(ft.Row(controls=[
            ft.Column(controls=[_txt("Activity", self.palette, muted=True),
                                self.profile_activity_text, self.profile_activity_hint],
                      spacing=SPACING["xs"], expand=True),
            ft.Icon(ft.Icons.CHEVRON_RIGHT, color=self.palette["muted"]),
        ], vertical_alignment=ft.CrossAxisAlignment.CENTER), self.palette)
        activity_control.on_click = self._open_activity_picker
        self.profile_editor_message = _txt("", self.palette, size=FONT_SIZES["small"], color="#E57373")
        target_preview = _txt(f"Calculated target: {calculate_targets(p)['calories']:,} kcal/day",
                              self.palette, size=FONT_SIZES["small"], muted=True)

        def save_click(event=None):
            self._save_profile_editor(goal, pace)

        header = ft.Row(controls=[
            ft.IconButton(icon=ft.Icons.CHEVRON_LEFT, tooltip="Back to Settings",
                          on_click=self._cancel_profile_editor, icon_color=self.palette["muted"]),
            _txt("Edit profile", self.palette, size=FONT_SIZES["title"], weight=ft.FontWeight.W_600),
            ft.TextButton("Save", on_click=save_click,
                          style=ft.ButtonStyle(color=self.palette["accent"])),
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        body = ft.Column(controls=[
            _txt("ABOUT YOU", self.palette, size=FONT_SIZES["small"], muted=True),
            self.profile_fields["name"],
            ft.Row(controls=[self.profile_fields["age"], self.profile_fields["height"]], spacing=SPACING["sm"]),
            sex,
            _card(ft.Column(controls=[
                ft.Row(controls=[_txt("Weight", self.palette, muted=True),
                                 _txt(weight_unit_label(unit), self.palette, muted=True)],
                       alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                self.profile_fields["weight"],
                _txt("Saving adds today's weigh-in.", self.palette, size=FONT_SIZES["small"], muted=True),
            ], spacing=SPACING["xs"]), self.palette),
            activity_control, goal, pace_container,
            self.profile_fields["goal_weight"],
            _txt("Leave goal weight blank if you don't want to set one.",
                 self.palette, size=FONT_SIZES["small"], muted=True),
            _txt("CUSTOM TARGETS (OPTIONAL)", self.palette, size=FONT_SIZES["small"], muted=True),
            self.profile_fields["calories"], target_preview,
            ft.Row(controls=[self.profile_fields["protein"], self.profile_fields["carbs"]], spacing=SPACING["sm"]),
            self.profile_fields["fat"], self.profile_editor_message,
        ], spacing=SPACING["tight"], scroll=ft.ScrollMode.HIDDEN, expand=True)
        footer = ft.Row(controls=[
            ft.FilledButton("Cancel", on_click=self._cancel_profile_editor,
                            bgcolor=self.palette["track"], color=self.palette["text"], expand=True),
            ft.FilledButton("Save changes", on_click=save_click,
                            bgcolor=self.palette["accent"], color=self.palette["accent_text"], expand=True),
        ], spacing=SPACING["sm"])
        return ft.Column(controls=[header, body, footer], spacing=SPACING["tight"], expand=True)

    def _set_editor_sex(self, sex):
        self.profile_sex_choice = sex
        for value, pill in self.profile_sex_pills:
            selected = value == sex
            pill.bgcolor = self.palette["accent"] if selected else self.palette["track"]
            pill.content.color = self.palette["accent_text"] if selected else self.palette["text"]
        self.page.update()

    def _open_activity_picker(self, event=None):
        question = next(q for q in QUESTIONS if q["key"] == "activity_level")
        choices = []
        for value, label in question["choices"]:
            title, subtitle = label.split(":", 1)
            selected = value == self.profile_activity_choice
            choices.append(ft.Container(
                content=ft.Row(controls=[ft.Column(controls=[
                    _txt(title, self.palette,
                         color=self.palette["accent"] if selected else self.palette["text"],
                         weight=ft.FontWeight.W_500),
                    _txt(subtitle.strip(), self.palette, muted=True),
                ], spacing=SPACING["xs"], expand=True),
                    ft.Icon(ft.Icons.CHECK if selected else ft.Icons.CIRCLE_OUTLINED,
                            color=self.palette["accent"] if selected else self.palette["muted"]),
                ]),
                bgcolor=self.palette["quote_strip"] if selected else self.palette["card"],
                border=ft.Border.all(1, self.palette["accent"] if selected else self.palette["track"]),
                border_radius=16, padding=12,
                on_click=lambda event, selected_value=value: self._select_editor_activity(selected_value),
            ))
        self.page.show_dialog(ft.BottomSheet(
            content=ft.Container(content=ft.Column(controls=[
                _txt("How active are you?", self.palette, size=FONT_SIZES["title"]),
                _txt("Pick the one that fits most weeks. Don't count today's workout separately.",
                     self.palette, muted=True),
                *choices,
            ], spacing=SPACING["sm"], scroll=ft.ScrollMode.HIDDEN),
                bgcolor=self.palette["surface"], padding=SPACING["page"]),
            bgcolor=self.palette["surface"], show_drag_handle=True, dismissible=True,
        ))

    def _select_editor_activity(self, value):
        self.profile_activity_choice = value
        question = next(q for q in QUESTIONS if q["key"] == "activity_level")
        label = next(text for key, text in question["choices"] if key == value)
        title, subtitle = label.split(":", 1)
        self.profile_activity_text.value = title
        self.profile_activity_hint.value = subtitle.strip()
        self.page.pop_dialog()
        self.page.update()

    def _set_pace_visibility(self, control, goal):
        control.visible = goal in ("lose", "gain")
        self.page.update()

    @staticmethod
    def _optional_number(value):
        return None if value is None or not str(value).strip() else float(value)

    def _save_profile_editor(self, goal, pace):
        fields = self.profile_fields
        try:
            person = Person(
                name=(fields["name"].value or "Me").strip() or "Me",
                age=int(fields["age"].value), sex=self.profile_sex_choice,
                weight_kg=to_kg(float(fields["weight"].value), self.pending_weight_unit),
                height_cm=float(fields["height"].value),
                activity_level=self.profile_activity_choice, goal=goal.value, pace=pace.value,
                goal_weight_kg=(None if not (fields["goal_weight"].value or "").strip()
                                else to_kg(float(fields["goal_weight"].value), self.pending_weight_unit)),
                custom_calorie_target=self._optional_number(fields["calories"].value),
                custom_protein_target=self._optional_number(fields["protein"].value),
                custom_carbs_target=self._optional_number(fields["carbs"].value),
                custom_fat_target=self._optional_number(fields["fat"].value),
            )
            self.storage.set_profile(person)
            self.profile_editing = False
            self.profile_editor_message.value = ""
            self.render()
        except (ValueError, TypeError) as exc:
            self.profile_editor_message.value = str(exc)
            self.page.update()

    def _cancel_profile_editor(self, event=None):
        self.profile_editing = False
        self.render()

    def _backup_directory(self):
        return Path(getattr(self, "backup_directory", Path.home() / "Downloads" / "CalorieTracker"))

    async def _backup_action(self, event=None):
        if not self.is_android:
            self._backup_data(event)
            return
        try:
            self.storage.save()
            payload = Path(self.storage.path).read_bytes()
            name = f"calorie_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            saved = await self.file_picker.save_file(
                dialog_title="Save calorie tracker backup", file_name=name,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"], src_bytes=payload,
            )
        except (OSError, ValueError, TypeError) as exc:
            self._info_dialog("Back up data", f"The backup could not be saved.\n\n{exc}")
            return
        if saved:
            self._info_dialog("Back up data", "Your JSON backup was saved.")

    async def _restore_action(self, event=None):
        if not self.is_android:
            self._restore_backup(event)
            return
        try:
            files = await self.file_picker.pick_files(
                dialog_title="Choose a calorie tracker backup", allow_multiple=False,
                with_data=True, file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
            )
            if not files:
                return
            selected = files[0]
            payload = selected.bytes
            if payload is None and selected.path:
                payload = Path(selected.path).read_bytes()
            if payload is None:
                raise ValueError("The selected file could not be read. Please choose a JSON backup again.")
            staged = Path(self.storage.path + ".picked_backup")
            staged.write_bytes(payload)
            self._picked_backup_path = staged
            self._show_restore_confirmation(staged, selected.name)
        except (OSError, ValueError, TypeError) as exc:
            self._info_dialog("Restore backup", f"Could not open that backup. Your current data was kept.\n\n{exc}")

    def _show_restore_confirmation(self, path, display_name):
        def cancel_restore(event=None):
            self.page.pop_dialog()
            picked = getattr(self, "_picked_backup_path", None)
            if picked and Path(picked).exists():
                Path(picked).unlink(missing_ok=True)
                self._picked_backup_path = None

        def restore_now(event=None):
            self.page.pop_dialog()
            try:
                safety_copy = self.storage.restore_from(path)
            except (OSError, ValueError, TypeError) as exc:
                self._info_dialog("Restore backup", f"The backup was not restored. Your current data was kept.\n\n{exc}")
                return
            self.pending_weight_unit = self.storage.preferences.get("weight_unit", "kg")
            self.pending_theme = self.storage.preferences.get("theme", "dark")
            self.palette = palette_for(self.pending_theme)
            self.page.theme_mode = ft.ThemeMode.DARK if self.pending_theme == "dark" else ft.ThemeMode.LIGHT
            picked = getattr(self, "_picked_backup_path", None)
            if picked and Path(picked).exists():
                Path(picked).unlink(missing_ok=True)
                self._picked_backup_path = None
            self.stats_reference_date = latest_food_log_date(self.storage, date.today())
            self.setup_mode = self.storage.profile is None
            self.setup_stage = "welcome" if self.setup_mode else "questions"
            self._info_dialog("Restore backup", "Backup restored successfully.\n"
                              + (f"A safety copy was kept at:\n{safety_copy}" if safety_copy else ""))
            self.render()

        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=f"Restore {display_name}?",
            content=ft.Text("This replaces the current tracker data. The app will keep a safety copy automatically."),
            actions=[ft.TextButton("Cancel", on_click=cancel_restore),
                     ft.FilledButton("Restore", on_click=restore_now,
                                     bgcolor=self.palette["accent"], color=self.palette["accent_text"])],
        ))

    def _backup_data(self, event=None):
        try:
            folder = self._backup_directory()
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"calorie_tracker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            self.storage.save()
            shutil.copy2(self.storage.path, path)
        except (OSError, ValueError) as exc:
            self._info_dialog("Back up data", f"The backup could not be saved.\n\n{exc}")
            return
        self._info_dialog("Back up data", f"Your data backup was saved to:\n{path}")

    def _restore_backup(self, event=None):
        try:
            backups = sorted(self._backup_directory().glob("calorie_tracker_backup_*.json"), reverse=True)
        except OSError as exc:
            self._info_dialog("Restore backup", f"Could not open the backups folder.\n\n{exc}")
            return
        if not backups:
            self._info_dialog("Restore backup", "No backups were found in Downloads/CalorieTracker yet.")
            return

        def confirm_restore(path):
            self.page.pop_dialog()
            def restore_now(event=None):
                self.page.pop_dialog()
                try:
                    safety_copy = self.storage.restore_from(path)
                except (OSError, ValueError, TypeError) as exc:
                    self._info_dialog("Restore backup", f"The backup was not restored. Your current data was kept.\n\n{exc}")
                    return
                self.pending_weight_unit = self.storage.preferences.get("weight_unit", "kg")
                self.pending_theme = self.storage.preferences.get("theme", "dark")
                self.palette = palette_for(self.pending_theme)
                self.page.theme_mode = ft.ThemeMode.DARK if self.pending_theme == "dark" else ft.ThemeMode.LIGHT
                self.stats_reference_date = latest_food_log_date(self.storage, date.today())
                self.setup_mode = self.storage.profile is None
                self.setup_stage = "welcome" if self.setup_mode else "questions"
                self._info_dialog("Restore backup", "Backup restored successfully.\n"
                                  + (f"A safety copy was kept at:\n{safety_copy}" if safety_copy else ""))
                self.render()

            self.page.show_dialog(ft.AlertDialog(
                modal=True, title="Restore this backup?",
                content=ft.Text("This replaces the current tracker data. The app will keep a safety copy automatically."),
                actions=[ft.TextButton("Cancel", on_click=lambda event: self.page.pop_dialog()),
                         ft.FilledButton("Restore", on_click=restore_now,
                                         bgcolor=self.palette["accent"], color=self.palette["accent_text"])],
            ))

        sheet = ft.BottomSheet(
            content=ft.Column(controls=[
                _txt("Choose a backup", self.palette, size=FONT_SIZES["title"]),
                *[ft.ListTile(title=path.name, leading=ft.Icons.INSERT_DRIVE_FILE,
                              on_click=lambda event, selected=path: confirm_restore(selected))
                  for path in backups],
            ], tight=True, scroll=ft.ScrollMode.HIDDEN),
            bgcolor=self.palette["surface"], show_drag_handle=True, dismissible=True,
        )
        self.page.show_dialog(sheet)

    def _on_tab_change(self, event):
        self.selected_tab = event.control.selected_index
        self.render()

    def _shift_day(self, amount: int):
        self.selected_date += timedelta(days=amount)
        self.render()

    def _shift_calendar_month(self, amount: int):
        month_index = self.calendar_month_ref.month - 1 + amount
        year = self.calendar_month_ref.year + month_index // 12
        month = month_index % 12 + 1
        day = min(self.selected_date.day, calendar.monthrange(year, month)[1])
        self.calendar_month_ref = date(year, month, 1)
        self.selected_date = date(year, month, day)
        self.render()

    def _select_calendar_day(self, selected_date: date):
        self.selected_date = selected_date
        self.calendar_month_ref = selected_date.replace(day=1)
        self.render()

    def _open_calendar_day_in_log(self, event=None):
        self.selected_tab = 0
        self.render()

    def _on_stats_kind_change(self, event):
        if isinstance(event, str):
            self.stat_kind = event
            self.render()
            return
        selected = event.control.selected
        if selected:
            self.stat_kind = selected[0]
            self.render()

    def _shift_stats_period(self, amount: int):
        reference = self.stats_reference_date
        if self.stat_kind == "day":
            reference += timedelta(days=amount)
        elif self.stat_kind == "week":
            reference += timedelta(days=7 * amount)
        else:
            month_index = reference.month - 1 + amount
            year = reference.year + month_index // 12
            month = month_index % 12 + 1
            day = min(reference.day, calendar.monthrange(year, month)[1])
            reference = date(year, month, day)
        self.stats_reference_date = reference
        self.render()

    def _open_add_sheet(self, event=None):
        def choose(callback):
            self.page.pop_dialog()
            callback()

        sheet = ft.BottomSheet(
            content=ft.Column(controls=[
                ft.ListTile(leading=ft.Icons.RESTAURANT, title="Add food",
                            on_click=lambda event: choose(self._add_food_dialog)),
                ft.ListTile(leading=ft.Icons.DIRECTIONS_RUN, title="Add exercise",
                            on_click=lambda event: choose(self._add_exercise_dialog)),
            ], tight=True),
            bgcolor=self.palette["surface"], show_drag_handle=True, dismissible=True,
        )
        self.page.show_dialog(sheet)

    def _open_calculations(self, event=None):
        person = (self.storage.person_on(date.today()) if self.storage.profile else None) or self.storage.profile
        if person is None and self.setup_mode:
            person = self.setup_person
        paragraphs = calculation_explanation(person)
        if person:
            targets = calculate_targets(person)
            factor = ACTIVITY_LEVELS[person.activity_level.lower()]
            if person.goal == "lose":
                adjustment = -PACE_ADJUSTMENT[person.pace]
            elif person.goal == "gain":
                adjustment = PACE_ADJUSTMENT[person.pace]
            else:
                adjustment = 0
            goal_label = person.goal.replace("_", " ").title()
            if person.custom_calorie_target is not None:
                goal_label = "Custom target"
                goal_value = "Set in your profile"
            else:
                goal_value = f"{adjustment:+,} kcal"
            rows = [
                ("1. BMR (at rest)", f"{calculate_bmr(person):,.0f} kcal"),
                (f"2. × {person.activity_level.replace('_', ' ')} activity ({factor:g})",
                 f"{calculate_tdee(person):,.0f} kcal TDEE"),
                (f"3. Goal: {goal_label}", goal_value),
                ("Daily target", f"{targets['calories']:,} kcal"),
            ]
            calculation_rows = [_card(ft.Row(controls=[
                _txt(label, self.palette, size=FONT_SIZES["body"], muted=True),
                _txt(value, self.palette, size=FONT_SIZES["body"]),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN, wrap=True), self.palette, padding=SPACING["sm"])
                for label, value in rows]
            macro_line = _txt(
                f"Macros: P {targets['protein_g']:g} g · C {targets['carbs_g']:g} g · F {targets['fat_g']:g} g",
                self.palette, size=FONT_SIZES["body"], muted=True)
        else:
            targets = None
            calculation_rows = [_card(_txt("Set up a profile to see your personalized calorie calculation.",
                                           self.palette, muted=True), self.palette)]
            macro_line = _txt("Nutrition targets will appear after profile setup.", self.palette, muted=True)

        details = ft.Column(controls=[_txt(line, self.palette, size=FONT_SIZES["small"], muted=True)
                                      for line in paragraphs], spacing=SPACING["sm"], visible=False)
        more_button = ft.TextButton("More about these estimates", on_click=lambda event: self._toggle_calc_details(details, more_button),
                                    style=ft.ButtonStyle(color=self.palette["muted"]))
        sheet = ft.BottomSheet(
            content=ft.Container(content=ft.Column(controls=[
                _txt("How is this calculated?", self.palette, size=FONT_SIZES["title"]),
                *calculation_rows,
                macro_line,
                _txt("Estimates only. Not medical advice.", self.palette,
                     size=FONT_SIZES["small"], muted=True),
                more_button, details,
                ft.FilledButton("Got it", on_click=lambda event: self.page.pop_dialog(),
                                bgcolor=self.palette["accent"], color=self.palette["accent_text"],
                                expand=True),
            ], spacing=SPACING["tight"], scroll=ft.ScrollMode.HIDDEN),
                padding=SPACING["page"], width=390),
            bgcolor=self.palette["surface"], show_drag_handle=True,
            scrollable=True, dismissible=True,
        )
        self.page.show_dialog(sheet)

    def _toggle_calc_details(self, details, button, event=None):
        details.visible = not details.visible
        button.content = "Less about these estimates" if details.visible else "More about these estimates"
        self.page.update()

    def _copy_yesterday(self, event=None):
        source_date = self.selected_date - timedelta(days=1)
        source = self.storage.logs.get(source_date)
        if not source or not source.foods:
            self._info_dialog("Copy yesterday", "There are no food entries from yesterday to copy.")
            return
        target = self.storage.get_log(self.selected_date)
        target.foods.extend(type(food)(**food.__dict__) for food in source.foods)
        self.storage.save()
        self.render()

    def _duplicate_food(self, index):
        log = self.storage.logs.get(self.selected_date)
        if log and 0 <= index < len(log.foods):
            entry = log.foods[index]
            log.foods.insert(index + 1, type(entry)(**entry.__dict__))
            self.storage.save()
            self.render()

    def _edit_food_dialog(self, index):
        log = self.storage.logs.get(self.selected_date)
        if not log or not (0 <= index < len(log.foods)):
            return
        original = log.foods[index]
        grams = self._field("Amount (grams)", f"{original.grams:g}", ft.KeyboardType.NUMBER)
        meal = ft.Dropdown(label="Meal", value=original.meal,
                           options=[ft.DropdownOption(key=value, text=value.title()) for value in MEALS])
        message = _txt("Change the amount or meal for this entry.", self.palette,
                       size=FONT_SIZES["small"], muted=True)

        def submit(event):
            try:
                replacement = make_food_entry(
                    original.name, grams.value, original.calories_per_100g,
                    original.protein_per_100g, original.carbs_per_100g,
                    original.fat_per_100g, meal.value,
                )
                self.storage.logs[self.selected_date].foods[index] = replacement
                self.storage.save()
                self.page.pop_dialog()
                self.render()
            except (ValueError, TypeError) as exc:
                message.value = str(exc)
                self.page.update()

        self.page.show_dialog(ft.AlertDialog(
            modal=True,
            title=f"Edit {original.name}",
            content=ft.Column(controls=[
                _txt(f"{original.calories_per_100g:g} kcal per 100 g", self.palette,
                     size=FONT_SIZES["small"], muted=True),
                grams, meal, message,
            ], tight=True, spacing=SPACING["tight"], width=340),
            actions=[ft.TextButton("Cancel", on_click=lambda event: self.page.pop_dialog()),
                     ft.FilledButton("Save changes", on_click=submit,
                                     bgcolor=self.palette["accent"], color=self.palette["accent_text"])],
            actions_alignment=ft.MainAxisAlignment.END,
        ))

    def _export_stats_csv(self, event=None):
        if not self.storage.profile:
            self._info_dialog("Export CSV", "Set up a profile in the desktop app before exporting a stats report.")
            return
        data = stats_dashboard(self.storage, self.stats_reference_date, self.stat_kind)
        targets = {record["day"]: record["target"] for record in data["records"]}
        file_name = f"calorie_tracker_{self.stat_kind}_{data['start'].isoformat()}_{data['end'].isoformat()}.csv"
        try:
            export_folder = Path(getattr(self, "export_directory", Path.home() / "Downloads" / "CalorieTracker"))
            export_folder.mkdir(parents=True, exist_ok=True)
            path = write_csv(export_folder / file_name,
                             period_csv_rows(data["records"], targets))
        except (OSError, ValueError) as exc:
            self._info_dialog("Export CSV", f"Could not save the report: {exc}")
            return
        self._info_dialog("Export CSV", f"Stats report saved to:\n{path}")

    async def _export_stats_csv_action(self, event=None):
        if not self.is_android:
            self._export_stats_csv(event)
            return
        if not self.storage.profile:
            self._info_dialog("Export CSV", "Set up a profile before exporting a stats report.")
            return
        data = stats_dashboard(self.storage, self.stats_reference_date, self.stat_kind)
        targets = {record["day"]: record["target"] for record in data["records"]}
        filename = (f"calorie_tracker_{self.stat_kind}_{data['start'].isoformat()}_"
                    f"{data['end'].isoformat()}.csv")
        try:
            saved = await self.file_picker.save_file(
                dialog_title="Save calorie report", file_name=filename,
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["csv"],
                src_bytes=period_csv_bytes(data["records"], targets),
            )
        except (OSError, ValueError, TypeError) as exc:
            self._info_dialog("Export CSV", f"Could not save the report.\n\n{exc}")
            return
        if saved:
            self._info_dialog("Export CSV", "Your CSV report was saved.")

    def _field(self, label, value="", keyboard_type=None, helper_text=None):
        return ft.TextField(label=label, value=value, keyboard_type=keyboard_type,
                            helper=helper_text, border_radius=RADIUS["button"],
                            height=TEXT_FIELD_HEIGHT)

    def _add_food_dialog(self, event=None):
        selected = {"food": None, "unit": "grams", "meal": default_meal()}
        amount = self._field("Amount", "100", ft.KeyboardType.NUMBER)
        amount.width = 96
        search = ft.TextField(hint_text="Search food", prefix_icon=ft.Icons.SEARCH,
                              filled=True, fill_color=self.palette["card"],
                              border=ft.NoInputBorder(), border_radius=24,
                              on_change=None)
        results = ft.Column(spacing=SPACING["xs"], tight=True)
        unit_choices = ft.Row(spacing=SPACING["sm"], scroll=ft.ScrollMode.HIDDEN, expand=True)
        meals = ft.Row(spacing=SPACING["sm"], wrap=True)
        estimate = _txt("Choose a food to see the calorie estimate.", self.palette,
                        size=FONT_SIZES["body"], color=self.palette["accent"])
        status = _txt("Nutrition values are typical estimates. Check the package when available.",
                      self.palette, size=FONT_SIZES["small"], muted=True)
        add_button = ft.FilledButton("Add food",
                                     on_click=None, expand=True,
                                     bgcolor=self.palette["accent"], color=self.palette["accent_text"])

        def current_grams():
            item = selected["food"]
            if not item:
                raise ValueError("Search for a food and choose it from the list.")
            quantity = float(amount.value)
            if selected["unit"] == "grams":
                return grams_for(quantity)
            return grams_for(quantity, item.servings[selected["unit"]])

        def update_estimate(event=None):
            item = selected["food"]
            if not item:
                estimate.value = "Choose a food to see the calorie estimate."
                add_button.content = "Add food"
                self.page.update()
                return
            try:
                grams = current_grams()
                kcal = grams * item.calories_per_100g / 100
                estimate.value = f"About {round(kcal):,} kcal · {grams:g} g"
                add_button.content = f"Add food · {round(kcal):,} kcal"
                status.value = "Nutrition values are estimates. Check the package when available."
            except (ValueError, TypeError, KeyError):
                estimate.value = "Enter a valid amount to see the calorie estimate."
                add_button.content = "Add food"
            self.page.update()

        def select_unit(unit):
            selected["unit"] = unit
            amount.value = "100" if unit == "grams" else "1"
            refresh_units()
            update_estimate()

        def refresh_units():
            item = selected["food"]
            options = [("grams", "grams")]
            if item:
                options.extend((label, label) for label in item.servings)
            unit_choices.controls = [
                ft.Container(
                    content=_txt(label, self.palette, size=FONT_SIZES["small"],
                                 color=self.palette["accent_text"] if unit == selected["unit"] else self.palette["text"]),
                    padding=ft.Padding(12, 8, 12, 8), border_radius=20,
                    bgcolor=self.palette["accent"] if unit == selected["unit"] else self.palette["track"],
                    on_click=lambda event, value=unit: select_unit(value),
                ) for unit, label in options
            ]

        def choose_meal(meal):
            selected["meal"] = meal
            refresh_meals()

        def refresh_meals():
            meal_labels = {"breakfast": "Breakfast", "lunch": "Lunch",
                           "snacks": "Snacks", "dinner": "Dinner"}
            meals.controls = [
                ft.Container(
                    content=_txt(label, self.palette, size=FONT_SIZES["small"],
                                 color=self.palette["accent_text"] if key == selected["meal"] else self.palette["text"]),
                    padding=ft.Padding(12, 8, 12, 8), border_radius=18,
                    bgcolor=self.palette["accent"] if key == selected["meal"] else self.palette["track"],
                    on_click=lambda event, value=key: choose_meal(value),
                ) for key, label in meal_labels.items()
            ]

        def choose_food(item):
            selected["food"] = item
            selected["unit"] = "grams"
            amount.value = "100"
            refresh_units()
            refresh_results()
            update_estimate()

        def toggle_favorite(item):
            self.storage.toggle_favorite(item.name)
            self.storage.save()
            refresh_results()

        def refresh_results(event=None):
            query = (search.value or "").strip()
            if query:
                found = self.storage.food_db.search(query, limit=6)
            else:
                found = self.storage.food_db.suggestions(self.storage.favorites,
                                                         self.storage.recents)
                if not found:
                    found = [self.storage.food_db.get(name) for name in
                             ("Yogurt / curd, plain", "Apple", "Rice, white, cooked",
                              "Banana", "Roti / chapati (whole wheat)")]
                    found = [item for item in found if item]
            results.controls = []
            if not found:
                results.controls.append(_txt("No matches. Try another name or choose Custom food.",
                                             self.palette, size=FONT_SIZES["small"], muted=True))
            for item in found:
                is_selected = selected["food"] is item
                favorite_button = ft.IconButton(
                    icon=ft.Icons.STAR if self.storage.is_favorite(item.name) else ft.Icons.STAR_OUTLINE,
                    icon_color=self.palette["accent"] if self.storage.is_favorite(item.name) else self.palette["muted"],
                    tooltip="Remove favorite" if self.storage.is_favorite(item.name) else "Add favorite",
                    on_click=lambda event, choice=item: toggle_favorite(choice),
                    width=36, height=40,
                )
                results.controls.append(ft.Container(
                    content=ft.Row(controls=[
                        favorite_button,
                        ft.Column(controls=[
                            _txt(item.name, self.palette, size=FONT_SIZES["body"]),
                            _txt(f"{item.calories_per_100g:g} kcal per 100 g" +
                                 (" · Your food" if item.custom else ""),
                                 self.palette, size=FONT_SIZES["small"], muted=True),
                        ], spacing=0, expand=True),
                    ], spacing=SPACING["xs"]),
                    padding=ft.Padding(4, 2, 8, 2), border_radius=RADIUS["chip"],
                    bgcolor=self.palette["track"] if is_selected else None,
                    on_click=lambda event, choice=item: choose_food(choice),
                ))
            if getattr(self, "_food_sheet_open", False):
                self.page.update()

        def add_food(event=None):
            try:
                item = selected["food"]
                grams = current_grams()
                entry = make_food_entry(item.name, grams, item.calories_per_100g,
                                        item.protein_per_100g, item.carbs_per_100g,
                                        item.fat_per_100g, selected["meal"])
                self.storage.get_log(self.selected_date).foods.append(entry)
                self.storage.record_recent(item.name)
                self.storage.save()
                self.page.pop_dialog()
                self.render()
            except (ValueError, TypeError, KeyError) as exc:
                status.value = str(exc) or "Choose a food and enter a valid amount."
                self.page.update()

        add_button.on_click = add_food
        amount.on_change = update_estimate
        search.on_change = refresh_results
        refresh_units()
        refresh_meals()
        sheet = ft.BottomSheet(
            content=ft.Container(content=ft.Column(controls=[
                search, results,
                _txt("Amount", self.palette, size=FONT_SIZES["small"], muted=True),
                ft.Row(controls=[amount, unit_choices], vertical_alignment=ft.CrossAxisAlignment.CENTER),
                _txt("Meal", self.palette, size=FONT_SIZES["small"], muted=True),
                meals, estimate, status, add_button,
                ft.TextButton("Custom food", on_click=lambda event: open_custom_food()),
            ], spacing=SPACING["tight"], scroll=ft.ScrollMode.HIDDEN,
               horizontal_alignment=ft.CrossAxisAlignment.STRETCH),
                bgcolor=self.palette["surface"], padding=SPACING["page"],
                border_radius=ft.BorderRadius(20, 20, 0, 0)),
            bgcolor=self.palette["surface"], show_drag_handle=True,
            scrollable=True, dismissible=True,
        )
        self.page.show_dialog(sheet)
        self._food_sheet_open = True
        refresh_results()

        def _finish_food_sheet(event=None):
            self._food_sheet_open = False

        sheet.on_dismiss = _finish_food_sheet

        def open_custom_food():
            self.page.pop_dialog()
            self._food_sheet_open = False
            self._custom_food_dialog()

    def _custom_food_dialog(self, event=None):
        name = self._field("Food name")
        amount = self._field("Amount (grams)", "100", ft.KeyboardType.NUMBER)
        calories = self._field("Calories per 100 g", keyboard_type=ft.KeyboardType.NUMBER)
        protein = self._field("Protein per 100 g", "0", ft.KeyboardType.NUMBER)
        carbs = self._field("Carbs per 100 g", "0", ft.KeyboardType.NUMBER)
        fat = self._field("Fat per 100 g", "0", ft.KeyboardType.NUMBER)
        meal = ft.Dropdown(label="Meal", value=default_meal(),
                           options=[ft.DropdownOption(key=value, text=value.title()) for value in MEALS])
        message = _txt("Use the package values per 100 g. This food will be saved for next time.",
                       self.palette, size=FONT_SIZES["small"], muted=True)

        def save_custom_food(event=None):
            try:
                item = FoodItem(name.value, float(calories.value), float(protein.value or 0),
                                float(carbs.value or 0), float(fat.value or 0), custom=True)
                entry = item.to_entry(float(amount.value), meal.value)
                self.storage.add_custom_food(item)
                self.storage.get_log(self.selected_date).foods.append(entry)
                self.storage.record_recent(item.name)
                self.storage.save()
                self.page.pop_dialog()
                self.render()
            except (ValueError, TypeError) as exc:
                message.value = str(exc)
                self.page.update()

        sheet = ft.BottomSheet(
            content=ft.Container(content=ft.Column(controls=[
                _txt("Add a custom food", self.palette, size=FONT_SIZES["title"]),
                name, amount, meal, calories, protein, carbs, fat, message,
                ft.FilledButton("Save and add food", on_click=save_custom_food,
                                bgcolor=self.palette["accent"], color=self.palette["accent_text"],
                                expand=True),
            ], spacing=SPACING["tight"], scroll=ft.ScrollMode.HIDDEN),
                bgcolor=self.palette["surface"], padding=SPACING["page"]),
            bgcolor=self.palette["surface"], show_drag_handle=True,
            scrollable=True, dismissible=True,
        )
        self.page.show_dialog(sheet)

    def _add_exercise_dialog(self, event=None):
        person = self.storage.person_on(self.selected_date) or self.storage.profile
        if person is None:
            self._info_dialog("Add exercise", "Set up a profile in the desktop app before logging exercise. The estimate uses the profile weight.")
            return
        activity_options = [ft.DropdownOption(key=activity.name, text=activity.name)
                            for activity in EXERCISES]
        activity_options.append(ft.DropdownOption(key="Other", text="Other (enter calories)"))
        activity = ft.Dropdown(label="Activity", value="Walking", options=activity_options,
                               enable_filter=True, editable=True)
        intensity = ft.Dropdown(label="Effort", value="moderate",
                                options=[ft.DropdownOption(key=level, text=level.title())
                                         for level in INTENSITIES])
        minutes = self._field("Duration (minutes)", keyboard_type=ft.KeyboardType.NUMBER)
        manual = self._field("Calories burned (if you already know it)",
                             keyboard_type=ft.KeyboardType.NUMBER)
        manual.visible = False
        preview = _txt("Calories are an estimate based on activity, effort and profile weight.",
                       self.palette, size=FONT_SIZES["small"], muted=True)
        message = _txt("", self.palette, size=FONT_SIZES["small"], muted=True)

        def update_estimate(change=None):
            is_manual = activity.value == "Other"
            manual.visible = is_manual
            if is_manual:
                preview.value = "Other activities use the calorie value you enter."
            else:
                try:
                    estimated = make_exercise_entry(activity.value, minutes.value or 30,
                                                    person.weight_kg, intensity.value).calories_burned
                    preview.value = f"Estimated burn: about {round(estimated):,} kcal"
                except (ValueError, TypeError):
                    preview.value = "Enter the duration to see an estimate."
            self.page.update()

        activity.on_select = update_estimate
        intensity.on_select = update_estimate
        minutes.on_change = update_estimate

        def submit(change):
            try:
                entry = make_exercise_entry(
                    activity.value, minutes.value, person.weight_kg, intensity.value,
                    manual.value if activity.value == "Other" else None,
                )
                self.storage.get_log(self.selected_date).exercises.append(entry)
                self.storage.save()
                self.page.pop_dialog()
                self.render()
            except (ValueError, TypeError) as exc:
                message.value = str(exc)
                self.page.update()

        dialog = ft.AlertDialog(
            modal=True,
            title="Add exercise",
            content=ft.Column(controls=[
                activity, intensity, minutes, manual, preview, message,
                _txt("Exercise calories are estimates and are added to the daily burn figure.",
                     self.palette, size=FONT_SIZES["small"], muted=True),
            ], tight=True, scroll=ft.ScrollMode.HIDDEN, width=CONTENT_MAX_WIDTH, spacing=SPACING["sm"]),
            actions=[ft.TextButton("Cancel", on_click=lambda change: self.page.pop_dialog()),
                     ft.FilledButton("Add to day", on_click=submit,
                                     bgcolor=self.palette["accent"], color=self.palette["accent_text"])],
            actions_alignment=ft.MainAxisAlignment.END,
        )
        update_estimate()
        self.page.show_dialog(dialog)

    def _info_dialog(self, title, message):
        self.page.show_dialog(ft.AlertDialog(
            modal=True, title=title,
            content=ft.Text(message, color=self.palette["text"]),
            actions=[ft.TextButton("Close", on_click=lambda event: self.page.pop_dialog())],
        ))

    def _remove_entry(self, kind, index):
        log = self.storage.logs.get(self.selected_date)
        entries = getattr(log, kind, None) if log else None
        if entries is not None and 0 <= index < len(entries):
            entries.pop(index)
            self.storage.save()
            self.render()

    def _screen(self):
        if self.selected_tab == 0:
            data = log_dashboard(self.storage, self.selected_date)
            log = self.storage.logs.get(self.selected_date) or DailyLog(log_date=self.selected_date)
            return build_log_screen(
                data, self.palette,
                on_previous=lambda event: self._shift_day(-1),
                on_next=lambda event: self._shift_day(1),
                log=log,
                on_remove_food=lambda index: self._remove_entry("foods", index),
                on_remove_exercise=lambda index: self._remove_entry("exercises", index),
                on_edit_food=self._edit_food_dialog,
                on_duplicate_food=self._duplicate_food,
                on_copy_yesterday=self._copy_yesterday,
                on_calculations=self._open_calculations,
            )
        if self.selected_tab == 1:
            data = calendar_month(self.storage, self.calendar_month_ref, self.selected_date)
            return build_calendar_screen(
                data, self.palette,
                on_previous=lambda event: self._shift_calendar_month(-1),
                on_next=lambda event: self._shift_calendar_month(1),
                on_select_day=self._select_calendar_day,
                on_open_log=self._open_calendar_day_in_log,
            )
        if self.selected_tab == 2:
            data = stats_dashboard(self.storage, self.stats_reference_date, self.stat_kind)
            return build_stats_screen(
                data, self.palette, self.stat_kind,
                on_kind_change=self._on_stats_kind_change,
                on_previous=lambda event: self._shift_stats_period(-1),
                on_next=lambda event: self._shift_stats_period(1),
                on_export=self._export_stats_csv_action,
            )
        if self.selected_tab == 3:
            return self._weight_screen()
        if self.selected_tab == 4:
            if self.profile_editing:
                return self._profile_editor_screen()
            return build_settings_screen({
                "profile": self.storage.profile,
                "weight_unit": self.pending_weight_unit,
                "theme": self.pending_theme,
            }, self.palette,
                on_weight_unit=self._set_pending_weight_unit,
                on_theme=self._set_pending_theme,
                on_save=self._save_settings,
                on_edit_profile=self._open_profile_editor,
                on_backup=self._backup_action,
                on_restore=self._restore_action,
                on_calculations=self._open_calculations,
                backup_help=("Choose where to save or restore a JSON backup on this device. "
                             "CSV reports can also be saved with the device file chooser. "
                             "Height stays in cm; food amounts stay in grams."
                             if self.is_android else None),
            )
        return ft.Column(expand=True)

    def _open_profile_editor(self, event=None):
        if not self.storage.profile:
            self.setup_mode = True
            self.setup_stage = "welcome"
            self.render()
            return
        self.profile_editing = True
        self.render()

    def render(self):
        in_setup = self.setup_mode
        editing_profile = self.profile_editing and not in_setup
        if in_setup or editing_profile:
            self.page.navigation_bar = None
            self.page.floating_action_button = None
            if self.setup_stage == "welcome":
                view = self._welcome_screen()
            elif self.setup_stage == "summary":
                view = self._plan_summary_screen()
            elif in_setup:
                self.setup_inputs = {}
                view = self._question_screen()
            else:
                view = self._profile_editor_screen()
        else:
            self.page.navigation_bar = navigation_bar(self.palette, self.selected_tab, self._on_tab_change)
            self.page.floating_action_button = (
                ft.FloatingActionButton(icon=ft.Icons.ADD, tooltip="Add food or exercise",
                                         on_click=self._open_add_sheet, bgcolor=self.palette["accent"],
                                         foreground_color=self.palette["accent_text"])
                if self.selected_tab == 0 else None
            )
            data = log_dashboard(self.storage, self.selected_date)
            screen = self._screen()
            if isinstance(getattr(screen, "controls", None), list):
                # End space lives INSIDE the scrolling content, so the scroll area itself
                # reaches the tab bar and the last element can scroll fully into view.
                screen.controls.append(ft.Container(
                    height=FAB_CLEARANCE if self.selected_tab == 0 else BOTTOM_SPACE))
            view = ft.Column(controls=[
                quote_strip(data["quote"], self.palette),
                ft.Container(content=screen, expand=True,
                             padding=ft.Padding(SPACING["page"], SPACING["xs"], SPACING["page"], 0),
                             bgcolor=self.palette["background"]),
            ], spacing=0, expand=True)

        # Respect OS cutouts/system bars. One plain container: no row that could add a
        # second scroll area or an unbounded height.
        view = ft.SafeArea(
            content=ft.Container(content=view, expand=True),
            expand=True,
            minimum_padding=SPACING["page"],
            avoid_intrusions_top=True,
            avoid_intrusions_bottom=True,
        )
        self._screen_serial += 1
        view.key = f"surface-{self._screen_serial}"
        if self._switcher is None:
            self.page.controls.clear()
            self._switcher = ft.AnimatedSwitcher(
                content=view, duration=240, reverse_duration=180,
                transition=ft.AnimatedSwitcherTransition.FADE,
                switch_in_curve=ft.AnimationCurve.EASE_OUT,
                switch_out_curve=ft.AnimationCurve.EASE_IN,
                expand=True,
            )
            self.page.add(self._switcher)
        else:
            self._switcher.content = view
        self.page.update()
