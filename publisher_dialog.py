"""The publisher profile window: create, edit and delete saved publishers."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from publisher_details_form import DetailsForm



class PublisherProfileDialog:
    """Create, edit, and delete locally stored publisher profiles."""

    FORM_FIELDS = (
        ("Publisher name *", "publisher_name"),
        ("Primary contact", "contact_name"),
        ("Contact title", "contact_title"),
        ("Contact email", "contact_email"),
        ("Contact phone", "contact_phone"),
        ("Website", "website"),
        ("Address line 1", "address_line1"),
        ("Address line 2", "address_line2"),
        ("City", "city"),
        ("State / Province / Region", "region"),
        ("Postal code", "postal_code"),
        ("Country", "country"),
    )

    def __init__(self, parent, store, on_close=None):
        self.parent = parent
        self.store = store
        self.on_close = on_close
        self.current_id = None
        self.loaded_snapshot = None
        self.ignore_selection_event = False

        self.window = tk.Toplevel(parent)
        self.window.title("Publisher Profiles")
        self.window.geometry("940x650")
        self.window.minsize(760, 520)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)

        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(
            outer,
            text="Publisher Profiles",
            font=("TkDefaultFont", 15, "bold"),
        ).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Save publisher and primary-contact details once, then load them "
                "into matching fields in any contract template."
            ),
            wraplength=860,
        ).pack(anchor="w", pady=(3, 12))

        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        list_frame = ttk.LabelFrame(body, text="Saved publishers", padding=8)
        list_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)
        self.tree = ttk.Treeview(list_frame, columns=("publisher",), show="headings")
        self.tree.heading("publisher", text="Publisher")
        self.tree.column("publisher", width=245, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        tree_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.select_profile)

        list_buttons = ttk.Frame(list_frame)
        list_buttons.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        ttk.Button(list_buttons, text="New profile", command=self.new_profile).pack(
            side="left", fill="x", expand=True
        )
        ttk.Button(list_buttons, text="Delete", command=self.delete_profile).pack(
            side="left", padx=(6, 0)
        )

        form = ttk.LabelFrame(body, text="Publisher information", padding=10)
        form.grid(row=0, column=1, sticky="nsew")
        form.columnconfigure(1, weight=1)
        self.variables = {}
        for row, (label, name) in enumerate(self.FORM_FIELDS):
            ttk.Label(form, text=label).grid(
                row=row, column=0, sticky="w", padx=(0, 12), pady=4
            )
            variable = tk.StringVar(master=self.window)
            self.variables[name] = variable
            ttk.Entry(form, textvariable=variable).grid(
                row=row, column=1, sticky="ew", pady=4
            )

        notes_row = len(self.FORM_FIELDS)
        ttk.Label(form, text="Notes").grid(
            row=notes_row, column=0, sticky="nw", padx=(0, 12), pady=(8, 0)
        )
        self.notes = tk.Text(
            form, height=4, wrap="word", undo=True,
            font="TkDefaultFont", relief="solid", borderwidth=1,
        )
        self.notes.grid(row=notes_row, column=1, sticky="ew", pady=(8, 0))

        self.details_form = DetailsForm(self.window, form, self.store)
        self.details_form.frame.grid(
            row=notes_row + 1, column=0, columnspan=2, sticky="ew", pady=(10, 0)
        )

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        ttk.Button(footer, text="Save profile", command=self.save_profile).pack(
            side="right", padx=(0, 8)
        )

        self.refresh_profiles()

    def refresh_profiles(self, selected_id=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        profiles = self.store.list_profiles()
        for profile in profiles:
            profile_id = str(profile["id"])
            self.tree.insert("", "end", iid=profile_id, values=(profile["publisher_name"],))
        if selected_id is not None and self.tree.exists(str(selected_id)):
            self.tree.selection_set(str(selected_id))
            self.tree.focus(str(selected_id))
            self.tree.see(str(selected_id))
            self._load_profile(int(selected_id))
        elif profiles:
            first_id = str(profiles[0]["id"])
            self.tree.selection_set(first_id)
            self.tree.focus(first_id)
            self._load_profile(int(first_id))
        else:
            self.new_profile()

    def _current_form_values(self):
        values = {name: variable.get() for name, variable in self.variables.items()}
        values["notes"] = self.notes.get("1.0", "end-1c")
        values["details"] = tuple(sorted(self.details_form.values().items()))
        return values

    def _has_unsaved_changes(self):
        current = self._current_form_values()
        if self.loaded_snapshot is None:
            return any(str(value).strip() for value in current.values())
        return current != self.loaded_snapshot

    def select_profile(self, _event=None):
        if self.ignore_selection_event:
            self.ignore_selection_event = False
            return
        selection = self.tree.selection()
        if not selection:
            return
        if self._has_unsaved_changes() and not messagebox.askyesno(
            "Discard unsaved changes?",
            "Discard the unsaved changes to this profile and open the selected publisher?",
            parent=self.window,
        ):
            if self.current_id is not None and self.tree.exists(str(self.current_id)):
                self.ignore_selection_event = True
                self.tree.selection_set(str(self.current_id))
                self.tree.focus(str(self.current_id))
            else:
                self.tree.selection_remove(*selection)
            return
        self._load_profile(int(selection[0]))

    def _load_profile(self, profile_id):
        profile = self.store.get_profile_with_details(profile_id)
        if profile is None:
            return
        self.current_id = profile_id
        self.details_form.set(profile.get("details") or {})
        for name, variable in self.variables.items():
            variable.set(str(profile.get(name) or ""))
        self.notes.delete("1.0", "end")
        self.notes.insert("1.0", str(profile.get("notes") or ""))
        self.loaded_snapshot = self._current_form_values()
        self.status.config(text=f"Editing {profile['publisher_name']}.")

    def new_profile(self):
        if self._has_unsaved_changes() and not messagebox.askyesno(
            "Discard unsaved changes?",
            "Discard the unsaved changes and start a new publisher profile?",
            parent=self.window,
        ):
            return
        self.current_id = None
        for variable in self.variables.values():
            variable.set("")
        self.notes.delete("1.0", "end")
        self.details_form.set({})
        self.loaded_snapshot = self._current_form_values()
        selection = self.tree.selection()
        if selection:
            self.tree.selection_remove(*selection)
        self.status.config(text="New publisher profile.")

    def save_profile(self):
        profile = {name: variable.get().strip() for name, variable in self.variables.items()}
        profile["notes"] = self.notes.get("1.0", "end-1c").strip()
        profile["details"] = self.details_form.values()
        try:
            profile_id = self.store.save_profile(profile, self.current_id)
        except (ValueError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Could not save profile", str(exc), parent=self.window)
            return
        self.status.config(text="Profile saved.")
        self.refresh_profiles(profile_id)

    def delete_profile(self):
        if self.current_id is None:
            messagebox.showinfo("No saved profile", "Select a saved profile to delete.", parent=self.window)
            return
        name = self.variables["publisher_name"].get() or "this publisher"
        if not messagebox.askyesno(
            "Delete publisher profile",
            f"Delete the profile for {name}? This cannot be undone.",
            parent=self.window,
        ):
            return
        self.store.delete_profile(self.current_id)
        self.refresh_profiles()
        self.status.config(text="Profile deleted.")

    def close(self):
        try:
            if self.on_close is not None:
                self.on_close()
        finally:
            self.window.destroy()
