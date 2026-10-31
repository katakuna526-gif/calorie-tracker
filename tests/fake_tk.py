"""A tiny stand-in for tkinter, so the screens can be built and clicked through in tests
without a display (or without Tk installed at all).

It is not a real GUI: widgets just remember their options, so tests can read what a label
would show and call the same functions a button click would call.
"""

import types
from unittest import mock


class Var:
    """Stands in for tk.StringVar: holds a value and calls trace callbacks when it is set."""

    def __init__(self, master=None, value="", name=None):
        self._value = "" if value is None else value
        self._callbacks = []

    def get(self):
        return self._value

    def set(self, value):
        self._value = value
        for callback in list(self._callbacks):
            callback("var", "", "write")

    def trace_add(self, mode, callback):
        self._callbacks.append(callback)


class Widget:
    """Any widget. Unknown methods (pack, grid, bind, ...) quietly do nothing."""

    def __init__(self, master=None, *args, **opts):
        self.master = master
        self.opts = dict(opts)
        self._children = []
        if isinstance(master, Widget):
            master._children.append(self)

    def config(self, **opts):
        self.opts.update(opts)

    configure = config

    def __setitem__(self, key, value):
        self.opts[key] = value

    def cget(self, key):
        return self.opts.get(key, "")

    def __getitem__(self, key):
        return self.opts[key]

    def winfo_children(self):
        return list(self._children)

    def destroy(self):
        if isinstance(self.master, Widget) and self in self.master._children:
            self.master._children.remove(self)

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return lambda *args, **kwargs: None


class Listbox(Widget):
    def __init__(self, master=None, **opts):
        super().__init__(master, **opts)
        self.items = []
        self.selection = ()

    def insert(self, index, text):
        self.items.append(text)

    def delete(self, first, last=None):
        self.items.clear()
        self.selection = ()

    def curselection(self):
        return self.selection

    def selection_set(self, index):
        self.selection = (index,)

    def selection_clear(self, first, last=None):
        self.selection = ()


class Canvas(Widget):
    """Records what is drawn on it so a chart can be inspected, or turned into a picture."""

    def __init__(self, master=None, **opts):
        super().__init__(master, **opts)
        self.items = []

    def delete(self, *tags):
        self.items.clear()

    def _record(self, kind, args, opts):
        self.items.append((kind, args, opts))
        return len(self.items)

    def create_line(self, *coords, **opts):
        return self._record("line", coords, opts)

    def create_rectangle(self, *coords, **opts):
        return self._record("rect", coords, opts)

    def create_oval(self, *coords, **opts):
        return self._record("oval", coords, opts)

    def create_text(self, x, y, **opts):
        return self._record("text", (x, y), opts)

    def texts(self):
        return [opts.get("text", "") for kind, _, opts in self.items if kind == "text"]


_ANCHORS = {  # tk anchor -> (svg text-anchor, svg dominant-baseline)
    "center": ("middle", "central"), "w": ("start", "central"), "e": ("end", "central"),
    "n": ("middle", "hanging"), "s": ("middle", "text-after-edge"),
    "nw": ("start", "hanging"), "ne": ("end", "hanging"),
    "sw": ("start", "text-after-edge"), "se": ("end", "text-after-edge"),
}


def canvas_to_svg(canvas, width, height, background="#ffffff"):
    """Draws the recorded items as an SVG picture (fonts and spacing are approximate)."""
    from xml.sax.saxutils import escape
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}"><rect width="{width}" height="{height}" fill="{background}"/>']

    def paint(opts, fill_key="fill", outline_key="outline"):
        fill, outline = opts.get(fill_key) or "none", opts.get(outline_key) or "none"
        stroke = f' stroke="{outline}" stroke-width="{opts.get("width", 1)}"' if outline != "none" else ""
        return f'fill="{fill}"{stroke}'

    for kind, args, opts in canvas.items:
        if kind == "line":
            points = " ".join(f"{args[i]:.1f},{args[i + 1]:.1f}" for i in range(0, len(args), 2))
            out.append(f'<polyline points="{points}" fill="none" stroke="{opts.get("fill", "black")}" '
                       f'stroke-width="{opts.get("width", 1)}" stroke-linejoin="round" stroke-linecap="round"/>')
        elif kind == "rect":
            x0, y0, x1, y1 = args
            out.append(f'<rect x="{min(x0, x1):.1f}" y="{min(y0, y1):.1f}" width="{abs(x1 - x0):.1f}" '
                       f'height="{abs(y1 - y0):.1f}" {paint(opts)}/>')
        elif kind == "oval":
            x0, y0, x1, y1 = args
            out.append(f'<ellipse cx="{(x0 + x1) / 2:.1f}" cy="{(y0 + y1) / 2:.1f}" rx="{abs(x1 - x0) / 2:.1f}" '
                       f'ry="{abs(y1 - y0) / 2:.1f}" {paint(opts)}/>')
        elif kind == "text":
            font = opts.get("font") or ("sans", 9)
            size_px = round(font[1] * 96 / 72, 1)
            weight = "bold" if "bold" in font[2:] else "normal"
            anchor, baseline = _ANCHORS.get(opts.get("anchor", "center"), _ANCHORS["center"])
            out.append(f'<text x="{args[0]:.1f}" y="{args[1]:.1f}" fill="{opts.get("fill", "black")}" '
                       f'font-family="Segoe UI, Arial, sans-serif" font-size="{size_px}" font-weight="{weight}" '
                       f'text-anchor="{anchor}" dominant-baseline="{baseline}">{escape(str(opts.get("text", "")))}</text>')
    out.append("</svg>")
    return "\n".join(out)



def install():
    """Returns a dict to patch into sys.modules so `import tkinter` finds the stand-in."""
    tk = types.ModuleType("tkinter")
    ttk = types.ModuleType("tkinter.ttk")
    messagebox = types.ModuleType("tkinter.messagebox")
    filedialog = types.ModuleType("tkinter.filedialog")
    filedialog.asksaveasfilename = mock.Mock(return_value="")
    filedialog.askopenfilename = mock.Mock(return_value="")

    class Style:
        def __init__(self, master=None):
            self.settings = {}
            self.current_theme = "default"

        def theme_use(self, name=None):
            if name is not None:
                self.current_theme = name
            return self.current_theme

        def configure(self, style, **opts):
            self.settings.setdefault(style, {}).update(opts)

        def map(self, style, **opts):
            self.settings.setdefault(style, {}).update(opts)

    for name in ("Tk", "Toplevel", "Frame", "Label", "Button", "Entry"):
        setattr(tk, name, Widget)
    tk.Canvas = Canvas
    tk.Listbox = Listbox
    tk.StringVar = Var
    tk.TclError = type("TclError", (Exception,), {})
    for name in ("Frame", "LabelFrame", "Label", "Button", "Entry", "Combobox",
                 "Notebook", "Radiobutton", "Scrollbar", "Progressbar"):
        setattr(ttk, name, Widget)
    ttk.Style = Style

    messagebox.showerror = mock.Mock()
    messagebox.showinfo = mock.Mock()
    messagebox.showwarning = mock.Mock()
    messagebox.askyesno = mock.Mock(return_value=True)

    tk.ttk = ttk
    tk.messagebox = messagebox
    tk.filedialog = filedialog
    return {"tkinter": tk, "tkinter.ttk": ttk, "tkinter.messagebox": messagebox,
            "tkinter.filedialog": filedialog}
