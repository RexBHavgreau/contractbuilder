"""Update checking, installing and settings for the main window."""
from __future__ import annotations

import threading
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import self_update
from update_checker import UpdateCheckError, check_for_update
from version import APP_VERSION, GITHUB_REPOSITORY


class UpdateDialogsMixin:
    """Update checking, installing and settings for the main window."""

    def check_for_updates(self, manual: bool):
        # Manual checks always run. Automatic checks are limited to once per day.
        if not manual and not self_update.automatic_update_check_due():
            return

        if self.update_checking:
            if manual:
                messagebox.showinfo(
                    "Update check",
                    "An update check is already in progress.",
                    parent=self.root,
                )
            return

        self.update_checking = True
        if manual:
            self.status.config(text="Checking for updates…", foreground="#555555")

        def worker():
            try:
                result = check_for_update(APP_VERSION, GITHUB_REPOSITORY, token=self_update.load_token())
                try:
                    self_update.record_successful_update_check()
                except OSError:
                    # A settings-file problem must not turn a successful check into a failure.
                    pass
                self.root.after(0, self._finish_update_check, result, None, manual)
            except UpdateCheckError as exc:
                self.root.after(0, self._finish_update_check, None, exc, manual)

        threading.Thread(target=worker, daemon=True).start()

    def _finish_update_check(self, result, error, manual: bool):
        self.update_checking = False
        if error:
            if manual:
                self.status.config(text="Update check could not be completed.", foreground="#8a5a00")
                messagebox.showwarning("Update check failed", str(error), parent=self.root)
            return

        if not result.available:
            if manual:
                self.status.config(text="You are using the latest published version.", foreground="#1b6e2e")
                messagebox.showinfo(
                    "No update available",
                    f"You are using the latest published version ({APP_VERSION}).",
                    parent=self.root,
                )
            return

        self.status.config(
            text=f"Version {result.latest_version} is available (you have {APP_VERSION}).",
            foreground="#1b6e2e",
        )
        heading = (
            f"{result.release_name} is available.\n"
            f"Installed version: {APP_VERSION}\n"
            f"Latest version: {result.latest_version}\n\n"
        )
        notes = result.notes.strip()
        if notes:
            note_lines = notes.splitlines()
            notes_preview = "\n".join(note_lines[:15])
            if len(note_lines) > 15:
                notes_preview += "\n…"
            heading += "What's new:\n" + notes_preview + "\n\n"
        asset = result.asset(self_update.WINDOWS_ASSET)
        if self_update.can_install_in_place() and asset:
            if messagebox.askyesno(
                "Update available",
                heading + "Download and install it now? The app will close and reopen "
                "as the new version. Anything not yet saved will be lost.",
                parent=self.root,
            ):
                self.install_update(result, asset)
            return
        if self_update.can_install_in_place():
            message = (heading + "That release has no Windows download attached yet, so it "
                       "cannot be installed automatically. Open the release page?")
        else:
            message = heading + "Open the GitHub release page to download it?"
        if messagebox.askyesno("Update available", message, parent=self.root) and result.release_url:
            webbrowser.open(result.release_url)

    def install_update(self, result, asset):
        """Download the new .exe with a progress bar, then swap it in and restart."""
        target = self_update.running_executable()
        in_place = self_update.folder_is_writable(target.parent)
        if in_place:
            destination = target.with_name(target.name + ".new")
        else:
            destination = self_update.downloads_folder() / f"Word Template Filler {result.latest_version}.exe"

        window = tk.Toplevel(self.root)
        window.title("Downloading update")
        window.transient(self.root)
        window.resizable(False, False)
        window.protocol("WM_DELETE_WINDOW", lambda: None)      # it finishes or fails on its own
        ttk.Label(window, text=f"Downloading version {result.latest_version}…",
                  padding=(16, 14, 16, 6)).pack(anchor="w")
        bar = ttk.Progressbar(window, length=360, mode="determinate", maximum=max(asset.size, 1))
        bar.pack(padx=16, pady=(0, 16))
        window.grab_set()

        def progress(done, _total):
            self.root.after(0, lambda: bar.configure(value=done))

        def worker():
            try:
                self_update.download_asset(asset, destination, self_update.load_token(), progress)
                self.root.after(0, finished, None)
            except self_update.UpdateInstallError as exc:
                self.root.after(0, finished, str(exc))

        def finished(problem):
            window.grab_release()
            window.destroy()
            if problem:
                messagebox.showerror("Update not installed", problem, parent=self.root)
                return
            if not in_place:
                messagebox.showinfo(
                    "Update downloaded",
                    f"The app's own folder cannot be written to:\n{target.parent}\n\n"
                    f"so the new version was saved to:\n{destination}\n\n"
                    "Close this app and use that file instead, or move it over the old one.",
                    parent=self.root,
                )
                return
            try:
                self_update.start_swap(target, destination)
            except OSError as exc:
                messagebox.showerror("Update not installed", f"The update could not start: {exc}",
                                     parent=self.root)
                return
            self.root.destroy()

        threading.Thread(target=worker, daemon=True).start()

    def _report_failed_update(self):
        if not self_update.can_install_in_place():
            return
        target = self_update.running_executable()
        self_update.cleanup_stale_update_download(target)
        note = self_update.leftover_note(target)
        if note:
            messagebox.showwarning("The last update did not finish", note, parent=self.root)

    def update_settings(self):
        """Manage the optional per-user GitHub token for update checks."""
        window = tk.Toplevel(self.root)
        window.title("Update settings")
        window.transient(self.root)
        window.resizable(False, False)
        frame = ttk.Frame(window, padding=16)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, wraplength=460, justify="left", text=(
            "You do not need a GitHub token for normal update checks. If you often see "
            "\"GitHub is limiting update checks from your network for now\", you can "
            "add an optional token here to raise GitHub's API limit for your checks.\n\n"
            "Create a fine-grained personal access token on GitHub (Settings > Developer "
            "settings) for this repository only, with read-only access to Contents and "
            "nothing else. It is saved for your Windows user only, in:\n"
            f"{self_update.settings_path()}"
        )).pack(anchor="w")
        token = tk.StringVar(value=self_update.load_token())
        entry = ttk.Entry(frame, textvariable=token, show="•", width=56)
        entry.pack(fill="x", pady=(12, 4))
        status = ttk.Label(frame, foreground="#555555", wraplength=460, justify="left")
        status.pack(anchor="w", pady=(0, 8))
        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        def save():
            try:
                self_update.save_token(token.get())
            except OSError as exc:
                status.config(text=f"Could not save: {exc}", foreground="#b00020")
                return
            status.config(text="Saved. Checking for updates…", foreground="#555555")
            window.destroy()
            self.check_for_updates(manual=True)

        def remove():
            token.set("")
            try:
                self_update.save_token("")
            except OSError:
                pass
            status.config(text="Token removed.", foreground="#555555")

        ttk.Button(buttons, text="Save and check now", command=save).pack(side="right")
        ttk.Button(buttons, text="Remove token", command=remove).pack(side="right", padx=8)
        ttk.Button(buttons, text="Close", command=window.destroy).pack(side="left")
        entry.focus_set()
