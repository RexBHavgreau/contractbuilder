"""Ask whether to use a page layout file that has something to read first (T-060-B).

Only used when the check found something the app cannot fix by itself (for
example, no page size). A file that merely lacks styles is accepted without
a question. Two plain buttons, not Yes and No.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def confirm_layout_file(parent, lines) -> bool:
    """Show the lines; return True for "Use this file", False otherwise."""
    window = tk.Toplevel(parent)
    window.title("Before you use this page layout file")
    window.transient(parent)
    window.resizable(True, True)
    outcome = {"use": False}

    frame = ttk.Frame(window, padding=16)
    frame.pack(fill="both", expand=True)
    label = ttk.Label(frame, text="\n\n".join(lines), justify="left", wraplength=460)
    label.pack(anchor="w", fill="x")
    frame.bind("<Configure>", lambda e: label.configure(wraplength=max(240, e.width - 40)))

    buttons = ttk.Frame(frame)
    buttons.pack(fill="x", pady=(16, 0))

    def finish(use):
        outcome["use"] = use
        window.destroy()

    ttk.Button(buttons, text="Choose another", command=lambda: finish(False)).pack(side="right")
    use_button = ttk.Button(buttons, text="Use this file", command=lambda: finish(True))
    use_button.pack(side="right", padx=(0, 8))
    window.bind("<Escape>", lambda _e: finish(False))
    window.protocol("WM_DELETE_WINDOW", lambda: finish(False))
    use_button.focus_set()
    window.grab_set()
    window.wait_window()
    return outcome["use"]
