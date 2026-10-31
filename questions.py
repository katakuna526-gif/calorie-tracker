"""The setup questionnaire, written as data.

To add, remove or reword a question, edit the QUESTIONS list below.
Each question is a dict:
    key      name of the answer (must match a field used in person_from_answers)
    prompt   the question shown to the person
    type     "text", "number" or "choice"
    help     optional small hint under the question
    unit     (number) shown after the box, e.g. "kg"
    min/max  (number) allowed range
    integer  (number) True to require a whole number
    choices  (choice) list of (value, label) pairs
    default  (text) used when left blank
    only_if  optional function(answers) -> bool; the question is skipped if it returns False

This module has no UI code, so it can be tested without opening a window.
"""

from calorie_engine import Person

QUESTIONS = [
    {"key": "name", "prompt": "What should we call you?", "type": "text",
     "default": "Me", "help": "Optional. You can leave this blank."},
    {"key": "age", "prompt": "How old are you?", "type": "number",
     "unit": "years", "min": 18, "max": 100, "integer": True,
     "help": "The calorie formulas used here are designed for adults."},
    {"key": "sex", "prompt": "Which option should we use for the calorie formula?",
     "type": "choice", "choices": [("male", "Male"), ("female", "Female")],
     "help": "The standard formulas use these two categories to estimate resting calories."},
    {"key": "height_cm", "prompt": "How tall are you?", "type": "number",
     "unit": "cm", "min": 100, "max": 250},
    {"key": "weight_kg", "prompt": "What is your current weight?", "type": "number",
     "unit": "kg", "min": 30, "max": 300},
    {"key": "activity_level", "prompt": "How active are you on a normal day?", "type": "choice",
     "choices": [
         ("sedentary", "Sedentary: desk job, little exercise"),
         ("light", "Light: exercise 1-3 days a week"),
         ("moderate", "Moderate: exercise 3-5 days a week"),
         ("high", "High: hard exercise 6-7 days a week"),
         ("very_high", "Very high: physical job plus hard training"),
     ],
     "help": "Pick the one that fits most weeks. Don't count today's workout separately."},
    {"key": "goal", "prompt": "What is your goal?", "type": "choice",
     "choices": [
         ("lose", "Lose weight"),
         ("maintain", "Maintain my weight"),
         ("gain", "Gain weight"),
     ]},
    {"key": "pace", "prompt": "How quickly would you like to go?", "type": "choice",
     "choices": [
         ("gentle", "Gentle: about 250 calories a day from maintenance"),
         ("steady", "Steady: about 500 calories a day from maintenance"),
     ],
     "help": "Slower is easier to keep up. You can change this any time.",
     "only_if": lambda answers: answers.get("goal") in ("lose", "gain")},
    {"key": "goal_weight_kg", "prompt": "Do you have a goal weight?", "type": "number",
     "unit": "kg (optional)", "min": 30, "max": 300, "optional": True,
     "help": "Leave blank if you don't want to set a weight goal."},
    {"key": "custom_calorie_target", "prompt": "Set a custom daily calorie target?", "type": "number",
     "unit": "kcal (optional)", "min": 500, "max": 10000, "optional": True,
     "help": "Leave blank to use the app's calculated target."},
    {"key": "custom_protein_target", "prompt": "Set a custom protein target?", "type": "number",
     "unit": "g (optional)", "min": 0, "max": 1000, "optional": True},
    {"key": "custom_carbs_target", "prompt": "Set a custom carbohydrate target?", "type": "number",
     "unit": "g (optional)", "min": 0, "max": 1500, "optional": True},
    {"key": "custom_fat_target", "prompt": "Set a custom fat target?", "type": "number",
     "unit": "g (optional)", "min": 0, "max": 1000, "optional": True},
]


def visible_questions(answers: dict) -> list:
    """Questions that apply, given the answers so far."""
    return [q for q in QUESTIONS if q.get("only_if") is None or q["only_if"](answers)]


def validate_answer(question: dict, raw):
    """Check one raw answer. Returns (value, None) if valid, else (None, error message)."""
    raw = "" if raw is None else str(raw).strip()
    kind = question["type"]

    if kind == "text":
        return (raw or question.get("default", "")), None

    if kind == "number" and question.get("optional") and not raw:
        return None, None

    if kind == "choice":
        if raw not in [value for value, _ in question["choices"]]:
            return None, "Please choose one of the options."
        return raw, None

    try:
        number = float(raw)
    except ValueError:
        return None, "Please enter a number."
    lo, hi = question["min"], question["max"]
    if not (lo <= number <= hi):  # also rejects nan and infinity
        return None, f"Please enter a value between {lo} and {hi}."
    if question.get("integer"):
        if number != int(number):
            return None, "Please enter a whole number."
        return int(number), None
    return number, None


def person_from_answers(answers: dict) -> Person:
    """Build a Person from the questionnaire answers."""
    needed = [q["key"] for q in visible_questions(answers)
              if q["key"] != "name" and not q.get("optional")]
    missing = [key for key in needed if key not in answers]
    if missing:
        raise ValueError("Missing answer: " + ", ".join(missing))
    return Person(
        name=(answers.get("name") or "Me").strip() or "Me",
        age=int(answers["age"]),
        sex=answers["sex"],
        weight_kg=float(answers["weight_kg"]),
        height_cm=float(answers["height_cm"]),
        activity_level=answers["activity_level"],
        goal=answers["goal"],
        pace=answers.get("pace", "gentle"),
        goal_weight_kg=answers.get("goal_weight_kg"),
        custom_calorie_target=answers.get("custom_calorie_target"),
        custom_protein_target=answers.get("custom_protein_target"),
        custom_carbs_target=answers.get("custom_carbs_target"),
        custom_fat_target=answers.get("custom_fat_target"),
    )


def answers_from_person(person: Person) -> dict:
    """Turn an existing profile back into answers, so the questionnaire can edit it."""
    return {
        "name": person.name,
        "age": person.age,
        "sex": person.sex,
        "height_cm": person.height_cm,
        "weight_kg": person.weight_kg,
        "activity_level": person.activity_level,
        "goal": person.goal,
        "pace": person.pace,
        "goal_weight_kg": person.goal_weight_kg,
        "custom_calorie_target": person.custom_calorie_target,
        "custom_protein_target": person.custom_protein_target,
        "custom_carbs_target": person.custom_carbs_target,
        "custom_fat_target": person.custom_fat_target,
    }
