"""Calorie Tracker UI (Tkinter, no extra packages). Run:  python app.py

All math lives in calorie_engine.py and stats.py; saving lives in storage.py.
This file only collects input and shows results.
"""

import calendar
import shutil
import tkinter as tk
from datetime import date
from tkinter import ttk, messagebox, filedialog

import stats
import trends
from calorie_engine import (
    MEALS, MEAL_LABELS,
    ACTIVITY_LEVELS, BASELINE_MULTIPLIER, MIN_CALORIES, PACE_ADJUSTMENT,
    calculate_bmr, calculate_tdee, calculate_targets, calculate_daily_summary,
    calculate_meal_totals,
)
from exercise_panel import ExercisePanel
from food_panel import FoodPanel
from questions import answers_from_person
from storage import Storage
from ui_helpers import ScrollFrame
from weight_panel import WeightPanel
from wizard import Wizard
from exporter import period_csv_rows, write_csv
from units import from_kg, weight_unit_label

GOAL_TEXT = {"lose": "lose weight", "maintain": "maintain weight", "gain": "gain weight"}

CONSUMED_COLOR = "#3b82f6"
BURNED_COLOR = "#f97316"
MACRO_COLORS = {"Protein": "#10b981", "Carbs": "#8b5cf6", "Fat": "#eab308"}


class App(tk.Tk):
    def __init__(self, storage: Storage = None):
        super().__init__()
        self.title("Calorie Tracker")
        self.geometry("820x860")
        self.store = storage or Storage()
        self.style = ttk.Style(self)
        self._apply_theme()
        self.today = date.today()
        self.selected = self.today
        self.cal_month = self.today.replace(day=1)
        self.stat_kind = tk.StringVar(value="week")

        self.banner = ttk.Label(self, text="", wraplength=780, justify="center",
                                font=("TkDefaultFont", 11, "italic"))
        self.banner.pack(fill="x", padx=10, pady=(8, 0))
        self.disclaimer = ttk.Label(
            self, text="Nutrition, calorie and exercise numbers are estimates, not medical advice.",
            wraplength=780, justify="center")
        self.disclaimer.pack(fill="x", padx=10, pady=(2, 0))

        self.tabs = ttk.Notebook(self)
        self.tabs.pack(fill="both", expand=True, padx=10, pady=8)
        self.log_scroll = ScrollFrame(self.tabs)   # the Log tab scrolls when it is taller than the window
        self.tab_log = self.log_scroll.inner
        self.tab_cal = ttk.Frame(self.tabs)
        self.tab_stats = ttk.Frame(self.tabs)
        self.tab_weight = ttk.Frame(self.tabs)
        self.tab_settings = ttk.Frame(self.tabs)
        self.tabs.add(self.log_scroll, text="Log")
        self.tabs.add(self.tab_cal, text="Calendar")
        self.tabs.add(self.tab_stats, text="Stats")
        self.tabs.add(self.tab_weight, text="Weight")
        self.tabs.add(self.tab_settings, text="Settings")
        self.tabs.bind("<<NotebookTabChanged>>", lambda e: self.refresh_all())

        self._build_day_nav(self.tab_log)
        self._build_profile(self.tab_log)
        self._build_food(self.tab_log)
        self._build_exercise(self.tab_log)
        self._build_summary(self.tab_log)
        self._build_calendar(self.tab_cal)
        self._build_stats(self.tab_stats)
        self._build_settings(self.tab_settings)
        self.weight_panel = WeightPanel(self.tab_weight, self.store, lambda: self.selected, self.refresh_all,
                                        lambda: self.store.preferences["weight_unit"])
        self.weight_panel.pack(fill="both", expand=True)

        self.refresh_all()
        if self.store.skipped_total:
            self.after(200, self._tell_about_skipped)
        if not self.store.profile:
            self.after(300, self.open_wizard)  # first run: start the questionnaire

    def _tell_about_skipped(self):
        n = self.store.skipped_total
        messagebox.showwarning(
            "Some saved entries were skipped",
            f"{n} saved item(s) had values that can't be real (for example more than 100 g of "
            "nutrients in 100 g of food, or more than 5,000 g in one entry), so they were left out.\n\n"
            "They are removed from your file the next time you add or change something.")
        self.store.skipped = {k: 0 for k in self.store.skipped}

    # ------------------------------------------------------------ helpers
    @property
    def log(self):
        return self.store.get_log(self.selected)

    def refresh_all(self):
        self.banner.config(text=f"“{stats.quote_for(self.today)}”")
        self.refresh_profile()
        self.refresh_log()
        self.refresh_calendar()
        self.refresh_stats()
        self.weight_panel.refresh()

    def _weight_for_exercise(self):
        """Weight used for exercise estimates: the weight you had on the selected day."""
        person = self.store.person_on(self.selected)
        return person.weight_kg if person else None

    def _apply_theme(self):
        dark = self.store.preferences.get("theme") == "dark"
        bg, fg = ("#202124", "#f1f3f4") if dark else ("#f4f5f7", "#202124")
        surface = "#2b2d30" if dark else "#ffffff"
        muted = "#c2c7cc" if dark else "#555b62"
        self.style.theme_use("clam")
        self.configure(bg=bg)
        self.style.configure(".", background=bg, foreground=fg)
        self.style.configure("TFrame", background=bg)
        self.style.configure("TLabel", background=bg, foreground=fg)
        self.style.configure("TLabelframe", background=bg, foreground=fg)
        self.style.configure("TLabelframe.Label", background=bg, foreground=fg)
        self.style.configure("TButton", background=surface, foreground=fg, padding=5)
        self.style.map("TButton", background=[("active", "#4b5563" if dark else "#e5e7eb")])
        self.style.configure("TNotebook", background=bg, borderwidth=0)
        self.style.configure("TNotebook.Tab", background=surface, foreground=fg, padding=(10, 5))
        self.style.map("TNotebook.Tab", background=[("selected", bg)])
        self.style.configure("TEntry", fieldbackground=surface, foreground=fg, insertcolor=fg)
        self.style.configure("TCombobox", fieldbackground=surface, foreground=fg)
        self.style.configure("TProgressbar", background="#2a78d6", troughcolor=surface)
        self.style.configure("TRadiobutton", background=bg, foreground=fg)
        self._theme_palette = (bg, fg, surface, muted)

    def _build_settings(self, parent):
        f = ttk.LabelFrame(parent, text="Display")
        f.pack(fill="x", padx=12, pady=12)
        self.weight_unit_var = tk.StringVar(value=self.store.preferences["weight_unit"])
        self.theme_var = tk.StringVar(value=self.store.preferences["theme"])
        ttk.Label(f, text="Body weight units").grid(row=0, column=0, sticky="w", padx=10, pady=8)
        ttk.Combobox(f, textvariable=self.weight_unit_var, state="readonly", width=12,
                     values=("kg", "lb")).grid(row=0, column=1, padx=10, pady=8)
        ttk.Label(f, text="Appearance").grid(row=1, column=0, sticky="w", padx=10, pady=8)
        ttk.Combobox(f, textvariable=self.theme_var, state="readonly", width=12,
                     values=("light", "dark")).grid(row=1, column=1, padx=10, pady=8)
        ttk.Label(f, text="Weight settings change body-weight displays and entries. Height stays in cm; food and macro amounts stay in grams.",
                  wraplength=650).grid(row=2, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 8))
        ttk.Button(f, text="Save settings", command=self.save_settings).grid(
            row=3, column=0, columnspan=2, padx=10, pady=(4, 10), sticky="w")

        data = ttk.LabelFrame(parent, text="Data backup")
        data.pack(fill="x", padx=12, pady=8)
        ttk.Label(data, text="Save a copy of your tracker data, or restore it from a backup file.",
                  wraplength=650).pack(anchor="w", padx=10, pady=(8, 4))
        buttons = ttk.Frame(data)
        buttons.pack(anchor="w", padx=10, pady=(2, 10))
        ttk.Button(buttons, text="Back up data…", command=self.backup_data).pack(side="left", padx=(0, 8))
        ttk.Button(buttons, text="Restore backup…", command=self.restore_backup).pack(side="left")

    def save_settings(self):
        self.store.set_preferences(self.weight_unit_var.get(), self.theme_var.get())
        self._apply_theme()
        self.refresh_all()

    def backup_data(self):
        path = filedialog.asksaveasfilename(
            title="Save calorie tracker backup", defaultextension=".json",
            filetypes=[("JSON backup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.store.save()
            shutil.copy2(self.store.path, path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Backup", f"The backup could not be saved.\n\n{exc}")
            return
        messagebox.showinfo("Backup", "Your tracker data was backed up successfully.")

    def restore_backup(self):
        path = filedialog.askopenfilename(
            title="Choose a calorie tracker backup",
            filetypes=[("JSON backup", "*.json"), ("All files", "*.*")])
        if not path:
            return
        if not messagebox.askyesno(
                "Restore backup", "Restoring replaces the current tracker data. "
                "A safety copy of the current data will be kept automatically. Continue?"):
            return
        try:
            safety_copy = self.store.restore_from(path)
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Restore", f"The backup could not be restored. Your current data was kept.\n\n{exc}")
            return
        self.weight_unit_var.set(self.store.preferences["weight_unit"])
        self.theme_var.set(self.store.preferences["theme"])
        self._apply_theme()
        self.refresh_all()
        note = "The backup was restored successfully."
        if safety_copy:
            note += f"\n\nA safety copy was saved beside your data file as:\n{safety_copy}"
        messagebox.showinfo("Restore", note)

    # ------------------------------------------------------------ day navigation
    def _build_day_nav(self, parent):
        bar = ttk.Frame(parent)
        bar.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Button(bar, text="◀ Previous day", command=lambda: self._shift_selected_day(-1)).pack(side="left")
        self.day_nav_label = ttk.Label(bar, text="", font=("TkDefaultFont", 10, "bold"), anchor="center")
        self.day_nav_label.pack(side="left", fill="x", expand=True, padx=8)
        ttk.Button(bar, text="Today", command=self._go_today).pack(side="left", padx=4)
        ttk.Button(bar, text="Next day ▶", command=lambda: self._shift_selected_day(1)).pack(side="left")

    def _shift_selected_day(self, delta):
        from datetime import timedelta
        self.selected = self.selected + timedelta(days=delta)
        self.refresh_all()

    def _go_today(self):
        self.selected = self.today
        self.cal_month = self.today.replace(day=1)
        self.refresh_all()

    # ------------------------------------------------------------ profile
    def _build_profile(self, parent):
        f = ttk.LabelFrame(parent, text="1. Your profile and daily target")
        f.pack(fill="x", padx=6, pady=4)
        self.profile_text = ttk.Label(f, text="", justify="left")
        self.profile_text.pack(side="left", padx=8, pady=6)
        self.profile_btn = ttk.Button(f, text="Set up profile", command=self.open_wizard)
        self.profile_btn.pack(side="right", padx=8, pady=6)
        ttk.Button(f, text="How is this calculated?", command=self.show_calculations).pack(
            side="right", padx=4, pady=6)

    def show_calculations(self):
        """Explain the estimates and the current targets without changing their maths."""
        window = tk.Toplevel(self)
        window.title("How your estimates are calculated")
        window.geometry("680x610")

        person = self.store.profile
        paragraphs = [
            "These figures are estimates based on the profile and food or activity details you enter. "
            "They are for general tracking and are not medical advice.",
            "Basal metabolic rate (BMR): estimated with the Mifflin–St Jeor equation, using age, "
            "height, weight and the sex value in your profile.",
            "Total daily energy expenditure (TDEE): BMR multiplied by your selected usual activity "
            "factor (" + ", ".join(f"{name.replace('_', ' ')} {factor:g}"
                                    for name, factor in ACTIVITY_LEVELS.items()) + "). "
            "It is shown as a reference estimate.",
            f"Daily calorie target: TDEE, adjusted by {PACE_ADJUSTMENT['gentle']} kcal/day for a gentle "
            f"pace or {PACE_ADJUSTMENT['steady']} kcal/day for a steady pace when losing or gaining. "
            "Maintaining uses no adjustment. Without a "
            "custom calorie target, the result is raised to at least 1,500 kcal/day for male profiles "
            "or 1,200 kcal/day for female profiles. Logged exercise is not added to this target.",
            "Macro targets: protein is estimated at 1.2 g per kg for maintaining or 1.6 g per kg for "
            "weight-loss or weight-gain goals. Fat is estimated as 25% of target calories, and "
            "carbohydrate uses the remaining calories. Any custom macro target replaces its estimate.",
            f"Daily burn display: baseline burn is BMR × {BASELINE_MULTIPLIER:g}, then logged exercise calories are added. "
            "Exercise calories use (MET − 1) × body weight in kg × activity hours.",
            "Food calories and macros are scaled from the nutrition values per 100 g. Actual values "
            "can differ from these estimates."
        ]
        if person:
            targets = calculate_targets(person)
            paragraphs.append(
                f"Your current profile estimates: BMR {calculate_bmr(person):.0f} kcal/day; "
                f"TDEE {calculate_tdee(person):.0f} kcal/day; target {targets['calories']} kcal/day. "
                f"Your profile activity factor is {ACTIVITY_LEVELS[person.activity_level.lower()]:g}.")
            floor = MIN_CALORIES[person.sex.lower()]
            if person.custom_calorie_target is not None:
                if person.custom_calorie_target < floor:
                    paragraphs.append(
                        f"Notice: your custom calorie target ({person.custom_calorie_target:g} kcal/day) "
                        f"is below the app's usual {floor} kcal/day minimum for this profile. "
                        "Custom targets can be below that minimum; the app cannot assess whether a "
                        "target is appropriate for you.")
                else:
                    paragraphs.append("Your calorie target is a custom value from your profile.")
            elif targets["floor_applied"]:
                paragraphs.append(f"The usual {floor} kcal/day minimum was applied to your calculated target.")

        self.calculation_text = ttk.Label(
            window, text="\n\n".join(paragraphs), wraplength=630, justify="left", anchor="nw")
        self.calculation_text.pack(fill="both", expand=True, padx=18, pady=16)
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=(0, 14))
        return window

    def open_wizard(self):
        answers = answers_from_person(self.store.profile) if self.store.profile else {}
        Wizard(self, answers=answers, on_done=self.save_profile,
               weight_unit=self.store.preferences["weight_unit"])

    def save_profile(self, person):
        self.store.set_profile(person)
        self.refresh_all()

    def refresh_profile(self):
        p = self.store.profile
        if not p:
            self.profile_text.config(text="No profile yet. Answer a few questions to get your daily target.")
            self.profile_btn.config(text="Set up profile")
            return
        t = calculate_targets(p)
        goal = GOAL_TEXT[p.goal] + (f" ({p.pace})" if p.goal != "maintain" else "")
        unit = self.store.preferences["weight_unit"]
        label = weight_unit_label(unit)
        lines = [
            f"{p.name}, {p.age}, {p.sex}, {from_kg(p.weight_kg, unit):.1f} {label}, {p.height_cm:g} cm",
            f"Activity: {p.activity_level.replace('_', ' ')}   |   Goal: {goal}",
            f"BMR {calculate_bmr(p):.0f} kcal   |   TDEE {calculate_tdee(p):.0f} kcal",
            f"Daily target: {t['calories']} kcal   "
            f"(protein {t['protein_g']} g, carbs {t['carbs_g']} g, fat {t['fat_g']} g)",
        ]
        if t["floor_applied"]:
            lines.append("Note: your target was raised to a minimum calorie level.")
        elif p.custom_calorie_target is not None and p.custom_calorie_target < MIN_CALORIES[p.sex.lower()]:
            lines.append(
                f"Notice: custom target is below the usual {MIN_CALORIES[p.sex.lower()]} kcal/day minimum. "
                "The app cannot assess whether it is appropriate for you.")
        if p.goal_weight_kg is not None:
            lines.append(f"Goal weight: {from_kg(p.goal_weight_kg, unit):.1f} {label}")
        self.profile_text.config(text="\n".join(lines))
        self.profile_btn.config(text="Edit profile")

    # ------------------------------------------------------------ food
    def _build_food(self, parent):
        self.food_panel = FoodPanel(parent, self.store, lambda: self.log, self.refresh_all)
        self.food_panel.pack(fill="x", padx=6, pady=4)

    # ------------------------------------------------------------ exercise
    def _build_exercise(self, parent):
        self.exercise_panel = ExercisePanel(parent, self.store, lambda: self.log,
                                            self._weight_for_exercise, self.refresh_all,
                                            lambda: self.store.preferences["weight_unit"])
        self.exercise_panel.pack(fill="x", padx=6, pady=4)

    # ------------------------------------------------------------ day summary
    def _build_summary(self, parent):
        f = ttk.LabelFrame(parent, text="4. Today's progress")
        f.pack(fill="both", expand=True, padx=6, pady=4)
        self.summary_frame = f
        self.summary_title = ttk.Label(f, text="", font=("TkDefaultFont", 11, "bold"))
        self.summary_title.pack(anchor="w", padx=8, pady=(6, 0))

        self.progress_text = ttk.Label(f, text="", font=("TkDefaultFont", 12, "bold"))
        self.progress_text.pack(anchor="w", padx=8, pady=(5, 2))
        self.calorie_bar = ttk.Progressbar(f, orient="horizontal", mode="determinate", maximum=100)
        self.calorie_bar.pack(fill="x", padx=8, pady=(0, 8))

        self.summary = ttk.Label(f, text="", font=("Courier", 10), justify="left")
        self.summary.pack(anchor="w", padx=8, pady=2)

        macro_box = ttk.Frame(f)
        macro_box.pack(fill="x", padx=8, pady=(6, 2))
        self.macro_progress = {}
        self.macro_labels = {}
        for name in ("Protein", "Carbs", "Fat"):
            row = ttk.Frame(macro_box)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=f"{name:<8}", width=9).pack(side="left")
            bar = ttk.Progressbar(row, orient="horizontal", mode="determinate", maximum=100)
            bar.pack(side="left", fill="x", expand=True, padx=4)
            label = ttk.Label(row, text="", width=18, anchor="e")
            label.pack(side="right")
            self.macro_progress[name] = bar
            self.macro_labels[name] = label

        self.meal_label = ttk.Label(f, text="", foreground="#374151")
        self.meal_label.pack(anchor="w", padx=8, pady=(6, 0))
        self.week_label = ttk.Label(f, text="", foreground="#374151", justify="left")
        self.week_label.pack(anchor="w", padx=8, pady=(5, 0))
        self.streak_label = ttk.Label(f, text="", foreground="#047857")
        self.streak_label.pack(anchor="w", padx=8, pady=(2, 6))

    def refresh_log(self):
        log = self.log
        label = "Today" if self.selected == self.today else self.selected.strftime("%A, %d %B %Y")
        self.summary_title.config(text=label)
        self.day_nav_label.config(text=f"Editing: {self.selected.strftime('%A, %d %B %Y')}" + (" (today)" if self.selected == self.today else ""))
        self.summary_frame.config(text="4. Today's progress" if self.selected == self.today else "4. Selected day's progress")

        self.food_panel.refresh()
        self.exercise_panel.refresh()

        person = self.store.person_on(self.selected)
        if not person:
            cal = sum(x.calories for x in log.foods)
            self.progress_text.config(text=f"{cal:.0f} kcal consumed")
            self.calorie_bar["value"] = 0
            self.summary.config(text="Save your profile to see targets, remaining calories and macro progress.")
            for name in self.macro_progress:
                self.macro_progress[name]["value"] = 0
                self.macro_labels[name].config(text="—")
        else:
            s = calculate_daily_summary(person, log)
            t = calculate_targets(person)
            consumed = s["calories_consumed"]
            remaining = t["calories"] - consumed
            if remaining >= 0:
                self.progress_text.config(text=f"{consumed:.0f} / {t['calories']} kcal   •   {remaining:.0f} remaining")
            else:
                self.progress_text.config(text=f"{consumed:.0f} / {t['calories']} kcal   •   {abs(remaining):.0f} over target")
            self.calorie_bar["value"] = stats.progress_fraction(consumed, t["calories"]) * 100
            self.summary.config(text=(
                f"Burned:   {s['calories_burned']:>7.0f} kcal   "
                f"(base {s['baseline_burn']:.0f} + exercise {s['exercise_calories']:.0f})\n"
                f"Balance:  {s['calorie_balance']:>+7.0f} kcal\n"
                f"Target:   {t['calories']:>7} kcal" + ("   (minimum floor applied)" if t["floor_applied"] else "")))
            for name, key, target_key in (("Protein", "protein_g", "protein_g"),
                                            ("Carbs", "carbs_g", "carbs_g"),
                                            ("Fat", "fat_g", "fat_g")):
                value = s[key]
                target = t[target_key]
                self.macro_progress[name]["value"] = stats.progress_fraction(value, target) * 100
                self.macro_labels[name].config(text=f"{value:.0f} / {target} g")

        meals = calculate_meal_totals(log)
        self.meal_label.config(text="By meal:  " + "   |   ".join(
            f"{MEAL_LABELS[m]} {meals[m]:.0f}" for m in MEALS) + " kcal")

        if self.store.profile:
            w = stats.weekly_summary(self.store.profile, self.store.logs, self.selected,
                                     person_on=self.store.person_on)
            self.week_label.config(text=(
                f"7-day summary: {w['days_logged']}/7 days logged   |   "
                f"{w['consumed_avg']:.0f} kcal/day eaten   |   "
                f"{w['protein_avg']:.0f} g protein/day"))
            extra = trends.week_comparison_text(trends.week_comparison(
                self.store.profile, self.store.logs, self.selected, self.store.person_on))
            if extra:
                self.week_label.config(text=self.week_label.cget("text") + "\n" + extra)
        else:
            self.week_label.config(text="7-day summary: set up your profile to see averages.")

        c = stats.consistency(self.store.logs, self.today)
        self.streak_label.config(text=f"{stats.consistency_message(c)}   "
                                      f"({c['days_logged']}/{c['window']} days logged, "
                                      f"best streak {c['longest_streak']})")

    # ------------------------------------------------------------ calendar
    def _build_calendar(self, parent):
        nav = ttk.Frame(parent)
        nav.pack(pady=8)
        ttk.Button(nav, text="◀", width=3, command=lambda: self._shift_month(-1)).pack(side="left")
        self.cal_title = ttk.Label(nav, text="", width=20, anchor="center", font=("TkDefaultFont", 12, "bold"))
        self.cal_title.pack(side="left", padx=8)
        ttk.Button(nav, text="▶", width=3, command=lambda: self._shift_month(1)).pack(side="left")
        self.cal_grid = tk.Frame(parent)
        self.cal_grid.pack(padx=10, pady=4)
        ttk.Label(parent, text="Green = food logged. Click a day to view or edit it.").pack(pady=2)
        self.cal_detail = ttk.Label(parent, text="", font=("Courier", 11), justify="left")
        self.cal_detail.pack(anchor="w", padx=20, pady=10)

    def _shift_month(self, delta):
        m = self.cal_month.month - 1 + delta
        self.cal_month = date(self.cal_month.year + m // 12, m % 12 + 1, 1)
        self.refresh_calendar()

    def _select_day(self, d):
        self.selected = d
        self.refresh_log()
        self.refresh_calendar()

    def refresh_calendar(self):
        for w in self.cal_grid.winfo_children():
            w.destroy()
        self.cal_title.config(text=self.cal_month.strftime("%B %Y"))
        for i, name in enumerate(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]):
            tk.Label(self.cal_grid, text=name, width=6, font=("TkDefaultFont", 9, "bold")).grid(row=0, column=i)
        for r, week in enumerate(calendar.monthcalendar(self.cal_month.year, self.cal_month.month), start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                d = date(self.cal_month.year, self.cal_month.month, day)
                log = self.store.logs.get(d)
                logged = bool(log and log.foods)
                bg = "#bbf7d0" if logged else "#f3f4f6"
                if d == self.selected:
                    bg = "#93c5fd"
                lbl = tk.Label(self.cal_grid, text=str(day), width=6, height=2, bg=bg,
                               relief="solid" if d == self.today else "flat", borderwidth=2, cursor="hand2")
                lbl.grid(row=r, column=c, padx=1, pady=1)
                lbl.bind("<Button-1>", lambda e, d=d: self._select_day(d))

        d = self.selected
        person = self.store.person_on(d)
        text = d.strftime("%A, %d %B %Y") + "\n"
        if person:
            s = calculate_daily_summary(person, self.store.get_log(d))
            text += (f"Consumed {s['calories_consumed']:.0f} kcal | Burned {s['calories_burned']:.0f} kcal | "
                     f"Balance {s['calorie_balance']:+.0f}\n"
                     f"Protein {s['protein_g']:.1f} g | Carbs {s['carbs_g']:.1f} g | Fat {s['fat_g']:.1f} g")
        else:
            text += "Save your profile on the Log tab to see calories burned."
        self.cal_detail.config(text=text)

    # ------------------------------------------------------------ stats + charts
    def _build_stats(self, parent):
        top = ttk.Frame(parent)
        top.pack(pady=8)
        for kind, label in (("day", "Day"), ("week", "Week"), ("month", "Month")):
            ttk.Radiobutton(top, text=label, value=kind, variable=self.stat_kind,
                            command=self.refresh_stats).pack(side="left", padx=8)
        self.stat_text = ttk.Label(parent, text="", font=("Courier", 11), justify="left")
        self.stat_text.pack(anchor="w", padx=14, pady=4)
        ttk.Label(parent, text="Calories: consumed (blue) vs burned (orange)").pack(anchor="w", padx=14)
        self.chart = tk.Canvas(parent, width=760, height=240, bg="white", highlightthickness=1,
                               highlightbackground="#d1d5db")
        self.chart.pack(padx=14, pady=4)
        ttk.Label(parent, text="Average daily nutrition (grams)").pack(anchor="w", padx=14)
        report_bar = ttk.Frame(parent)
        report_bar.pack(fill="x", padx=14, pady=(6, 2))
        self.adherence_label = ttk.Label(report_bar, text="", justify="left")
        self.adherence_label.pack(side="left", fill="x", expand=True)
        ttk.Button(report_bar, text="Export CSV", command=self.export_stats_csv).pack(side="right")
        self.macro_chart = tk.Canvas(parent, width=760, height=110, bg="white", highlightthickness=1,
                                     highlightbackground="#d1d5db")
        self.macro_chart.pack(padx=14, pady=4)
        ttk.Label(parent, text="Progress insights").pack(anchor="w", padx=14, pady=(6, 0))
        self.insight_label = ttk.Label(parent, text="", justify="left", wraplength=760)
        self.insight_label.pack(anchor="w", padx=14, pady=(2, 8))

    def refresh_stats(self):
        self.chart.delete("all")
        self.macro_chart.delete("all")
        person = self.store.profile
        if not person:
            self.stat_text.config(text="Save your profile on the Log tab to see statistics.")
            self.insight_label.config(text="")
            self.adherence_label.config(text="")
            return
        kind = self.stat_kind.get()
        recs, agg = stats.period_stats(person, self.store.logs, kind, self.selected,
                                       person_on=self.store.person_on)
        title = {"day": self.selected.strftime("%d %B %Y"),
                 "week": "Week of " + stats.week_range(self.selected)[0].strftime("%d %b"),
                 "month": self.selected.strftime("%B %Y")}[kind]
        self.stat_text.config(text=(
            f"{title}  ({agg['days_logged']}/{agg['days_in_range']} days logged)\n"
            f"Consumed: {agg['consumed_total']:.0f} kcal total, {agg['consumed_avg']:.0f}/day\n"
            f"Burned:   {agg['burned_total']:.0f} kcal total, {agg['burned_avg']:.0f}/day\n"
            f"Balance:  {agg['balance_total']:+.0f} kcal total\n"
            f"Average macros: {agg['protein_avg']:.0f} g protein | {agg['carbs_avg']:.0f} g carbs | {agg['fat_avg']:.0f} g fat"))
        self._draw_calorie_bars(recs, kind)
        self._draw_macro_bars(agg)
        insights = stats.progress_insights(
            recs, lambda d: calculate_targets(self.store.person_on(d) or person)["calories"]
        )
        self.insight_label.config(text=self._format_progress_insights(insights))
        adherence = stats.target_adherence(
            recs, lambda d: calculate_targets(self.store.person_on(d) or person)["calories"]
        )
        if adherence["days_logged"]:
            avg = adherence["average_variance"]
            direction = "over" if avg > 0 else "under" if avg < 0 else "exactly at"
            self.adherence_label.config(
                text=(f"Target adherence: {adherence['days_on_target']}/{adherence['days_logged']} days "
                      f"within ±10% ({adherence['on_target_pct']:.0f}%)  |  "
                      f"Average {abs(avg):.0f} kcal {direction} target  |  "
                      f"Exercise logged on {adherence['exercise_days']} day(s)")
            )
        else:
            self.adherence_label.config(text="Target adherence: log food to see how consistently you are landing near target.")

    def _format_progress_insights(self, insights):
        if not insights["days_logged"]:
            return "Log some food to build personalized insights."
        best = insights["best_day"]
        high = insights["highest_day"]
        low = insights["lowest_day"]
        variance = insights["average_variance"]
        direction = "over" if variance > 0 else "under" if variance < 0 else "exactly at"
        return (
            f"Closest-to-target day: {best['date'].strftime('%d %b')} "
            f"({best['variance']:+.0f} kcal).  "
            f"Highest intake: {high['calories']:.0f} kcal on {high['date'].strftime('%d %b')}.  "
            f"Lowest: {low['calories']:.0f} kcal on {low['date'].strftime('%d %b')}.\n"
            f"Average target {insights['average_target']:.0f} kcal; average intake was "
            f"{abs(variance):.0f} kcal {direction}.  "
            f"Exercise logged on {insights['exercise_days']} day(s), "
            f"{insights['exercise_calories']:.0f} exercise kcal total.")

    def export_stats_csv(self):
        person = self.store.profile
        if not person:
            messagebox.showinfo("Export CSV", "Set up your profile first.")
            return
        kind = self.stat_kind.get()
        recs, _ = stats.period_stats(person, self.store.logs, kind, self.selected,
                                     person_on=self.store.person_on)
        targets = {
            r["day"]: calculate_targets(self.store.person_on(r["day"]) or person)["calories"]
            for r in recs
        }
        rows = period_csv_rows(recs, targets)
        default_name = f"calorie_tracker_{kind}_{self.selected.isoformat()}.csv"
        path = filedialog.asksaveasfilename(
            title="Export calorie report",
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            write_csv(path, rows)
        except OSError as exc:
            messagebox.showerror("Export CSV", f"Could not save the report.\n\n{exc}")
            return
        messagebox.showinfo("Export CSV", f"Report saved to:\n{path}")

    def _draw_calorie_bars(self, recs, kind):
        c, W, H = self.chart, 760, 240
        left, bottom, top = 50, H - 28, 14
        peak = max([r["calories_consumed"] for r in recs] + [r["calories_burned"] for r in recs] + [1])
        peak = (int(peak / 500) + 1) * 500
        for i in range(0, 5):
            y = bottom - (bottom - top) * i / 4
            c.create_line(left, y, W - 10, y, fill="#e5e7eb")
            c.create_text(left - 6, y, text=f"{peak * i / 4:.0f}", anchor="e", font=("TkDefaultFont", 8))
        slot = (W - left - 10) / len(recs)
        bar = max(2, min(22, slot / 3))
        for i, r in enumerate(recs):
            x = left + slot * i + slot / 2
            for off, key, color in ((-bar / 2, "calories_consumed", CONSUMED_COLOR),
                                    (bar / 2, "calories_burned", BURNED_COLOR)):
                if key == "calories_burned" and not r["logged"] and kind != "day":
                    continue  # don't draw burn for days with no log
                h = (bottom - top) * r[key] / peak
                c.create_rectangle(x + off - bar / 2, bottom - h, x + off + bar / 2, bottom,
                                   fill=color, outline="")
            if kind == "month":
                label = str(r["day"].day) if r["day"].day % 5 == 1 or r["day"].day == 1 else ""
            elif kind == "week":
                label = r["day"].strftime("%a")
            else:
                label = r["day"].strftime("%d %b")
            c.create_text(x, bottom + 12, text=label, font=("TkDefaultFont", 8))

    def _draw_macro_bars(self, agg):
        c = self.macro_chart
        vals = {"Protein": agg["protein_avg"], "Carbs": agg["carbs_avg"], "Fat": agg["fat_avg"]}
        peak = max(list(vals.values()) + [1])
        for i, (name, v) in enumerate(vals.items()):
            y = 12 + i * 32
            c.create_text(8, y + 10, text=name, anchor="w", font=("TkDefaultFont", 9))
            w = 560 * v / peak
            c.create_rectangle(80, y, 80 + w, y + 20, fill=MACRO_COLORS[name], outline="")
            c.create_text(86 + w, y + 10, text=f"{v:.1f} g", anchor="w", font=("TkDefaultFont", 9))


if __name__ == "__main__":
    App().mainloop()
