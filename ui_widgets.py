"""Small widgets and helpers shared by the main window and the assembly field window."""
from __future__ import annotations

import pathlib
import sys
import tkinter as tk
from tkinter import ttk

import core


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

    def set(self, value):
        """Set this field from a saved publisher profile."""
        if self.field.kind == "yesno":
            self.variable.set(core.as_bool(value))
        elif self.text is not None:
            self.text.delete("1.0", "end")
            self.text.insert("1.0", "" if value is None else str(value))
        else:
            self.variable.set("" if value is None else str(value))

    def clear(self):
        if self.field.kind == "yesno":
            self.variable.set(False)
        elif self.text is not None:
            self.text.delete("1.0", "end")
        else:
            self.variable.set("")
