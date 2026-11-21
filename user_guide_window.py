"""The user guide window: a contents tree beside the full text (Help menu).

Clicking a heading in the tree moves the text to that heading. The whole guide
stays one scrollable text, so scrolling by hand still works.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext, ttk

from user_guide_outline import outline


def open_user_guide(parent, contents: str, title: str = "User instructions") -> tk.Toplevel:
    window = tk.Toplevel(parent)
    window.title(title)
    window.transient(parent)
    window.geometry("960x640")
    window.minsize(640, 420)

    panes = ttk.PanedWindow(window, orient="horizontal")
    panes.pack(fill="both", expand=True, padx=8, pady=8)

    contents_frame = ttk.Frame(panes)
    tree = ttk.Treeview(contents_frame, show="tree", selectmode="browse")
    tree_scroll = ttk.Scrollbar(contents_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=tree_scroll.set)
    tree.column("#0", width=345, minwidth=200, stretch=True)
    tree.pack(side="left", fill="both", expand=True)
    tree_scroll.pack(side="right", fill="y")
    panes.add(contents_frame, weight=1)

    text_frame = ttk.Frame(panes)
    box = scrolledtext.ScrolledText(text_frame, wrap="word", font="TkDefaultFont", padx=14, pady=12)
    box.pack(fill="both", expand=True)
    box.insert("1.0", contents)
    box.configure(state="disabled")
    panes.add(text_frame, weight=3)

    lines_by_item: dict[str, int] = {}
    main_item = None
    for heading in outline(contents):
        if heading.level == 1 or main_item is None:
            item = tree.insert("", "end", text=heading.title, open=False)
            main_item = item
        else:
            item = tree.insert(main_item, "end", text=heading.title)
        lines_by_item[item] = heading.line

    def show_heading(_event=None):
        selected = tree.selection()
        if not selected or selected[0] not in lines_by_item:
            return
        item = selected[0]
        if tree.get_children(item):
            tree.item(item, open=True)  # show the steps and subsections under a main section
        box.yview(f"{lines_by_item[item]}.0")

    tree.bind("<<TreeviewSelect>>", show_heading)

    buttons = ttk.Frame(window)
    buttons.pack(fill="x", padx=8, pady=(0, 8))
    ttk.Button(buttons, text="Close", command=window.destroy).pack(side="right")
    return window
