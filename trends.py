"""Weight trend vs plan, and week-on-week comparison. Pure logic, neutral wording."""

from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from calorie_engine import Person, calculate_targets, calculate_tdee
import stats

KCAL_PER_KG = 7700.0        # rule of thumb: about 7,700 kcal per kg of body weight
TREND_WINDOW_DAYS = 28
MIN_TREND_SPAN_DAYS = 7
STEADY_KG_PER_WEEK = 0.25


def weight_points(weights: Dict[date, float], today: date, days: Optional[int]) -> List[Tuple[date, float]]:
    """Weigh-ins from the last `days` days (all of them when days is None), oldest first."""
    cutoff = None if days is None else today - timedelta(days=days)
    return sorted((d, kg) for d, kg in weights.items() if (cutoff is None or d >= cutoff) and d <= today)


def weight_rate(weights: Dict[date, float], today: date, window: int = TREND_WINDOW_DAYS) -> dict:
    """Weight change per week from a straight line fitted through recent weigh-ins.

    Needs at least two weigh-ins at least a week apart; otherwise ok is False.
    """
    points = weight_points(weights, today, window)
    if len(points) < 2 or (points[-1][0] - points[0][0]).days < MIN_TREND_SPAN_DAYS:
        return {"ok": False, "n": len(points), "kg_per_week": None}
    xs = [(d - points[0][0]).days for d, _ in points]
    ys = [kg for _, kg in points]
    mean_x, mean_y = sum(xs) / len(xs), sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    slope_per_day = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denominator
    return {"ok": True, "n": len(points), "kg_per_week": round(slope_per_day * 7, 2),
            "span_days": xs[-1], "start": points[0][0], "end": points[-1][0]}


def planned_kg_per_week(person: Person) -> float:
    """The weekly change your chosen goal and pace aims for (negative = losing).

    Uses the real target (after the safety floor), so it never promises more than the target allows.
    """
    daily = calculate_targets(person)["calories"] - calculate_tdee(person)
    return round(daily * 7 / KCAL_PER_KG, 2)


def _kg(value: float, unit="kg") -> str:
    shown = value if unit == "kg" else value * 2.2046226218
    return f"{shown:+.1f} {unit}"


def describe_trend(person: Person, trend: dict, unit="kg") -> dict:
    """A short, neutral explanation of the trend compared with the plan. Returns {status, text}."""
    if not trend["ok"]:
        return {"status": "need_data",
                "text": "Log your weight on two days at least a week apart to see your trend."}

    rate, plan = trend["kg_per_week"], planned_kg_per_week(person)
    summary = f"Over the last {trend['span_days']} days your weight changed about {_kg(rate, unit)} per week."

    if person.goal == "maintain":
        if abs(rate) <= STEADY_KG_PER_WEEK:
            return {"status": "steady", "text": summary + " That's steady."}
        return {"status": "moving", "text": summary + " That's more movement than a maintain goal expects."}

    if plan == 0:   # the safety floor can cancel a plan completely
        return {"status": "moving", "text": summary}
    ratio = rate / plan   # positive means moving the planned way
    plan_text = f"Your plan aims for about {_kg(plan, unit)} per week."
    if ratio < 0.1:
        return {"status": "opposite", "text": summary + " " + plan_text +
                " It isn't moving that way yet. Weight bounces around day to day, so give it a couple more weeks."}
    if ratio < 0.6:
        return {"status": "slower", "text": summary + " " + plan_text + " That's a bit slower than planned."}
    if ratio <= 1.5:
        return {"status": "on_plan", "text": summary + " " + plan_text + " Right on plan."}
    return {"status": "faster", "text": summary + " " + plan_text +
            " That's faster than planned. Make sure you're eating enough."}




def week_comparison(person, logs, ref: date, person_on=None) -> dict:
    """This 7-day window (ending ref) against the 7 days before it."""
    this = stats.weekly_summary(person, logs, ref, person_on)
    prev = stats.weekly_summary(person, logs, ref - timedelta(days=7), person_on)
    return {"this": this, "previous": prev,
            "days_diff": this["days_logged"] - prev["days_logged"],
            "calorie_diff": (round(this["consumed_avg"] - prev["consumed_avg"])
                             if this["days_logged"] and prev["days_logged"] else None)}


def week_comparison_text(cmp: dict) -> str:
    diff = cmp["days_diff"]
    if cmp["previous"]["days_logged"] == 0 and cmp["this"]["days_logged"] == 0:
        return ""
    if diff > 0:
        text = f"Logged {diff} more day{'s' if diff != 1 else ''} than the 7 days before."
    elif diff < 0:
        text = f"Logged {-diff} fewer day{'s' if diff != -1 else ''} than the 7 days before."
    else:
        text = "Logged the same number of days as the 7 days before."
    cd = cmp["calorie_diff"]
    if cd is not None and cd != 0:
        text += f" Average intake {abs(cd):,} kcal {'higher' if cd > 0 else 'lower'}."
    return text
