"""The saved-assemblies list with a preview of the highlighted assembly (T-063).

The list is on the left, the whole contract as the builder previews it on the
right, so the user can see what an assembly says before opening it. The data
and the open actions are passed in by ``assembly_open_dialog``; nothing here
reads or writes the database except to fetch a revision for the preview.

The preview shows the pinned component versions only (never newer wording) and
is drawn once the highlight has rested for a moment, so a long list stays quick.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from assembly_helpers import revision_preview_segments
from component_preview import PREVIEW_KEY, configure_preview_tags

PREVIEW_DELAY_MS = 180


class AssemblyPicker:
    """List, search and preview saved assemblies; open one to its fields."""

    def __init__(self, app, library, assemblies, open_revision, edit_revision=None):
        """``open_revision(revision_id, parent)`` opens to the fields and returns a
        truthy value on success; ``edit_revision(revision)`` opens the builder."""
        self.app = app
        self.library = library
        self.assemblies = assemblies
        self.open_revision = open_revision
        self.edit_revision = edit_revision
        self._preview_after_id = None
        self._shown_revision_id = None
        self._cache = {}
        self.by_id = {}

        self.window = dialog = tk.Toplevel(app.root)
        dialog.title("Choose an existing contract assembly")
        dialog.geometry("1060x600")
        dialog.minsize(700, 400)
        dialog.lift()
        dialog.columnconfigure(0, weight=1)
        dialog.rowconfigure(1, weight=1)

        self.search_var = tk.StringVar(master=dialog)
        search_row = ttk.Frame(dialog, padding=(12, 12, 12, 6))
        search_row.grid(row=0, column=0, sticky="ew")
        search_row.columnconfigure(1, weight=1)
        ttk.Label(search_row, text="Search assemblies").grid(row=0, column=0, padx=(0, 8))
        self.search_entry = ttk.Entry(search_row, textvariable=self.search_var)
        self.search_entry.grid(row=0, column=1, sticky="ew")

        panes = ttk.Panedwindow(dialog, orient="horizontal")
        panes.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        table_frame = ttk.Frame(panes)
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        panes.add(table_frame, weight=1)
        self.tree = ttk.Treeview(
            table_frame, columns=("name", "revision", "date", "updates"),
            show="headings", selectmode="browse",
        )
        for column, title in (
            ("name", "Assembly"), ("revision", "Latest revision"),
            ("date", "Saved"), ("updates", "Wording"),
        ):
            self.tree.heading(column, text=title)
        self.tree.column("name", width=230, anchor="w")
        self.tree.column("revision", width=105, anchor="center", stretch=False)
        self.tree.column("date", width=90, anchor="w", stretch=False)
        self.tree.column("updates", width=135, anchor="center", stretch=False)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scroll.set)

        # The preview is the pane that grows when the window does.
        preview_frame = ttk.LabelFrame(panes, text="Preview", padding=4)
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(1, weight=1)
        panes.add(preview_frame, weight=3)
        self.preview_heading = ttk.Label(preview_frame, text="", foreground="#555555")
        self.preview_heading.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.preview = tk.Text(
            preview_frame, wrap="word", state="disabled", font="TkDefaultFont",
            relief="solid", borderwidth=1, padx=8, pady=6, cursor="arrow", width=50,
        )
        self.preview.grid(row=1, column=0, sticky="nsew")
        preview_scroll = ttk.Scrollbar(
            preview_frame, orient="vertical", command=self.preview.yview
        )
        preview_scroll.grid(row=1, column=1, sticky="ns")
        self.preview.configure(yscrollcommand=preview_scroll.set)
        configure_preview_tags(self.preview)
        ttk.Label(
            preview_frame, text=PREVIEW_KEY, foreground="#555555", wraplength=520,
            justify="left",
        ).grid(row=2, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.tree.bind("<Double-1>", self.open_latest)
        self.tree.bind("<Return>", self.open_latest)
        self.tree.bind("<<TreeviewSelect>>", self._highlight_changed)
        self.search_var.trace_add("write", self.refresh_rows)

        buttons = ttk.Frame(dialog, padding=(12, 0, 12, 12))
        buttons.grid(row=2, column=0, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=dialog.destroy).pack(side="right")
        ttk.Button(buttons, text="Open latest", command=self.open_latest).pack(
            side="right", padx=(0, 7)
        )
        ttk.Button(
            buttons, text="Earlier revisions…", command=self.choose_earlier
        ).pack(side="right", padx=(0, 7))
        if edit_revision is not None:
            ttk.Button(
                buttons, text="Edit in Build an assembly…", command=self.edit_latest
            ).pack(side="left")
        dialog.bind("<Destroy>", self._destroyed, add="+")
        self.refresh_rows()
        self.search_entry.focus_set()

    # -- the list ------------------------------------------------------------

    def refresh_rows(self, *_args):
        query = self.search_var.get().strip().casefold()
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.by_id.clear()
        for item in self.assemblies:
            assembly = item["assembly"]
            if query and query not in assembly["name"].casefold():
                continue
            revision = item["latest"]
            key = str(assembly["id"])
            self.by_id[key] = item
            self.tree.insert(
                "", "end", iid=key,
                values=(
                    assembly["name"], f"Revision {revision['number']}",
                    str(revision["created"])[:10],
                    "New wording available" if item["has_updates"] else "Up to date",
                ),
            )
        rows = self.tree.get_children()
        if rows:
            self.tree.selection_set(rows[0])
            self.tree.focus(rows[0])
        else:
            self._show_message("No saved assembly matches your search.")

    def selected_item(self):
        selected = self.tree.selection()
        return self.by_id.get(selected[0]) if selected else None

    # -- the preview ---------------------------------------------------------

    def _highlight_changed(self, _event=None):
        """Draw the highlighted assembly once the highlight has rested."""
        if self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
        try:
            self._preview_after_id = self.window.after(PREVIEW_DELAY_MS, self.show_latest_preview)
        except tk.TclError:
            self._preview_after_id = None

    def show_latest_preview(self):
        self._preview_after_id = None
        item = self.selected_item()
        if item is None:
            return
        revision = item["latest"]
        self.show_revision_preview(
            int(revision["id"]),
            f"{item['assembly']['name']} · revision {revision['number']}",
            item["has_updates"],
        )

    def show_revision_preview(self, revision_id, heading, has_updates=False):
        """Show one pinned revision in the preview pane (never newer wording)."""
        try:
            if not self.window.winfo_exists():
                return
        except tk.TclError:
            return
        self.preview_heading.configure(text=heading)
        try:
            segments = self._cache.get(revision_id)
            if segments is None:
                revision = self.library.get_assembly_revision(revision_id)
                if revision is None:
                    raise ValueError("revision missing")
                segments = revision_preview_segments(revision, has_updates)
                self._cache[revision_id] = segments
        except Exception:  # noqa: BLE001  the preview is a convenience and must never raise
            self._show_message(
                "This assembly cannot be previewed (a component or its wording could not "
                "be read). You can still try to open it."
            )
            return
        self._shown_revision_id = revision_id
        self._set_preview(segments)

    def _set_preview(self, segments):
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        for text, tags in segments:
            self.preview.insert("end", text, tags)
        self.preview.configure(state="disabled")
        self.preview.yview_moveto(0)

    def _show_message(self, text):
        self._shown_revision_id = None
        self._set_preview([(text, ("source_text",))])

    # -- actions ----------------------------------------------------------------

    def open_latest(self, _event=None):
        item = self.selected_item()
        if item is None:
            return
        if self.open_revision(int(item["latest"]["id"]), self.window):
            self.window.destroy()

    def edit_latest(self):
        item = self.selected_item()
        if item is None or self.edit_revision is None:
            return
        try:
            revision = self.library.get_assembly_revision(int(item["latest"]["id"]))
        except Exception as exc:  # noqa: BLE001
            messagebox.showerror("Could not open this assembly", str(exc), parent=self.window)
            return
        if revision is None:
            return
        self.edit_revision(revision)
        self.window.destroy()

    def choose_earlier(self):
        item = self.selected_item()
        if item is None:
            return
        revisions = [
            revision for revision in self.library.list_assembly_revisions(
                item["assembly"]["id"]
            ) if revision["finalized"]
        ]
        if len(revisions) < 2:
            messagebox.showinfo(
                "No earlier revisions",
                "This assembly has only one saved revision.",
                parent=self.window,
            )
            return
        name = item["assembly"]["name"]
        earlier = tk.Toplevel(self.window)
        earlier.title(f"Earlier revisions of {name}")
        earlier.geometry("560x320")
        earlier.minsize(440, 240)
        earlier.transient(self.window)
        earlier.columnconfigure(0, weight=1)
        earlier.rowconfigure(0, weight=1)
        tree = ttk.Treeview(
            earlier, columns=("revision", "date", "note"),
            show="headings", selectmode="browse",
        )
        for column, title in (("revision", "Revision"), ("date", "Saved"), ("note", "Note")):
            tree.heading(column, text=title)
        tree.column("revision", width=100, anchor="center", stretch=False)
        tree.column("date", width=120, anchor="w", stretch=False)
        tree.column("note", width=280, anchor="w")
        tree.grid(row=0, column=0, sticky="nsew", padx=(12, 0), pady=12)
        revision_scroll = ttk.Scrollbar(earlier, orient="vertical", command=tree.yview)
        revision_scroll.grid(row=0, column=1, sticky="ns", padx=(0, 12), pady=12)
        tree.configure(yscrollcommand=revision_scroll.set)
        numbers = {}
        for revision in revisions[1:]:
            numbers[str(revision["id"])] = revision["number"]
            tree.insert(
                "", "end", iid=str(revision["id"]),
                values=(
                    f"Revision {revision['number']}",
                    str(revision["created"])[:10], revision.get("note", ""),
                ),
            )

        def preview_selected(_event=None):
            """Highlighting an earlier revision shows it in the main preview."""
            selected = tree.selection()
            if selected:
                self.show_revision_preview(
                    int(selected[0]), f"{name} · revision {numbers[selected[0]]} (earlier)"
                )

        def back_to_latest(_event=None):
            if _event is None or _event.widget is earlier:
                try:
                    self.show_latest_preview()
                except tk.TclError:      # the whole window is closing
                    pass

        def open_earlier(_event=None):
            selected = tree.selection()
            if not selected:
                return
            if self.open_revision(int(selected[0]), earlier):
                earlier.destroy()
                self.window.destroy()

        tree.bind("<Double-1>", open_earlier)
        tree.bind("<Return>", open_earlier)
        tree.bind("<<TreeviewSelect>>", preview_selected)
        earlier.bind("<Destroy>", back_to_latest, add="+")
        buttons = ttk.Frame(earlier, padding=(12, 0, 12, 12))
        buttons.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(buttons, text="Cancel", command=earlier.destroy).pack(side="right")
        ttk.Button(buttons, text="Open", command=open_earlier).pack(side="right", padx=(0, 7))
        rows = tree.get_children()
        if rows:
            tree.selection_set(rows[0])
            tree.focus(rows[0])

    def _destroyed(self, event):
        if event.widget is self.window and self._preview_after_id is not None:
            try:
                self.window.after_cancel(self._preview_after_id)
            except tk.TclError:
                pass
            self._preview_after_id = None
