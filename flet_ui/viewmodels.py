"""Plain-data view models for Flet screens; calculations stay in the existing engine."""

import calendar
from datetime import date

import stats
from calorie_engine import (
    ACTIVITY_LEVELS, BASELINE_MULTIPLIER, MIN_CALORIES, PACE_ADJUSTMENT, DailyLog,
    Person, calculate_bmr, calculate_daily_summary, calculate_food_totals,
    calculate_targets, calculate_tdee,
)


def _macro_row(label, value, target):
    value = round(value)
    target = round(target)
    if value > target:
        status = f"{value - target} g over target"
    else:
        status = f"{target - value} g remaining"
    return {
        "label": label,
        "value": value,
        "target": target,
        "fraction": stats.progress_fraction(value, target),
        "value_text": f"{value} / {target} g",
        "status": status,
    }


def log_dashboard(storage, selected_date: date, today: date | None = None) -> dict:
    """Create all values used by Phase 26's Log progress screen without changing storage."""
    today = today or date.today()
    quote = stats.quote_for(selected_date)
    # Use a portable day-number format that works on Windows and Android.
    label = "Today" if selected_date == today else f"{selected_date.strftime('%a')}, {selected_date.day} {selected_date.strftime('%b')}"
    result = {
        "selected_date": selected_date,
        "day_label": label,
        "quote": quote,
        "has_profile": bool(storage.profile),
        "consumed": 0,
        "burned": 0,
        "balance": 0,
        "target": 0,
        "remaining": 0,
        "remaining_text": "Set up your profile to see your target",
        "remaining_label": "Remaining",
        "remaining_amount": 0,
        "calorie_fraction": 0.0,
        "macros": [],
        "goal_label": "",
        "floor_applied": False,
        "below_minimum_custom_target": False,
    }
    if not storage.profile:
        return result

    person = storage.person_on(selected_date) or storage.profile
    log = storage.logs.get(selected_date) or DailyLog(log_date=selected_date)
    summary = calculate_daily_summary(person, log)
    targets = calculate_targets(person)
    consumed = round(summary["calories_consumed"])
    target = targets["calories"]
    remaining = target - consumed
    result.update({
        "consumed": consumed,
        "burned": round(summary["calories_burned"]),
        "balance": round(summary["calorie_balance"]),
        "target": target,
        "remaining": remaining,
        "remaining_label": "Remaining" if remaining >= 0 else "Over target",
        "remaining_amount": abs(remaining),
        "remaining_text": (f"{abs(remaining):,} kcal remaining" if remaining >= 0
                           else f"{abs(remaining):,} kcal over target"),
        "calorie_fraction": stats.progress_fraction(consumed, target),
        "macros": [
            _macro_row("Protein", summary["protein_g"], targets["protein_g"]),
            _macro_row("Carbs", summary["carbs_g"], targets["carbs_g"]),
            _macro_row("Fat", summary["fat_g"], targets["fat_g"]),
        ],
        "goal_label": {"lose": "Lose weight", "maintain": "Maintain weight", "gain": "Gain weight"}[person.goal],
        "floor_applied": targets["floor_applied"],
        "below_minimum_custom_target": (
            person.custom_calorie_target is not None
            and person.custom_calorie_target < MIN_CALORIES[person.sex.lower()]
        ),
    })
    return result


def day_marker(day_log) -> str | None:
    """Which dot a calendar day shows: 'food', 'exercise' (exercise only) or None."""
    if day_log and day_log.foods:
        return "food"
    if day_log and day_log.exercises:
        return "exercise"
    return None


_PERIOD_WORDS = {"day": "on this day", "week": "this week", "month": "this month"}


def exercise_insight_text(exercise_days: int, kind: str = "week") -> str:
    """Plain sentence about exercise for the Stats insight card."""
    if exercise_days <= 0:
        return f"No exercise logged {_PERIOD_WORDS.get(kind, 'this week')}."
    if kind == "day":
        return "Exercise logged on this day."
    return f"Exercise on {exercise_days} {'day' if exercise_days == 1 else 'days'}."


def calendar_month(storage, month_ref: date, selected_date: date, today: date | None = None) -> dict:
    """Month grid and selected-day details, without creating or changing saved logs."""
    today = today or date.today()
    person = storage.person_on(selected_date) if storage.profile else None
    log = storage.logs.get(selected_date) or DailyLog(log_date=selected_date)
    foods = calculate_food_totals(log)
    day_summary = calculate_daily_summary(person, log) if person else None
    weeks = []
    for week in calendar.Calendar(firstweekday=0).monthdayscalendar(month_ref.year, month_ref.month):
        cells = []
        for day_number in week:
            if not day_number:
                cells.append(None)
                continue
            d = date(month_ref.year, month_ref.month, day_number)
            day_log = storage.logs.get(d)
            cells.append({
                "day": day_number,
                "date": d,
                "selected": d == selected_date,
                "today": d == today,
                "has_food": bool(day_log and day_log.foods),
                "has_exercise": bool(day_log and day_log.exercises),
                "marker": day_marker(day_log),
            })
        weeks.append(cells)
    return {
        "month": month_ref.replace(day=1),
        "title": month_ref.strftime("%B %Y"),
        "weeks": weeks,
        "selected_date": selected_date,
        "selected_label": selected_date.strftime("%A, %d %B %Y"),
        "food_count": len(log.foods),
        "exercise_count": len(log.exercises),
        "food_calories": round(foods["calories"]),
        "has_profile": bool(person),
        "consumed": round(day_summary["calories_consumed"]) if day_summary else round(foods["calories"]),
        "burned": round(day_summary["calories_burned"]) if day_summary else None,
        "balance": round(day_summary["calorie_balance"]) if day_summary else None,
        "protein": round(foods["protein_g"]),
        "carbs": round(foods["carbs_g"]),
        "fat": round(foods["fat_g"]),
        "has_entries": bool(log.foods or log.exercises),
    }


def _period_dates(selected_date: date, kind: str):
    if kind == "day":
        return selected_date, selected_date
    if kind == "week":
        return stats.week_range(selected_date)
    if kind == "month":
        return stats.month_range(selected_date)
    raise ValueError("kind must be day, week or month")


def stats_dashboard(storage, selected_date: date, kind: str = "week") -> dict:
    """Summarize the existing daily records for the selected day, week or month."""
    start, end = _period_dates(selected_date, kind)
    if kind == "day":
        title = selected_date.strftime("%A, %d %B %Y")
    elif kind == "week":
        title = f"{start.strftime('%d %b')} – {end.strftime('%d %b %Y')}"
    else:
        title = selected_date.strftime("%B %Y")

    result = {
        "kind": kind,
        "title": title,
        "start": start,
        "end": end,
        "has_profile": bool(storage.profile),
        "days_logged": 0,
        "days_in_range": (end - start).days + 1,
        "consumed_total": 0,
        "consumed_avg": 0,
        "burned_total": 0,
        "burned_avg": 0,
        "balance_total": 0,
        "protein_avg": 0,
        "carbs_avg": 0,
        "fat_avg": 0,
        "records": [],
        "adherence": None,
        "insights": None,
        "consistency": stats.consistency(storage.logs, end),
    }
    if not storage.profile:
        return result

    person = storage.profile
    records, aggregate = stats.period_stats(
        person, storage.logs, kind, selected_date, person_on=storage.person_on,
    )

    def target_for_day(day):
        return calculate_targets(storage.person_on(day) or person)["calories"]

    for record in records:
        record["target"] = target_for_day(record["day"])
        record["target_fraction"] = stats.progress_fraction(
            record["calories_consumed"], record["target"],
        )

    result.update(aggregate)
    # These are presentation averages; retain the raw daily records for exports.
    for macro_key in ("protein_avg", "carbs_avg", "fat_avg"):
        if macro_key in result:
            result[macro_key] = round(result[macro_key])
    logged_records = [record for record in records if record["logged"]]
    macro_targets = {"protein": 0, "carbs": 0, "fat": 0}
    if logged_records:
        for record in logged_records:
            day_targets = calculate_targets(storage.person_on(record["day"]) or person)
            macro_targets["protein"] += day_targets["protein_g"]
            macro_targets["carbs"] += day_targets["carbs_g"]
            macro_targets["fat"] += day_targets["fat_g"]
        macro_targets = {name: round(value / len(logged_records))
                         for name, value in macro_targets.items()}
    result.update({
        "has_profile": True,
        "records": records,
        "macro_targets": macro_targets,
        "adherence": stats.target_adherence(records, target_for_day),
        "insights": stats.progress_insights(records, target_for_day),
    })
    return result


def goal_weight_progress_label(remaining_kg: float, goal: str, unit: str) -> str:
    """Describe distance from goal in the direction of the selected goal."""
    from units import from_kg, weight_unit_label

    amount = from_kg(abs(remaining_kg), unit)
    if abs(remaining_kg) < 1e-9:
        return "At goal"
    moving_toward = (remaining_kg < 0 if goal == "lose" else
                     remaining_kg > 0 if goal == "gain" else False)
    relation = "to go" if moving_toward else "past goal"
    return f"{amount:g} {weight_unit_label(unit)} {relation}"


def latest_food_log_date(storage, fallback: date | None = None) -> date:
    """Pick the newest food-logged day so Stats opens on data the person has."""
    dates = [day for day, log in storage.logs.items() if log.foods]
    return max(dates) if dates else (fallback or date.today())


def calculation_explanation(person: Person | None) -> list[str]:
    """Plain-language estimate explanations and current profile figures for the UI sheet."""
    paragraphs = [
        "These figures are estimates based on the profile and food or activity details you enter. "
        "They are for general tracking and are not medical advice.",
        "Basal metabolic rate (BMR): estimated with the Mifflin–St Jeor equation, using age, "
        "height, weight and the sex value in your profile.",
        "Total daily energy expenditure (TDEE): BMR multiplied by your selected usual activity "
        "factor (" + ", ".join(f"{name.replace('_', ' ')} {factor:g}"
                                for name, factor in ACTIVITY_LEVELS.items()) + "). It is a reference estimate.",
        f"Daily calorie target: TDEE adjusted by {PACE_ADJUSTMENT['gentle']} kcal/day for a gentle "
        f"pace or {PACE_ADJUSTMENT['steady']} kcal/day for a steady pace when losing or gaining. "
        "Maintaining uses no adjustment. Without a custom calorie target, the result is raised to "
        "at least 1,500 kcal/day for male profiles or 1,200 kcal/day for female profiles. "
        "Logged exercise is not added to this target.",
        "Macro targets: protein is estimated at 1.2 g per kg for maintaining or 1.6 g per kg for "
        "weight-loss or weight-gain goals. Fat is estimated as 25% of target calories, and "
        "carbohydrate uses the remaining calories. Custom macro targets replace those estimates.",
        f"Daily burn display: baseline burn is BMR × {BASELINE_MULTIPLIER:g}, then logged exercise calories are added. "
        "Exercise calories use (MET − 1) × body weight in kg × activity hours.",
        "Food calories and macros are scaled from the nutrition values per 100 g. Actual values "
        "can differ from these estimates.",
    ]
    if person:
        targets = calculate_targets(person)
        paragraphs.append(
            f"Your profile estimates: BMR {calculate_bmr(person):.0f} kcal/day; "
            f"TDEE {calculate_tdee(person):.0f} kcal/day; target {targets['calories']} kcal/day. "
            f"Your profile activity factor is {ACTIVITY_LEVELS[person.activity_level.lower()]:g}."
        )
        floor = MIN_CALORIES[person.sex.lower()]
        if person.custom_calorie_target is not None:
            if person.custom_calorie_target < floor:
                paragraphs.append(
                    f"Notice: your custom calorie target ({person.custom_calorie_target:g} kcal/day) "
                    f"is below the app's usual {floor} kcal/day minimum for this profile. "
                    "Custom targets can be below that minimum; the app cannot assess whether a "
                    "target is appropriate for you."
                )
            else:
                paragraphs.append("Your calorie target is a custom value from your profile.")
        elif targets["floor_applied"]:
            paragraphs.append(f"The usual {floor} kcal/day minimum was applied to your calculated target.")
    return paragraphs
