"""
Contract Builder
Build 3

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

GREY = "#666666"
GOOD = "#1b6e2e"
BAD = "#b00020"
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
    """One line of the form: a label, a box to fill in, and a hint beneath."""

    def __init__(self, app, parent, field, row):
        self.app = app
        self.field = field
        self.var = None
        self.text = None
        self.hint = None
        kind = field.kind

        if kind == "yesno":
            self.var = tk.BooleanVar(value=False)
            ttk.Checkbutton(parent, text=field.name, variable=self.var,
                            command=self.changed).grid(row=row, column=0, columnspan=3,
                                                       sticky="w", pady=3)
            return

        ttk.Label(parent, text=field.name).grid(row=row, column=0, sticky="nw",
                                                padx=(0, 14), pady=(7, 0))
        if kind == "long":
            self.text = tk.Text(parent, height=4, wrap="word", undo=True, font="TkDefaultFont",
                                relief="solid", borderwidth=1, highlightthickness=0)
            self.text.grid(row=row, column=1, sticky="ew", pady=(5, 0))
            self.text.bind("<KeyRelease>", lambda e: self.changed())
            self.text.bind("<Tab>", self._focus_next)
        else:
            self.var = tk.StringVar()
            if kind == "choice":
                box = ttk.Combobox(parent, textvariable=self.var, state="readonly",
                                   values=[""] + field.choices)
            else:
                box = ttk.Entry(parent, textvariable=self.var)
            box.grid(row=row, column=1, sticky="ew", pady=(5, 0))
            self.var.trace_add("write", lambda *a: self.changed())
        if kind == "date":
            ttk.Button(parent, text="Today", width=7, command=self.today).grid(
                row=row, column=2, sticky="w", padx=(6, 0), pady=(5, 0))
        self.hint = ttk.Label(parent, foreground=GREY, font=app.small_font, wraplength=520,
                              justify="left")
        self.hint.grid(row=row + 1, column=1, columnspan=2, sticky="w")
        self.show_hint()

    @staticmethod
    def _focus_next(event):
        event.widget.tk_focusNext().focus()
        return "break"

    def get(self):
        if self.field.kind == "yesno":
            return bool(self.var.get())
        if self.text is not None:
            return self.text.get("1.0", "end-1c")
        return self.var.get()

    def set(self, value):
        if self.field.kind == "yesno":
            self.var.set(core.as_bool(value))
        elif self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", "" if value is None else str(value))
        elif self.field.kind == "choice":
            match = [c for c in self.field.choices if core.key(c) == core.key(value)]
            self.var.set(match[0] if match else "" if value is None else str(value))
        else:
            self.var.set("" if value is None else str(value))
        self.changed()

    def today(self):
        d = datetime.date.today()
        self.var.set(f"{d.month}/{d.day}/{d.year}")

    def changed(self):
        self.app.memory[self.field.key] = self.get()
        self.show_hint()

    def show_hint(self):
        if self.hint is None:
            return
        raw = self.get()
        kind = self.field.kind
        if not str(raw).strip():
            hint = ("e.g. " + self.field.example) if self.field.example else ""
            if "list" in self.field.formats:
                hint = "One per line."
            if self.field.in_condition and not self.field.compared:
                hint = (hint + ".  " if hint else "") + "Leave empty to leave out the part that depends on it."
            self.hint.config(text=hint, foreground=GREY)
            return
        try:
            preview = self.field.preview(raw)
        except ValueError as exc:
            self.hint.config(text="✗  " + str(exc), foreground=BAD)
            return
        if kind == "choice" and self.field.choices and \
                core.key(raw) not in [core.key(c) for c in self.field.choices]:
            self.hint.config(text="✗  not one of the choices", foreground=BAD)
            return
        self.hint.config(text=("→  " + preview) if preview else "", foreground=GOOD)


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
        settings = core.load_settings()
        folder = settings.get("templates_folder")
        self.templates_folder = pathlib.Path(folder) if folder and pathlib.Path(folder).is_dir() else None
        out = settings.get("output_folder")
        self.output_folder = pathlib.Path(out) if out and pathlib.Path(out).is_dir() else None
        self.highlight = tk.BooleanVar(value=settings.get("highlight", False))
        self.open_after = tk.BooleanVar(value=settings.get("open_after", True))

        root.title(f"{core.APP_NAME}  -  Build {core.BUILD}")
        root.minsize(780, 640)
        self.heading_font = ("Helvetica", 16, "bold")
        self.bold_font = ("Helvetica", 11, "bold") if sys.platform != "darwin" else ("Helvetica", 13, "bold")
        self.small_font = ("Helvetica", 9) if sys.platform != "darwin" else ("Helvetica", 11)

        self.build_menu()

        ttk.Label(root, text="Contract Builder", font=self.heading_font).pack(
            fill="x", padx=16, pady=(14, 0))
        ttk.Label(root, foreground=GREY, text=(
            "Choose a template, fill in what changes, and create the finished Word contract.")
        ).pack(fill="x", padx=16)

        trow = ttk.Frame(root)
        trow.pack(fill="x", padx=16, pady=(12, 0))
        ttk.Label(trow, text="Template:").pack(side="left")
        self.picker = ttk.Combobox(trow, state="readonly", width=48)
        self.picker.pack(side="left", padx=8)
        self.picker.bind("<<ComboboxSelected>>", self.picked)
        ttk.Button(trow, text="Browse…", command=self.choose_template).pack(side="left")
        ttk.Button(trow, text="Reload", command=self.reload).pack(side="left", padx=(6, 0))
        self.folder_label = ttk.Label(root, foreground=GREY, font=self.small_font)
        self.folder_label.pack(fill="x", padx=16, pady=(2, 0))
        self.status = ttk.Label(root, font=self.small_font)
        self.status.pack(fill="x", padx=16)

        panes = ttk.PanedWindow(root, orient="vertical")
        panes.pack(fill="both", expand=True, padx=16, pady=(8, 0))
        form_box = ttk.Frame(panes)
        self.form = ScrollFrame(form_box)
        self.form.pack(fill="both", expand=True)
        panes.add(form_box, weight=4)
        self.log = scrolledtext.ScrolledText(panes, height=7, wrap="word", state="disabled",
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
        found = len(core.templates_in(self.templates_folder))
        self.say(f"Templates folder set: {found} template(s) found. It will be remembered.")
        if found and not self.template:
            self.picker.focus_set()

    def reload(self):
        if self.template:
            self.load_template(self.template.path)

    def load_template(self, path, quiet=False):
        try:
            template = core.Template(path)
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
        self.rebuild_form()
        if template.problems:
            self.status.config(text=f"⚠  This template has {len(template.problems)} problem(s). "
                                    "They are listed in the report below.", foreground=BAD)
        else:
            self.status.config(text="")
        if quiet:
            return
        self.say("")
        self.say(f"--- Template: {path.name}")
        for line in template.summary():
            self.say("    " + line)
        for problem in template.problems:
            self.say("    PROBLEM  " + problem)
        for note in template.warnings:
            self.say("    NOTE  " + note)

    def open_template(self):
        if self.template:
            open_path(self.template.path)

    def check(self):
        if not self.template:
            messagebox.showinfo("No template", "Choose a template first.")
            return
        self.load_template(self.template.path, quiet=True)
        t = self.template
        lines = []
        for f in t.field_list():
            how = {"yesno": "tick box", "choice": "choice of " + ", ".join(f.choices)}.get(f.kind, f.kind)
            fmts = ", ".join(x or "as typed" for x in f.formats)
            lines.append(f"• {f.name}: {how}" + (f"  (shown {fmts})" if f.formats and f.kind != "choice" else ""))
        body = "\n".join(lines) or "No {{fields}} found."
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

    def rebuild_form(self):
        inner = self.form.inner
        for c in inner.winfo_children():
            c.destroy()
        inner.columnconfigure(1, weight=1)
        self.rows = []
        r = 0
        values = self.template.value_fields()
        switches = [f for f in self.template.field_list() if f.kind == "yesno"]
        if not values and not switches:
            ttk.Label(inner, foreground=GREY, wraplength=600, justify="left", text=(
                "This template has no {{fields}} in it yet, so there is nothing to fill in. "
                "See Help → How to write a template.")).grid(row=0, column=0, sticky="w", pady=20)
            return
        if values:
            ttk.Label(inner, text="Details", font=self.bold_font).grid(row=r, column=0, sticky="w",
                                                                       pady=(4, 2))
            r += 1
            for f in values:
                self.rows.append(FieldRow(self, inner, f, r))
                r += 2
        if switches:
            ttk.Label(inner, text="Optional sections", font=self.bold_font).grid(
                row=r, column=0, sticky="w", pady=(16, 2))
            r += 1
            for f in switches:
                self.rows.append(FieldRow(self, inner, f, r))
                r += 1
        for row in self.rows:                      # bring back anything typed before
            if row.field.key in self.memory:
                row.set(self.memory[row.field.key])
        self.form.top()

    def collect(self):
        return {row.field.name: row.get() for row in self.rows}

    def clear(self):
        if self.rows and not messagebox.askyesno("Clear the form", "Empty every box on the form?"):
            return
        self.memory = {}
        for row in self.rows:
            row.set(False if row.field.kind == "yesno" else "")

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
        if report.blanks:
            listed = "\n".join("• " + b for b in report.blanks)
            if not messagebox.askyesno(
                    "Some things are empty",
                    f"These were left empty and will appear as {core.BLANK} in the contract:\n\n"
                    f"{listed}\n\nCreate the contract anyway?"):
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
        self.say("")
        self.say(f"--- Contract from {self.template.path.name}")
        self.say(f"    filled in {report.filled} place(s)")
        if report.kept or report.removed:
            self.say(f"    optional sections: {report.kept} included, {report.removed} left out")
        if report.blanks:
            self.say(f"    left blank: {', '.join(report.blanks)}")
        self.say(f"    wrote {out}")
        if self.open_after.get():
            open_path(out)

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
        values = {core.key(k): v for k, v in data["values"].items()}
        used = 0
        for row in self.rows:
            if row.field.key in values:
                row.set(values[row.field.key])
                used += 1
        unused = [k for k in data["values"] if core.key(k) not in {r.field.key for r in self.rows}]
        self.say("")
        self.say(f"--- Loaded {pathlib.Path(path).name}: {used} answer(s) filled in")
        if data.get("template") and data["template"] != self.template.path.name:
            self.say(f"    they were saved from {data['template']}")
        if unused:
            self.say(f"    not in this template: {', '.join(unused)}")

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
