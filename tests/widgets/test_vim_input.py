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
    def __init__(self, value: str = "", start_mode: str = "insert") -> None:
        super().__init__()
        self._vim_value = value
        self._vim_start_mode = start_mode

    def compose(self) -> ComposeResult:
        yield VimInput(
            value=self._vim_value,
            placeholder="type here",
            start_mode=self._vim_start_mode,
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
