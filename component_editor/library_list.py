"""The saved-components list of the Components window: search, filters, selection.

A mixin of ComponentEditorWindow.
"""
from __future__ import annotations


class LibraryListMixin:
    """Saved-components list of the Components window."""

    def refresh_components(self, selected_id: int | None = None):
        include_archived = bool(self.show_archived_variable.get())
        all_components = self.library.list_components(
            include_archived=include_archived
        )

        categories = sorted(
            {item["category"].strip() for item in all_components if item["category"].strip()},
            key=str.casefold,
        )
        tags = sorted(
            {
                str(tag).strip()
                for item in all_components
                for tag in item["tags"]
                if str(tag).strip()
            },
            key=str.casefold,
        )
        category_values = ["All categories"] + categories
        tag_values = ["All tags"] + tags
        self.category_filter.configure(values=category_values)
        self.tag_filter.configure(values=tag_values)
        if self.category_filter_variable.get() not in category_values:
            self.category_filter_variable.set("All categories")
        if self.tag_filter_variable.get() not in tag_values:
            self.tag_filter_variable.set("All tags")

        query = self.search_variable.get().strip()
        components = (
            self.library.search_components(
                query, include_archived=include_archived
            )
            if query
            else all_components
        )
        wanted_category = self.category_filter_variable.get()
        wanted_tag = self.tag_filter_variable.get()
        if wanted_category != "All categories":
            components = [
                item for item in components
                if item["category"].casefold() == wanted_category.casefold()
            ]
        if wanted_tag != "All tags":
            components = [
                item for item in components
                if wanted_tag.casefold() in {
                    str(tag).casefold() for tag in item["tags"]
                }
            ]

        self.suspend_selection = True
        try:
            for item in self.tree.get_children():
                self.tree.delete(item)
            for component in components:
                item_id = str(component["id"])
                row_tags = ("archived",) if component["status"] == "archived" else ()
                versions = self.library.list_component_versions(component["id"])
                latest = str(versions[0]["number"]) if versions else ""
                self.tree.insert(
                    "", "end", iid=item_id,
                    values=(component["name"], component["category"], latest),
                    tags=row_tags,
                )
            target = str(selected_id) if selected_id is not None else None
            if target and self.tree.exists(target):
                self.tree.selection_set(target)
                self.tree.focus(target)
                self.tree.see(target)
            elif self.current_component_id is not None and self.tree.exists(
                str(self.current_component_id)
            ):
                self.tree.selection_set(str(self.current_component_id))
        finally:
            self.suspend_selection = False

        if self.history_button is not None:
            self.history_button.configure(
                state="normal" if self.current_component_id is not None else "disabled"
            )

    def select_component(self, _event=None):
        if self.suspend_selection:
            return
        selection = self.tree.selection()
        if not selection:
            return
        selected_id = int(selection[0])
        if selected_id == self.current_component_id:
            return
        if not self._confirm_pending_changes("opening another component"):
            self.suspend_selection = True
            try:
                if self.current_component_id is not None and self.tree.exists(
                    str(self.current_component_id)
                ):
                    self.tree.selection_set(str(self.current_component_id))
                    self.tree.focus(str(self.current_component_id))
                else:
                    self.tree.selection_remove(*selection)
            finally:
                self.suspend_selection = False
            return
        self._load_component(selected_id)
