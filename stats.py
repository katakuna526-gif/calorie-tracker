"""Statistics built by aggregating the daily records (nothing is stored per week/month)."""

from calendar import monthrange
from datetime import date, timedelta
from typing import Dict, List

from calorie_engine import Person, DailyLog, calculate_daily_summary

QUOTES = [
    "Small steps every day add up to big change.",
    "Progress, not perfection.",
    "You don't have to be extreme, just consistent.",
    "Logging today makes tomorrow easier.",
    "What gets measured gets understood.",
    "One good day at a time.",
    "Consistency beats intensity.",
    "Showing up counts, even on the messy days.",
    "Be patient with yourself. You're building a habit.",
    "Every entry is a vote for the person you want to become.",
]


def quote_for(d: date) -> str:
    """Same quote all day, a different one tomorrow."""
    return QUOTES[d.toordinal() % len(QUOTES)]


def week_range(d: date):
    start = d - timedelta(days=d.weekday())  # Monday
    return start, start + timedelta(days=6)


def month_range(d: date):
    return d.replace(day=1), d.replace(day=monthrange(d.year, d.month)[1])


def daily_records(person: Person, logs: Dict[date, DailyLog], start: date, end: date,
                  person_on=None) -> List[dict]:
    """One summary per calendar day. `logged` is True if any food was logged.

    `person_on` is an optional function(date) -> Person, so each day can use the weight
    you had on that day instead of today's weight."""
    out = []
    d = start
    while d <= end:
        log = logs.get(d) or DailyLog(log_date=d)
        s = calculate_daily_summary(person_on(d) if person_on else person, log)
        s["logged"] = bool(log.foods)
        s["exercise_minutes"] = round(sum(e.duration_minutes for e in log.exercises), 1)
        s["day"] = d
        out.append(s)
        d += timedelta(days=1)
    return out


def aggregate(records: List[dict]) -> dict:
    """Totals and averages. Averages only use days where food was logged,
    so a forgotten day doesn't look like a zero-calorie day."""
    logged = [r for r in records if r["logged"]]
    n = len(logged)

    def total(key):
        return round(sum(r[key] for r in logged), 2)

    def avg(key):
        return round(total(key) / n, 2) if n else 0.0

    return {
        "days_in_range": len(records),
        "days_logged": n,
        "consumed_total": total("calories_consumed"),
        "burned_total": total("calories_burned"),
        "balance_total": total("calorie_balance"),
        "consumed_avg": avg("calories_consumed"),
        "burned_avg": avg("calories_burned"),
        "protein_avg": avg("protein_g"),
        "carbs_avg": avg("carbs_g"),
        "fat_avg": avg("fat_g"),
    }


def period_stats(person, logs, kind: str, ref: date, person_on=None):
    """kind: 'day', 'week' or 'month'. Returns (records, aggregate)."""
    if kind == "day":
        start = end = ref
    elif kind == "week":
        start, end = week_range(ref)
    elif kind == "month":
        start, end = month_range(ref)
    else:
        raise ValueError("kind must be day, week or month")
    recs = daily_records(person, logs, start, end, person_on)
    return recs, aggregate(recs)


def consistency(logs: Dict[date, DailyLog], today: date, window: int = 30) -> dict:
    """Rewards logging, not hitting a particular calorie number."""
    def logged(d):
        log = logs.get(d)
        return bool(log and log.foods)

    last = [today - timedelta(days=i) for i in range(window)]
    days_logged = sum(logged(d) for d in last)

    # Current streak: consecutive logged days ending today.
    # If today isn't logged yet, the streak from yesterday still counts.
    d = today if logged(today) else today - timedelta(days=1)
    streak = 0
    while logged(d):
        streak += 1
        d -= timedelta(days=1)

    longest = run = 0
    for d in sorted(x for x in logs if logged(x)):
        run = run + 1 if (d - timedelta(days=1)) in logs and logged(d - timedelta(days=1)) else 1
        longest = max(longest, run)

    return {"window": window, "days_logged": days_logged,
            "current_streak": streak, "longest_streak": longest}


def consistency_message(c: dict) -> str:
    s, n = c["current_streak"], c["days_logged"]
    if s >= 14:
        return f"{s}-day streak. That's a real habit now."
    if s >= 7:
        return f"{s} days in a row. A full week of showing up."
    if s >= 3:
        return f"{s}-day streak. Keep it going."
    if s >= 1:
        return f"{s} day logged. Come back tomorrow to build the streak."
    if n > 0:
        return f"You've logged {n} of the last {c['window']} days. Log today and start a new streak."
    return "Log your first meal today to start your streak."


def weight_summary(weights: Dict[date, float]) -> dict:
    """Entries newest first (with change since the previous weigh-in) plus overall change."""
    ordered = sorted(weights.items())
    entries = []
    for i, (d, kg) in enumerate(ordered):
        change = round(kg - ordered[i - 1][1], 1) if i > 0 else None
        entries.append({"date": d, "kg": kg, "change": change})
    entries.reverse()
    if not ordered:
        return {"entries": [], "first": None, "latest": None, "change": None, "days": 0}
    first, latest = ordered[0], ordered[-1]
    return {
        "entries": entries,
        "first": first,
        "latest": latest,
        "change": round(latest[1] - first[1], 1),
        "days": (latest[0] - first[0]).days,
    }


def weekly_summary(person, logs, ref: date, person_on=None) -> dict:
    """Seven-day summary ending on ref. Uses only days with food logged for averages."""
    start = ref - timedelta(days=6)
    records = daily_records(person, logs, start, ref, person_on)
    logged = [r for r in records if r["logged"]]
    n = len(logged)
    def avg(key):
        return round(sum(r[key] for r in logged) / n, 1) if n else 0.0
    return {
        "start": start, "end": ref, "days_logged": n,
        "consumed_avg": avg("calories_consumed"),
        "burned_avg": avg("calories_burned"),
        "balance_avg": avg("calorie_balance"),
        "protein_avg": avg("protein_g"),
        "carbs_avg": avg("carbs_g"),
        "fat_avg": avg("fat_g"),
        "records": records,
    }


def weight_trend(weights: Dict[date, float], end: date, days: int = 30) -> List[dict]:
    """Weight entries in a date window, oldest first, suitable for a simple chart."""
    start = end - timedelta(days=max(1, days) - 1)
    return [{"date": d, "kg": kg} for d, kg in sorted(weights.items()) if start <= d <= end]


def progress_fraction(value: float, target: float) -> float:
    """Clamp progress to 0..1; target <= 0 produces zero progress."""
    if target <= 0:
        return 0.0
    return max(0.0, min(1.0, value / target))


def target_adherence(records, target_for_day, tolerance=0.10):
    """Summarize how consistently logged calories land near the daily target.

    Only food-logged days count. A day is "on target" when consumed calories
    are within ``tolerance`` of that day's target. ``target_for_day`` receives
    each record's date and returns the target calories for that day.
    """
    logged = [r for r in records if r["logged"]]
    if not logged:
        return {
            "days_logged": 0, "days_on_target": 0, "on_target_pct": 0.0,
            "average_variance": 0.0, "exercise_days": 0,
        }

    variances = []
    on_target = 0
    exercise_days = 0
    for r in logged:
        target = float(target_for_day(r["day"]))
        variance = r["calories_consumed"] - target
        variances.append(variance)
        if abs(variance) <= target * tolerance:
            on_target += 1
        if r["exercise_calories"] > 0:
            exercise_days += 1

    return {
        "days_logged": len(logged),
        "days_on_target": on_target,
        "on_target_pct": round(on_target / len(logged) * 100, 1),
        "average_variance": round(sum(variances) / len(variances), 1),
        "exercise_days": exercise_days,
    }


def progress_insights(records, target_for_day):
    """Human-friendly insights for a period of daily records.

    Only food-logged days are used for calorie comparisons. Exercise totals use
    those same logged days so an unlogged day is not mistaken for zero activity.
    """
    logged = [r for r in records if r.get("logged")]
    if not logged:
        return {
            "days_logged": 0,
            "best_day": None,
            "lowest_day": None,
            "average_target": 0.0,
            "average_variance": 0.0,
            "exercise_days": 0,
            "exercise_minutes": 0.0,
            "exercise_calories": 0.0,
        }

    enriched = []
    for r in logged:
        target = float(target_for_day(r["day"]))
        enriched.append((r, target, r["calories_consumed"] - target))

    best = min(enriched, key=lambda x: abs(x[2]))
    highest = max(enriched, key=lambda x: x[0]["calories_consumed"])
    lowest = min(enriched, key=lambda x: x[0]["calories_consumed"])
    exercise_minutes = 0.0
    for r, _, _ in enriched:
        # daily_records currently contains exercise calories, not minutes.
        # Callers may provide exercise_minutes when they have it; otherwise zero.
        exercise_minutes += float(r.get("exercise_minutes", 0.0))

    return {
        "days_logged": len(logged),
        "best_day": {"date": best[0]["day"], "variance": round(best[2], 1)},
        "highest_day": {"date": highest[0]["day"], "calories": round(highest[0]["calories_consumed"], 1)},
        "lowest_day": {"date": lowest[0]["day"], "calories": round(lowest[0]["calories_consumed"], 1)},
        "average_target": round(sum(x[1] for x in enriched) / len(enriched), 1),
        "average_variance": round(sum(x[2] for x in enriched) / len(enriched), 1),
        "exercise_days": sum(1 for r, _, _ in enriched if r["exercise_calories"] > 0),
        "exercise_minutes": round(exercise_minutes, 1),
        "exercise_calories": round(sum(r["exercise_calories"] for r, _, _ in enriched), 1),
    }


def weight_goal_insight(weights: Dict[date, float], goal: str) -> dict:
    """Describe whether the observed weight direction matches the selected goal."""
    ordered = sorted(weights.items())
    if len(ordered) < 2:
        return {"status": "not_enough_data", "change": None, "message": "Log at least two weigh-ins to see goal progress."}
    change = round(ordered[-1][1] - ordered[0][1], 1)
    if goal == "lose":
        if change < 0:
            status = "aligned"
        elif change > 0:
            status = "opposite"
        else:
            status = "steady"
    elif goal == "gain":
        if change > 0:
            status = "aligned"
        elif change < 0:
            status = "opposite"
        else:
            status = "steady"
    else:
        status = "steady" if abs(change) <= 0.5 else "moving"
    return {
        "status": status,
        "change": change,
        "first_date": ordered[0][0],
        "last_date": ordered[-1][0],
        "message": {
            "aligned": "Your recent weight direction matches your goal.",
            "opposite": "Your recent weight direction is opposite to your selected goal.",
            "steady": "Your recent weight is broadly steady.",
            "moving": "Your weight is changing; compare this with your maintenance goal.",
        }[status],
    }


def goal_weight_progress(weights: Dict[date, float], goal_weight_kg):
    """Summarize progress from the first recorded weight toward a profile goal."""
    if goal_weight_kg is None or not weights:
        return None
    first_day, start = min(weights.items())
    current_day, current = max(weights.items())
    distance = goal_weight_kg - start
    progress = 100.0 if distance == 0 else max(0.0, min(100.0, (current - start) / distance * 100))
    return {
        "start_date": first_day, "current_date": current_day,
        "start_kg": start, "current_kg": current,
        "goal_kg": goal_weight_kg,
        "remaining_kg": round(goal_weight_kg - current, 1),
        "progress_pct": round(progress, 1),
    }
