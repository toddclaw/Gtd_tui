"""Config presets for integration tests.

Production default is ``startup_focus_sidebar=True`` (sidebar focused on launch).
Many tests send keys that must reach the task list; they use ``CFG_TASK_LIST_FOCUS``.
"""

from __future__ import annotations

from dataclasses import replace

from gtd_tui.config import Config, load_config

CFG_TASK_LIST_FOCUS: Config = replace(load_config(), startup_focus_sidebar=False)
