"""A focused desktop interface for filling Word templates.

The original contract-generation GUI remains in app.py for reference, but the
packaged application starts here and exposes only the single-document workflow.
"""
from __future__ import annotations

import pathlib
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from tkinter import filedialog, messagebox, scrolledtext, ttk

import core
from update_checker import UpdateCheckError, check_for_update
from version import APP_NAME, APP_VERSION, GITHUB_REPOSITORY


def resource_path(name: str) -> pathlib.Path:
    """Find a bundled resource both in source form and in a PyInstaller build."""
    base = pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(__file__).resolve().parent))
    return base / name


class ScrollableFrame(ttk.Frame):
    """A compact, vertically scrollable container for a template's fields."""

    def __init__(self, parent):
        super().__init__(parent)
        self.canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.inner = ttk.Frame(self.canvas, padding=(4, 4, 14, 4))
        self.window = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind(
            "<Configure>",
            lambda _event: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.canvas.bind(
            "<Configure>",
            lambda event: self.canvas.itemconfigure(self.window, width=event.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        self.canvas.bind("<Enter>", self._bind_wheel)
        self.canvas.bind("<Leave>", self._unbind_wheel)
        self.inner.columnconfigure(1, weight=1)

    def _bind_wheel(self, _event=None):
        self.canvas.bind_all("<MouseWheel>", self._wheel)
        self.canvas.bind_all("<Button-4>", lambda _e: self.canvas.yview_scroll(-3, "units"))
        self.canvas.bind_all("<Button-5>", lambda _e: self.canvas.yview_scroll(3, "units"))

    def _unbind_wheel(self, _event=None):
        for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.canvas.unbind_all(sequence)

    def _wheel(self, event):
        if self.canvas.winfo_height() >= self.inner.winfo_height():
            return
        step = -event.delta if sys.platform == "darwin" else -int(event.delta / 120) * 3
        self.canvas.yview_scroll(step, "units")

    def clear(self):
        for child in self.inner.winfo_children():
            child.destroy()
        self.canvas.yview_moveto(0)


class FieldInput:
    """A basic form control corresponding to one unique placeholder."""

    def __init__(self, parent, field, row):
        self.field = field
        self.variable = None
        self.text = None
        self.control = None

        if field.kind == "yesno":
            self.variable = tk.BooleanVar(master=parent, value=False)
            self.control = ttk.Checkbutton(
                parent, text=field.name, variable=self.variable
            )
            self.control.grid(row=row, column=0, columnspan=2, sticky="w", pady=5)
            return

        ttk.Label(parent, text=field.name).grid(
            row=row, column=0, sticky="nw", padx=(0, 16), pady=(8, 0)
        )

        if field.kind == "long":
            self.text = tk.Text(
                parent,
                height=4,
                wrap="word",
                undo=True,
                font="TkDefaultFont",
                relief="solid",
                borderwidth=1,
                highlightthickness=0,
            )
            self.text.grid(row=row, column=1, sticky="ew", pady=(5, 0))
        else:
            self.variable = tk.StringVar(master=parent, value="")
            if field.kind == "choice":
                self.control = ttk.Combobox(
                    parent,
                    textvariable=self.variable,
                    values=[""] + field.choices,
                    state="readonly",
                )
            else:
                self.control = ttk.Entry(parent, textvariable=self.variable)
            self.control.grid(row=row, column=1, sticky="ew", pady=(5, 0))

    def get(self):
        if self.field.kind == "yesno":
            return bool(self.variable.get())
        if self.text is not None:
            return self.text.get("1.0", "end-1c")
        return self.variable.get()

    def clear(self):
        if self.field.kind == "yesno":
            self.variable.set(False)
        elif self.text is not None:
            self.text.delete("1.0", "end")
        else:
            self.variable.set("")


class WordTemplateFiller:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{APP_NAME} {APP_VERSION}")
        self.root.geometry("820x680")
        self.root.minsize(620, 480)

        self.template = None
        self.inputs = []
        self.update_checking = False
        self.update_queue = queue.Queue()

        self._build_menu()
        self._build_window()
        self._show_welcome()
        self.root.after(1200, lambda: self.check_for_updates(manual=False))

    def _build_menu(self):
        menu = tk.Menu(self.root)
        help_menu = tk.Menu(menu, tearoff=False)
        help_menu.add_command(label="User instructions", command=self.show_user_guide)
        help_menu.add_command(label="Check for updates", command=lambda: self.check_for_updates(manual=True))
        help_menu.add_separator()
        help_menu.add_command(label="About", command=self.show_about)
        menu.add_cascade(label="Help", menu=help_menu)
        self.root.config(menu=menu)

    def _build_window(self):
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill="both", expand=True)

        heading = ttk.Label(
            outer,
            text="Create a Word document from a template",
            font=("TkDefaultFont", 15, "bold"),
        )
        heading.pack(anchor="w")
        ttk.Label(
            outer,
            text="Choose a template, fill in its fields, and save a completed copy.",
        ).pack(anchor="w", pady=(3, 12))

        template_row = ttk.Frame(outer)
        template_row.pack(fill="x", pady=(0, 10))
        ttk.Label(template_row, text="Word template").pack(side="left")
        self.template_name = ttk.Label(
            template_row, text="No template selected", foreground="#666666"
        )
        self.template_name.pack(side="left", padx=(10, 10), fill="x", expand=True)
        ttk.Button(template_row, text="Browse…", command=self.choose_template).pack(side="right")

        self.summary = ttk.Label(
            outer, text="Select a .docx or .dotx file to begin.", foreground="#555555"
        )
        self.summary.pack(anchor="w", pady=(0, 8))

        self.form_frame = ttk.LabelFrame(outer, text="Fields to fill in", padding=8)
        self.form_frame.pack(fill="both", expand=True)
        self.scroll = ScrollableFrame(self.form_frame)
        self.scroll.pack(fill="both", expand=True)

        bottom = ttk.Frame(outer)
        bottom.pack(fill="x", pady=(12, 0))
        self.highlight_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            bottom,
            text="Highlight inserted text for review",
            variable=self.highlight_var,
        ).pack(side="left")
        self.clear_button = ttk.Button(bottom, text="Clear fields", command=self.clear_fields)
        self.clear_button.pack(side="right", padx=(8, 0))
        self.create_button = ttk.Button(
            bottom, text="Create document…", command=self.create_document, state="disabled"
        )
        self.create_button.pack(side="right")

        self.status = ttk.Label(outer, text="", foreground="#555555", wraplength=760)
        self.status.pack(anchor="w", pady=(8, 0))

    def _show_welcome(self):
        self.scroll.clear()
        ttk.Label(
            self.scroll.inner,
            text=(
                "Browse for a Word template. The application will find each unique "
                "placeholder, such as {{Recipient Name}}, and show one field for it. "
                "The same placeholder can appear more than once in the document."
            ),
            wraplength=690,
            justify="left",
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=12)

    def choose_template(self):
        selected = filedialog.askopenfilename(
            parent=self.root,
            title="Choose a Word template",
            filetypes=[
                ("Word documents and templates", "*.docx *.dotx"),
                ("All files", "*.*"),
            ],
        )
        if selected:
            self.load_template(pathlib.Path(selected))

    def load_template(self, path: pathlib.Path):
        try:
            template = core.Template(path)
        except (core.TemplateError, OSError, PermissionError) as exc:
            messagebox.showerror("Could not read the template", str(exc), parent=self.root)
            return

        self.template = template
        self.inputs = []
        self.scroll.clear()
        self.template_name.config(text=path.name)
        fields = template.field_list()
        self.summary.config(
            text=f"Found {len(fields)} unique field(s) in {template.places} location(s)."
        )

        if template.problems:
            self.create_button.config(state="disabled")
            ttk.Label(
                self.scroll.inner,
                text=(
                    "This template has problems that should be corrected in Word "
                    "before creating a document:\n\n"
                    + "\n".join("• " + problem for problem in template.problems)
                ),
                foreground="#a00000",
                wraplength=690,
                justify="left",
            ).grid(row=0, column=0, columnspan=2, sticky="w", pady=10)
        elif not fields:
            self.create_button.config(state="disabled")
            ttk.Label(
                self.scroll.inner,
                text="No placeholders were found in this document.",
                foreground="#666666",
            ).grid(row=0, column=0, sticky="w", pady=10)
        else:
            row = 0
            for field in fields:
                control = FieldInput(self.scroll.inner, field, row)
                self.inputs.append(control)
                row += 1 if field.kind == "yesno" else 2
            self.create_button.config(state="normal")

        if template.warnings:
            self.status.config(
                text="Template notes: " + " ".join(template.warnings),
                foreground="#8a5a00",
            )
        elif template.problems:
            self.status.config(text="Correct the template problems before continuing.", foreground="#a00000")
        else:
            self.status.config(text="", foreground="#555555")

    def collect_values(self):
        return {control.field.name: control.get() for control in self.inputs}

    def clear_fields(self):
        for control in self.inputs:
            control.clear()
        self.status.config(text="All fields cleared.", foreground="#555555")

    def create_document(self):
        if self.template is None:
            return

        values = self.collect_values()
        problems = core.problems_with(self.template, values)
        if problems:
            messagebox.showerror(
                "Some entries need attention",
                "\n".join(f"• {name}: {reason}" for name, reason in problems),
                parent=self.root,
            )
            return

        try:
            document_bytes, report = core.render(
                self.template, values, highlight=self.highlight_var.get()
            )
        except core.TemplateError as exc:
            messagebox.showerror("Could not create the document", str(exc), parent=self.root)
            return

        if report.blanks:
            names = "\n".join("• " + name for name in report.blanks)
            proceed = messagebox.askyesno(
                "Some fields are empty",
                "These fields will be left as blank lines in the document:\n\n"
                + names
                + "\n\nCreate the document anyway?",
                parent=self.root,
            )
            if not proceed:
                return

        suggested = core.suggested_name(self.template, values) + ".docx"
        output = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save the completed Word document",
            defaultextension=".docx",
            initialdir=str(self.template.path.parent),
            initialfile=suggested,
            filetypes=[("Word document", "*.docx")],
        )
        if not output:
            return

        destination = pathlib.Path(output)
        try:
            if destination.resolve() == self.template.path.resolve():
                messagebox.showerror(
                    "Choose a different file name",
                    "The completed document cannot overwrite its template.",
                    parent=self.root,
                )
                return
            destination.write_bytes(document_bytes)
        except OSError as exc:
            messagebox.showerror("Could not save the document", str(exc), parent=self.root)
            return

        self.status.config(
            text=f"Created {destination.name} — filled {report.filled} placeholder(s).",
            foreground="#1b6e2e",
        )
        messagebox.showinfo(
            "Document created",
            f"The completed document was saved to:\n{destination}",
            parent=self.root,
        )

    def show_user_guide(self):
        path = resource_path("USER-GUIDE.txt")
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            contents = (
                "Choose a Word template, fill in the fields discovered from its "
                "double-braced placeholders, and create a new document. The original "
                "template is never changed."
            )

        window = tk.Toplevel(self.root)
        window.title("User instructions")
        window.transient(self.root)
        window.geometry("720x620")
        box = scrolledtext.ScrolledText(
            window, wrap="word", font="TkDefaultFont", padx=14, pady=12
        )
        box.pack(fill="both", expand=True)
        box.insert("1.0", contents)
        box.configure(state="disabled")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def show_about(self):
        messagebox.showinfo(
            "About",
            f"{APP_NAME}\nVersion {APP_VERSION}\n\n"
            "A local Word-template tool. Your template and completed documents "
            "remain on your computer.",
            parent=self.root,
        )

    def check_for_updates(self, manual: bool):
        if self.update_checking:
            if manual:
                messagebox.showinfo(
                    "Update check",
                    "An update check is already in progress.",
                    parent=self.root,
                )
            return

        self.update_checking = True
        self.status.config(text="Checking for updates…", foreground="#555555")

        def worker():
            try:
                result = check_for_update(APP_VERSION, GITHUB_REPOSITORY)
                self.root.after(0, self._finish_update_check, result, None, manual)
            except UpdateCheckError as exc:
                self.root.after(0, self._finish_update_check, None, str(exc), manual)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_check(self, result, error, manual: bool):
        self.update_checking = False
        if error:
            self.status.config(text="Update check could not be completed.", foreground="#8a5a00")
            if manual:
                messagebox.showwarning("Update check failed", error, parent=self.root)
            return

        if result.available:
            self.status.config(
                text=f"Version {result.latest_version} is available (you have {APP_VERSION}).",
                foreground="#1b6e2e",
            )
            open_release = messagebox.askyesno(
                "Update available",
                f"{result.release_name} is available.\n"
                f"Installed version: {APP_VERSION}\n"
                f"Latest version: {result.latest_version}\n\n"
                "Open the GitHub release page to download it?",
                parent=self.root,
            )
            if open_release and result.release_url:
                webbrowser.open(result.release_url)
        elif manual:
            self.status.config(text="You are using the latest published version.", foreground="#1b6e2e")
            messagebox.showinfo(
                "No update available",
                f"You are using the latest published version ({APP_VERSION}).",
                parent=self.root,
            )
        else:
            self.status.config(text="", foreground="#555555")


def main():
    root = tk.Tk()
    WordTemplateFiller(root)
    root.mainloop()


if __name__ == "__main__":
    main()
