"""Pure toolbar wrapping rule: no Tkinter (the widgets are in toolbar.py)."""
from __future__ import annotations


def wrap_toolbar_groups(groups, available_width: int, gap: int = 4) -> list[list[tuple[str, int]]]:
    """Lay out named (widget, requested-width) items without splitting a fitting group."""
    width = max(1, int(available_width))
    spacing = max(0, int(gap))
    rows: list[list[tuple[str, int]]] = []
    current: list[tuple[str, int]] = []
    current_width = 0

    def finish_row():
        nonlocal current, current_width
        if current:
            rows.append(current)
            current = []
            current_width = 0

    for group in groups:
        items = [(str(name), max(1, int(item_width))) for name, item_width in group]
        if not items:
            continue
        group_width = sum(item_width for _name, item_width in items) + spacing * (len(items) - 1)
        if current and current_width + spacing + group_width <= width:
            current.extend(items)
            current_width += spacing + group_width
            continue
        if current:
            finish_row()
        if group_width <= width:
            current = list(items)
            current_width = group_width
            continue
        # A group wider than the window may split between buttons, never within one.
        for name, item_width in items:
            if current and current_width + spacing + item_width > width:
                finish_row()
            if current:
                current_width += spacing + item_width
            else:
                current_width = item_width
            current.append((name, item_width))
            if item_width > width:
                finish_row()
    finish_row()
    return rows
