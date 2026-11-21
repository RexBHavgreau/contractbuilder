"""The Help menu windows of the main window."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

import core
from ui_widgets import resource_path
from version import APP_NAME, APP_VERSION


class HelpWindowsMixin:
    """The Help menu windows of the main window."""

    def show_user_guide(self):
        path = resource_path("USER-GUIDE.txt")
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            contents = (
                "Choose a saved assembly, a new assembly or a Word template, fill in the fields discovered from its "
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

    def show_third_party_licenses(self):
        """Show the bundled notices for third-party packages."""
        path = resource_path("THIRD-PARTY-LICENSES.txt")
        try:
            contents = path.read_text(encoding="utf-8")
        except OSError:
            contents = "The third-party licence notice file could not be found."

        window = tk.Toplevel(self.root)
        window.title("Third-party licences")
        window.transient(self.root)
        window.geometry("720x620")
        box = scrolledtext.ScrolledText(
            window, wrap="word", font="TkFixedFont", padx=14, pady=12
        )
        box.pack(fill="both", expand=True)
        box.insert("1.0", contents)
        box.configure(state="disabled")
        ttk.Button(window, text="Close", command=window.destroy).pack(pady=8)

    def show_template_guide(self):
        """Show the template-authoring section without the rest of the user guide."""
        path = resource_path("USER-GUIDE.txt")
        try:
            contents = path.read_text(encoding="utf-8")
            start = contents.index("WRITING A TEMPLATE")
            end = contents.index("TEMPLATE CHECKS", start)
            contents = contents[start:end].strip()
        except (OSError, ValueError):
            contents = core.CHEAT_SHEET

        window = tk.Toplevel(self.root)
        window.title("How to write a template and choose fields")
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
