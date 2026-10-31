"""Food logging UI: search, servings, meals, favorites, recent foods and entry editing."""

import tkinter as tk
from tkinter import ttk, messagebox

from calorie_engine import MEALS, MEAL_LABELS, calculate_meal_totals
from foods import FoodItem, default_meal, grams_for

GRAMS = "grams"
HINT = "Search for a food, choose a serving or grams, then add it to a meal."


class FoodPanel(ttk.LabelFrame):
    def __init__(self, parent, store, get_log, on_change):
        super().__init__(parent, text="2. What did you eat?")
        self.store = store
        self.get_log = get_log
        self.on_change = on_change
        self.results = []
        self.selected = None
        self.entry_map = []
        self._build()
        self._search()
        self.refresh()

    def _build(self):
        top = ttk.Frame(self)
        top.pack(fill="x", padx=6, pady=(6, 2))
        ttk.Label(top, text="Search").pack(side="left")
        self.query = tk.StringVar()
        self.query.trace_add("write", lambda *_: self._search())
        ttk.Entry(top, textvariable=self.query, width=28).pack(side="left", padx=6)
        ttk.Button(top, text="Custom food...", command=self._open_custom).pack(side="right")
        self.fav_btn = ttk.Button(top, text="☆ Favorite", command=self._toggle_favorite, state="disabled")
        self.fav_btn.pack(side="right", padx=6)

        self.result_list = tk.Listbox(self, height=5, exportselection=False)
        self.result_list.pack(fill="x", padx=6)
        self.result_list.bind("<<ListboxSelect>>", lambda e: self._select())

        self.info = ttk.Label(self, text=HINT, foreground="#6b7280", wraplength=760)
        self.info.pack(anchor="w", padx=6, pady=2)

        add = ttk.Frame(self)
        add.pack(fill="x", padx=6, pady=2)
        ttk.Label(add, text="Quantity").pack(side="left")
        self.qty = tk.StringVar(value="100")
        ttk.Entry(add, textvariable=self.qty, width=7).pack(side="left", padx=4)
        self.unit = tk.StringVar(value=GRAMS)
        self.unit_box = ttk.Combobox(add, textvariable=self.unit, values=[GRAMS], width=23, state="readonly")
        self.unit_box.pack(side="left", padx=4)
        ttk.Label(add, text="Meal").pack(side="left", padx=(10, 0))
        self.meal = tk.StringVar(value=MEAL_LABELS[default_meal()])
        ttk.Combobox(add, textvariable=self.meal, values=[MEAL_LABELS[m] for m in MEALS],
                     width=11, state="readonly").pack(side="left", padx=4)
        ttk.Button(add, text="Add food", command=self._add).pack(side="left", padx=8)

        quick = ttk.Frame(self)
        quick.pack(fill="x", padx=6, pady=(4, 0))
        ttk.Button(quick, text="Copy yesterday's meals", command=self._copy_yesterday).pack(side="left")
        ttk.Button(quick, text="Copy selected meal", command=self._copy_selected_meal).pack(side="left", padx=6)

        ttk.Label(self, text="Today's food", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=6, pady=(7, 1))
        self.entries = tk.Listbox(self, height=8, exportselection=False)
        self.entries.pack(fill="x", padx=6)
        self.entries.bind("<Double-Button-1>", lambda e: self._edit())

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=6, pady=4)
        ttk.Button(actions, text="Edit selected", command=self._edit).pack(side="left")
        ttk.Button(actions, text="Duplicate selected", command=self._duplicate).pack(side="left", padx=5)
        ttk.Button(actions, text="Delete selected", command=self._remove).pack(side="left")
        self.meal_totals = ttk.Label(self, text="", foreground="#374151")
        self.meal_totals.pack(anchor="w", padx=6, pady=(0, 6))

    def _search(self):
        text = self.query.get()
        if text.strip():
            self.results = self.store.food_db.search(text)
        else:
            self.results = self.store.food_db.suggestions(self.store.favorites, self.store.recents)
        self.result_list.delete(0, "end")
        for item in self.results:
            star = "★ " if self.store.is_favorite(item.name) else ""
            tag = "  [mine]" if item.custom else ""
            self.result_list.insert("end", f"{star}{item.name}   ({item.calories_per_100g:g} kcal/100 g){tag}")
        if not self.results:
            self.result_list.insert("end", "No matches. Use \"Custom food...\" to add it." if text.strip()
                                    else "Your favorites and recent foods will appear here.")
        if self.selected in self.results:
            self.result_list.selection_set(self.results.index(self.selected))
        else:
            self.selected = None
            self._show_selection()

    def _select(self):
        sel = self.result_list.curselection()
        if not sel or sel[0] >= len(self.results):
            return
        self.selected = self.results[sel[0]]
        self._show_selection()

    def _show_selection(self):
        item = self.selected
        if not item:
            self.info.config(text=HINT)
            self.unit_box.config(values=[GRAMS])
            self.unit.set(GRAMS)
            self.fav_btn.config(text="☆ Favorite", state="disabled")
            return
        self.info.config(text=(f"{item.name}: {item.calories_per_100g:g} kcal, protein {item.protein_per_100g:g} g, "
                               f"carbs {item.carbs_per_100g:g} g, fat {item.fat_per_100g:g} g per 100 g"))
        units = [GRAMS] + [f"{label} ({g:g} g)" for label, g in item.servings.items()]
        self.unit_box.config(values=units)
        if item.servings:
            self.unit.set(units[1])
            self.qty.set("1")
        else:
            self.unit.set(GRAMS)
            self.qty.set("100")
        self._update_fav_button()

    def _update_fav_button(self):
        if self.selected:
            self.fav_btn.config(text="★ Favorited" if self.store.is_favorite(self.selected.name) else "☆ Favorite",
                                state="normal")

    def _toggle_favorite(self):
        if self.selected:
            self.store.toggle_favorite(self.selected.name)
            self._update_fav_button()
            self._search()

    def _meal_key(self):
        return next(m for m in MEALS if MEAL_LABELS[m] == self.meal.get())

    def _grams_from_controls(self, item):
        quantity = float(self.qty.get())
        unit = self.unit.get()
        if unit == GRAMS:
            return grams_for(quantity)
        label = unit.rsplit(" (", 1)[0]
        return grams_for(quantity, item.servings[label])

    def _add(self):
        if not self.selected:
            messagebox.showinfo("Add food", "Search for a food and click it in the list first.")
            return
        try:
            entry = self.selected.to_entry(self._grams_from_controls(self.selected), self._meal_key())
        except (ValueError, KeyError, StopIteration) as exc:
            messagebox.showerror("Add food", str(exc) or "Please check the amount.")
            return
        self.get_log().foods.append(entry)
        self.store.record_recent(self.selected.name)
        self.store.save()
        self.on_change()

    def _selected_index(self):
        sel = self.entries.curselection()
        if not sel or sel[0] >= len(self.entry_map):
            return None
        idx = self.entry_map[sel[0]]
        return idx if idx is not None else None

    def _remove(self):
        idx = self._selected_index()
        if idx is None:
            return
        del self.get_log().foods[idx]
        self.store.save()
        self.on_change()

    def _duplicate(self):
        idx = self._selected_index()
        if idx is None:
            return
        original = self.get_log().foods[idx]
        self.get_log().foods.insert(idx + 1, type(original)(**original.__dict__))
        self.store.record_recent(original.name)
        self.store.save()
        self.on_change()

    def _edit(self):
        idx = self._selected_index()
        if idx is None:
            return
        FoodEntryDialog(self, self.get_log().foods[idx], self._finish_edit)

    def _finish_edit(self, idx, replacement):
        self.get_log().foods[idx] = replacement
        self.store.save()
        self.on_change()

    def _copy_yesterday(self):
        from datetime import timedelta
        source_date = self.get_log().log_date - timedelta(days=1)
        source = self.store.logs.get(source_date)
        if not source or not source.foods:
            messagebox.showinfo("Copy meals", "There are no food entries yesterday to copy.")
            return
        target = self.get_log()
        target.foods.extend(type(f)(**f.__dict__) for f in source.foods)
        self.store.save()
        self.on_change()

    def _copy_selected_meal(self):
        idx = self._selected_index()
        if idx is None:
            return
        source_meal = self.get_log().foods[idx].meal
        choices = [m for m in MEALS if m != source_meal]
        MealCopyDialog(self, MEAL_LABELS[source_meal], choices, self._finish_copy_meal)

    def _finish_copy_meal(self, target_meal):
        foods = self.get_log().foods
        sel = self.entries.curselection()
        if not sel:
            return
        source_meal = foods[self.entry_map[sel[0]]].meal
        copies = []
        for f in foods:
            if f.meal == source_meal:
                data = dict(f.__dict__)
                data["meal"] = target_meal
                copies.append(type(f)(**data))
        foods.extend(copies)
        self.store.save()
        self.on_change()

    def refresh(self):
        foods = self.get_log().foods
        order = sorted(range(len(foods)), key=lambda i: (MEALS.index(foods[i].meal), i))
        self.entry_map = []
        self.entries.delete(0, "end")
        last_meal = None
        for i in order:
            f = foods[i]
            if f.meal != last_meal:
                if last_meal is not None:
                    self.entries.insert("end", "")
                    self.entry_map.append(None)
                meal_total = sum(x.calories for x in foods if x.meal == f.meal)
                self.entries.insert("end", f"--- {MEAL_LABELS[f.meal]} ({meal_total:.0f} kcal) ---")
                self.entry_map.append(None)
                last_meal = f.meal
            self.entries.insert("end", f"{MEAL_LABELS[f.meal]}: {f.name}, {f.grams:g} g -> {f.calories:.0f} kcal "
                                       f"(P {f.protein:.1f} / C {f.carbs:.1f} / F {f.fat:.1f})")
            self.entry_map.append(i)
        totals = calculate_meal_totals(self.get_log())
        self.meal_totals.config(text="Daily meal totals: " + "   |   ".join(
            f"{MEAL_LABELS[m]} {totals[m]:.0f} kcal" for m in MEALS))

    def _open_custom(self):
        CustomFoodDialog(self, self.store, self._custom_added)

    def _custom_added(self, item):
        self.query.set(item.name)
        self._search()
        if item in self.results:
            self.result_list.selection_clear(0, "end")
            self.result_list.selection_set(self.results.index(item))
            self.selected = item
            self._show_selection()


class FoodEntryDialog(tk.Toplevel):
    def __init__(self, parent, entry, on_save):
        super().__init__(parent)
        self.title("Edit food entry")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.entry = entry
        self.on_save = on_save
        form = ttk.Frame(self)
        form.pack(padx=16, pady=12)
        ttk.Label(form, text="Food").grid(row=0, column=0, sticky="w", pady=3)
        ttk.Label(form, text=entry.name).grid(row=0, column=1, sticky="w", padx=8)
        ttk.Label(form, text="Grams").grid(row=1, column=0, sticky="w", pady=3)
        self.grams = tk.StringVar(value=f"{entry.grams:g}")
        ttk.Entry(form, textvariable=self.grams, width=16).grid(row=1, column=1, padx=8)
        ttk.Label(form, text="Meal").grid(row=2, column=0, sticky="w", pady=3)
        self.meal = tk.StringVar(value=MEAL_LABELS[entry.meal])
        ttk.Combobox(form, textvariable=self.meal, values=[MEAL_LABELS[m] for m in MEALS],
                     state="readonly", width=14).grid(row=2, column=1, padx=8)
        self.error = ttk.Label(self, text="", foreground="#b91c1c")
        self.error.pack(padx=16)
        buttons = ttk.Frame(self)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Save changes", command=self._save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    def _save(self):
        try:
            grams = float(self.grams.get())
            meal = next(m for m in MEALS if MEAL_LABELS[m] == self.meal.get())
            replacement = type(self.entry)(
                name=self.entry.name, grams=grams,
                calories_per_100g=self.entry.calories_per_100g,
                protein_per_100g=self.entry.protein_per_100g,
                carbs_per_100g=self.entry.carbs_per_100g,
                fat_per_100g=self.entry.fat_per_100g, meal=meal)
        except (ValueError, StopIteration) as exc:
            self.error.config(text=str(exc) or "Please check the entry.")
            return
        # Locate by identity in the caller's list before closing.
        idx = self.master.entry_map[self.master.entries.curselection()[0]] if self.master.entries.curselection() else None
        if idx is None:
            self.error.config(text="Select the entry again and try editing.")
            return
        self.destroy()
        self.on_save(idx, replacement)


class MealCopyDialog(tk.Toplevel):
    def __init__(self, parent, source_label, choices, on_save):
        super().__init__(parent)
        self.title("Copy meal")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.on_save = on_save
        ttk.Label(self, text=f"Copy all {source_label} entries into:").pack(padx=16, pady=(14, 5))
        self.meal = tk.StringVar(value=MEAL_LABELS[choices[0]])
        ttk.Combobox(self, textvariable=self.meal, values=[MEAL_LABELS[m] for m in choices],
                     state="readonly", width=14).pack(padx=16)
        buttons = ttk.Frame(self)
        buttons.pack(pady=12)
        ttk.Button(buttons, text="Copy", command=self._save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    def _save(self):
        target = next(m for m in MEALS if MEAL_LABELS[m] == self.meal.get())
        self.destroy()
        self.on_save(target)


class CustomFoodDialog(tk.Toplevel):
    """Add your own food, with nutrition per 100 g and an optional serving size."""
    def __init__(self, parent, store, on_added):
        super().__init__(parent)
        self.title("Add a custom food")
        self.transient(parent.winfo_toplevel())
        self.grab_set()
        self.store = store
        self.on_added = on_added
        self.vars = {}
        form = ttk.Frame(self)
        form.pack(padx=16, pady=12)
        rows = [("name", "Food name", ""), ("kcal", "Calories per 100 g", ""),
                ("protein", "Protein per 100 g", "0"), ("carbs", "Carbs per 100 g", "0"),
                ("fat", "Fat per 100 g", "0"),
                ("serving", "Serving name (optional, e.g. 1 slice)", ""),
                ("serving_g", "Serving size in grams (optional)", "")]
        for r, (key, label, default) in enumerate(rows):
            ttk.Label(form, text=label).grid(row=r, column=0, sticky="w", pady=3)
            self.vars[key] = tk.StringVar(value=default)
            ttk.Entry(form, textvariable=self.vars[key], width=24).grid(row=r, column=1, padx=8, pady=3)
        self.error = ttk.Label(self, text="", foreground="#b91c1c", wraplength=380)
        self.error.pack(padx=16)
        buttons = ttk.Frame(self)
        buttons.pack(pady=10)
        ttk.Button(buttons, text="Save food", command=self._save).pack(side="left", padx=6)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="left", padx=6)

    def _number(self, key, label):
        try:
            return float(self.vars[key].get() or 0)
        except ValueError:
            raise ValueError(f"{label} must be a number.")

    def _save(self):
        try:
            servings = {}
            serving = self.vars["serving"].get().strip()
            serving_g = self.vars["serving_g"].get().strip()
            if serving or serving_g:
                if not (serving and serving_g):
                    raise ValueError("Fill in both the serving name and its size in grams, or leave both empty.")
                servings[serving] = self._number("serving_g", "Serving size")
            item = FoodItem(name=self.vars["name"].get(),
                calories_per_100g=self._number("kcal", "Calories"),
                protein_per_100g=self._number("protein", "Protein"),
                carbs_per_100g=self._number("carbs", "Carbs"),
                fat_per_100g=self._number("fat", "Fat"), servings=servings, custom=True)
            self.store.add_custom_food(item)
        except ValueError as exc:
            self.error.config(text=str(exc))
            return
        self.destroy()
        self.on_added(item)
