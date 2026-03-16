"""VimInput — single-line text-entry widget with vim normal/insert sub-modes.

INSERT mode  standard text editing; Esc → COMMAND mode (event stopped).
COMMAND mode vim motions (h/l/w/b/0/$/x/cw) and i/a/A to return to INSERT;
             Enter submits; Esc is NOT stopped — it bubbles to the parent so
             the parent can decide what to do (cancel, save, etc.).
"""

from __future__ import annotations

from textual import events
from textual.app import RenderableType
from textual.message import Message
from textual.widget import Widget


class VimInput(Widget, can_focus=True):
    """Single-line text input with vim normal/insert sub-modes."""

    DEFAULT_CSS = """
    VimInput {
        height: 3;
        border: tall $panel;
        padding: 0 1;
        background: $surface;
        color: $text;
    }
    VimInput:focus {
        border: tall $accent;
    }
    VimInput.vim-insert-mode {
        border: tall $success;
    }
    """

    # ------------------------------------------------------------------
    # Messages
    # ------------------------------------------------------------------

    class Submitted(Message):
        """Posted when Enter is pressed in either sub-mode."""

        def __init__(self, vim_input: "VimInput", value: str) -> None:
            super().__init__()
            self.vim_input = vim_input
            self.value = value

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        value: str = "",
        placeholder: str = "",
        start_mode: str = "insert",  # "insert" | "command"
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._text: str = value
        self._placeholder: str = placeholder
        self._vim_mode: str = start_mode
        self._pending: str = ""  # for multi-key sequences like "cw"
        self._view_offset: int = 0  # horizontal scroll offset for long lines
        # In command mode the cursor stays within the text (not past last char).
        if start_mode == "command":
            self._cursor: int = max(0, len(value) - 1) if value else 0
        else:
            self._cursor = len(value)

    def on_mount(self) -> None:
        if self._vim_mode == "insert":
            self.add_class("vim-insert-mode")

    def on_focus(self) -> None:
        self.refresh()

    def on_blur(self) -> None:
        self.refresh()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def value(self) -> str:
        return self._text

    @value.setter
    def value(self, text: str) -> None:
        self._text = text
        self._cursor = min(self._cursor, len(text))
        self.refresh()

    def clear(self) -> None:
        self._text = ""
        self._cursor = 0
        self._pending = ""
        self._view_offset = 0
        self.refresh()

    def set_placeholder(self, placeholder: str) -> None:
        self._placeholder = placeholder
        self.refresh()

    def set_mode(self, mode: str) -> None:
        """Switch between 'insert' and 'command' sub-modes."""
        self._vim_mode = mode
        self._pending = ""
        if mode == "command":
            self.remove_class("vim-insert-mode")
            # Command-mode cursor cannot sit past the last character.
            if self._text:
                self._cursor = min(self._cursor, len(self._text) - 1)
            else:
                self._cursor = 0
        else:
            self.add_class("vim-insert-mode")
        self.refresh()

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _scroll_to_cursor(self) -> None:
        """Adjust _view_offset so the cursor is always visible."""
        width = self.content_size.width or 40
        if self._cursor < self._view_offset:
            self._view_offset = self._cursor
        elif self._cursor >= self._view_offset + width:
            self._view_offset = self._cursor - width + 1

    def render(self) -> RenderableType:
        from rich.text import Text

        if not self._text:
            if not self.has_focus:
                return Text(self._placeholder, style="dim")
            return Text(" ", style="reverse")

        self._scroll_to_cursor()
        text = self._text
        cursor = max(0, min(self._cursor, len(text)))
        offset = self._view_offset
        visible = text[offset:]

        t = Text(no_wrap=True)
        rel = cursor - offset  # cursor position within visible slice
        if 0 <= rel < len(visible):
            t.append(visible[:rel])
            t.append(visible[rel], style="reverse")
            t.append(visible[rel + 1 :])
        elif rel == len(visible):
            t.append(visible)
            t.append(" ", style="reverse")
        else:
            t.append(visible)
        return t

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def _on_key(self, event: events.Key) -> None:
        if self._vim_mode == "insert":
            self._handle_insert(event)
        else:
            self._handle_command(event)
        self.refresh()

    def _handle_insert(self, event: events.Key) -> None:
        key = event.key

        if key == "escape":
            # Switch to command sub-mode; consume the event so it does not
            # propagate to the parent (which might cancel the whole operation).
            event.stop()
            event.prevent_default()
            self.set_mode("command")

        elif key == "enter":
            event.stop()
            event.prevent_default()
            self.post_message(self.Submitted(self, self._text))

        elif key == "backspace":
            event.stop()
            event.prevent_default()
            if self._cursor > 0:
                self._text = self._text[: self._cursor - 1] + self._text[self._cursor :]
                self._cursor -= 1

        elif key == "delete":
            event.stop()
            event.prevent_default()
            if self._cursor < len(self._text):
                self._text = self._text[: self._cursor] + self._text[self._cursor + 1 :]

        elif key == "left":
            event.stop()
            event.prevent_default()
            self._cursor = max(0, self._cursor - 1)

        elif key == "right":
            event.stop()
            event.prevent_default()
            self._cursor = min(len(self._text), self._cursor + 1)

        elif key in ("home", "ctrl+a"):
            event.stop()
            event.prevent_default()
            self._cursor = 0

        elif key in ("end", "ctrl+e"):
            event.stop()
            event.prevent_default()
            self._cursor = len(self._text)

        elif event.is_printable and event.character:
            event.stop()
            event.prevent_default()
            self._text = (
                self._text[: self._cursor] + event.character + self._text[self._cursor :]
            )
            self._cursor += 1

    def _handle_command(self, event: events.Key) -> None:
        key = event.key

        # Resolve pending multi-key sequences (e.g. "cw", "dd", "d$", "d0").
        if self._pending:
            pending = self._pending
            self._pending = ""
            if pending == "c" and key == "w":
                event.stop()
                event.prevent_default()
                self._cmd_change_word()
            elif pending == "d":
                event.stop()
                event.prevent_default()
                if key == "d":
                    self._text = ""
                    self._cursor = 0
                elif key == "dollar":
                    self._text = self._text[: self._cursor]
                    self._cursor = max(0, len(self._text) - 1)
                elif key == "0":
                    self._text = self._text[self._cursor :]
                    self._cursor = 0
            # Unknown sequence — silently discard; do not consume the event.
            return

        if key == "escape":
            # Do NOT stop the event: let it bubble to the parent so the parent
            # can cancel/save as appropriate for the current context.
            return

        # Every other command-mode key is consumed here.
        event.stop()
        event.prevent_default()

        if key == "i":
            self.set_mode("insert")
        elif key == "a":
            if self._cursor < len(self._text):
                self._cursor += 1
            self.set_mode("insert")
        elif key == "A":
            self._cursor = len(self._text)
            self.set_mode("insert")
        elif key in ("h", "left"):
            self._cursor = max(0, self._cursor - 1)
        elif key in ("l", "right"):
            if self._text:
                self._cursor = min(len(self._text) - 1, self._cursor + 1)
        elif key == "w":
            self._cmd_word_forward()
        elif key == "b":
            self._cmd_word_backward()
        elif key == "0":
            self._cursor = 0
        elif key == "dollar":
            if self._text:
                self._cursor = len(self._text) - 1
        elif key == "x":
            if self._cursor < len(self._text):
                self._text = (
                    self._text[: self._cursor] + self._text[self._cursor + 1 :]
                )
                self._cursor = min(self._cursor, max(0, len(self._text) - 1))
        elif key == "c":
            self._pending = "c"
        elif key == "d":
            self._pending = "d"
        elif key == "D":
            # Delete from cursor to end of line (same as d$).
            self._text = self._text[: self._cursor]
            self._cursor = max(0, len(self._text) - 1)
        elif key == "enter":
            self.post_message(self.Submitted(self, self._text))

    # ------------------------------------------------------------------
    # Word motion helpers
    # ------------------------------------------------------------------

    def _cmd_word_forward(self) -> None:
        pos = self._cursor
        text = self._text
        while pos < len(text) and not text[pos].isspace():
            pos += 1
        while pos < len(text) and text[pos].isspace():
            pos += 1
        self._cursor = min(pos, max(0, len(text) - 1))

    def _cmd_word_backward(self) -> None:
        pos = self._cursor
        text = self._text
        if pos == 0:
            return
        pos -= 1
        while pos > 0 and text[pos].isspace():
            pos -= 1
        while pos > 0 and not text[pos - 1].isspace():
            pos -= 1
        self._cursor = pos

    def _cmd_change_word(self) -> None:
        pos = self._cursor
        text = self._text
        end = pos
        while end < len(text) and not text[end].isspace():
            end += 1
        self._text = text[:pos] + text[end:]
        self._cursor = pos
        self.set_mode("insert")
