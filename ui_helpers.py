"""Small Tkinter helpers shared by the screens."""

import tkinter as tk
from tkinter import ttk

# Widgets that scroll themselves; the page should not scroll while the pointer is over them.
_SELF_SCROLLING = ("Listbox", "TCombobox", "Text")


class ScrollFrame(ttk.Frame):
    """A frame whose contents scroll vertically when they are taller than the window.

    Put your widgets in `.inner`, not in the ScrollFrame itself.
    """

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set, yscrollincrement=24)
        bar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.inner = ttk.Frame(self.canvas)
        self._window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", self._on_inner_resize)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

        # One app-wide binding; the handler checks the pointer is over this frame.
        self.bind_all("<MouseWheel>", self._on_wheel, add="+")  # Windows and macOS
        self.bind_all("<Button-4>", self._on_wheel, add="+")    # Linux scroll up
        self.bind_all("<Button-5>", self._on_wheel, add="+")    # Linux scroll down

    def _on_inner_resize(self, _event):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_resize(self, event):
        self.canvas.itemconfigure(self._window, width=event.width)  # contents follow the window width

    def _pointer_is_over_me(self, event):
        try:
            widget = self.winfo_containing(event.x_root, event.y_root)
        except (KeyError, tk.TclError):  # internal widgets such as a combobox drop-down
            return None
        node = widget
        while node is not None:
            if node is self:
                return widget
            node = node.master
        return None

    def _on_wheel(self, event):
        if not self.winfo_viewable():
            return
        widget = self._pointer_is_over_me(event)
        if widget is None or widget.winfo_class() in _SELF_SCROLLING:
            return
        if self.inner.winfo_reqheight() <= self.canvas.winfo_height():
            return  # everything fits, nothing to scroll
        if event.num == 4:
            direction = -1
        elif event.num == 5:
            direction = 1
        else:
            direction = -1 if event.delta > 0 else 1
        steps = 3 if event.num in (4, 5) else max(1, abs(event.delta) // 120) * 3
        self.canvas.yview_scroll(direction * steps, "units")
