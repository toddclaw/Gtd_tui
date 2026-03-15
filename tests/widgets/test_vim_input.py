"""Unit tests for VimInput widget.

Each test uses a minimal Textual app that contains only a VimInput so we can
drive it with the Pilot API without any app-level key handlers interfering.
"""

from __future__ import annotations

import pytest
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
        await pilot.press("dollar")
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
