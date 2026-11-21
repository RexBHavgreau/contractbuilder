"""Define the parties of a contract with more than one publisher (T-046-D)."""
from __future__ import annotations

import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk


class PartyDialog:
    """List, add, rename and remove parties such as "Publisher One"."""

    def __init__(self, parent, store, on_close=None):
        self.store = store
        self.on_close = on_close
        self.current_id = None
        self.window = tk.Toplevel(parent)
        self.window.title("Parties in a contract")
        self.window.geometry("720x480")
        self.window.minsize(600, 420)
        self.window.transient(parent)
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        outer = ttk.Frame(self.window, padding=14)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Parties in a contract", font=("TkDefaultFont", 14, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=(
                "Use this when one contract names more than one publisher. Give each party "
                "a name, such as Publisher One, and optionally the role it plays. Fields "
                "that start with the name, such as “Publisher One’s Address” or "
                "“Publisher One’s State”, are then filled from the publisher you choose for "
                "that party. A field named exactly for the party, or for the party and its "
                "role in brackets, is filled with the publisher’s name."
            ),
            wraplength=660, justify="left",
        ).pack(anchor="w", pady=(4, 10))
        body = ttk.Frame(outer)
        body.pack(fill="both", expand=True)
        body.columnconfigure(0, weight=1)
        body.rowconfigure(0, weight=1)
        self.tree = ttk.Treeview(body, columns=("name", "role"), show="headings", selectmode="browse", height=6)
        self.tree.heading("name", text="Party")
        self.tree.heading("role", text="Role")
        self.tree.column("name", width=240, anchor="w")
        self.tree.column("role", width=200, anchor="w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        self.tree.bind("<<TreeviewSelect>>", self._select)
        form = ttk.Frame(body)
        form.grid(row=0, column=1, sticky="nsew", padx=(12, 0))
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w", pady=4)
        self.name = tk.StringVar(master=self.window)
        ttk.Entry(form, textvariable=self.name, width=28).grid(row=0, column=1, pady=4)
        ttk.Label(form, text="Role (optional)").grid(row=1, column=0, sticky="w", pady=4)
        self.role = tk.StringVar(master=self.window)
        ttk.Entry(form, textvariable=self.role, width=28).grid(row=1, column=1, pady=4)
        ttk.Label(
            form, text="Example: Publisher One, role Proprietor.", foreground="#555555",
            wraplength=300,
        ).grid(row=2, column=0, columnspan=2, sticky="w")
        buttons = ttk.Frame(form)
        buttons.grid(row=3, column=0, columnspan=2, sticky="w", pady=(10, 0))
        ttk.Button(buttons, text="New", command=self.new).pack(side="left")
        ttk.Button(buttons, text="Save party", command=self.save).pack(side="left", padx=(6, 0))
        ttk.Button(buttons, text="Delete", command=self.delete).pack(side="left", padx=(6, 0))
        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(10, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555", wraplength=520, justify="left")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")
        self.refresh()

    def refresh(self, selected=None):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for party in self.store.list_parties():
            self.tree.insert("", "end", iid=str(party["id"]), values=(party["name"], party["role"]))
        if selected is not None and self.tree.exists(str(selected)):
            self.tree.selection_set(str(selected))

    def _select(self, _event=None):
        selection = self.tree.selection()
        if not selection:
            return
        values = self.tree.item(selection[0], "values")
        self.current_id = int(selection[0])
        self.name.set(values[0])
        self.role.set(values[1])

    def new(self):
        self.current_id = None
        self.name.set("")
        self.role.set("")
        for item in self.tree.selection():
            self.tree.selection_remove(item)
        self.status.configure(text="New party.")

    def save(self):
        try:
            saved = self.store.save_party(self.name.get(), self.role.get(), self.current_id)
        except (ValueError, sqlite3.Error, OSError) as exc:
            messagebox.showerror("Could not save the party", str(exc), parent=self.window)
            return
        self.current_id = saved
        self.refresh(saved)
        self.status.configure(text="Party saved.")

    def delete(self):
        if self.current_id is None:
            messagebox.showinfo("No party chosen", "Choose a party to delete.", parent=self.window)
            return
        if not messagebox.askyesno(
            "Delete party", f"Delete the party “{self.name.get()}”? Fields named for it "
            "will no longer be filled from a publisher.", parent=self.window,
        ):
            return
        self.store.delete_party(self.current_id)
        self.new()
        self.refresh()
        self.status.configure(text="Party deleted.")

    def close(self):
        try:
            if self.on_close is not None:
                self.on_close()
        finally:
            self.window.destroy()
