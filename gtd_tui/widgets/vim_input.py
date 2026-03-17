"""VimInput — single-line or multi-line text-entry widget with vim normal/insert sub-modes.

INSERT mode  standard text editing; Esc → COMMAND mode (event stopped).
COMMAND mode vim motions (h/l/w/b/W/B/0/$/j/k/x/cw/dw/dW/dd/d$/d0) and i/a/A to
             return to INSERT; Enter submits (single-line only); Esc is NOT stopped
             — it bubbles to the parent so the parent can decide what to do.

Multi-line mode (multiline=True):
  Enter in INSERT mode inserts a newline instead of submitting.
  j/k in COMMAND mode move down/up one logical line.
  Submit is triggered by the parent (e.g. Esc closes a modal screen).
"""

from __future__ import annotations

from textual import events
from textual.app import RenderableType
from textual.message import Message
from textual.widget import Widget


class VimInput(Widget, can_focus=True):
    """Single-line or multi-line text input with vim normal/insert sub-modes."""

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
        """Posted when Enter is pressed in single-line mode."""

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
        multiline: bool = False,
        **kwargs: object,
    ) -> None:
        super().__init__(**kwargs)
        self._text: str = value
        self._placeholder: str = placeholder
        self._vim_mode: str = start_mode
        self._multiline: bool = multiline
        self._pending: str = ""  # for multi-key sequences like "cw"
        self._view_offset: int = 0  # horizontal scroll offset for the cursor line
        self._view_row: int = 0  # vertical scroll: first visible logical line
        self._undo_stack: list[tuple[str, int]] = []
        self._redo_stack: list[tuple[str, int]] = []
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
        self._update_scroll()
        self.refresh()

    def _push_undo(self) -> None:
        """Save current (text, cursor) to undo stack and clear redo stack."""
        self._undo_stack.append((self._text, self._cursor))
        self._redo_stack.clear()

    def clear(self) -> None:
        self._text = ""
        self._cursor = 0
        self._pending = ""
        self._view_offset = 0
        self._view_row = 0
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
            self._clamp_cursor_for_command()
        else:
            self.add_class("vim-insert-mode")
        self._update_scroll()
        self.refresh()

    # ------------------------------------------------------------------
    # Cursor helpers
    # ------------------------------------------------------------------

    def _cursor_row_col(self) -> tuple[int, int]:
        """Return (row, col) of the cursor within the text."""
        parts = self._text[: self._cursor].split("\n")
        return len(parts) - 1, len(parts[-1])

    def _offset_from_row_col(self, row: int, col: int) -> int:
        """Return the flat text offset for a (row, col) position."""
        lines = self._text.split("\n")
        return sum(len(lines[i]) + 1 for i in range(row)) + col

    def _current_line(self) -> str:
        row, _ = self._cursor_row_col()
        return self._text.split("\n")[row]

    def _clamp_cursor_for_command(self) -> None:
        """In command mode the cursor must not sit past the last char of its line."""
        if not self._text:
            self._cursor = 0
            return
        if self._multiline:
            row, col = self._cursor_row_col()
            line = self._text.split("\n")[row]
            if line and col >= len(line):
                self._cursor -= col - (len(line) - 1)
            elif not line:
                pass  # cursor stays at the newline position
        else:
            self._cursor = min(self._cursor, len(self._text) - 1)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _scroll_to_cursor(self) -> None:
        """Adjust _view_offset so the cursor column stays visible (single-line)."""
        width = self.content_size.width or 40
        if self._cursor < self._view_offset:
            self._view_offset = self._cursor
        elif self._cursor >= self._view_offset + width:
            self._view_offset = self._cursor - width + 1

    def _cursor_visual_position(self, width: int) -> int:
        """Return the 0-indexed visual row of the cursor, accounting for line wrapping.

        Each logical line occupies ceil(len(line) / width) visual rows (minimum 1).
        The cursor's visual row is the sum of all visual rows above it plus the
        sub-row index within its own line (cursor_col // width).
        """
        lines = self._text.split("\n")
        cursor_row, cursor_col = self._cursor_row_col()
        visual = 0
        for i in range(cursor_row):
            visual += max(1, (len(lines[i]) + width - 1) // width)
        visual += cursor_col // width
        return visual

    def _update_scroll(self) -> None:
        """Ensure the cursor remains visible. Call after any cursor movement."""
        if not self._multiline:
            return
        height = max(1, self.content_size.height or 4)
        width = max(1, self.content_size.width or 40)
        cursor_visual = self._cursor_visual_position(width)
        if cursor_visual < self._view_row:
            self._view_row = cursor_visual
        elif cursor_visual >= self._view_row + height:
            self._view_row = cursor_visual - height + 1

    def render(self) -> RenderableType:
        if self._multiline:
            return self._render_multiline()
        return self._render_singleline()

    def _render_singleline(self) -> RenderableType:
        from rich.text import Text

        if not self._text:
            if not self.has_focus:
                return Text(self._placeholder, style="dim")
            return Text(" ", style="reverse")

        self._scroll_to_cursor()
        text = self._text
        offset = self._view_offset
        visible = text[offset:]

        if not self.has_focus:
            return Text(visible, no_wrap=True)

        cursor = max(0, min(self._cursor, len(text)))
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

    def _render_multiline(self) -> RenderableType:
        from rich.text import Text

        height = max(1, self.content_size.height or 4)
        width = max(1, self.content_size.width or 40)

        if not self._text:
            if not self.has_focus:
                return Text(self._placeholder, style="dim")
            return Text(" ", style="reverse")

        lines = self._text.split("\n")
        cursor_row, cursor_col = self._cursor_row_col()
        cursor_sub = cursor_col // width  # which visual sub-row within cursor_row
        cursor_rel = cursor_col % width  # column within that sub-row

        # Belt-and-suspenders: re-apply scroll at render time using the actual
        # content_size, in case _update_scroll ran with a stale value.
        cursor_visual = self._cursor_visual_position(width)
        if cursor_visual < self._view_row:
            self._view_row = cursor_visual
        elif cursor_visual >= self._view_row + height:
            self._view_row = cursor_visual - height + 1

        t = Text(no_wrap=True)
        visual_idx = 0  # running count of visual rows from top of text
        rendered = 0  # visual rows written to `t`

        for i, line in enumerate(lines):
            # Number of visual sub-rows this logical line occupies.
            lh = max(1, (len(line) + width - 1) // width)

            for sub in range(lh):
                if visual_idx < self._view_row:
                    visual_idx += 1
                    continue
                if rendered >= height:
                    return t

                if rendered > 0:
                    t.append("\n")

                col_start = sub * width
                line_slice = line[col_start : col_start + width]

                if self.has_focus and i == cursor_row and sub == cursor_sub:
                    if cursor_rel < len(line_slice):
                        t.append(line_slice[:cursor_rel])
                        t.append(line_slice[cursor_rel], style="reverse")
                        t.append(line_slice[cursor_rel + 1 :])
                    else:
                        # Cursor at end of this sub-row (insert mode).
                        t.append(line_slice)
                        t.append(" ", style="reverse")
                else:
                    t.append(line_slice)

                rendered += 1
                visual_idx += 1

            # Edge case: cursor in insert mode sits exactly at a width boundary
            # (e.g. col 40 in a 40-char line with width=40).  That position maps
            # to a new visual sub-row not covered by the loop above.
            if (
                self.has_focus
                and i == cursor_row
                and cursor_col == len(line)
                and len(line) > 0
                and len(line) % width == 0
            ):
                if visual_idx >= self._view_row and rendered < height:
                    if rendered > 0:
                        t.append("\n")
                    t.append(" ", style="reverse")
                    rendered += 1
                visual_idx += 1

        return t

    # ------------------------------------------------------------------
    # Key handling
    # ------------------------------------------------------------------

    def on_resize(self, event: events.Resize) -> None:
        self._update_scroll()
        self.refresh()

    def _on_key(self, event: events.Key) -> None:
        if self._vim_mode == "insert":
            self._handle_insert(event)
        else:
            self._handle_command(event)
        self._update_scroll()
        self.refresh()

    def _handle_insert(self, event: events.Key) -> None:
        key = event.key

        if key == "escape":
            event.stop()
            event.prevent_default()
            self.set_mode("command")

        elif key == "enter":
            event.stop()
            event.prevent_default()
            if self._multiline:
                # Insert newline at cursor position.
                self._text = (
                    self._text[: self._cursor] + "\n" + self._text[self._cursor :]
                )
                self._cursor += 1
            else:
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
            if self._multiline:
                row, _ = self._cursor_row_col()
                self._cursor = self._offset_from_row_col(row, 0)
            else:
                self._cursor = 0

        elif key in ("end", "ctrl+e"):
            event.stop()
            event.prevent_default()
            if self._multiline:
                row, _ = self._cursor_row_col()
                line = self._text.split("\n")[row]
                self._cursor = self._offset_from_row_col(row, len(line))
            else:
                self._cursor = len(self._text)

        elif key == "up" and self._multiline:
            event.stop()
            event.prevent_default()
            self._cmd_line_up()

        elif key == "down" and self._multiline:
            event.stop()
            event.prevent_default()
            self._cmd_line_down()

        elif event.is_printable and event.character:
            event.stop()
            event.prevent_default()
            self._text = (
                self._text[: self._cursor]
                + event.character
                + self._text[self._cursor :]
            )
            self._cursor += 1

    def _handle_command(self, event: events.Key) -> None:
        key = event.key

        # Resolve pending multi-key sequences (e.g. "cw", "dd", "d$", "d0", "dw", "dW").
        if self._pending:
            pending = self._pending
            self._pending = ""
            if pending == "r":
                event.stop()
                event.prevent_default()
                ch = key if len(key) == 1 else (" " if key == "space" else None)
                if ch is not None and self._cursor < len(self._text):
                    self._push_undo()
                    self._text = (
                        self._text[: self._cursor] + ch + self._text[self._cursor + 1 :]
                    )
            elif pending == "c":
                event.stop()
                event.prevent_default()
                if key == "w":
                    self._push_undo()
                    self._cmd_change_word()
                elif key in ("dollar", "dollar_sign"):
                    self._push_undo()
                    self._cmd_change_to_line_end()
            elif pending == "d":
                event.stop()
                event.prevent_default()
                self._push_undo()
                if key == "d":
                    if self._multiline:
                        self._cmd_delete_line()
                    else:
                        self._text = ""
                        self._cursor = 0
                elif key in ("dollar", "dollar_sign"):
                    self._cmd_delete_to_line_end()
                elif key == "0":
                    self._text = self._text[self._cursor :]
                    self._cursor = 0
                elif key == "w":
                    self._cmd_delete_word(word_only=False)
                elif key == "W":
                    self._cmd_delete_word(word_only=True)
                elif key == "b":
                    self._cmd_delete_to_word_backward(word=True)
                elif key == "B":
                    self._cmd_delete_to_word_backward(word=False)
            # Unknown sequence — silently discard; do not consume the event.
            return

        if key in ("escape", "tab", "shift+tab"):
            # Do NOT stop these events: let them bubble so Esc reaches the parent
            # and Tab/Shift-Tab reach Textual's focus-traversal handler.
            return

        if key in ("j", "k") and not self._multiline:
            # In single-line command mode, let j/k bubble for field navigation.
            return

        if key == "j" and self._multiline:
            row, _ = self._cursor_row_col()
            if row + 1 >= len(self._text.split("\n")):
                return  # at last line — bubble to parent for field navigation

        if key == "k" and self._multiline:
            row, _ = self._cursor_row_col()
            if row == 0:
                return  # at first line — bubble to parent for field navigation

        # Every other command-mode key is consumed here.
        event.stop()
        event.prevent_default()

        if key == "i":
            self._push_undo()
            self.set_mode("insert")
        elif key == "a":
            self._push_undo()
            if self._cursor < len(self._text):
                self._cursor += 1
            self.set_mode("insert")
        elif key == "A":
            self._push_undo()
            if self._multiline:
                row, _ = self._cursor_row_col()
                line = self._text.split("\n")[row]
                self._cursor = self._offset_from_row_col(row, len(line))
            else:
                self._cursor = len(self._text)
            self.set_mode("insert")
        elif key == "o":
            self._push_undo()
            if self._multiline:
                self._cmd_open_line_below()
            else:
                self._cursor = len(self._text)
                self.set_mode("insert")
        elif key == "O":
            self._push_undo()
            if self._multiline:
                self._cmd_open_line_above()
            else:
                self._cursor = 0
                self.set_mode("insert")
        elif key == "u":
            self._cmd_undo()
        elif key == "ctrl+r":
            self._cmd_redo()
        elif key in ("h", "left"):
            if self._multiline:
                row, col = self._cursor_row_col()
                if col > 0:
                    self._cursor -= 1
            else:
                self._cursor = max(0, self._cursor - 1)
        elif key in ("l", "right"):
            if self._multiline:
                row, col = self._cursor_row_col()
                line = self._text.split("\n")[row]
                if line and col < len(line) - 1:
                    self._cursor += 1
            else:
                if self._text:
                    self._cursor = min(len(self._text) - 1, self._cursor + 1)
        elif key == "j" and self._multiline:
            self._cmd_line_down()
        elif key == "k" and self._multiline:
            self._cmd_line_up()
        elif key == "e":
            self._cmd_word_end_forward()
        elif key == "w":
            self._cmd_word_forward(word=True)
        elif key == "W":
            self._cmd_word_forward(word=False)
        elif key == "b":
            self._cmd_word_backward(word=True)
        elif key == "B":
            self._cmd_word_backward(word=False)
        elif key == "0":
            if self._multiline:
                row, _ = self._cursor_row_col()
                self._cursor = self._offset_from_row_col(row, 0)
            else:
                self._cursor = 0
        elif key in ("dollar", "dollar_sign"):
            if self._multiline:
                row, _ = self._cursor_row_col()
                line = self._text.split("\n")[row]
                new_col = max(0, len(line) - 1) if line else 0
                self._cursor = self._offset_from_row_col(row, new_col)
            elif self._text:
                self._cursor = len(self._text) - 1
        elif key == "tilde":
            self._push_undo()
            self._cmd_toggle_case()
        elif key == "r":
            self._pending = "r"
        elif key == "s":
            self._push_undo()
            self._cmd_substitute()
        elif key == "left_parenthesis":
            self._cmd_sentence_backward()
        elif key == "right_parenthesis":
            self._cmd_sentence_forward()
        elif key == "x":
            if self._cursor < len(self._text) and self._text[self._cursor] != "\n":
                self._push_undo()
                self._text = self._text[: self._cursor] + self._text[self._cursor + 1 :]
                if self._multiline:
                    row, col = self._cursor_row_col()
                    line = self._text.split("\n")[row]
                    if line and col >= len(line):
                        self._cursor -= 1
                else:
                    self._cursor = min(self._cursor, max(0, len(self._text) - 1))
        elif key == "c":
            self._pending = "c"
        elif key == "d":
            self._pending = "d"
        elif key == "D":
            self._push_undo()
            if self._multiline:
                row, col = self._cursor_row_col()
                line_start = self._offset_from_row_col(row, 0)
                line = self._text.split("\n")[row]
                self._text = (
                    self._text[: self._cursor] + self._text[line_start + len(line) :]
                )
                self._clamp_cursor_for_command()
            else:
                self._text = self._text[: self._cursor]
                self._cursor = max(0, len(self._text) - 1)
        elif key == "enter" and not self._multiline:
            self.post_message(self.Submitted(self, self._text))

    # ------------------------------------------------------------------
    # Line motion helpers (multi-line)
    # ------------------------------------------------------------------

    def _cmd_line_down(self) -> None:
        row, col = self._cursor_row_col()
        lines = self._text.split("\n")
        if row + 1 >= len(lines):
            return
        next_line = lines[row + 1]
        new_col = min(col, len(next_line))
        if self._vim_mode == "command" and next_line:
            new_col = min(new_col, len(next_line) - 1)
        self._cursor = self._offset_from_row_col(row + 1, new_col)

    def _cmd_line_up(self) -> None:
        row, col = self._cursor_row_col()
        if row == 0:
            return
        lines = self._text.split("\n")
        prev_line = lines[row - 1]
        new_col = min(col, len(prev_line))
        if self._vim_mode == "command" and prev_line:
            new_col = min(new_col, len(prev_line) - 1)
        self._cursor = self._offset_from_row_col(row - 1, new_col)

    def _cmd_delete_line(self) -> None:
        """dd in multi-line: delete the current line."""
        row, _ = self._cursor_row_col()
        lines = self._text.split("\n")
        lines.pop(row)
        self._text = "\n".join(lines)
        # Move cursor to start of same row (now the next line).
        new_row = min(row, len(lines) - 1) if lines else 0
        self._cursor = self._offset_from_row_col(new_row, 0) if lines else 0
        self._clamp_cursor_for_command()

    def _cmd_open_line_below(self) -> None:
        """o in multi-line: insert a new line after the current line, enter INSERT."""
        row, _ = self._cursor_row_col()
        lines = self._text.split("\n")
        line_end = self._offset_from_row_col(row, len(lines[row]))
        self._text = self._text[:line_end] + "\n" + self._text[line_end:]
        self._cursor = line_end + 1
        self.set_mode("insert")

    def _cmd_open_line_above(self) -> None:
        """O in multi-line: insert a new line before the current line, enter INSERT."""
        row, _ = self._cursor_row_col()
        line_start = self._offset_from_row_col(row, 0)
        self._text = self._text[:line_start] + "\n" + self._text[line_start:]
        self._cursor = line_start
        self.set_mode("insert")

    # ------------------------------------------------------------------
    # Word motion helpers
    # ------------------------------------------------------------------

    def _word_boundary(self, ch: str, word: bool) -> bool:
        """Return True if ch is a word-boundary character.

        word=True uses vim 'w' semantics (whitespace or punctuation boundary).
        word=False uses vim 'W' semantics (whitespace-only boundary).
        """
        if word:
            return ch.isspace()
        return ch.isspace()  # W/B: whitespace-delimited (same as w/b for our model)

    def _cmd_word_forward(self, word: bool = True) -> None:
        """Move cursor to start of next word (word=True) or WORD (word=False)."""
        pos = self._cursor
        text = self._text
        # Skip current non-space run.
        while pos < len(text) and not text[pos].isspace():
            pos += 1
        # Skip whitespace (but not newlines in multi-line — stop at newline).
        while (
            pos < len(text)
            and text[pos].isspace()
            and (not self._multiline or text[pos] != "\n")
        ):
            pos += 1
        if self._multiline:
            # Clamp to end of current line.
            row, _ = self._cursor_row_col()
            line = text.split("\n")[row]
            line_end = self._offset_from_row_col(row, len(line))
            pos = min(pos, line_end)
        self._cursor = min(pos, max(0, len(text) - 1))

    def _cmd_word_backward(self, word: bool = True) -> None:
        """Move cursor to start of previous word (word=True) or WORD (word=False)."""
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

    def _cmd_delete_word(self, word_only: bool = False) -> None:
        """dw / dW: delete from cursor to start of next word."""
        pos = self._cursor
        text = self._text
        end = pos
        while end < len(text) and not text[end].isspace():
            end += 1
        # Also consume trailing whitespace (standard vim dw behaviour).
        while end < len(text) and text[end] == " ":
            end += 1
        self._text = text[:pos] + text[end:]
        if self._multiline:
            self._clamp_cursor_for_command()
        else:
            self._cursor = min(self._cursor, max(0, len(self._text) - 1))

    def _cmd_undo(self) -> None:
        """u: restore previous (text, cursor) from undo stack."""
        if not self._undo_stack:
            return
        self._redo_stack.append((self._text, self._cursor))
        self._text, self._cursor = self._undo_stack.pop()
        self._clamp_cursor_for_command()

    def _cmd_redo(self) -> None:
        """Ctrl+R: reapply the most recently undone change."""
        if not self._redo_stack:
            return
        self._undo_stack.append((self._text, self._cursor))
        self._text, self._cursor = self._redo_stack.pop()
        self._clamp_cursor_for_command()

    def _cmd_delete_to_line_end(self) -> None:
        """d$: delete from cursor to end of current line (multiline-aware)."""
        if self._multiline:
            row, _ = self._cursor_row_col()
            lines = self._text.split("\n")
            line_end = self._offset_from_row_col(row, len(lines[row]))
            self._text = self._text[: self._cursor] + self._text[line_end:]
        else:
            self._text = self._text[: self._cursor]
        self._cursor = (
            max(0, min(self._cursor, len(self._text) - 1)) if self._text else 0
        )
        self._clamp_cursor_for_command()

    def _cmd_change_to_line_end(self) -> None:
        """c$: delete from cursor to end of current line, enter INSERT mode."""
        self._cmd_delete_to_line_end()
        self.set_mode("insert")

    def _cmd_word_end_forward(self) -> None:
        """e: move to end of current or next word."""
        text = self._text
        n = len(text)
        pos = self._cursor
        if pos >= n - 1:
            return
        pos += 1
        while pos < n and text[pos].isspace():
            pos += 1
        while pos + 1 < n and not text[pos + 1].isspace():
            pos += 1
        self._cursor = min(pos, n - 1)
        self._clamp_cursor_for_command()

    def _cmd_delete_to_word_backward(self, word: bool = True) -> None:
        """db / dB: delete from cursor back to start of previous word."""
        end = self._cursor
        self._cmd_word_backward(word=word)
        start = self._cursor
        if start == end:
            return
        self._text = self._text[:start] + self._text[end:]
        self._clamp_cursor_for_command()

    def _cmd_toggle_case(self) -> None:
        """~: toggle case of char under cursor and advance one position."""
        text = self._text
        if not text or self._cursor >= len(text):
            return
        ch = text[self._cursor]
        toggled = ch.upper() if ch.islower() else ch.lower()
        self._text = text[: self._cursor] + toggled + text[self._cursor + 1 :]
        self._cursor = min(self._cursor + 1, max(0, len(self._text) - 1))
        self._clamp_cursor_for_command()

    def _cmd_substitute(self) -> None:
        """s: delete char under cursor and enter INSERT mode (like xi)."""
        if self._cursor < len(self._text):
            self._text = self._text[: self._cursor] + self._text[self._cursor + 1 :]
        self._clamp_cursor_for_command()
        self.set_mode("insert")

    def _cmd_sentence_forward(self) -> None:
        """): move to start of next sentence."""
        text = self._text
        n = len(text)
        pos = self._cursor + 1
        while pos < n:
            if text[pos - 1] in ".!?" and text[pos].isspace():
                while pos < n and text[pos].isspace():
                    pos += 1
                self._cursor = min(pos, max(0, n - 1))
                self._clamp_cursor_for_command()
                return
            pos += 1
        self._cursor = max(0, n - 1)
        self._clamp_cursor_for_command()

    def _cmd_sentence_backward(self) -> None:
        """(: move to start of previous sentence."""
        text = self._text
        n = len(text)
        pos = self._cursor - 1
        if pos <= 0:
            self._cursor = 0
            return
        # Skip whitespace immediately before cursor (may be in inter-sentence gap).
        while pos > 0 and text[pos].isspace():
            pos -= 1
        # Scan backward for a sentence terminator that lands us before cursor.
        while pos > 0:
            if text[pos] in ".!?" and pos + 1 < n and text[pos + 1].isspace():
                skip = pos + 1
                while skip < n and text[skip].isspace():
                    skip += 1
                if skip < self._cursor:  # only jump if we'd actually move backward
                    self._cursor = skip
                    self._clamp_cursor_for_command()
                    return
            pos -= 1
        self._cursor = 0
        self._clamp_cursor_for_command()
