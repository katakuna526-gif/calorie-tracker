"""Exercise list: activities with three effort levels, and a calorie estimate.

Calories burned come from MET values (metabolic equivalents), rounded from the
Compendium of Physical Activities. One MET is the energy you use sitting still.
The formula itself lives in calorie_engine.calculate_exercise_calories:

    extra calories = (MET - 1) x weight in kg x hours

It subtracts 1 MET because the daily "burned" figure already includes your resting
energy, so the minutes you exercise would otherwise be counted twice.

These are estimates. Where the Compendium does not list three distinct effort levels
for an activity, the missing level is interpolated. Real burn also varies with fitness,
pace, terrain and body composition; a heart-rate watch or gym machine reading is better
when you have one (choose "Other" in the exercise box and type it in).

No UI code here, so it is tested without opening a window.
"""

from dataclasses import dataclass
from typing import List, Optional

from calorie_engine import calculate_exercise_calories

INTENSITIES = ("light", "moderate", "vigorous")


@dataclass(frozen=True)
class Exercise:
    name: str
    light: float
    moderate: float
    vigorous: float
    note: str  # what the three effort levels mean for this activity

    def met(self, intensity: str) -> float:
        if intensity not in INTENSITIES:
            raise ValueError("Effort must be light, moderate or vigorous.")
        return getattr(self, intensity)


def _e(name, light, moderate, vigorous, note):
    return Exercise(name, light, moderate, vigorous, note)


EXERCISES: List[Exercise] = [
    _e("Walking", 2.8, 3.5, 5.0, "Light: slow stroll (~3 km/h). Moderate: steady (~5 km/h). Vigorous: brisk (~6.5 km/h)."),
    _e("Hiking", 4.5, 6.0, 7.8, "Light: easy trail. Moderate: hills. Vigorous: steep terrain or carrying a pack."),
    _e("Running", 6.0, 8.3, 11.0, "Light: easy jog (~6.5 km/h). Moderate: ~8 km/h. Vigorous: ~11 km/h."),
    _e("Cycling (outdoor)", 4.0, 6.8, 10.0, "Light: leisure (<16 km/h). Moderate: ~18 km/h. Vigorous: ~25 km/h."),
    _e("Stationary bike", 3.5, 6.8, 8.8, "Light: easy pedalling. Moderate: steady. Vigorous: hard intervals."),
    _e("Swimming", 4.8, 5.8, 9.8, "Light: relaxed. Moderate: steady laps. Vigorous: fast laps."),
    _e("Elliptical trainer", 4.0, 5.0, 6.5, "Light: easy. Moderate: steady. Vigorous: high resistance."),
    _e("Rowing machine", 4.8, 7.0, 8.5, "Light: easy. Moderate: steady. Vigorous: hard."),
    _e("Weight training", 3.0, 3.5, 6.0, "Light: long rests. Moderate: normal gym session. Vigorous: heavy lifting, short rests."),
    _e("Bodyweight exercises", 2.8, 3.8, 8.0, "Light: easy push-ups/squats. Moderate: home workout. Vigorous: fast, high effort."),
    _e("Circuit training / HIIT", 4.3, 6.0, 8.0, "Light: slow circuits. Moderate: steady circuits. Vigorous: intervals, little rest."),
    _e("Skipping / jump rope", 8.8, 11.8, 12.3, "Light: slow (<100 skips/min). Moderate: 100-120/min. Vigorous: >120/min."),
    _e("Aerobics / Zumba", 5.0, 6.5, 8.5, "Light: low impact. Moderate: general class. Vigorous: high impact or step."),
    _e("Dancing", 3.0, 5.0, 7.3, "Light: slow. Moderate: social dancing. Vigorous: fast or aerobic."),
    _e("Yoga", 2.0, 2.5, 4.0, "Light: gentle. Moderate: hatha. Vigorous: power yoga."),
    _e("Pilates", 2.5, 3.0, 4.0, "Light: gentle. Moderate: general class. Vigorous: advanced."),
    _e("Badminton", 4.0, 5.5, 7.0, "Light: casual. Moderate: social games. Vigorous: competitive."),
    _e("Cricket", 3.5, 4.8, 6.0, "Light: fielding. Moderate: batting and bowling. Vigorous: a lot of running."),
    _e("Football / soccer", 5.0, 7.0, 10.0, "Light: kick-about. Moderate: casual game. Vigorous: competitive match."),
    _e("Basketball", 4.5, 6.5, 8.0, "Light: shooting hoops. Moderate: general play. Vigorous: full game."),
    _e("Tennis", 5.0, 6.0, 8.0, "Light: casual rally. Moderate: doubles. Vigorous: singles match."),
    _e("Martial arts", 5.3, 7.5, 10.3, "Light: slow practice. Moderate: training session. Vigorous: sparring or hard drills."),
    _e("Gardening", 2.5, 4.0, 5.5, "Light: watering, light weeding. Moderate: general. Vigorous: digging."),
    _e("Housework / cleaning", 2.3, 3.5, 4.5, "Light: tidying. Moderate: general cleaning. Vigorous: scrubbing, moving furniture."),
]


def get_exercise(name: str) -> Optional[Exercise]:
    """Exact (case-insensitive) match on the activity name, or None."""
    key = (name or "").strip().lower()
    for exercise in EXERCISES:
        if exercise.name.lower() == key:
            return exercise
    return None


def estimate_calories(name: str, intensity: str, weight_kg: float, minutes: float) -> float:
    """Extra calories burned by a listed activity at a given effort level."""
    exercise = get_exercise(name)
    if exercise is None:
        raise ValueError(f"Unknown activity: {name!r}.")
    return calculate_exercise_calories(exercise.met(intensity), weight_kg, minutes)
