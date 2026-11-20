"""The formatting toolbar of the Components window: its buttons, wrapping and state.

A mixin of ComponentEditorWindow, so every button stays an attribute of the
window (editor.bold_button and so on).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .text_rules import inline_format_active, markdown_block_state
from .toolbar_layout import wrap_toolbar_groups


class ToolbarMixin:
    """Toolbar parts of the Components window."""

    def _build_toolbar(self, edit_frame):
        # Two short rows, so the toolbar does not force the window to be wider than the screen.
        toolbar = ttk.Frame(edit_frame)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        self.toolbar = toolbar
        self._toolbar_layout_after_id = None
        self._toolbar_last_width = None

        self.bold_variable = tk.BooleanVar(master=self.window, value=False)
        self.italic_variable = tk.BooleanVar(master=self.window, value=False)
        self.bullet_variable = tk.BooleanVar(master=self.window, value=False)
        self.numbered_variable = tk.BooleanVar(master=self.window, value=False)

        self.bold_button = ttk.Checkbutton(
            toolbar, text="Bold", style="Toolbutton", variable=self.bold_variable,
            command=lambda: self.apply_format("bold"),
        )
        self.italic_button = ttk.Checkbutton(
            toolbar, text="Italic", style="Toolbutton", variable=self.italic_variable,
            command=lambda: self.apply_format("italic"),
        )
        self.heading_button = ttk.Menubutton(toolbar, text="Heading")
        self.heading_menu = tk.Menu(self.heading_button, tearoff=False)
        self.heading_menu.add_command(
            label="Normal text", command=lambda: self.apply_format("normal")
        )
        for level in (1, 2, 3):
            self.heading_menu.add_command(
                label=f"Heading {level}",
                command=lambda selected=level: self.apply_format("heading", selected),
            )
        self.heading_button["menu"] = self.heading_menu

        self.bullet_button = ttk.Checkbutton(
            toolbar, text="Bullets", style="Toolbutton", variable=self.bullet_variable,
            command=lambda: self.apply_format("bullet"),
        )
        self.numbered_button = ttk.Checkbutton(
            toolbar, text="Numbering", style="Toolbutton",
            variable=self.numbered_variable,
            command=lambda: self.apply_format("numbered"),
        )
        self.indent_button = ttk.Button(
            toolbar, text="Indent one level", command=lambda: self.apply_format("indent")
        )
        self.outdent_button = ttk.Button(
            toolbar, text="Outdent one level", command=lambda: self.apply_format("outdent")
        )
        self.table_button = ttk.Button(
            toolbar, text="Insert table", command=self.open_table_editor
        )
        self.field_button = ttk.Button(
            toolbar, text="Insert field", command=self.open_field_dialog
        )
        self.import_button = ttk.Button(
            toolbar, text="Import Word", command=self.open_import_dialog
        )

        self.source_view_variable = tk.BooleanVar(master=self.window, value=False)
        self.source_view_button = ttk.Checkbutton(
            toolbar, text="Show raw text", variable=self.source_view_variable,
            command=self.toggle_source_view,
        )
        self.toolbar_button_widgets = {
            "bold": self.bold_button,
            "italic": self.italic_button,
            "heading": self.heading_button,
            "bullet": self.bullet_button,
            "numbered": self.numbered_button,
            "indent": self.indent_button,
            "outdent": self.outdent_button,
            "table": self.table_button,
            "field": self.field_button,
            "import": self.import_button,
            "source_view": self.source_view_button,
        }
        self.toolbar_groups = [
            ["bold", "italic", "heading"],
            ["bullet", "numbered", "indent", "outdent"],
            ["table", "field", "import"],
            ["source_view"],
        ]
        toolbar.bind("<Configure>", self._schedule_toolbar_layout, add="+")
        self._layout_toolbar(force=True)

    def _schedule_toolbar_layout(self, _event=None):
        """Coalesce resize events and reflow the toolbar when its pane changes width."""
        if self._toolbar_layout_after_id is not None:
            try:
                self.window.after_cancel(self._toolbar_layout_after_id)
            except tk.TclError:
                pass
        try:
            self._toolbar_layout_after_id = self.window.after_idle(self._layout_toolbar)
        except tk.TclError:
            self._toolbar_layout_after_id = None

    def _layout_toolbar(self, force: bool = False):
        """Arrange toolbar controls in rows without hiding or horizontally scrolling them."""
        self._toolbar_layout_after_id = None
        if not hasattr(self, "toolbar") or not self.toolbar.winfo_exists():
            return
        available = self.toolbar.winfo_width()
        if available <= 1:
            available = self.toolbar.winfo_reqwidth()
        if not force and self._toolbar_last_width == available:
            return
        self._toolbar_last_width = available
        groups = [
            [
                (name, self.toolbar_button_widgets[name].winfo_reqwidth())
                for name in group
            ]
            for group in self.toolbar_groups
        ]
        rows = wrap_toolbar_groups(groups, available, gap=4)
        # Use place within each row. Tk grid columns are shared across rows;
        # a wide control in one row otherwise shifts every later row's controls.
        for widget in self.toolbar_button_widgets.values():
            widget.grid_forget()
            widget.place_forget()

        y = 0
        for row in rows:
            x = 0
            row_height = 0
            for name, requested_width in row:
                widget = self.toolbar_button_widgets[name]
                requested_height = widget.winfo_reqheight()
                widget.place(x=x, y=y)
                x += requested_width + 4
                row_height = max(row_height, requested_height)
            y += row_height + 2

        self.toolbar.grid_propagate(False)
        self.toolbar.configure(height=max(1, y))

    def _update_toolbar_state(self, _event=None):
        """Keep pressed controls in step with the wording at the cursor or selection."""
        if not hasattr(self, "wording") or not self.wording.winfo_exists():
            return
        try:
            if not self.editor_markdown_mode:
                self.bold_variable.set(False)
                self.italic_variable.set(False)
                self.bullet_variable.set(False)
                self.numbered_variable.set(False)
                self.heading_button.configure(text="Heading")
                return
            selected = self.wording.tag_ranges("sel")
            if selected:
                start_index, end_index = str(selected[0]), str(selected[1])
            else:
                start_index = end_index = self.wording.index("insert")
            source = self.wording.get("1.0", "end-1c")
            start = len(self.wording.get("1.0", start_index))
            end = len(self.wording.get("1.0", end_index))
            self.bold_variable.set(inline_format_active(source, start, end, "bold"))
            self.italic_variable.set(inline_format_active(source, start, end, "italic"))
            state = markdown_block_state(source, start, end)
            self.bullet_variable.set(state["bullet"])
            self.numbered_variable.set(state["numbered"])
            self.heading_button.configure(
                text=f"Heading {state['heading']}" if state["heading"] else "Heading"
            )
        except tk.TclError:
            return
