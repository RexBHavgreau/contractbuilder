"""Markdown-backed component editor with formatting, tables, fields and DOCX import review.

The editor keeps Markdown as the saved source, presents a simplified formatted
view by default, and uses the existing Markdown and DOCX conversion modules.

Where things live (T-052). Modules marked *pure* import no Tkinter, so their
tests run without a display:

=====================  ======================================================
``text_rules``         *pure* escaping, block/inline formatting, toggles
``toolbar_layout``     *pure* toolbar wrapping rule
``tables``             *pure* find, split and build Markdown tables
``fields``             *pure* field placeholders, checks, known field names
``save_feedback``      *pure* words and timing of the Save result
``styling``            formatted view of Markdown in a Text widget
``table_dialog``       table grid dialog
``field_dialog``       legacy one-off insert dialog
``field_picker``       searchable picker and guided field creator
``import_dialog``      Word import review dialog
``history_dialog``     version history dialog
``toolbar``            toolbar buttons, wrapping and state (window mixin)
``wording_actions``    formatting, field, table and import actions (mixin)
``library_list``       saved-components list, search and filters (mixin)
``window``             ComponentEditorWindow itself
=====================  ======================================================

A new window or dialog is a new module, not more lines in an existing one.
Everything the app and tests import is re-exported here, so
``from component_editor import ...`` works as it did when this was one file.
"""
from __future__ import annotations

import tkinter as tk  # noqa: F401  (re-exported, as in the single-file module)
from tkinter import filedialog, messagebox, ttk  # noqa: F401

from .fields import (  # noqa: F401
    _FIELD_FORMATS,
    _PROFILE_FIELD_NAMES,
    available_field_names,
    make_field_placeholder,
    malformed_field_message,
)
from .save_feedback import (  # noqa: F401
    SAVE_FEEDBACK_COLORS,
    SAVE_FEEDBACK_SECONDS,
    save_feedback_text,
)
from .styling import _style_markdown_widget, configure_preview_tags  # noqa: F401
from .tables import (  # noqa: F401
    _escape_table_cell,
    _has_markdown_table_delimiter,
    _is_markdown_table_separator,
    _split_markdown_table_row,
    build_markdown_table,
    find_markdown_table,
)
from .text_rules import (  # noqa: F401
    _MARKDOWN_SPECIAL,
    _PLAIN_TEXT_SPECIAL,
    _emphasis_matches,
    _escape_line_marker,
    _escape_plain_segment,
    _markdown_is_editable,
    _protected_markdown_spans,
    _strip_emphasis,
    format_markdown_block,
    inline_format_active,
    markdown_block_state,
    markdown_to_plain_text,
    plain_text_to_markdown,
    toggle_inline_format,
    toggle_markdown_block,
)
from .toolbar_layout import wrap_toolbar_groups  # noqa: F401

# Dialogs and the window last: wording_actions looks the dialogs up here.
from .field_dialog import FieldInsertDialog  # noqa: F401,E402
from .field_picker import (  # noqa: F401,E402
    FIELD_KINDS,
    FieldCreatorDialog,
    FieldPickerDialog,
    build_created_field,
    field_kind_definition,
    field_definition_placeholder,
)
# Preserve the public dialog hook used by existing integrations and tests.
FieldInsertDialog = FieldPickerDialog
from .conditional_walkthrough import (  # noqa: F401,E402
    ConditionalWordingDialog,
    build_conditional_text,
    build_optional_text,
    parse_conditional_text,
)
from .backup_dialog import LibraryBackupDialog  # noqa: F401,E402
from .history_dialog import open_version_history_dialog  # noqa: F401,E402
from .import_dialog import ImportReviewDialog  # noqa: F401,E402
from .table_dialog import TableEditorDialog  # noqa: F401,E402
from .window import ComponentEditorWindow  # noqa: F401,E402
