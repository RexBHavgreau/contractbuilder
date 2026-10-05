"""
TMAI Contract Builder
Build 4

Choose a contract template, fill in what changes, and get a finished Word
contract. The wording that never changes comes from the template exactly as
written. Works on Windows and macOS.
"""
import datetime
import os
import pathlib
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

import core
import fieldsets

GREY = "#666666"
GOOD = "#1b6e2e"
BAD = "#b00020"
WARN = "#a15c00"
NO_SET = "(none)"
FORMATS = ["", "upper", "long", "list", "date", "date-formal", "date-short",
           "money", "money-words", "money-whole", "number", "number-words", "plural: work, works"]


def open_path(path):
    """Open a file or folder the way double-clicking it would."""
    path = str(path)
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)                                # noqa: S606
        elif sys.platform == "darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
    except OSError:
        pass


class ScrollFrame(ttk.Frame):
    """A frame whose contents scroll, for templates with many fields."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        bar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(2, 2, 14, 2))
        self.inner.bind("<Configure>",
                        lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self._win = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfigure(self._win, width=e.width))
        self.canvas.configure(yscrollcommand=bar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        bar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._wheel_on)
        self.canvas.bind("<Leave>", self._wheel_off)

    def _wheel_on(self, _):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda e: self.canvas.yview_scroll(3, "units"))

    def _wheel_off(self, _):
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(seq)

    def _wheel(self, event):
        if self.inner.winfo_height() <= self.canvas.winfo_height():
            return
        step = -event.delta if sys.platform == "darwin" else -int(event.delta / 120) * 3
        self.canvas.yview_scroll(step, "units")

    def top(self):
        self.canvas.yview_moveto(0)


class FieldRow:
    """
    One line of the form: a tick box saying whether the field is relevant to
    this contract, a label, a box to fill in, and a hint beneath.
    """

    def __init__(self, app, parent, field, row, slot=None):
        self.app = app
        self.field = field
        self.slot = slot                 # (group, number) for a work or a party
        self.var = self.text = self.hint = self.world = self.entry = None
        self.checks = {}                 # a checklist: label -> BooleanVar
        self.widgets = []
        self.use = tk.BooleanVar(value=True)
        kind = field.kind

        if kind == "yesno":
            self.var = tk.BooleanVar(value=False)
            ttk.Checkbutton(parent, text=field.name, variable=self.var,
                            command=self.changed).grid(row=row, column=0, columnspan=4,
                                                       sticky="w", pady=3)
            return

        include = ttk.Checkbutton(parent, variable=self.use, command=self.toggled)
        include.grid(row=row, column=0, sticky="nw", pady=(6, 0), padx=(0, 4))
        Tooltip(include, "Untick if this does not apply to this contract.")
        name = field.label if slot else field.name
        ttk.Label(parent, text=name + ("  *" if field.expected else "")).grid(
            row=row, column=1, sticky="nw", padx=(0, 14), pady=(7, 0))

        if kind == "long":
            self.text = tk.Text(parent, height=3, wrap="word", undo=True, font="TkDefaultFont",
                                relief="solid", borderwidth=1, highlightthickness=0)
            self.text.grid(row=row, column=2, columnspan=2, sticky="ew", pady=(5, 0))
            self.text.bind("<KeyRelease>", lambda e: self.changed())
            self.text.bind("<Tab>", self._focus_next)
            self.widgets.append(self.text)
        elif kind == "checklist":
            box = ttk.Frame(parent)
            box.grid(row=row, column=2, columnspan=2, sticky="w", pady=(5, 0))
            for i, label in enumerate(field.choices):
                v = tk.BooleanVar(value=False)
                cb = ttk.Checkbutton(box, text=label, variable=v, command=self.changed)
                cb.grid(row=i // 2, column=i % 2, sticky="w", padx=(0, 18), pady=1)
                self.checks[label] = v
                self.widgets.append(cb)
        elif kind == "territory":
            box = ttk.Frame(parent)
            box.grid(row=row, column=2, columnspan=2, sticky="ew", pady=(5, 0))
            box.columnconfigure(0, weight=1)
            self.var = tk.StringVar()
            self.entry = ttk.Entry(box, textvariable=self.var)
            self.entry.grid(row=0, column=0, sticky="ew")
            self.world = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(box, text="Worldwide", variable=self.world, command=self.changed)
            cb.grid(row=0, column=1, padx=(10, 0))
            self.var.trace_add("write", lambda *a: self.changed())
            self.widgets += [self.entry, cb]
        else:
            self.var = tk.StringVar()
            if kind == "choice":
                box = ttk.Combobox(parent, textvariable=self.var, state="readonly",
                                   values=[""] + field.choices)
            else:
                box = ttk.Entry(parent, textvariable=self.var)
            box.grid(row=row, column=2, sticky="ew", pady=(5, 0))
            self.var.trace_add("write", lambda *a: self.changed())
            self.widgets.append(box)
        if kind == "date":
            today = ttk.Button(parent, text="Today", width=7, command=self.today)
            today.grid(row=row, column=3, sticky="w", padx=(6, 0), pady=(5, 0))
            self.widgets.append(today)
        self.hint = ttk.Label(parent, foreground=GREY, font=app.small_font, wraplength=520,
                              justify="left")
        self.hint.grid(row=row + 1, column=2, columnspan=2, sticky="w")
        self.show_hint()

    @property
    def memory_key(self):
        if self.slot:
            return (self.slot[0].key, self.slot[1], self.field.key)
        return self.field.key

    @staticmethod
    def _focus_next(event):
        event.widget.tk_focusNext().focus()
        return "break"

    def get(self):
        kind = self.field.kind
        if kind == "yesno":
            return bool(self.var.get())
        if not self.use.get():
            return dict(core.NOT_RELEVANT)
        if self.text is not None:
            return self.text.get("1.0", "end-1c")
        if kind == "checklist":
            ticked = [label for label, v in self.checks.items() if v.get()]
            everything = [t for t in ticked if (self.field.option(t) or {}).get("all")]
            return everything[:1] or ticked
        if kind == "territory":
            return {"worldwide": bool(self.world.get()), "place": self.var.get()}
        return self.var.get()

    def set(self, value):
        kind = self.field.kind
        if kind == "yesno":
            self.var.set(core.as_bool(value))
            self.changed()
            return
        if core.is_excluded(value):
            self.use.set(False)
            self.toggled()
            return
        self.use.set(True)
        if self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", "" if value is None else str(value))
        elif kind == "checklist":
            picked = {o["label"] for o in core.picked_options(self.field, value or [])}
            for label, v in self.checks.items():
                v.set(label in picked)
        elif kind == "territory":
            world, place = core.territory_parts(value or "")
            self.world.set(world)
            self.var.set(place)
        elif kind == "choice":
            option = self.field.option(value or "")
            match = [c for c in self.field.choices if core.key(c) == core.key(value or "")]
            self.var.set(option["label"] if option else match[0] if match else
                         "" if value is None else str(value))
        else:
            self.var.set("" if value is None else str(value))
        self.toggled()

    def today(self):
        d = datetime.date.today()
        self.var.set(f"{d.month}/{d.day}/{d.year}")

    def toggled(self):
        """Grey out the box while the field is marked not relevant."""
        on = self.use.get()
        for wdg in self.widgets:
            if isinstance(wdg, tk.Text):
                wdg.configure(state="normal" if on else "disabled",
                              background="white" if on else "#eeeeee")
            elif isinstance(wdg, ttk.Combobox):
                wdg.configure(state="readonly" if on else "disabled")
            else:
                wdg.configure(state="normal" if on else "disabled")
        self.changed()

    def changed(self):
        if self.field.kind == "checklist" and self.use.get():
            everything = any((self.field.option(t) or {}).get("all") and v.get() for t, v in self.checks.items())
            for wdg in self.widgets:
                label = wdg.cget("text")
                if not (self.field.option(label) or {}).get("all"):
                    wdg.configure(state="disabled" if everything else "normal")
        if self.field.kind == "territory" and self.use.get():
            self.entry.configure(state="disabled" if self.world.get() else "normal")
        self.app.memory[self.memory_key] = self.get()
        self.show_hint()

    def show_hint(self):
        if self.hint is None:
            return
        raw = self.get()
        field = self.field
        if core.is_excluded(raw):
            if field.expected and self.app.template and self.app.template.fieldset:
                self.hint.config(text=f"Left out as not relevant, though a "
                                      f"{self.app.template.fieldset.name.lower()} usually has it.",
                                 foreground=WARN)
            else:
                self.hint.config(text="Left out as not relevant to this contract.", foreground=GREY)
            return
        if core.is_empty(raw):
            hint = field.help or (("e.g. " + field.example) if field.example else "")
            if field.kind == "checklist":
                hint = hint or "Tick any that apply."
            if "list" in field.formats:
                hint = "One per line."
            if field.in_condition and not field.compared:
                hint = (hint + "  " if hint else "") + "Leave empty to leave out the part that depends on it."
            self.hint.config(text=hint, foreground=GREY)
            return
        try:
            if field.kind in ("checklist", "territory", "choice"):
                preview = str(core.word_value(field, "", raw))
                if core.key(preview) == core.key(str(raw)):
                    preview = ""
            else:
                preview = field.preview(raw)
        except ValueError as exc:
            self.hint.config(text="✗  " + str(exc), foreground=BAD)
            return
        if field.kind == "choice" and field.choices and \
                core.key(raw) not in [core.key(c) for c in field.choices]:
            self.hint.config(text="✗  not one of the choices", foreground=BAD)
            return
        self.hint.config(text=("→  " + preview) if preview else "", foreground=GOOD)


class Tooltip:
    """A small note that appears while the pointer rests on a widget."""

    def __init__(self, widget, text):
        self.widget, self.text, self.tip = widget, text, None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 20
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        tk.Label(self.tip, text=self.text, background="#ffffe0", relief="solid", borderwidth=1,
                 padx=6, pady=3).pack()

    def hide(self, _):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class FieldSetDialog(tk.Toplevel):
    """Look at, make and name field sets: clusters of fields, plus fields of one's own."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.current = None
        self.own = []
        self.title("Field sets")
        self.transient(app.root)
        self.minsize(900, 620)

        outer = ttk.Frame(self, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Field sets", font=app.heading_font).pack(anchor="w")
        ttk.Label(outer, foreground=GREY, wraplength=760, justify="left", text=(
            "A field set says what a kind of contract should contain. It lays out the form, "
            "chooses the box for each field, fills in defaults, and warns when something "
            "expected is missing. Build one from the clusters below and add fields of your "
            "own. Field sets are saved in the templates folder, so everyone using it shares "
            "them.")).pack(anchor="w", pady=(2, 10))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body)
        left.pack(side="left", fill="y", padx=(0, 14))
        self.listbox = tk.Listbox(left, width=27, height=16, exportselection=False)
        self.listbox.pack(fill="y", expand=True)
        self.listbox.bind("<<ListboxSelect>>", lambda e: self.chosen())
        lb = ttk.Frame(left)
        lb.pack(fill="x", pady=(6, 0))
        ttk.Button(lb, text="New", command=self.new).pack(side="left")
        ttk.Button(lb, text="Copy", command=self.copy).pack(side="left", padx=4)
        self.delete_btn = ttk.Button(lb, text="Delete", command=self.delete)
        self.delete_btn.pack(side="left")

        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        row = ttk.Frame(right)
        row.pack(fill="x")
        ttk.Label(row, text="Name:").pack(side="left")
        self.name = tk.StringVar()
        self.name_entry = ttk.Entry(row, textvariable=self.name, width=34)
        self.name_entry.pack(side="left", padx=8)
        self.builtin_note = ttk.Label(right, foreground=GREY, font=app.small_font)
        self.builtin_note.pack(anchor="w")

        ttk.Label(right, text="Clusters", font=app.bold_font).pack(anchor="w", pady=(10, 2))
        grid = ttk.Frame(right)
        grid.pack(fill="x")
        self.cluster_vars = {}
        self.cluster_boxes = []
        for i, c in enumerate(fieldsets.CLUSTERS):
            v = tk.BooleanVar()
            names = ", ".join(f["name"] + ("*" if f.get("expected") else "") for f in c["fields"])
            repeat = "  (repeats)" if c.get("group") else ""
            cb = ttk.Checkbutton(grid, text=c["name"] + repeat, variable=v)
            cb.grid(row=i, column=0, sticky="nw", pady=1)
            ttk.Label(grid, text=names, foreground=GREY, font=app.small_font, wraplength=380,
                      justify="left").grid(row=i, column=1, sticky="w", padx=(10, 0))
            self.cluster_vars[c["name"]] = v
            self.cluster_boxes.append(cb)
        ttk.Label(right, text="* expected: the app warns when it is missing", foreground=GREY,
                  font=app.small_font).pack(anchor="w", pady=(2, 0))

        ttk.Label(right, text="Fields of your own", font=app.bold_font).pack(anchor="w", pady=(10, 2))
        self.scroll = ScrollFrame(right)
        self.scroll.pack(fill="both", expand=True)
        inner = self.scroll.inner
        for col, text in enumerate(("Field name", "Kind", "Options, with commas",
                                    "Expected", "Section")):
            ttk.Label(inner, text=text, font=app.small_font).grid(row=0, column=col, sticky="w")
        self.next_row = 1
        self.add_btn = ttk.Button(right, text="Add a field", command=lambda: self.add_field())
        self.add_btn.pack(anchor="w", pady=(4, 0))

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Show field codes", command=self.codes).pack(side="left")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")
        self.save_btn = ttk.Button(bottom, text="Save", command=self.save)
        self.save_btn.pack(side="right", padx=8)

        self.refresh(app.template.fieldset.name if app.template and app.template.fieldset else None)
        self.geometry(f"980x660+{app.root.winfo_rootx() + 10}+{app.root.winfo_rooty() + 10}")

    # -- the list --
    def refresh(self, select=None):
        self.sets = fieldsets.load_all(self.app.templates_folder)
        self.listbox.delete(0, "end")
        for s in self.sets:
            self.listbox.insert("end", s.name + ("  (built in)" if s.builtin else ""))
        names = [s.name for s in self.sets]
        i = names.index(select) if select in names else 0
        self.listbox.selection_clear(0, "end")
        self.listbox.selection_set(i)
        self.show(self.sets[i])

    def chosen(self):
        sel = self.listbox.curselection()
        if sel:
            self.show(self.sets[sel[0]])

    def show(self, fs):
        self.current = fs
        self.name.set(fs.name)
        for name, v in self.cluster_vars.items():
            v.set(name in fs.cluster_names)
        for entry in list(self.own):
            self.remove_field(entry)
        for f in fs.custom:
            self.add_field(f)
        state = "disabled" if fs.builtin else "normal"
        for wdg in [self.name_entry, self.save_btn, self.delete_btn, self.add_btn] + self.cluster_boxes:
            wdg.configure(state=state)
        for entry in self.own:
            for wdg in entry["widgets"]:
                wdg.configure(state="disabled" if fs.builtin else
                              ("readonly" if isinstance(wdg, ttk.Combobox) else "normal"))
        self.builtin_note.config(text="Built in. Copy it to make a version of your own."
                                 if fs.builtin else "")

    # -- fields of one's own --
    def add_field(self, f=None):
        f = f or {}
        r = self.next_row
        self.next_row += 1
        inner = self.scroll.inner
        entry = {
            "name": tk.StringVar(value=f.get("name", "")),
            "kind": tk.StringVar(value=fieldsets.KIND_LABELS.get(f.get("kind", "text"))),
            "options": tk.StringVar(value=", ".join(o["label"] for o in f.get("options", []))),
            "expected": tk.BooleanVar(value=bool(f.get("expected"))),
            "section": tk.StringVar(value=f.get("section", "")),
        }
        widgets = [
            ttk.Entry(inner, textvariable=entry["name"], width=16),
            ttk.Combobox(inner, textvariable=entry["kind"], state="readonly", width=13,
                         values=[fieldsets.KIND_LABELS[k] for k in fieldsets.KINDS]),
            ttk.Entry(inner, textvariable=entry["options"], width=16),
            ttk.Checkbutton(inner, variable=entry["expected"]),
            ttk.Entry(inner, textvariable=entry["section"], width=9),
        ]
        for col, wdg in enumerate(widgets):
            wdg.grid(row=r, column=col, sticky="ew" if col != 3 else "", padx=(0, 6), pady=2)
        remove = ttk.Button(inner, text="×", width=3, command=lambda: self.remove_field(entry))
        remove.grid(row=r, column=5, pady=2)
        entry["widgets"] = widgets + [remove]
        self.own.append(entry)

    def remove_field(self, entry):
        for wdg in entry["widgets"]:
            wdg.destroy()
        self.own.remove(entry)

    def gather(self):
        name = core.tidy_name(self.name.get())
        if not name:
            raise ValueError("Give the field set a name.")
        if core.key(name) in [core.key(s.name) for s in self.sets if s is not self.current]:
            raise ValueError(f"There is already a field set called {name}.")
        clusters = [n for n, v in self.cluster_vars.items() if v.get()]
        taken = {core.key(f["name"]) for c in clusters for f in fieldsets.cluster(c)["fields"]}
        own = []
        by_label = {v: k for k, v in fieldsets.KIND_LABELS.items()}
        for entry in self.own:
            fname = core.tidy_name(entry["name"].get())
            if not fname:
                continue
            if core.key(fname) in taken:
                raise ValueError(f"{fname} is already in one of the chosen clusters.")
            taken.add(core.key(fname))
            kind = by_label.get(entry["kind"].get(), "text")
            spec = {"name": fname, "kind": kind}
            labels = [o.strip() for o in entry["options"].get().split(",") if o.strip()]
            if kind in ("choice", "checklist"):
                if not labels:
                    raise ValueError(f"{fname} needs its options, separated by commas.")
                spec["options"] = [{"label": o, "wording": o.lower() if kind == "checklist" else o}
                                   for o in labels]
            if kind == "territory":
                spec.update(worldwide="throughout the world", place="in {}")
            if entry["expected"].get():
                spec["expected"] = True
            if entry["section"].get().strip():
                spec["section"] = entry["section"].get().strip()
            own.append(spec)
        if not clusters and not own:
            raise ValueError("Choose at least one cluster, or add a field.")
        return fieldsets.FieldSet(name, clusters, own, path=self.current.path if self.current else None)

    # -- buttons --
    def new(self):
        self.current = fieldsets.FieldSet("New field set")
        self.listbox.selection_clear(0, "end")
        self.show(self.current)
        self.name_entry.focus_set()
        self.name_entry.select_range(0, "end")

    def copy(self):
        if not self.current:
            return
        source = self.current
        self.current = fieldsets.FieldSet("Copy of " + source.name, source.cluster_names, source.custom)
        self.listbox.selection_clear(0, "end")
        self.show(self.current)

    def save(self):
        try:
            fs = self.gather()
        except ValueError as exc:
            messagebox.showerror("Cannot save yet", str(exc), parent=self)
            return
        path = fieldsets.save(fs, self.app.templates_folder)
        self.app.say(f"Field set “{fs.name}” saved in {path.parent}.")
        self.refresh(fs.name)
        self.app.sets_changed()

    def delete(self):
        fs = self.current
        if not fs or fs.builtin or not fs.path:
            return
        if messagebox.askyesno("Delete field set", f"Delete the field set “{fs.name}”?\n\n"
                               "Templates that use it will simply have no field set.", parent=self):
            fieldsets.delete(fs)
            self.refresh()
            self.app.sets_changed()

    def codes(self):
        try:
            fs = self.current if self.current.builtin else self.gather()
        except ValueError as exc:
            messagebox.showerror("Not ready", str(exc), parent=self)
            return
        self.app.text_window(f"Field codes: {fs.name}", fs.codes())


class MakeTemplateDialog(tk.Toplevel):
    """Turn an existing contract into a template by naming what changes."""

    def __init__(self, app):
        super().__init__(app.root)
        self.app = app
        self.source = None
        self.rows = []
        self.title("Turn a contract into a template")
        self.transient(app.root)
        self.minsize(760, 480)

        top = ttk.Frame(self, padding=16)
        top.pack(fill="both", expand=True)
        ttk.Label(top, text="Turn an existing contract into a template",
                  font=app.heading_font).pack(anchor="w")
        ttk.Label(top, foreground=GREY, wraplength=700, justify="left", text=(
            "Choose a finished contract. Then list the wording that changes from one contract "
            "to the next, exactly as it appears, and give each a field name. Every place it "
            "appears is replaced. The original contract is not changed: the template is "
            "saved as a new file.")).pack(anchor="w", pady=(2, 10))

        row = ttk.Frame(top)
        row.pack(fill="x")
        ttk.Button(row, text="Choose contract…", command=self.choose).pack(side="left")
        self.source_label = ttk.Label(row, text="Nothing chosen yet", foreground=GREY)
        self.source_label.pack(side="left", padx=10)

        self.scroll = ScrollFrame(top)
        self.scroll.pack(fill="both", expand=True, pady=(14, 0))
        self.scroll.inner.columnconfigure(0, weight=3)
        self.scroll.inner.columnconfigure(1, weight=2)
        for col, text in enumerate(("Wording in the contract", "Field name", "Format")):
            ttk.Label(self.scroll.inner, text=text, font=app.bold_font).grid(
                row=0, column=col, sticky="w", pady=(0, 4))
        self.next_row = 1

        self.accept_changes = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, variable=self.accept_changes, text=(
            "Accept all tracked changes and remove comments first")).pack(anchor="w", pady=(10, 0))
        self.reset_spacing = tk.BooleanVar(value=True)
        ttk.Checkbutton(top, variable=self.reset_spacing, text=(
            "Reset letter spacing to normal (removes squeezed or stretched spacing left by "
            "fitting lines by hand or converting from PDF)")).pack(anchor="w", pady=(2, 0))

        buttons = ttk.Frame(top)
        buttons.pack(fill="x", pady=(10, 0))
        ttk.Button(buttons, text="Add a row", command=self.add_row).pack(side="left")
        ttk.Button(buttons, text="Suggest dates and amounts",
                   command=self.suggest).pack(side="left", padx=8)
        ttk.Button(buttons, text="Cancel", command=self.destroy).pack(side="right")
        ttk.Button(buttons, text="Make template…", command=self.make).pack(side="right", padx=8)

        for _ in range(4):
            self.add_row()
        self.geometry(f"+{app.root.winfo_rootx() + 40}+{app.root.winfo_rooty() + 40}")

    def add_row(self, text="", name="", fmt=""):
        r = self.next_row
        self.next_row += 1
        parent = self.scroll.inner
        find, field, form = tk.StringVar(value=text), tk.StringVar(value=name), tk.StringVar(value=fmt)
        widgets = [
            ttk.Entry(parent, textvariable=find),
            ttk.Entry(parent, textvariable=field),
            ttk.Combobox(parent, textvariable=form, values=FORMATS, width=20),
        ]
        for col, wdg in enumerate(widgets):
            wdg.grid(row=r, column=col, sticky="ew", padx=(0, 6), pady=2)
        entry = (find, field, form, widgets)
        remove = ttk.Button(parent, text="×", width=3, command=lambda: self.remove(entry))
        remove.grid(row=r, column=3, pady=2)
        widgets.append(remove)
        self.rows.append(entry)

    def remove(self, entry):
        for wdg in entry[3]:
            wdg.destroy()
        self.rows.remove(entry)

    def choose(self):
        path = filedialog.askopenfilename(parent=self, title="Choose a finished contract",
                                          filetypes=[("Word documents", "*.docx")])
        if path:
            self.source = pathlib.Path(path)
            self.source_label.config(text=self.source.name, foreground="#000")

    def suggest(self):
        if not self.source:
            messagebox.showinfo("Choose a contract first",
                                "Choose the contract to look through first.", parent=self)
            return
        have = {f.get() for f, _, _, _ in self.rows}
        found = [c for c in core.find_candidates(self.source) if c[0] not in have]
        if not found:
            messagebox.showinfo("Nothing found", "No dollar amounts or dates were found that are "
                                "not already listed.", parent=self)
            return
        for f, n, form, wdgs in list(self.rows):              # replace empty rows first
            if not f.get() and not n.get():
                self.remove((f, n, form, wdgs))
        for text, fmt, _count in found:
            self.add_row(text, "", fmt)
        messagebox.showinfo("Suggestions added", f"{len(found)} date(s) and amount(s) added. "
                            "Give each a field name, or remove the ones that never change.",
                            parent=self)

    def make(self):
        if not self.source:
            messagebox.showinfo("Choose a contract first", "Choose the contract to start from.",
                                parent=self)
            return
        swaps = []
        for find, name, fmt, _ in self.rows:
            if not find.get().strip():
                continue
            if not name.get().strip():
                messagebox.showerror("A field needs a name",
                                     f"“{find.get()}” has no field name.", parent=self)
                return
            swaps.append((find.get(), core.tidy_name(name.get()), fmt.get()))
        if not swaps:
            messagebox.showinfo("Nothing to replace",
                                "List at least one piece of wording to turn into a field.", parent=self)
            return
        folder = self.app.templates_folder or self.source.parent
        out = filedialog.asksaveasfilename(
            parent=self, title="Save the new template as", defaultextension=".docx",
            initialdir=str(folder), initialfile=f"{self.source.stem} TEMPLATE.docx",
            filetypes=[("Word document", "*.docx")])
        if not out:
            return
        if pathlib.Path(out).resolve() == self.source.resolve():
            messagebox.showerror("Choose another name", "That would overwrite the original contract.",
                                 parent=self)
            return
        try:
            notes = []
            counts = core.make_template(self.source, out, swaps, self.reset_spacing.get(),
                                        self.accept_changes.get(), notes)
        except PermissionError:
            messagebox.showerror("Could not save", "That file is open in Word. Close it and try again.",
                                 parent=self)
            return
        except Exception as exc:                              # noqa: BLE001
            messagebox.showerror("Could not make the template", str(exc), parent=self)
            return
        say = self.app.say
        say("")
        say(f"--- New template made from {self.source.name}")
        missed = []
        for find, name, _ in swaps:
            n = counts.get(find, 0)
            say(f"    {name}: replaced {n} time(s)  (“{core.snippet(find, 40)}”)")
            if not n:
                missed.append(find)
        say(f"    wrote {pathlib.Path(out).name}")
        for line in notes:
            say("    " + line)
        say("    Track Changes is off in the new template" +
            (", and letter spacing is back to normal." if self.reset_spacing.get() else "."))
        note = ""
        if missed:
            note = ("\n\nNot found, so not replaced:\n  " + "\n  ".join(missed) +
                    "\n\nCheck the spelling and punctuation match the contract exactly.")
        self.destroy()
        if messagebox.askyesno("Template made", f"The template is saved as\n{pathlib.Path(out).name}.{note}"
                               "\n\nOpen it in Word now to check it and add any optional "
                               "clauses?\n(It is also loaded here, ready to use.)"):
            open_path(out)
        self.app.load_template(pathlib.Path(out))


class App:
    def __init__(self, root):
        self.root = root
        self.template = None
        self.rows = []
        self.memory = {}                 # what was typed, kept when switching templates
        self.counts = {}                 # how many works, parties ... the form shows
        settings = core.load_settings()
        folder = settings.get("templates_folder")
        self.templates_folder = pathlib.Path(folder) if folder and pathlib.Path(folder).is_dir() else None
        out = settings.get("output_folder")
        self.output_folder = pathlib.Path(out) if out and pathlib.Path(out).is_dir() else None
        self.highlight = tk.BooleanVar(value=settings.get("highlight", False))
        self.open_after = tk.BooleanVar(value=settings.get("open_after", True))
        self.sets = fieldsets.load_all(self.templates_folder)

        root.title(f"{core.APP_NAME}  -  Build {core.BUILD}")
        root.minsize(820, 680)
        self.heading_font = ("Helvetica", 16, "bold")
        self.bold_font = ("Helvetica", 11, "bold") if sys.platform != "darwin" else ("Helvetica", 13, "bold")
        self.small_font = ("Helvetica", 9) if sys.platform != "darwin" else ("Helvetica", 11)

        self.build_menu()

        ttk.Label(root, text="Contract Builder", font=self.heading_font).pack(
            fill="x", padx=16, pady=(14, 0))
        ttk.Label(root, foreground=GREY, text=(
            "Choose a template, fill in what changes, and create the finished Word contract.")
        ).pack(fill="x", padx=16)

        top = ttk.Frame(root)
        top.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(top, text="Template:").grid(row=0, column=0, sticky="w")
        self.picker = ttk.Combobox(top, state="readonly", width=48)
        self.picker.grid(row=0, column=1, sticky="w", padx=8)
        self.picker.bind("<<ComboboxSelected>>", self.picked)
        buttons = ttk.Frame(top)
        buttons.grid(row=0, column=2, sticky="w")
        ttk.Button(buttons, text="Browse…", command=self.choose_template).pack(side="left")
        ttk.Button(buttons, text="Reload", command=self.reload).pack(side="left", padx=(6, 0))
        ttk.Label(top, text="Field set:").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.set_picker = ttk.Combobox(top, state="readonly", width=48)
        self.set_picker.grid(row=1, column=1, sticky="w", padx=8, pady=(6, 0))
        self.set_picker.bind("<<ComboboxSelected>>", self.set_picked)
        ttk.Button(top, text="Field sets…", command=lambda: FieldSetDialog(self)).grid(
            row=1, column=2, sticky="w", pady=(6, 0))
        self.folder_label = ttk.Label(root, foreground=GREY, font=self.small_font)
        self.folder_label.pack(fill="x", padx=16, pady=(4, 0))
        self.status = ttk.Label(root, font=self.small_font)
        self.status.pack(fill="x", padx=16)

        panes = ttk.PanedWindow(root, orient="vertical")
        panes.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        form_box = ttk.Frame(panes)
        self.form = ScrollFrame(form_box)
        self.form.pack(fill="both", expand=True)
        panes.add(form_box, weight=4)
        self.log = scrolledtext.ScrolledText(panes, height=5, wrap="word", state="disabled",
                                             font="TkFixedFont", relief="solid", borderwidth=1)
        panes.add(self.log, weight=1)

        bottom = ttk.Frame(root)
        bottom.pack(fill="x", padx=16, pady=12)
        ttk.Checkbutton(bottom, text="Highlight filled-in wording (for review)",
                        variable=self.highlight, command=self.save_options).pack(side="left")
        ttk.Checkbutton(bottom, text="Open the contract when done",
                        variable=self.open_after, command=self.save_options).pack(side="left", padx=12)
        self.create_btn = ttk.Button(bottom, text="Create contract…", command=self.create)
        self.create_btn.pack(side="right")
        ttk.Button(bottom, text="Clear", command=self.clear).pack(side="right", padx=8)

        self.say(f"Build {core.BUILD}. Ready.")
        self.refresh_picker()
        self.refresh_set_picker()
        last = settings.get("last_template")
        if last and pathlib.Path(last).is_file():
            self.load_template(pathlib.Path(last))
        else:
            self.empty_form()

        if core.running_from_temp():
            messagebox.showwarning(
                "Unzip the folder first",
                "This is running from inside a zip file, which does not work.\n\n"
                "Extract the whole folder somewhere ordinary, such as your Desktop, "
                "then run it from there.")

    # ---------------------------------------------------------------- menus --
    def build_menu(self):
        bar = tk.Menu(self.root)
        mod = "Command" if sys.platform == "darwin" else "Control"
        acc = "Cmd" if sys.platform == "darwin" else "Ctrl"

        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="Choose template…", command=self.choose_template,
                      accelerator=f"{acc}+O")
        m.add_command(label="Choose templates folder…", command=self.choose_folder)
        m.add_command(label="Reload template", command=self.reload)
        m.add_separator()
        m.add_command(label="Save answers…", command=self.save_answers, accelerator=f"{acc}+S")
        m.add_command(label="Load answers…", command=self.load_answers)
        m.add_command(label="Clear the form", command=self.clear)
        m.add_separator()
        m.add_command(label="Create contract…", command=self.create, accelerator=f"{acc}+Enter")
        m.add_separator()
        m.add_command(label="Quit", command=self.root.destroy)
        bar.add_cascade(label="File", menu=m)

        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="Make a blank spreadsheet for this template…", command=self.blank_sheet)
        m.add_command(label="Create contracts from a spreadsheet…", command=self.run_batch)
        bar.add_cascade(label="Many contracts", menu=m)

        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="Check this template", command=self.check)
        m.add_command(label="Open this template in Word", command=self.open_template)
        m.add_separator()
        m.add_command(label="Field sets…", command=lambda: FieldSetDialog(self))
        m.add_command(label="Field codes for this field set", command=self.show_codes)
        m.add_separator()
        m.add_command(label="Turn a contract into a template…",
                      command=lambda: MakeTemplateDialog(self))
        bar.add_cascade(label="Template tools", menu=m)

        m = tk.Menu(bar, tearoff=False)
        m.add_command(label="How to write a template", command=self.cheat_sheet)
        m.add_command(label="About", command=lambda: messagebox.showinfo(
            "About", f"{core.APP_NAME}\nBuild {core.BUILD}\n\n"
                     "Settings are kept in\n" + str(core.SETTINGS_FILE)))
        bar.add_cascade(label="Help", menu=m)
        self.root.config(menu=bar)

        self.root.bind_all(f"<{mod}-o>", lambda e: self.choose_template())
        self.root.bind_all(f"<{mod}-s>", lambda e: self.save_answers())
        self.root.bind_all(f"<{mod}-Return>", lambda e: self.create())

    # ------------------------------------------------------------------ log --
    def say(self, text):
        """Add a line to the report. Safe from the worker thread."""
        self.root.after(0, self._say, text)

    def _say(self, text):
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")

    def save_options(self):
        core.remember(highlight=self.highlight.get(), open_after=self.open_after.get())

    # ------------------------------------------------------------ templates --
    def refresh_picker(self):
        names = []
        self.choices = {}
        if self.templates_folder:
            for p in core.templates_in(self.templates_folder):
                self.choices[p.name] = p
                names.append(p.name)
            self.folder_label.config(text=f"Templates folder: {self.templates_folder}")
        else:
            self.folder_label.config(text="No templates folder chosen yet (File → Choose templates folder)")
        if self.template and self.template.path.name not in self.choices:
            self.choices[self.template.path.name] = self.template.path
            names.append(self.template.path.name)
        self.picker.config(values=names)
        if self.template:
            self.picker.set(self.template.path.name)

    def refresh_set_picker(self):
        self.set_picker.config(values=[NO_SET] + [s.name for s in self.sets])
        fs = self.template.fieldset if self.template else None
        self.set_picker.set(fs.name if fs else NO_SET)

    def sets_changed(self):
        """A field set was saved or deleted: read them again and refresh the form."""
        self.sets = fieldsets.load_all(self.templates_folder)
        if self.template:
            self.load_template(self.template.path, quiet=True)
        self.refresh_set_picker()

    def set_for(self, path):
        """The field set chosen for this template before, or the best fit."""
        chosen = core.load_settings().get("template_sets", {}).get(str(path))
        if chosen == NO_SET:
            return None
        if chosen:
            fs = fieldsets.find(self.sets, chosen)
            if fs:
                return fs
        try:
            return fieldsets.best_for(path, self.sets)
        except core.TemplateError:
            return None

    def set_picked(self, _event=None):
        if not self.template:
            return
        name = self.set_picker.get()
        chosen = core.load_settings().get("template_sets", {})
        chosen[str(self.template.path)] = name
        core.remember(template_sets=chosen)
        self.load_template(self.template.path)

    def picked(self, _event=None):
        path = self.choices.get(self.picker.get())
        if path:
            self.load_template(path)

    def choose_template(self):
        path = filedialog.askopenfilename(
            title="Choose a contract template",
            initialdir=str(self.templates_folder) if self.templates_folder else None,
            filetypes=[("Word templates", "*.docx *.dotx"), ("All files", "*.*")])
        if path:
            self.load_template(pathlib.Path(path))

    def choose_folder(self):
        folder = filedialog.askdirectory(title="Choose the folder holding your contract templates")
        if not folder:
            return
        self.templates_folder = pathlib.Path(folder)
        core.remember(templates_folder=self.templates_folder)
        self.refresh_picker()
        self.sets_changed()
        found = len(core.templates_in(self.templates_folder))
        self.say(f"Templates folder set: {found} template(s) found. It will be remembered.")
        if found and not self.template:
            self.picker.focus_set()

    def reload(self):
        if self.template:
            self.load_template(self.template.path)

    def load_template(self, path, quiet=False):
        try:
            template = core.Template(path, self.set_for(path))
        except core.TemplateError as exc:
            messagebox.showerror("Could not read the template", str(exc))
            return
        except PermissionError:
            messagebox.showerror("Could not read the template",
                                 f"{path.name} is locked, probably because it is open in Word "
                                 "with unsaved changes. Save or close it and try again.")
            return
        self.template = template
        core.remember(last_template=path)
        self.refresh_picker()
        self.refresh_set_picker()
        self.rebuild_form()
        if template.problems:
            self.status.config(text=f"⚠  This template has {len(template.problems)} problem(s). "
                                    "They are listed in the report below.", foreground=BAD)
        else:
            self.status.config(text="")
        if quiet:
            return
        self.say("")
        self.say(f"--- Template: {path.name}" +
                 (f"  (field set: {template.fieldset.name})" if template.fieldset else ""))
        for line in template.summary():
            self.say("    " + line)
        for problem in template.problems:
            self.say("    PROBLEM  " + problem)
        for note in template.warnings:
            self.say("    NOTE  " + note)

    def open_template(self):
        if self.template:
            open_path(self.template.path)

    def show_codes(self):
        fs = self.template.fieldset if self.template else None
        if not fs:
            messagebox.showinfo("No field set", "Choose a field set first, beside the template.")
            return
        self.text_window(f"Field codes: {fs.name}", fs.codes())

    def check(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first.")
            return
        self.load_template(self.template.path, quiet=True)
        t = self.template
        lines = []
        for f in t.field_list():
            how = {"yesno": "tick box", "choice": "choice of " + ", ".join(f.choices),
                   "checklist": "tick any of " + ", ".join(f.choices),
                   "territory": "territory, with Worldwide"}.get(f.kind, f.kind)
            fmts = ", ".join(x or "as typed" for x in f.formats)
            extra = f"  (shown {fmts})" if f.formats and f.kind not in ("choice", "checklist") else ""
            where = f"  [repeats for each {f.group.item.lower()}]" if f.group else ""
            lines.append(f"• {f.name}: {how}{extra}{where}")
        body = "\n".join(lines) or "No {{fields}} found."
        if t.fieldset:
            body = f"Field set: {t.fieldset.name}\n\n" + body
        if t.problems:
            body += "\n\nPROBLEMS\n" + "\n".join("• " + p for p in t.problems)
        else:
            body += "\n\nNo problems found."
        if t.warnings:
            body += "\n\nWORTH CHECKING\n" + "\n\n".join("• " + p for p in t.warnings)
        self.text_window(f"Check: {t.path.name}", body)

    # ----------------------------------------------------------------- form --
    def empty_form(self):
        for c in self.form.inner.winfo_children():
            c.destroy()
        ttk.Label(self.form.inner, foreground=GREY, wraplength=600, justify="left", text=(
            "To begin, choose a single template with Browse, or a folder of templates "
            "with File → Choose templates folder.\n\n"
            "A template is a Word document with the parts that change written in double "
            "braces, like {{Client Name}}. Help → How to write a template explains it, "
            "and Template tools → Turn a contract into a template makes one from a "
            "contract you already have.")).grid(row=0, column=0, sticky="w", pady=20)

    def rebuild_form(self, keep_place=False):
        place = self.form.canvas.yview()[0] if keep_place else 0
        inner = self.form.inner
        for c in inner.winfo_children():
            c.destroy()
        inner.columnconfigure(2, weight=1)
        self.rows = []
        sections = self.template.layout()
        if not sections:
            ttk.Label(inner, foreground=GREY, wraplength=600, justify="left", text=(
                "This template has no {{fields}} in it yet, so there is nothing to fill in. "
                "See Help → How to write a template.")).grid(row=0, column=0, sticky="w", pady=20)
            return
        r = 0
        fs = self.template.fieldset
        if fs and any(f.expected for f in self.template.field_list()):
            ttk.Label(inner, foreground=GREY, font=self.small_font, text=(
                f"* usually expected in a {fs.name.lower()}.  Untick the box at the left of a "
                "field that does not apply to this contract.")).grid(
                row=r, column=0, columnspan=4, sticky="w")
            r += 1
        for title, entries in sections:
            ttk.Label(inner, text=title, font=self.bold_font).grid(
                row=r, column=0, columnspan=4, sticky="w", pady=(14 if r else 4, 2))
            r += 1
            for entry in entries:
                if isinstance(entry, core.Group):
                    r = self.group_rows(inner, entry, r)
                else:
                    self.rows.append(FieldRow(self, inner, entry, r))
                    r += 1 if entry.kind == "yesno" else 2
        self.fill_in_rows()
        self.root.update_idletasks()
        self.form.canvas.yview_moveto(place)

    def group_rows(self, inner, group, r):
        """A panel for each work (or party), and a button to add another."""
        n = self.counts.setdefault(group.key, group.first_count)
        for i in range(1, n + 1):
            panel = ttk.LabelFrame(inner, text=f"{group.item} {i}", padding=(8, 2, 8, 6))
            panel.grid(row=r, column=0, columnspan=4, sticky="ew", pady=(4, 2))
            panel.columnconfigure(2, weight=1)
            rr = 0
            if i > group.minimum:
                ttk.Button(panel, text=f"Remove this {group.item.lower()}",
                           command=lambda i=i: self.remove_item(group, i)).grid(
                    row=rr, column=0, columnspan=4, sticky="e")
                rr += 1
            for f in group.members:
                self.rows.append(FieldRow(self, panel, f, rr, slot=(group, i)))
                rr += 1 if f.kind == "yesno" else 2
            r += 1
        ttk.Button(inner, text=f"+ Add another {group.item.lower()}",
                   command=lambda: self.add_item(group)).grid(row=r, column=0, columnspan=4,
                                                              sticky="w", pady=(2, 8))
        return r + 1

    def add_item(self, group):
        self.counts[group.key] = self.counts.get(group.key, group.first_count) + 1
        self.rebuild_form(keep_place=True)

    def remove_item(self, group, i):
        n = self.counts.get(group.key, group.first_count)
        for j in range(i, n + 1):                     # move the later ones up
            for f in group.members:
                later = self.memory.pop((group.key, j + 1, f.key), None)
                if later is not None:
                    self.memory[(group.key, j, f.key)] = later
                else:
                    self.memory.pop((group.key, j, f.key), None)
        self.counts[group.key] = max(group.minimum, n - 1)
        self.rebuild_form(keep_place=True)

    def remembered(self):
        fs = self.template.fieldset if self.template else None
        if not fs:
            return {}
        return core.load_settings().get("remembered", {}).get(fs.name, {})

    def fill_in_rows(self):
        """What was typed before, else what was used last time, else the field set's default."""
        last_time = self.remembered()
        for row in self.rows:
            k = row.memory_key
            number = row.slot[1] if row.slot else None
            if k in self.memory:
                row.set(self.memory[k])
                continue
            value = None
            if row.field.remember and number in (None, 1):
                value = last_time.get(row.field.key)
            if value is None:
                value = row.field.default(number)
            if value is not None:
                row.set(value)

    def collect(self):
        values = {}
        for g in self.template.groups.values():
            if g.used:
                n = self.counts.get(g.key, g.first_count)
                values[g.name] = [({} if g.members else {"present": "yes"}) for _ in range(n)]
        for row in self.rows:
            if row.slot:
                g, i = row.slot
                values[g.name][i - 1][row.field.name] = row.get()
            else:
                values[row.field.name] = row.get()
        return values

    def clear(self):
        if self.rows and not messagebox.askyesno(
                "Clear the form", "Empty every box on the form? Defaults, and what was used last "
                "time for the first party, are filled in again."):
            return
        self.memory = {}
        self.counts = {}
        self.rebuild_form()

    # --------------------------------------------------------------- create --
    def create(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first.")
            return
        values = self.collect()
        bad = core.problems_with(self.template, values)
        if bad:
            messagebox.showerror("Some answers need fixing",
                                 "\n".join(f"• {name}: {why}" for name, why in bad))
            return
        try:
            data, report = core.render(self.template, values, highlight=self.highlight.get())
        except core.TemplateError as exc:
            messagebox.showerror("The template has a problem", str(exc))
            return
        gaps = self.template.expected_gaps(values)
        others = [b for b in report.blanks
                  if not (self.template.field_for(b) and self.template.field_for(b).expected)]
        message = []
        if gaps:
            kind = self.template.fieldset.name.lower()
            message.append(f"A {kind} is expected to have these, but they are missing:\n\n" +
                           "\n".join("• " + g for g in gaps))
        if others:
            message.append(f"These were left empty and will appear as {core.BLANK} in the "
                           "contract:\n\n" + "\n".join("• " + b for b in others))
        if message and not messagebox.askyesno(
                "Before the contract is made", "\n\n".join(message) + "\n\nCreate the contract anyway?",
                icon="warning"):
            return
        folder = self.output_folder or (self.template.path.parent)
        out = filedialog.asksaveasfilename(
            title="Save the contract as", defaultextension=".docx",
            initialdir=str(folder), initialfile=core.suggested_name(self.template, values) + ".docx",
            filetypes=[("Word document", "*.docx")])
        if not out:
            return
        out = pathlib.Path(out)
        if out.resolve() == self.template.path.resolve():
            messagebox.showerror("Choose another name", "That would overwrite the template itself.")
            return
        try:
            out.write_bytes(data)
        except PermissionError:
            messagebox.showerror("Could not save",
                                 f"{out.name} is open in Word. Close it there and try again.")
            return
        self.output_folder = out.parent
        core.remember(output_folder=out.parent)
        self.keep_for_next_time()
        self.say("")
        self.say(f"--- Contract from {self.template.path.name}")
        self.say(f"    filled in {report.filled} place(s)")
        if report.kept or report.removed:
            self.say(f"    optional sections: {report.kept} included, {report.removed} left out")
        if report.left_out:
            self.say(f"    not relevant, so left out: {', '.join(report.left_out)}")
        if gaps:
            self.say(f"    expected but missing: {', '.join(gaps)}")
        if report.blanks:
            self.say(f"    left blank: {', '.join(report.blanks)}")
        self.say(f"    wrote {out}")
        if self.open_after.get():
            open_path(out)

    def keep_for_next_time(self):
        """Fields the field set marks to remember (the first party) start as this next time."""
        fs = self.template.fieldset
        if not fs:
            return
        kept = {}
        for row in self.rows:
            if row.field.remember and (row.slot is None or row.slot[1] == 1):
                value = row.get()
                if not core.is_excluded(value) and not core.is_empty(value):
                    kept[row.field.key] = value
        if kept:
            everything = core.load_settings().get("remembered", {})
            everything.setdefault(fs.name, {}).update(kept)
            core.remember(remembered=everything)

    # -------------------------------------------------------------- answers --
    def save_answers(self):
        if not self.template:
            return
        values = self.collect()
        path = filedialog.asksaveasfilename(
            title="Save these answers", defaultextension=".json",
            initialdir=str(self.output_folder or self.template.path.parent),
            initialfile=core.suggested_name(self.template, values) + " answers.json",
            filetypes=[("Saved answers", "*.json")])
        if not path:
            return
        core.save_answers(self.template, values, path)
        self.say(f"Answers saved to {pathlib.Path(path).name}. Load them again from the File menu.")

    def load_answers(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first, then load the answers into it.")
            return
        path = filedialog.askopenfilename(
            title="Load saved answers",
            initialdir=str(self.output_folder) if self.output_folder else None,
            filetypes=[("Saved answers", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            data = core.load_answers(path)
        except Exception as exc:                              # noqa: BLE001
            messagebox.showerror("Could not load the answers", str(exc))
            return
        used, unused = self.apply_values(data["values"])
        self.say("")
        self.say(f"--- Loaded {pathlib.Path(path).name}: {used} answer(s) filled in")
        if data.get("template") and data["template"] != self.template.path.name:
            self.say(f"    they were saved from {data['template']}")
        if unused:
            self.say(f"    not in this template: {', '.join(unused)}")

    def apply_values(self, values):
        """Put saved values into the form, works and parties included. Returns (used, unused names)."""
        vals = self.template.normalize(values)
        used, matched = 0, set()
        for f in self.template.fields.values():
            if f.group is None and f.key in vals:
                self.memory[f.key] = vals[f.key]
                used += 1
                matched.add(f.key)
        for g in self.template.groups.values():
            items = vals.get(g.key)
            if not g.used or items is None:
                continue
            matched.add(g.key)
            self.counts[g.key] = max(g.minimum, len(items))
            for i, item in enumerate(items, 1):
                for f in g.members:
                    if f.key in item:
                        self.memory[(g.key, i, f.key)] = item[f.key]
                        used += 1
        self.rebuild_form()
        unused = [name for name in values if core.key(name) not in matched]
        return used, unused

    # ------------------------------------------------------- many contracts --
    def blank_sheet(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first.")
            return
        path = filedialog.asksaveasfilename(
            title="Save the blank spreadsheet as", defaultextension=".xlsx",
            initialdir=str(self.output_folder or self.template.path.parent),
            initialfile=f"{self.template.name} - contracts.xlsx",
            filetypes=[("Excel workbook", "*.xlsx")])
        if not path:
            return
        try:
            core.blank_sheet(self.template, path)
        except PermissionError:
            messagebox.showerror("Could not save", "That spreadsheet is open in Excel. Close it and try again.")
            return
        self.say("")
        self.say(f"--- Wrote {pathlib.Path(path).name}")
        self.say("    One row per contract. Hover over a column heading for what it expects.")
        self.say("    Then use Many contracts → Create contracts from a spreadsheet.")
        open_path(path)

    def run_batch(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first.")
            return
        sheet = filedialog.askopenfilename(
            title="Choose the filled-in spreadsheet",
            filetypes=[("Spreadsheets", "*.xlsx *.csv"), ("All files", "*.*")])
        if not sheet:
            return
        folder = filedialog.askdirectory(
            title="Choose the folder to put the contracts in",
            initialdir=str(self.output_folder) if self.output_folder else None)
        if not folder:
            return
        self.output_folder = pathlib.Path(folder)
        core.remember(output_folder=folder)
        self.create_btn.config(state="disabled", text="Working…")
        self.say("")
        self.say(f"--- {pathlib.Path(sheet).name} with {self.template.path.name}")
        threading.Thread(target=self._batch, args=(sheet, folder, self.highlight.get()),
                         daemon=True).start()

    def _batch(self, sheet, folder, highlight):
        try:
            made, skipped = core.batch(self.template, sheet, folder, highlight,
                                       say=lambda line: self.say("    " + line))
            self.say(f"    Finished: {made} made, {skipped} skipped.")
            if made:
                self.root.after(0, open_path, folder)
        except PermissionError:
            self.say("    FAILED  the spreadsheet is open in Excel; close it and try again.")
        except Exception as exc:                              # noqa: BLE001
            self.say(f"    FAILED  {exc}")
        self.root.after(0, lambda: self.create_btn.config(state="normal", text="Create contract…"))

    # ----------------------------------------------------------------- help --
    def cheat_sheet(self):
        self.text_window("How to write a template", core.CHEAT_SHEET)

    def text_window(self, title, body):
        win = tk.Toplevel(self.root)
        win.title(title)
        win.transient(self.root)
        box = scrolledtext.ScrolledText(win, width=72, height=34, wrap="word", font="TkFixedFont",
                                        padx=12, pady=10)
        box.pack(fill="both", expand=True)
        box.insert("1.0", body)
        box.configure(state="disabled")
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=8)
        win.geometry(f"+{self.root.winfo_rootx() + 60}+{self.root.winfo_rooty() + 40}")


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
