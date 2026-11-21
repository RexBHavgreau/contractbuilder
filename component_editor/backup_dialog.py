"""Backup, restore and Markdown export tools for the Components window."""
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from library_backup import (
    backup_reminder_due,
    export_library_backup,
    get_backup_reminder_settings,
    import_library_backup,
    preview_library_import,
    safe_markdown_filename,
    set_backup_reminder_enabled,
)
from markdown_files import read_markdown_file, write_component_markdown_file


class LibraryBackupDialog:
    """A small front end for portable backups and component Markdown files."""

    def __init__(self, parent, library, selected_component_id: int | None = None):
        self.library = library
        self.selected_component_id = selected_component_id
        self.window = tk.Toplevel(parent)
        self.window.title("Library backup and export")
        self.window.geometry("650x470")
        self.window.minsize(560, 420)
        self.window.transient(parent)
        self.window.grab_set()

        outer = ttk.Frame(self.window, padding=16)
        outer.pack(fill="both", expand=True)
        ttk.Label(outer, text="Protect and move your component library",
                  font=("TkDefaultFont", 13, "bold")).pack(anchor="w")
        ttk.Label(
            outer,
            text=("A full backup preserves every component version, assembly revision, "
                  "and reusable field definition. Markdown files are convenient for "
                  "sharing individual components."),
            wraplength=610,
        ).pack(anchor="w", pady=(5, 14))

        backup_box = ttk.LabelFrame(outer, text="Complete library backup", padding=10)
        backup_box.pack(fill="x", pady=(0, 10))
        self.include_profiles = tk.BooleanVar(master=self.window, value=False)
        ttk.Checkbutton(
            backup_box,
            text="Include publisher profiles and contact details (private business data)",
            variable=self.include_profiles,
        ).pack(anchor="w")
        ttk.Button(
            backup_box, text="Export full backup…", command=self.export_backup
        ).pack(anchor="w", pady=(8, 3))
        ttk.Button(
            backup_box, text="Import backup…", command=self.import_backup
        ).pack(anchor="w")

        markdown_box = ttk.LabelFrame(outer, text="Markdown files", padding=10)
        markdown_box.pack(fill="x", pady=(0, 10))
        self.export_selected_button = ttk.Button(
            markdown_box, text="Export selected component…",
            command=self.export_selected_markdown,
            state="normal" if selected_component_id is not None else "disabled",
        )
        self.export_selected_button.pack(anchor="w")
        ttk.Button(
            markdown_box, text="Export all components…",
            command=self.export_all_markdown,
        ).pack(anchor="w", pady=4)
        ttk.Button(
            markdown_box, text="Import Markdown file(s)…",
            command=self.import_markdown,
        ).pack(anchor="w")

        reminder_box = ttk.LabelFrame(outer, text="Backup reminder", padding=10)
        reminder_box.pack(fill="x")
        reminder = get_backup_reminder_settings(self.library.path)
        self.reminder_enabled = tk.BooleanVar(
            master=self.window, value=reminder["enabled"]
        )
        ttk.Checkbutton(
            reminder_box,
            text="Remind me when I have not made a backup in four weeks",
            variable=self.reminder_enabled,
            command=self.save_reminder_setting,
        ).pack(anchor="w")
        ttk.Label(
            reminder_box,
            text="Off by default. The reminder preference is stored on this computer, not in the backup.",
            wraplength=600,
        ).pack(anchor="w", pady=(3, 0))

        footer = ttk.Frame(outer)
        footer.pack(fill="x", pady=(12, 0))
        self.status = ttk.Label(footer, text="", foreground="#555555")
        self.status.pack(side="left", fill="x", expand=True)
        ttk.Button(footer, text="Close", command=self.close).pack(side="right")

        if backup_reminder_due(self.library.path):
            messagebox.showinfo(
                "Time to back up your library",
                "It has been at least four weeks since your last library backup. "
                "Export a full backup to protect the saved components and assemblies.",
                parent=self.window,
            )

    def save_reminder_setting(self):
        set_backup_reminder_enabled(
            self.library.path, bool(self.reminder_enabled.get())
        )

    def export_backup(self):
        path = filedialog.asksaveasfilename(
            parent=self.window,
            title="Save library backup",
            defaultextension=".json",
            filetypes=(("Contract Builder backup", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            result = export_library_backup(
                self.library.path, path,
                include_publisher_profiles=bool(self.include_profiles.get()),
            )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Backup failed", str(exc), parent=self.window)
            return
        count = sum(result["counts"].values())
        self.status.configure(text=f"Backup saved: {count} records.")
        messagebox.showinfo(
            "Backup complete",
            f"Saved the complete component library to:\n{path}\n\n"
            f"{count} records were included. "
            + ("Publisher profiles were included." if result["includes_publisher_profiles"]
               else "Publisher profiles were left out."),
            parent=self.window,
        )

    def import_backup(self):
        path = filedialog.askopenfilename(
            parent=self.window,
            title="Choose a Contract Builder backup",
            filetypes=(("Contract Builder backup", "*.json"), ("All files", "*.*")),
        )
        if not path:
            return
        include_profiles = bool(self.include_profiles.get())
        try:
            preview = preview_library_import(
                self.library.path, path, mode="merge",
                include_publisher_profiles=include_profiles,
            )
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror("Backup cannot be imported", str(exc), parent=self.window)
            return
        messagebox.showinfo(
            "Review this backup",
            preview["summary"] + "\n\nNext, choose how to bring these records into this library.",
            parent=self.window,
        )
        choice = messagebox.askyesnocancel(
            "Merge or replace?",
            "Yes: merge the backup with this library. Existing records are kept when "
            "a field or profile name already exists.\n\n"
            "No: replace the component library with the backup. "
            "This cannot be undone.\n\n"
            "Cancel: make no changes.",
            parent=self.window,
        )
        if choice is None:
            return
        mode = "merge" if choice else "replace"
        try:
            result = import_library_backup(
                self.library.path, path, mode=mode,
                include_publisher_profiles=include_profiles,
            )
        except (OSError, ValueError, TypeError, RuntimeError) as exc:
            messagebox.showerror("Import failed", str(exc), parent=self.window)
            return
        inserted = sum(result["inserted"].values())
        skipped = sum(result["skipped"].values())
        self.status.configure(text=f"Imported {inserted} records.")
        details = [f"Imported {inserted} records using {mode}."]
        if skipped:
            details.append(f"Kept {skipped} existing record(s) with matching names.")
        if not result["includes_publisher_profiles"]:
            details.append("Publisher profiles on this computer were not changed.")
        messagebox.showinfo("Import complete", " ".join(details), parent=self.window)

    def _write_component(self, component_id: int, destination: Path):
        component = self.library.get_component(component_id)
        versions = self.library.list_component_versions(component_id)
        if component is None or not versions:
            raise ValueError("The selected component or its saved wording is unavailable.")
        latest = versions[0]
        write_component_markdown_file(
            destination, latest["markdown"], component, latest
        )

    def export_selected_markdown(self):
        if self.selected_component_id is None:
            return
        component = self.library.get_component(self.selected_component_id)
        if component is None:
            messagebox.showerror("Export failed", "The selected component no longer exists.",
                                 parent=self.window)
            return
        path = filedialog.asksaveasfilename(
            parent=self.window, title="Export component as Markdown",
            initialfile=safe_markdown_filename(component["name"], component["id"]),
            defaultextension=".md",
            filetypes=(("Markdown files", "*.md"), ("All files", "*.*")),
        )
        if not path:
            return
        try:
            self._write_component(self.selected_component_id, Path(path))
        except (OSError, ValueError) as exc:
            messagebox.showerror("Export failed", str(exc), parent=self.window)
            return
        self.status.configure(text="Component exported.")

    def export_all_markdown(self):
        directory = filedialog.askdirectory(
            parent=self.window, title="Choose a folder for Markdown exports"
        )
        if not directory:
            return
        components = self.library.list_components(include_archived=True)
        outputs = [
            (component, Path(directory) / safe_markdown_filename(
                component["name"], component["id"]
            ))
            for component in components
        ]
        existing = [path.name for _component, path in outputs if path.exists()]
        if existing and not messagebox.askyesno(
            "Replace existing Markdown files?",
            f"{len(existing)} file(s) with matching names already exist in that folder. "
            "Replace them?",
            parent=self.window,
        ):
            return
        try:
            for component, path in outputs:
                self._write_component(component["id"], path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Export failed", str(exc), parent=self.window)
            return
        self.status.configure(text=f"Exported {len(outputs)} component(s).")
        messagebox.showinfo(
            "Markdown export complete",
            f"Exported {len(outputs)} component(s) to:\n{directory}",
            parent=self.window,
        )

    def import_markdown(self):
        paths = filedialog.askopenfilenames(
            parent=self.window, title="Import component Markdown files",
            filetypes=(("Markdown files", "*.md"), ("All files", "*.*")),
        )
        if not paths:
            return
        pending = []
        warnings = []
        try:
            for raw_path in paths:
                path = Path(raw_path)
                imported = read_markdown_file(path)
                metadata = imported.metadata or {}
                component = metadata.get("component", {})
                saved_version = metadata.get("saved_version", {})
                name = str(component.get("name") or path.stem).strip()
                if not name:
                    name = path.stem or "Imported component"
                pending.append((path, imported, name, component, saved_version))
                warnings.extend(f"{path.name}: {warning}" for warning in imported.warnings)
        except (OSError, UnicodeError, ValueError) as exc:
            messagebox.showerror("Markdown import failed", str(exc), parent=self.window)
            return
        summary = f"Ready to import {len(pending)} component file(s):\n" + "\n".join(
            f"• {name} — {path.name}" for path, _item, name, _component, _version in pending
        )
        if warnings:
            summary += "\n\nNotes:\n" + "\n".join(warnings[:8])
        if not messagebox.askyesno(
            "Review Markdown import", summary + "\n\nAdd these as new components?",
            parent=self.window,
        ):
            return
        made = 0
        try:
            for _path, imported, name, component, saved_version in pending:
                component_id = self.library.create_component(
                    name,
                    imported.text,
                    description=str(component.get("description") or ""),
                    category=str(component.get("category") or ""),
                    tags=component.get("tags") or [],
                    note=str(saved_version.get("note") or "Imported from Markdown"),
                    paragraph_styles=saved_version.get("paragraph_styles") or (),
                )
                if component.get("status") == "archived":
                    self.library.archive_component(component_id)
                made += 1
        except (OSError, ValueError, TypeError) as exc:
            messagebox.showerror(
                "Markdown import incomplete",
                f"Imported {made} file(s) before the error:\n{exc}",
                parent=self.window,
            )
            return
        self.status.configure(text=f"Imported {made} component(s).")
        messagebox.showinfo("Markdown import complete",
                            f"Added {made} component(s) to the library.", parent=self.window)

    def close(self):
        self.save_reminder_setting()
        self.window.destroy()
