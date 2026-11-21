"""The "Saved publisher" panel shared by the template form and the assembly form.

One choice for the whole form, plus one choice for each **party** (a named
publisher such as "Publisher One") that appears in the document (T-046-D). Each
choice has a "Fill all" button; each field a party can fill has its own
"From publisher" button (T-046-B). Matching of fields to publisher details,
extra details and parties is in ``publisher_parties``.
"""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

import publisher_parties
from publisher_profiles import unmatched_profile_details

OK_COLOR = "#1b6e2e"
ERROR_COLOR = "#a00000"


class PublisherPanel:
    """Choose saved publishers and fill form fields from them."""

    def __init__(self, parent_window, container, store, store_error, get_inputs,
                 set_status, manage_command, no_match_text):
        self.parent_window = parent_window
        self.store = store
        self.store_error = store_error
        self.get_inputs = get_inputs
        self.set_status = set_status
        self.no_match_text = no_match_text
        self.profile_ids: dict[str, int] = {}
        self.resolutions: dict = {}
        self.party_rows: dict = {}          # party name -> (variable, combobox, button)

        self.frame = ttk.LabelFrame(container, text="Saved publisher", padding=8)
        self.frame.pack(fill="x", pady=(0, 10))
        main_row = ttk.Frame(self.frame)
        main_row.pack(fill="x")
        self.variable = tk.StringVar(master=self.frame)
        self.combo = ttk.Combobox(main_row, textvariable=self.variable, state="disabled")
        self.combo.pack(side="left", fill="x", expand=True)
        self.fill_button = ttk.Button(
            main_row, text="Fill all from publisher",
            command=lambda: self.fill(None), state="disabled",
        )
        self.fill_button.pack(side="left", padx=(8, 0))
        ttk.Button(main_row, text="Manage profiles…", command=manage_command).pack(
            side="left", padx=(8, 0)
        )
        self.auto_fill = tk.BooleanVar(master=self.frame, value=False)
        ttk.Checkbutton(
            self.frame, text="Fill automatically when I choose a publisher",
            variable=self.auto_fill,
        ).pack(anchor="w", pady=(6, 0))
        self.combo.bind("<<ComboboxSelected>>", lambda _e: self._chosen(None))
        self.party_frame = ttk.Frame(self.frame)
        self.party_frame.pack(fill="x")

    # -- the list of saved publishers -------------------------------------

    def refresh_profiles(self):
        if self.store is None:
            self._disable()
            if self.store_error:
                self.set_status(f"Publisher profiles are unavailable: {self.store_error}", ERROR_COLOR)
            return
        try:
            profiles = self.store.list_profiles()
        except sqlite3.Error as exc:
            self._disable()
            self.set_status(f"Could not read publisher profiles: {exc}", ERROR_COLOR)
            return
        self.profile_ids = {str(p["publisher_name"]): int(p["id"]) for p in profiles}
        names = list(self.profile_ids)
        state = "readonly" if names else "disabled"
        self.combo.configure(values=names, state=state)
        self.fill_button.configure(state="normal" if names else "disabled")
        self.variable.set("")
        for variable, combo, button in self.party_rows.values():
            combo.configure(values=names, state=state)
            button.configure(state="normal" if names else "disabled")
            variable.set("")

    def _disable(self):
        self.combo.configure(state="disabled", values=[])
        self.fill_button.configure(state="disabled")
        for _variable, combo, button in self.party_rows.values():
            combo.configure(state="disabled", values=[])
            button.configure(state="disabled")

    # -- which fields can be filled, and from which party -------------------

    def analyze(self, field_names):
        """Work out what fills each field and show a choice for each party found."""
        self.resolutions = {}
        if self.store is not None:
            try:
                self.resolutions = publisher_parties.resolutions_for(
                    field_names,
                    parties=self.store.list_parties(),
                    user_matches=self.store.field_match_map(),
                    detail_links=self.store.detail_links(),
                )
            except sqlite3.Error:
                self.resolutions = {}
        self._rebuild_party_rows(publisher_parties.parties_in(self.resolutions))

    def callback_for(self, field_name):
        """The "From publisher" action for one field, or None if nothing fills it."""
        resolution = self.resolutions.get(field_name)
        if resolution is None:
            return None
        return lambda: self.fill(resolution.party, field_name)

    def _rebuild_party_rows(self, parties):
        for child in self.party_frame.winfo_children():
            child.destroy()
        self.party_rows = {}
        roles = {}
        if self.store is not None:
            try:
                roles = {p["name"]: p["role"] for p in self.store.list_parties()}
            except sqlite3.Error:
                roles = {}
        names = list(self.profile_ids)
        for party in parties:
            row = ttk.Frame(self.party_frame)
            row.pack(fill="x", pady=(6, 0))
            role = roles.get(party)
            label = f"{party} ({role})" if role else party
            ttk.Label(row, text=label, width=24).pack(side="left")
            variable = tk.StringVar(master=self.frame)
            combo = ttk.Combobox(
                row, textvariable=variable, values=names,
                state="readonly" if names else "disabled",
            )
            combo.pack(side="left", fill="x", expand=True)
            button = ttk.Button(
                row, text="Fill all for " + party,
                command=lambda name=party: self.fill(name),
                state="normal" if names else "disabled",
            )
            button.pack(side="left", padx=(8, 0))
            combo.bind("<<ComboboxSelected>>", lambda _e, name=party: self._chosen(name))
            self.party_rows[party] = (variable, combo, button)

    def _chosen(self, party):
        if self.auto_fill.get():
            self.fill(party)

    def _selected_name(self, party):
        if party is None:
            return self.variable.get()
        return self.party_rows[party][0].get() if party in self.party_rows else ""

    # -- filling -----------------------------------------------------------

    def fill(self, party, field_name=None):
        """Fill the fields of ``party`` (None: the ordinary fields), or just one."""
        if self.store is None:
            return
        who = f"for {party}" if party else ""
        profile_id = self.profile_ids.get(self._selected_name(party))
        if profile_id is None:
            messagebox.showinfo(
                "Choose a publisher",
                f"Choose a saved publisher {who} before filling fields.".replace("  ", " "),
                parent=self.parent_window,
            )
            return
        try:
            profile = self.store.get_profile_with_details(profile_id)
        except sqlite3.Error as exc:
            messagebox.showerror("Could not load publisher profile", str(exc), parent=self.parent_window)
            return
        if profile is None:
            self.refresh_profiles()
            messagebox.showwarning(
                "Profile not found",
                "That publisher profile was removed. Refresh the list and try again.",
                parent=self.parent_window,
            )
            return

        inputs = self.get_inputs()
        names = [control.field.name for control in inputs]
        result = publisher_parties.fill_values(profile, self.resolutions, party, field_name)
        values = result.values
        if not values:
            reasons = "\n".join(
                f"• {name}: no {detail} is saved for this publisher; choose it yourself."
                for name, detail in result.no_value
            )
            messagebox.showinfo(
                "No matching fields",
                (f"No saved publisher value is available for “{field_name}”."
                 if field_name else self.no_match_text)
                + (("\n\n" + reasons) if reasons else ""),
                parent=self.parent_window,
            )
            return
        overwritten = [
            item for item in values
            if any(c.field.name == item and str(c.get()).strip() for c in inputs)
        ]
        if overwritten and not messagebox.askyesno(
            "Replace existing entries?",
            "Loading this profile will replace these non-empty fields:\n\n"
            + "\n".join("• " + item for item in overwritten) + "\n\nContinue?",
            parent=self.parent_window,
        ):
            return
        for control in inputs:
            if control.field.name in values:
                control.set(values[control.field.name])
        summary = ("Filled " + who + ": " if who else "Filled: ") + ", ".join(values)
        if result.no_value:
            summary += ". Choose these yourself (no value saved): " + ", ".join(
                f"{name} ({detail})" for name, detail in result.no_value
            )
        elif party is None:
            try:
                missing = unmatched_profile_details(profile, names, self.store.field_match_map())
            except sqlite3.Error:
                missing = []
            if missing:
                summary += ". No matching field for: " + ", ".join(missing)
            else:
                summary += ". All populated publisher details have a matching field."
        self.set_status(summary, OK_COLOR)
