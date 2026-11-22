"""Ask how much of a Word document to import (T-064-C).

The first choice goes on exactly as importing has always worked. "Split into
components and an assembly" is offered only when that import exists (T-064-D).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

WHOLE = "whole"
PART = "part"
SPLIT = "split"

_CHOICES = (
    (WHOLE, "Whole document",
     "Bring all of it in as one component, then check it before saving."),
    (PART, "Part of it",
     "Choose the paragraphs, headings, lists and tables you want, and bring only those in."),
    (SPLIT, "Split into components and an assembly",
     "Cut it into separate components, one per section, saved together as an assembly."),
)


def ask_import_mode(parent, file_name, split_available=False):
    """Show the choices; return WHOLE, PART, SPLIT, or None if cancelled."""
    window = tk.Toplevel(parent)
    window.title("Import from a Word file")
    window.transient(parent)
    window.resizable(False, False)
    result = {"mode": None}

    frame = ttk.Frame(window, padding=16)
    frame.pack(fill="both", expand=True)
    ttk.Label(frame, text=f"How much of “{file_name}” do you want to import?", wraplength=440,
              font=("TkDefaultFont", 11, "bold")).pack(anchor="w", pady=(0, 10))

    def choose(mode):
        result["mode"] = mode
        window.destroy()

    first = None
    for mode, label, caption in _CHOICES:
        if mode == SPLIT and not split_available:
            continue
        button = ttk.Button(frame, text=label, command=lambda m=mode: choose(m))
        button.pack(fill="x")
        ttk.Label(frame, text=caption, foreground="#555555", wraplength=440,
                  justify="left").pack(anchor="w", pady=(2, 10))
        first = first or button
    ttk.Label(frame, text="Your Word file is never changed.", foreground="#555555").pack(anchor="w")
    ttk.Button(frame, text="Cancel", command=window.destroy).pack(anchor="e", pady=(8, 0))
    window.bind("<Escape>", lambda _e: window.destroy())
    if first is not None:
        first.focus_set()
    window.grab_set()
    window.wait_window()
    return result["mode"]
