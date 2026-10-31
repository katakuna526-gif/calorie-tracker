"""Display and input conversions for body weight; stored values always remain kilograms."""

KG_PER_LB = 0.45359237
LB_PER_KG = 1 / KG_PER_LB


def from_kg(value, unit="kg"):
    return value if unit == "kg" else value * LB_PER_KG


def to_kg(value, unit="kg"):
    return value if unit == "kg" else value * KG_PER_LB


def weight_unit_label(unit="kg"):
    return "lb" if unit == "lb" else "kg"
