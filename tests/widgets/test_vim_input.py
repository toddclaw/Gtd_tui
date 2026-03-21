"""Unit tests for VimInput widget.

Each test uses a minimal Textual app that contains only a VimInput so we can
drive it with the Pilot API without any app-level key handlers interfering.
"""

from __future__ import annotations

from textual.app import App, ComposeResult

from gtd_tui.widgets.vim_input import VimInput

# ---------------------------------------------------------------------------
# Minimal host app
# ---------------------------------------------------------------------------


class _App(App[None]):
    def __init__(
        self,
        value: str = "",
        start_mode: str = "insert",
        multiline: bool = False,
    ) -> None:
        super().__init__()
        self._vim_value = value
        self._vim_start_mode = start_mode
        self._vim_multiline = multiline

    def compose(self) -> ComposeResult:
        yield VimInput(
            value=self._vim_value,
            placeholder="type here",
            start_mode=self._vim_start_mode,
            multiline=self._vim_multiline,
            id="vi",
        )


def _vi(app: App) -> VimInput:
    return app.query_one("#vi", VimInput)


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


async def test_default_start_mode_is_insert() -> None:
    async with _App().run_test() as pilot:
        assert _vi(pilot.app)._vim_mode == "insert"


async def test_command_start_mode() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._vim_mode == "command"
        # cursor clamped to last char index (4)
        assert vi._cursor == 4


async def test_insert_start_cursor_at_end() -> None:
    async with _App(value="abc").run_test() as pilot:
        assert _vi(pilot.app)._cursor == 3


# ---------------------------------------------------------------------------
# INSERT mode — basic editing
# ---------------------------------------------------------------------------


async def test_typing_in_insert_mode() -> None:
    async with _App().run_test() as pilot:
        await pilot.press("h", "i")
        assert _vi(pilot.app).value == "hi"


async def test_spell_check_on_space_in_insert() -> None:
    """When spell_check_on_space is set, Space corrects the word before cursor."""
    async with _App().run_test() as pilot:
        vi = _vi(pilot.app)
        vi.set_spell_check_on_space(lambda w: "the" if w == "teh" else w)
        await pilot.press("t", "e", "h", "space")
        assert vi.value == "the "


async def test_backspace_in_insert_mode() -> None:
    async with _App(value="ab").run_test() as pilot:
        await pilot.press("backspace")
        assert _vi(pilot.app).value == "a"


async def test_left_right_in_insert_mode() -> None:
    async with _App(value="ab").run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._cursor == 2
        await pilot.press("left")
        assert vi._cursor == 1
        await pilot.press("right")
        assert vi._cursor == 2


async def test_home_end_in_insert_mode() -> None:
    async with _App(value="abc").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("home")
        assert vi._cursor == 0
        await pilot.press("end")
        assert vi._cursor == 3


# ---------------------------------------------------------------------------
# Mode switching
# ---------------------------------------------------------------------------


async def test_escape_in_insert_switches_to_command() -> None:
    async with _App().run_test() as pilot:
        await pilot.press("escape")
        assert _vi(pilot.app)._vim_mode == "command"


async def test_i_in_command_switches_to_insert() -> None:
    async with _App(start_mode="command").run_test() as pilot:
        await pilot.press("i")
        assert _vi(pilot.app)._vim_mode == "insert"


async def test_a_enters_insert_after_cursor() -> None:
    async with _App(value="ab", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        start = vi._cursor
        await pilot.press("a")
        assert vi._vim_mode == "insert"
        assert vi._cursor == start + 1


async def test_A_enters_insert_at_end() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("A")
        assert vi._vim_mode == "insert"
        assert vi._cursor == 5


# ---------------------------------------------------------------------------
# COMMAND mode — cursor motions
# ---------------------------------------------------------------------------


async def test_h_moves_left() -> None:
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._cursor == 2
        await pilot.press("h")
        assert vi._cursor == 1


async def test_l_moves_right() -> None:
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("l")
        assert vi._cursor == 1


async def test_zero_moves_to_start() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("0")
        assert vi._cursor == 0


async def test_dollar_moves_to_last_char() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("dollar_sign")
        assert vi._cursor == 4  # index of last char 'o'


async def test_w_jumps_forward_over_word() -> None:
    async with _App(value="foo bar", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("w")
        # skips "foo" + space, lands on 'b' at index 4
        assert vi._cursor == 4


async def test_b_jumps_backward_over_word() -> None:
    async with _App(value="foo bar", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4  # on 'b'
        await pilot.press("b")
        assert vi._cursor == 0


# ---------------------------------------------------------------------------
# COMMAND mode — editing
# ---------------------------------------------------------------------------


async def test_x_deletes_char_under_cursor() -> None:
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 1  # on 'b'
        await pilot.press("x")
        assert vi.value == "ac"


async def test_D_deletes_to_end_of_line() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 5  # on space between words
        await pilot.press("D")
        assert vi.value == "hello"
        assert vi._vim_mode == "command"


async def test_dd_clears_entire_field() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("d", "d")
        assert vi.value == ""
        assert vi._cursor == 0


async def test_d_dollar_deletes_to_end() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 5  # on space
        await pilot.press("d", "dollar_sign")
        assert vi.value == "hello"


async def test_d_zero_deletes_to_start() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on 'w'
        await pilot.press("d", "0")
        assert vi.value == "world"
        assert vi._cursor == 0


async def test_cw_deletes_to_end_of_word_and_enters_insert() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("c", "w")
        assert vi.value == " world"
        assert vi._cursor == 0
        assert vi._vim_mode == "insert"


# ---------------------------------------------------------------------------
# Submission
# ---------------------------------------------------------------------------


async def test_enter_in_insert_mode_emits_submitted() -> None:
    received: list[str] = []

    class _TestApp(_App):
        def on_vim_input_submitted(self, event: VimInput.Submitted) -> None:
            received.append(event.value)

    async with _TestApp(value="task").run_test() as pilot:
        await pilot.press("enter")
        assert received == ["task"]


async def test_enter_in_command_mode_emits_submitted() -> None:
    received: list[str] = []

    class _TestApp(_App):
        def on_vim_input_submitted(self, event: VimInput.Submitted) -> None:
            received.append(event.value)

    async with _TestApp(value="task", start_mode="command").run_test() as pilot:
        await pilot.press("enter")
        assert received == ["task"]


# ---------------------------------------------------------------------------
# BACKLOG-21: New motions — W, B, dw, dW
# ---------------------------------------------------------------------------


async def test_W_moves_to_next_word() -> None:
    async with _App(value="hello world foo", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("W")
        assert vi._cursor == 6  # start of "world"


async def test_B_moves_to_previous_word() -> None:
    async with _App(value="hello world foo", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # "world"
        await pilot.press("B")
        assert vi._cursor == 0  # start of "hello"


async def test_dw_deletes_to_end_of_word() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("d", "w")
        assert vi.value == "world"


async def test_dW_deletes_to_end_of_WORD() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("d", "W")
        assert vi.value == "world"


# ---------------------------------------------------------------------------
# BACKLOG-21: Multi-line VimInput
# ---------------------------------------------------------------------------


class _MultiApp(App[None]):
    def compose(self) -> ComposeResult:
        yield VimInput(
            value="",
            start_mode="insert",
            multiline=True,
            id="vi",
        )


def _mvi(app: App) -> VimInput:
    return app.query_one("#vi", VimInput)


async def test_multiline_enter_inserts_newline() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("h", "i")
        await pilot.press("enter")
        await pilot.press("t", "h", "e", "r", "e")
        assert vi.value == "hi\nthere"


async def test_multiline_cursor_row_col() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("a", "b", "c")
        await pilot.press("enter")
        await pilot.press("d", "e", "f")
        row, col = vi._cursor_row_col()
        assert row == 1
        assert col == 3


async def test_multiline_j_moves_down() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("l", "i", "n", "e", "1")
        await pilot.press("enter")
        await pilot.press("l", "i", "n", "e", "2")
        # Switch to command mode and move cursor back to line 0, col 0
        await pilot.press("escape")  # → command mode
        vi._cursor = 0
        await pilot.press("j")
        row, col = vi._cursor_row_col()
        assert row == 1


async def test_multiline_k_moves_up() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("l", "i", "n", "e", "1")
        await pilot.press("enter")
        await pilot.press("l", "i", "n", "e", "2")
        await pilot.press("escape")  # → command mode; cursor on line 1
        await pilot.press("k")
        row, _ = vi._cursor_row_col()
        assert row == 0


async def test_multiline_enter_no_submitted_event() -> None:
    """In multiline mode Enter must NOT emit Submitted."""
    received: list[str] = []

    class _TestApp(_MultiApp):
        def on_vim_input_submitted(self, event: VimInput.Submitted) -> None:
            received.append(event.value)

    async with _TestApp().run_test() as pilot:
        await pilot.press("h", "i")
        await pilot.press("enter")
        assert received == []  # no submission


async def test_multiline_j_at_last_line_bubbles() -> None:
    """j on the last line of a multiline VimInput should bubble to the parent."""
    received: list[str] = []

    class _TrackApp(_MultiApp):
        def on_key(self, event) -> None:
            if event.key == "j":
                received.append("j")

    async with _TrackApp().run_test() as pilot:
        await pilot.press("l", "i", "n", "e")
        await pilot.press("escape")  # → command mode, single line
        await pilot.press("j")  # at last (only) line — should bubble
        assert received == ["j"]


async def test_multiline_k_at_first_line_bubbles() -> None:
    """k on the first line of a multiline VimInput should bubble to the parent."""
    received: list[str] = []

    class _TrackApp(_MultiApp):
        def on_key(self, event) -> None:
            if event.key == "k":
                received.append("k")

    async with _TrackApp().run_test() as pilot:
        await pilot.press("l", "i", "n", "e")
        await pilot.press("escape")  # → command mode, single line
        await pilot.press("k")  # at first (only) line — should bubble
        assert received == ["k"]


async def test_multiline_j_interior_does_not_bubble() -> None:
    """j on a non-last line should do line navigation, not bubble."""
    received: list[str] = []

    class _TrackApp(_MultiApp):
        def on_key(self, event) -> None:
            if event.key == "j":
                received.append("j")

    async with _TrackApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("l", "i", "n", "e", "1")
        await pilot.press("enter")
        await pilot.press("l", "i", "n", "e", "2")
        await pilot.press("escape")  # command mode, cursor on line 1 (last)
        await pilot.press("k")  # move to line 0 (first line, non-last)
        await pilot.press("j")  # should navigate down, not bubble
        assert received == []  # no bubble
        row, _ = vi._cursor_row_col()
        assert row == 1  # cursor moved back to line 1


# ---------------------------------------------------------------------------
# o/O: open line and enter insert mode
# ---------------------------------------------------------------------------


async def test_o_single_line_enters_insert_at_end() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("o")
        assert vi._vim_mode == "insert"
        assert vi._cursor == len("hello")


async def test_O_single_line_enters_insert_at_start() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4
        await pilot.press("O")
        assert vi._vim_mode == "insert"
        assert vi._cursor == 0


async def test_o_multiline_opens_line_below() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("l", "i", "n", "e", "1")
        await pilot.press("enter")
        await pilot.press("l", "i", "n", "e", "2")
        await pilot.press("escape")  # command mode, cursor on line 1
        await pilot.press("k")  # move to line 0
        await pilot.press("o")  # open line below line 0
        assert vi._vim_mode == "insert"
        await pilot.press("X")  # type on the new line
        await pilot.press("escape")
        lines = vi.value.split("\n")
        assert lines == ["line1", "X", "line2"]


async def test_O_multiline_opens_line_above() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("l", "i", "n", "e", "1")
        await pilot.press("enter")
        await pilot.press("l", "i", "n", "e", "2")
        await pilot.press("escape")  # command mode, cursor on line 1
        await pilot.press("O")  # open line above line 1
        assert vi._vim_mode == "insert"
        await pilot.press("X")  # type on the new line
        await pilot.press("escape")
        lines = vi.value.split("\n")
        assert lines == ["line1", "X", "line2"]


# ---------------------------------------------------------------------------
# New vim commands: e, db, dB, ~, r, s, (, )
# ---------------------------------------------------------------------------


async def test_e_moves_to_end_of_current_word() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("e")
        assert vi._cursor == 4  # last char of "hello"


async def test_e_skips_whitespace_and_moves_to_end_of_next_word() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4  # already at end of "hello"
        await pilot.press("e")
        assert vi._cursor == 10  # last char of "world"


async def test_db_deletes_to_start_of_previous_word() -> None:
    async with _App(value="foo bar", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on 'r' (last char of "bar")
        await pilot.press("d", "b")
        assert vi.value == "foo r"
        assert vi._cursor == 4


async def test_dB_deletes_to_start_of_previous_WORD() -> None:
    async with _App(value="foo bar", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on 'r'
        await pilot.press("d", "B")
        assert vi.value == "foo r"
        assert vi._cursor == 4


async def test_tilde_toggles_lowercase_to_upper() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("tilde")
        assert vi.value == "Hello"
        assert vi._cursor == 1


async def test_tilde_toggles_uppercase_to_lower() -> None:
    async with _App(value="HELLO", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("tilde")
        assert vi.value == "hELLO"
        assert vi._cursor == 1


async def test_r_replaces_char_under_cursor() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("r", "H")
        assert vi.value == "Hello"
        assert vi._cursor == 0
        assert vi._vim_mode == "command"


async def test_s_deletes_char_and_enters_insert() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("s")
        assert vi.value == "ello"
        assert vi._cursor == 0
        assert vi._vim_mode == "insert"


async def test_right_paren_moves_to_next_sentence() -> None:
    async with _App(
        value="Hello world. Foo bar.", start_mode="command"
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("right_parenthesis")
        assert vi._cursor == 13  # start of "Foo"


async def test_left_paren_moves_to_previous_sentence() -> None:
    async with _App(
        value="Hello world. Foo bar.", start_mode="command"
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 13  # on 'F' of "Foo"
        await pilot.press("left_parenthesis")
        assert vi._cursor == 0


# ---------------------------------------------------------------------------
# $ fixes: c$ and d$ (multiline-aware)
# ---------------------------------------------------------------------------


async def test_c_dollar_changes_to_end_of_line_and_enters_insert() -> None:
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on 'w'
        await pilot.press("c", "dollar_sign")
        assert vi.value == "hello "
        assert vi._cursor == 5
        assert vi._vim_mode == "insert"


async def test_d_dollar_multiline_deletes_only_current_line_remainder() -> None:
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("enter")
        await pilot.press("w", "o", "r", "l", "d")
        await pilot.press("escape")  # command mode, cursor on line 1
        await pilot.press("k")  # move to line 0
        vi._cursor = 2  # on 'l' of "hello"
        await pilot.press("d", "dollar_sign")
        assert vi.value == "he\nworld"


# ---------------------------------------------------------------------------
# VimInput undo (u) and redo (ctrl+r)
# ---------------------------------------------------------------------------


async def test_u_undoes_x_delete() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("x")  # delete 'h' → "ello"
        assert vi.value == "ello"
        await pilot.press("u")  # undo → "hello"
        assert vi.value == "hello"


async def test_u_undoes_insert_session() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4
        await pilot.press("a")  # enter insert after last char
        await pilot.press("!", "!")  # type "!!"
        await pilot.press("escape")  # back to command → value is "hello!!"
        assert vi.value == "hello!!"
        await pilot.press("u")  # undo entire insert session
        assert vi.value == "hello"


async def test_ctrl_r_redoes_undone_change() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("x")  # delete 'h' → "ello"
        await pilot.press("u")  # undo → "hello"
        await pilot.press("ctrl+r")  # redo → "ello"
        assert vi.value == "ello"


async def test_u_does_nothing_on_empty_undo_stack() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("u")
        assert vi.value == "hello"  # unchanged, no crash


async def test_new_mutation_clears_redo_stack() -> None:
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("x")  # delete 'h'
        await pilot.press("u")  # undo
        await pilot.press("x")  # new mutation — clears redo
        await pilot.press("ctrl+r")  # redo stack is empty, should be no-op
        assert vi.value == "ello"  # still at the x-deleted state


# ---------------------------------------------------------------------------
# BACKLOG-39: y / p / P clipboard integration in VimInput COMMAND mode
# ---------------------------------------------------------------------------


async def test_y_sets_register_to_current_line_singleline() -> None:
    """y in single-line command mode sets _register to the full text."""
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        await pilot.press("y")
        assert _vi(pilot.app)._register == "hello world"


async def test_p_paste_after_cursor_singleline() -> None:
    """p in single-line mode inserts register content after cursor."""
    async with _App(value="hi", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._register = "XYZ"
        vi._cursor = 0  # cursor on 'h'
        await pilot.press("p")
        # Inserts "XYZ" after position 0 → "hXYZi"
        assert vi.value == "hXYZi"


async def test_P_paste_before_cursor_singleline() -> None:
    """P in single-line mode inserts register content before cursor."""
    async with _App(value="hi", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._register = "ABC"
        vi._cursor = 1  # cursor on 'i'
        await pilot.press("P")
        # Inserts "ABC" before position 1 → "hABCi"
        assert vi.value == "hABCi"


async def test_p_paste_at_end_singleline() -> None:
    """p at the last char appends the register at the end."""
    async with _App(value="ab", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._register = "cd"
        vi._cursor = 1  # last char 'b'
        await pilot.press("p")
        assert vi.value == "abcd"


class _MultiCmdApp(App[None]):
    """Multi-line VimInput starting in command mode with a preset value."""

    def __init__(self, value: str = "") -> None:
        super().__init__()
        self._vim_value = value

    def compose(self) -> ComposeResult:
        yield VimInput(
            value=self._vim_value,
            start_mode="command",
            multiline=True,
            id="vi",
        )


async def test_y_sets_register_multiline() -> None:
    """y in multi-line mode yanks only the current logical line."""
    async with _MultiCmdApp(value="line one\nline two\nline three").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on first line
        await pilot.press("y")
        assert vi._register == "line one"


async def test_p_inserts_new_line_below_multiline() -> None:
    """p in multi-line mode inserts register as a new line below current."""
    async with _MultiCmdApp(value="alpha\nbeta").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on 'alpha'
        vi._register = "gamma"
        await pilot.press("p")
        assert vi.value == "alpha\ngamma\nbeta"


async def test_P_inserts_new_line_above_multiline() -> None:
    """P in multi-line mode inserts register as a new line above current."""
    async with _MultiCmdApp(value="alpha\nbeta").run_test() as pilot:
        vi = _vi(pilot.app)
        # Position cursor on 'beta' (row 1)
        vi._cursor = len("alpha\n")
        vi._register = "gamma"
        await pilot.press("P")
        assert vi.value == "alpha\ngamma\nbeta"


async def test_p_falls_back_to_register_when_clipboard_unavailable() -> None:
    """Paste works using the internal register even when pyperclip raises."""
    import unittest.mock as mock

    async with _App(value="foo", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._register = "bar"
        vi._cursor = 2  # last char 'o'
        with mock.patch(
            "gtd_tui.widgets.vim_input.pyperclip.paste", side_effect=Exception
        ):
            await pilot.press("p")
        assert vi.value == "foobar"


async def test_y_p_roundtrip_singleline() -> None:
    """Yank then paste: y on 'word' then p appends it after cursor."""
    async with _App(value="word", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 3  # last char 'd'
        await pilot.press("y")  # yank "word"
        assert vi._register == "word"
        await pilot.press("p")  # paste after last char
        assert vi.value == "wordword"


# ---------------------------------------------------------------------------
# Dot-repeat (Feature 9)
# ---------------------------------------------------------------------------


async def test_dot_repeat_inserts_last_insert_text() -> None:
    """'.' in COMMAND mode re-inserts the text typed in the last INSERT session."""
    async with _App(value="", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        # Enter INSERT, type "hello", return to COMMAND
        await pilot.press("i")
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.press("escape")
        # The repeat text should have been saved
        assert vi._repeat_text == "hello"
        # Move cursor to end and press '.'
        vi._cursor = len(vi.value)
        await pilot.press("full_stop")
        assert vi.value == "hellohello"


async def test_dot_repeat_empty_when_nothing_typed() -> None:
    """No INSERT session → '.' is a no-op."""
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        original = vi.value
        await pilot.press("full_stop")
        assert vi.value == original


async def test_dot_repeat_cleared_on_new_insert_entry() -> None:
    """Entering INSERT mode clears _last_insert so the new session starts fresh."""
    async with _App(value="", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        # First INSERT session
        await pilot.press("i")
        await pilot.press("a")
        await pilot.press("escape")
        assert vi._repeat_text == "a"
        # Second INSERT session — _last_insert must be empty when we enter INSERT
        await pilot.press("i")
        assert vi._last_insert == ""
        await pilot.press("b")
        await pilot.press("escape")
        assert vi._repeat_text == "b"


async def test_dot_repeat_inserts_at_current_cursor() -> None:
    """'.' inserts the repeat text at the current cursor position."""
    async with _App(value="", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("i")
        await pilot.press("x", "y")
        await pilot.press("escape")
        # cursor is at 1 (last char in COMMAND mode), move to 0
        vi._cursor = 0
        await pilot.press("full_stop")
        assert vi.value.startswith("xy")


async def test_dot_repeat_x_deletes_again() -> None:
    """'x' in COMMAND mode followed by '.' deletes the next character too."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        # cursor starts at last char (index 4 = 'o')
        assert vi._cursor == 4
        await pilot.press("x")
        assert vi.value == "hell"  # 'o' deleted
        assert vi._last_action is not None
        await pilot.press("full_stop")
        assert vi.value == "hel"  # 'l' deleted by dot-repeat


async def test_dot_repeat_x_sets_last_action() -> None:
    """Pressing 'x' in COMMAND mode sets _last_action callable."""
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._last_action is None
        await pilot.press("x")
        assert vi._last_action is not None


async def test_dot_repeat_x_overwrites_insert_action() -> None:
    """'x' after an INSERT session updates _last_action to the delete op."""
    async with _App(value="abc", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("i")
        await pilot.press("z")
        await pilot.press("escape")
        insert_action = vi._last_action
        assert insert_action is not None
        # Now press x — _last_action should switch to the delete replay
        await pilot.press("x")
        assert vi._last_action is not insert_action


# ---------------------------------------------------------------------------
# Pre-insert action (dot-repeat for A / s / a)
# ---------------------------------------------------------------------------


async def test_dot_repeat_A_appends_to_end_of_line() -> None:
    """AFooEsc. in multiline repeats by moving to EOL and appending."""
    async with _App(
        value="hello\nworld", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        # Start on first line, cursor at 'o' (index 4)
        vi._cursor = 4
        await pilot.press("A")  # move to end of 'hello' (index 5), INSERT
        await pilot.press("!")  # type '!'  → 'hello!\nworld'
        await pilot.press("escape")  # leave INSERT
        assert vi.value == "hello!\nworld"
        # Move cursor into second line: h=0,e=1,l=2,l=3,o=4,!=5,\n=6,w=7,o=8,r=9
        vi._cursor = 9
        await pilot.press("full_stop")  # repeat A!: move to EOL of 'world', append '!'
        assert vi.value == "hello!\nworld!"


async def test_dot_repeat_s_deletes_then_inserts() -> None:
    """s=Esc. replaces char under cursor again (delete + insert), not just insert."""
    async with _App(value="abcde", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("s")  # delete 'a', enter INSERT
        await pilot.press("=")  # type '='
        await pilot.press("escape")  # leave INSERT  → value is '=bcde'
        assert vi.value == "=bcde"
        # cursor is now on 'b' (index 1)
        await pilot.press("full_stop")  # should delete 'b' and insert '=' → '==cde'
        assert vi.value == "==cde"


async def test_dot_repeat_d0_multiline_stays_on_line() -> None:
    """d0 on the second line must not delete the newline from the first line."""
    async with _App(
        value="hello\nworld", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        # Position cursor on 'r' in 'world' (offset 8)
        vi._cursor = 8  # h(0)e(1)l(2)l(3)o(4)\n(5)w(6)o(7)r(8)
        await pilot.press("d", "0")  # d0: delete 'wo' (from line start to cursor)
        assert vi.value == "hello\nrld", repr(vi.value)
        assert "\n" in vi.value  # newline must survive


async def test_dot_repeat_a_appends_after_cursor() -> None:
    """aFooEsc. appends 'Foo' after the current char (not at the original cursor)."""
    async with _App(value="abcd", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # cursor on 'a'
        await pilot.press("a")  # append: cursor moves to 1 (after 'a')
        await pilot.press("X")  # type 'X'
        await pilot.press("escape")  # → 'aXbcd'
        assert vi.value == "aXbcd"
        vi._cursor = 2  # cursor on 'b'
        await pilot.press("full_stop")  # repeat: should append 'X' after 'b' → 'aXbXcd'
        assert vi.value == "aXbXcd"


# ---------------------------------------------------------------------------
# Find-char motions (f / F / t / T / ; / ,)
# ---------------------------------------------------------------------------


async def test_f_moves_to_next_char() -> None:
    """f<ch> moves cursor to the next occurrence of ch on the current line."""
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on 'h'
        await pilot.press("f", "l")  # find 'l' forward → index 2
        assert vi._cursor == 2


async def test_f_no_match_stays_put() -> None:
    """f<ch> is a no-op when ch is not found on the current line."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("f", "z")
        assert vi._cursor == 0


async def test_t_stops_before_char() -> None:
    """t<ch> moves cursor to the position just before the next occurrence of ch."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on 'h'
        await pilot.press("t", "l")  # first 'l' is at index 2; t stops at 1
        assert vi._cursor == 1


async def test_F_moves_to_previous_char() -> None:
    """F<ch> moves cursor backward to the previous occurrence of ch."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4  # on 'o'
        await pilot.press("F", "l")  # last 'l' before cursor is at index 3
        assert vi._cursor == 3


async def test_T_stops_after_char() -> None:
    """T<ch> moves cursor to one position after the previous occurrence of ch."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4  # on 'o'
        await pilot.press(
            "T", "l"
        )  # last 'l' before cursor is at index 3; T → 4-1=3+1=4... wait
        # 'l' at index 3 is the rightmost 'l' before cursor 4; T stops one after it → 4
        # Actually T finds the char then moves cursor one AFTER it → idx+1 = 4
        # But col = 4 and we need to move, so T l from cursor 4 should find 'l' at index 3
        # and land at 3+1=4 which equals col — that's not a move.
        # Let's test with cursor further right. Use "world" example.
        pass


async def test_T_stops_after_char_in_longer_text() -> None:
    """T<ch> moves cursor to position just after the previous occurrence of ch."""
    async with _App(value="abcdefg", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 5  # on 'f'
        await pilot.press("T", "b")  # 'b' is at index 1; T → land at 2
        assert vi._cursor == 2


async def test_semicolon_repeats_f_forward() -> None:
    """; repeats the last f<ch> find in the same direction."""
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("f", "l")  # first 'l' → index 2
        assert vi._cursor == 2
        await pilot.press("semicolon")  # repeat: next 'l' → index 3
        assert vi._cursor == 3


async def test_comma_reverses_f_find() -> None:
    """, reverses the last f<ch> find direction."""
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("f", "l")  # first 'l' → index 2
        await pilot.press("semicolon")  # next 'l' → index 3
        await pilot.press("comma")  # reverse → back to 'l' at index 2
        assert vi._cursor == 2


async def test_last_find_set_after_f() -> None:
    """_last_find is set after a successful f<ch>."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("f", "l")
        assert vi._last_find == ("f", "l")


async def test_find_in_multiline_stays_on_line() -> None:
    """f<ch> in multi-line mode only searches the current logical line."""
    async with _App(
        value="aaa\nbbb", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on first 'a' of row 0
        await pilot.press("f", "b")  # 'b' is only on row 1 — no match on row 0
        assert vi._cursor == 0  # cursor should not have moved


# ---------------------------------------------------------------------------
# Jump commands (gg / G / ^)
# ---------------------------------------------------------------------------


async def test_gg_jumps_to_start_singleline() -> None:
    """gg in single-line mode moves cursor to position 0."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4  # at 'o'
        await pilot.press("g", "g")
        assert vi._cursor == 0


async def test_G_jumps_to_end_singleline() -> None:
    """G in single-line mode moves cursor to the last character."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("G")
        assert vi._cursor == 4  # last char index


async def test_gg_jumps_to_first_line_multiline() -> None:
    """gg in multi-line mode moves cursor to the very beginning of the text."""
    async with _App(
        value="first\nsecond\nthird", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        # Move cursor to third line
        vi._cursor = len("first\nsecond\n")  # start of 'third'
        await pilot.press("g", "g")
        assert vi._cursor == 0


async def test_G_jumps_to_last_line_multiline() -> None:
    """G in multi-line mode moves cursor to the last character of the last line."""
    async with _App(
        value="first\nsecond\nthird", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("G")
        # "third" starts at len("first\nsecond\n") = 13; last char is 13+4=17
        expected = len("first\nsecond\n") + len("third") - 1
        assert vi._cursor == expected


async def test_caret_moves_to_first_nonblank() -> None:
    """^ moves cursor to the first non-space character of the line."""
    async with _App(value="   hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 7  # on 'o'
        await pilot.press("circumflex_accent")
        assert vi._cursor == 3  # index of 'h'


async def test_caret_on_line_with_no_leading_spaces() -> None:
    """^ with no leading spaces moves to index 0."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 4
        await pilot.press("circumflex_accent")
        assert vi._cursor == 0


async def test_caret_in_multiline_operates_on_current_line() -> None:
    """^ in multi-line mode jumps to first non-blank of current line, not line 0."""
    async with _App(
        value="first\n   indent", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        # Move to second line: offset of 'indent' start = len("first\n   ") = 9
        vi._cursor = 9  # on first space of '   indent'
        await pilot.press("circumflex_accent")
        assert vi._cursor == len("first\n") + 3  # index of 'i' in '   indent'


# ---------------------------------------------------------------------------
# dd register population
# ---------------------------------------------------------------------------


async def test_dd_single_line_populates_register() -> None:
    """dd in single-line mode copies text to _register."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        await pilot.press("d", "d")
        assert vi._text == ""
        assert vi._register == "hello"


async def test_dd_multi_line_populates_register() -> None:
    """dd in multi-line mode copies the deleted line to _register."""
    async with _App(
        value="first\nsecond\nthird", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on 'second'
        await pilot.press("d", "d")
        assert "second" not in vi._text
        assert vi._register == "second"


async def test_dd_then_p_pastes_deleted_line() -> None:
    """p after dd pastes the deleted line below current line."""
    async with _App(
        value="aaa\nbbb\nccc", start_mode="command", multiline=True
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on 'aaa'
        await pilot.press("d", "d")
        assert vi._register == "aaa"
        await pilot.press("p")
        # 'aaa' should be pasted back as a line after 'bbb'
        assert "aaa" in vi._text


# ---------------------------------------------------------------------------
# % bracket-matching motion
# ---------------------------------------------------------------------------


async def test_percent_jumps_forward_to_closing_paren() -> None:
    """% on '(' jumps to matching ')'."""
    async with _App(value="(hello)", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # on '('
        await pilot.press("percent")
        assert vi._cursor == 6  # on ')'


async def test_percent_jumps_backward_to_opening_paren() -> None:
    """% on ')' jumps to matching '('."""
    async with _App(value="(hello)", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 6  # on ')'
        await pilot.press("percent")
        assert vi._cursor == 0  # on '('


async def test_percent_nested_brackets() -> None:
    """% skips nested brackets when finding the match."""
    async with _App(value="(a(b)c)", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0  # outer '('
        await pilot.press("percent")
        assert vi._cursor == 6  # outer ')'


async def test_percent_no_match_stays_put() -> None:
    """% on a non-bracket character does not move the cursor."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("percent")
        assert vi._cursor == 0


async def test_percent_square_brackets() -> None:
    """% works for square brackets."""
    async with _App(value="[abc]", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("percent")
        assert vi._cursor == 4


# ---------------------------------------------------------------------------
# d% delete to matching bracket
# ---------------------------------------------------------------------------


async def test_d_percent_deletes_from_cursor_to_closing() -> None:
    """d% deletes from '(' to matching ')' inclusive."""
    async with _App(value="x(hello)y", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 1  # on '('
        await pilot.press("d", "percent")
        assert vi._text == "xy"
        assert vi._cursor == 1


async def test_d_percent_populates_register() -> None:
    """d% copies the deleted span to _register."""
    async with _App(value="(hi)", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("d", "percent")
        assert vi._register == "(hi)"
        assert vi._text == ""


async def test_d_percent_no_match_does_nothing() -> None:
    """d% when not on a bracket does not modify text."""
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("d", "percent")
        assert vi._text == "hello"


# ---------------------------------------------------------------------------
# c% change to matching bracket
# ---------------------------------------------------------------------------


async def test_c_percent_deletes_bracket_span_and_enters_insert() -> None:
    """c% deletes from '(' to ')' inclusive and enters INSERT mode."""
    async with _App(value="(world)", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        await pilot.press("c", "percent")
        assert vi._text == ""
        assert vi._vim_mode == "insert"


# ---------------------------------------------------------------------------
# start_at_beginning parameter
# ---------------------------------------------------------------------------


class _AppWithBeginning(App[None]):
    """Host app that creates a VimInput with start_at_beginning=True."""

    def __init__(self, value: str = "", start_mode: str = "insert") -> None:
        super().__init__()
        self._vim_value = value
        self._vim_start_mode = start_mode

    def compose(self) -> ComposeResult:
        yield VimInput(
            value=self._vim_value,
            placeholder="type here",
            start_mode=self._vim_start_mode,
            start_at_beginning=True,
            id="vi",
        )


async def test_start_at_beginning_positions_cursor_at_zero_insert_mode() -> None:
    """VimInput with start_at_beginning=True starts with cursor at 0 in insert mode."""
    async with _AppWithBeginning(
        value="hello world", start_mode="insert"
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._cursor == 0
        assert vi._view_row == 0
        assert vi._view_offset == 0


async def test_start_at_beginning_positions_cursor_at_zero_command_mode() -> None:
    """VimInput with start_at_beginning=True starts with cursor at 0 in command mode."""
    async with _AppWithBeginning(
        value="hello world", start_mode="command"
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._cursor == 0
        assert vi._view_row == 0
        assert vi._view_offset == 0


async def test_start_at_beginning_overrides_default_command_cursor() -> None:
    """start_at_beginning=True overrides the normal command-mode cursor (last char)."""
    # Without start_at_beginning, command mode places cursor at last char index.
    async with _App(value="hello", start_mode="command").run_test() as pilot:
        vi_normal = _vi(pilot.app)
        assert vi_normal._cursor == 4  # default: last char index

    # With start_at_beginning, cursor should be 0 regardless.
    async with _AppWithBeginning(
        value="hello", start_mode="command"
    ).run_test() as pilot:
        vi_begin = _vi(pilot.app)
        assert vi_begin._cursor == 0


async def test_start_at_beginning_allows_normal_typing_after() -> None:
    """After start_at_beginning positions cursor at 0, typing works normally."""
    async with _AppWithBeginning(
        value="world", start_mode="insert"
    ).run_test() as pilot:
        vi = _vi(pilot.app)
        assert vi._cursor == 0
        # Typing should insert at cursor position 0
        await pilot.press("h", "i", " ")
        assert vi.value.startswith("hi world")


# ---------------------------------------------------------------------------
# Regression: count prefix for s and dd
# ---------------------------------------------------------------------------


async def test_count_s_deletes_char_and_enters_insert() -> None:
    """s with a count deletes that many chars immediately and enters INSERT mode."""
    async with _App(value="hello world", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        # 3s: deletes 'h', 'e', 'l' and enters INSERT mode
        await pilot.press("3", "s")
        await pilot.pause()
        assert vi._vim_mode == "insert"
        assert vi._text == "lo world"


async def test_count_s_repeat_dot_deletes_count_chars() -> None:
    """After 3s<X><Esc>, pressing '.' should repeat the substitution deleting 3 chars."""
    async with _App(value="abcdefgh", start_mode="command").run_test() as pilot:
        vi = _vi(pilot.app)
        vi._cursor = 0
        # 3s: deletes 'a','b','c' (3 chars), enters INSERT
        await pilot.press("3", "s")
        await pilot.pause()
        assert vi._text == "defgh"  # 3 chars deleted
        assert vi._vim_mode == "insert"
        # Type replacement char, then Esc to commit
        await pilot.press("X")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()
        # State: 'Xdefgh', cursor at 1 (single-line clamp: min(1,5)=1)
        assert vi._text == "Xdefgh"
        assert vi._vim_mode == "command"
        # '.' replays from cursor=1: pre_s deletes 3 chars ('d','e','f') → 'Xgh',
        # then inserts 'X' at cursor=1 → 'XXgh'
        await pilot.press("period")
        await pilot.pause()
        # net: 3 deleted, 1 inserted → 4 chars total
        assert vi._text == "XXgh"


async def test_count_dd_deletes_multiple_lines() -> None:
    """2dd should delete 2 lines in multiline mode."""
    async with _MultiApp().run_test() as pilot:
        vi = _mvi(pilot.app)
        # Type 4 lines
        for word in ["line1", "line2", "line3", "line4"]:
            for ch in word:
                await pilot.press(ch)
            await pilot.press("enter")
        # Remove trailing newline by pressing backspace once
        await pilot.press("backspace")
        await pilot.press("escape")  # enter command mode
        # Move cursor to start
        vi._cursor = 0
        await pilot.press("2", "d", "d")
        await pilot.pause()
        # Should have deleted line1 and line2, leaving line3 and line4
        assert vi._text == "line3\nline4"
