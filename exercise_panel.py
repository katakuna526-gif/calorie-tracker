"""The exercise section of the Log tab.

Pick an activity and effort level and the calories are estimated from your weight,
or choose "Other" and type the calories yourself (for example from a fitness watch).
The maths lives in calorie_engine.py and exercises.py, which are tested without a window.
"""

import tkinter as tk
from tkinter import ttk, messagebox

from calorie_engine import ExerciseEntry, is_unusually_high_burn
from exercises import EXERCISES, INTENSITIES, estimate_calories, get_exercise
from units import from_kg, weight_unit_label

OTHER = "Other (I'll enter the calories)"


class ExercisePanel(ttk.LabelFrame):
    def __init__(self, parent, store, get_log, get_weight, on_change, get_weight_unit=lambda: "kg"):
        super().__init__(parent, text="3. Exercise")
        self.store = store
        self.get_log = get_log        # function returning the DailyLog being edited
        self.get_weight = get_weight  # function returning weight in kg, or None without a profile
        self.get_weight_unit = get_weight_unit
        self.on_change = on_change
        self._build()
        self._update_estimate()

    # ---------------------------------------------------------- layout
    def _build(self):
        row1 = ttk.Frame(self)
        row1.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(row1, text="Activity").pack(side="left")
        self.activity = tk.StringVar(value=EXERCISES[0].name)
        box = ttk.Combobox(row1, textvariable=self.activity, state="readonly", width=26,
                           values=[e.name for e in EXERCISES] + [OTHER])
        box.pack(side="left", padx=6)
        ttk.Label(row1, text="Effort").pack(side="left", padx=(8, 0))
        self.intensity = tk.StringVar(value="moderate")
        self.intensity_box = ttk.Combobox(row1, textvariable=self.intensity, state="readonly",
                                          width=10, values=list(INTENSITIES))
        self.intensity_box.pack(side="left", padx=6)
        ttk.Label(row1, text="Minutes").pack(side="left", padx=(8, 0))
        self.minutes = tk.StringVar(value="30")
        ttk.Entry(row1, textvariable=self.minutes, width=7).pack(side="left", padx=6)

        self.hint = ttk.Label(self, text="", foreground="#6b7280")
        self.hint.pack(anchor="w", padx=6)

        row2 = ttk.Frame(self)
        row2.pack(fill="x", padx=6, pady=2)
        ttk.Label(row2, text="Name").pack(side="left")
        self.name = tk.StringVar()
        self.name_entry = ttk.Entry(row2, textvariable=self.name, width=18)
        self.name_entry.pack(side="left", padx=6)
        ttk.Label(row2, text="Calories burned").pack(side="left", padx=(8, 0))
        self.calories = tk.StringVar()
        self.cal_entry = ttk.Entry(row2, textvariable=self.calories, width=8)
        self.cal_entry.pack(side="left", padx=6)
        ttk.Button(row2, text="Add exercise", command=self._add).pack(side="left", padx=10)

        self.estimate = ttk.Label(self, text="", font=("TkDefaultFont", 10, "bold"))
        self.estimate.pack(anchor="w", padx=6, pady=2)

        self.entries = tk.Listbox(self, height=3, exportselection=False)
        self.entries.pack(fill="x", padx=6, pady=(4, 0))
        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=6, pady=4)
        ttk.Button(actions, text="Edit selected", command=self._edit).pack(side="left")
        ttk.Button(actions, text="Duplicate selected", command=self._duplicate).pack(side="left", padx=5)
        ttk.Button(actions, text="Remove selected", command=self._remove).pack(side="left")
        self.entries.bind("<Double-Button-1>", lambda e: self._edit())

        for var in (self.activity, self.intensity, self.minutes):
            var.trace_add("write", lambda *_: self._update_estimate())

    def _manual(self) -> bool:
        return self.activity.get() == OTHER

    # ---------------------------------------------------------- estimate
    def _update_estimate(self):
        manual = self._manual()
        self.intensity_box.config(state="disabled" if manual else "readonly")
        self.name_entry.config(state="normal" if manual else "disabled")
        self.cal_entry.config(state="normal" if manual else "disabled")
        if manual:
            self.hint.config(text="Type a name and the calories burned (for example from your watch or gym machine).")
            self.estimate.config(text="")
            return

        exercise = get_exercise(self.activity.get())
        self.hint.config(text=exercise.note if exercise else "")
        weight = self.get_weight()
        if weight is None:
            self.estimate.config(text="Set up your profile to get a calorie estimate.")
            return
        try:
            kcal = estimate_calories(self.activity.get(), self.intensity.get(), weight, float(self.minutes.get()))
            shown_weight = from_kg(weight, self.get_weight_unit())
            self.estimate.config(text=f"Estimated burn: about {kcal:.0f} kcal  "
                                       f"(based on {shown_weight:g} {weight_unit_label(self.get_weight_unit())})")
        except ValueError:
            self.estimate.config(text="Enter the minutes to see an estimate.")

    # ---------------------------------------------------------- add / remove
    def _add(self):
        try:
            minutes = float(self.minutes.get())
        except ValueError:
            messagebox.showerror("Add exercise", "Minutes must be a number.")
            return
        try:
            if self._manual():
                name = self.name.get().strip() or "Exercise"
                kcal = float(self.calories.get())
            else:
                weight = self.get_weight()
                if weight is None:
                    messagebox.showinfo("Add exercise", "Set up your profile first so we can estimate the calories, "
                                                        "or choose \"Other\" and enter them yourself.")
                    return
                name = f"{self.activity.get()} ({self.intensity.get()})"
                kcal = estimate_calories(self.activity.get(), self.intensity.get(), weight, minutes)
            entry = ExerciseEntry(name=name, duration_minutes=minutes, calories_burned=kcal)
        except ValueError as exc:
            messagebox.showerror("Add exercise", str(exc) if str(exc) and "could not convert" not in str(exc)
                                 else "Calories burned must be a number.")
            return

        if is_unusually_high_burn(minutes, kcal):
            if not messagebox.askyesno(
                    "Check this entry",
                    f"{kcal:.0f} kcal in {minutes:g} minutes is an unusually high burn "
                    f"({kcal / (minutes / 60):.0f} kcal per hour).\n\nAdd it anyway?"):
                return
        self.get_log().exercises.append(entry)
        self.store.save()
        self.on_change()

    def _selected_index(self):
        sel = self.entries.curselection()
        if not sel or sel[0] >= len(self.get_log().exercises):
            return None
        return sel[0]

    def _edit(self):
        idx = self._selected_index()
        if idx is None:
            return
        ExerciseEntryDialog(self, self.get_log().exercises[idx], self._finish_edit)

    def _finish_edit(self, idx, replacement):
        self.get_log().exercises[idx] = replacement
        self.store.save()
        self.on_change()

    def _duplicate(self):
        idx = self._selected_index()
        if idx is None:
            return
        original = self.get_log().exercises[idx]
        self.get_log().exercises.insert(idx + 1, type(original)(**original.__dict__))
        self.store.save()
        self.on_change()

    def _remove(self):
        idx = self._selected_index()
        if idx is not None:
            del self.get_log().exercises[idx]
            self.store.save()
            self.on_change()

    def refresh(self):
        self.entries.delete(0, "end")
        for x in self.get_log().exercises:
            self.entries.insert("end", f"{x.name}: {x.duration_minutes:g} min -> {x.calories_burned:.0f} kcal")
        self._update_estimate()  # the weight may have changed


class ExerciseEntryDialog(tk.Toplevel):
    """Edit a logged exercise without changing its activity estimate model."""
    def __init__(self, parent, entry, on_save):
        super().__init__(parent)
        self.title("Edit exercise entry")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.entry = entry
        self.on_save = on_save
        form = ttk.Frame(self)
        form.pack(padx=16, pady=12)
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", pady=3)
        self.name = tk.StringVar(value=entry.name)
        ttk.Entry(form, textvariable=self.name, width=28).grid(row=0, column=1, padx=8)
        ttk.Label(form, text="Minutes").grid(row=1, column=0, sticky="w", pady=3)
        self.minutes = tk.StringVar(value=f"{entry.duration_minutes:g}")
        ttk.Entry(form, textvariable=self.minutes, width=12).grid(row=1, column=1, padx=8, sticky="w")
        ttk.Label(form, text="Calories burned").grid(row=2, column=0, sticky="w", pady=3)
        self.calories = tk.StringVar(value=f"{entry.calories_burned:g}")
        ttk.Entry(form, textvariable=self.calories, width=12).grid(row=2, column=1, padx=8, sticky="w")
        self.error = ttk.Label(self, text="", foreground="#b91c1c", wraplength=360)
        self.error.pack(padx=16)
        buttons = ttk.Frame(self)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Save changes", command=self._save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    def _save(self):
        try:
            name = self.name.get().strip() or "Exercise"
            minutes = float(self.minutes.get())
            calories = float(self.calories.get())
            replacement = type(self.entry)(name=name, duration_minutes=minutes, calories_burned=calories)
        except ValueError as exc:
            self.error.config(text=str(exc) or "Please check the values.")
            return
        sel = self.master.entries.curselection()
        if not sel:
            self.error.config(text="Select the exercise again and try editing.")
            return
        self.destroy()
        self.on_save(sel[0], replacement)
