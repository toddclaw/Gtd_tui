"""Tests for newer operations: regex search, is_divider_task, duplicate_task, add_tag_to_task."""

from __future__ import annotations

from gtd_tui.gtd.operations import (
    add_tag_to_task,
    duplicate_task,
    is_divider_task,
    search_tasks,
)
from gtd_tui.gtd.task import Task

# ---------------------------------------------------------------------------
# search_tasks — regex and case-sensitivity behaviour
# ---------------------------------------------------------------------------


def test_search_plain_valid_regex_matches_with_dot() -> None:
    """A plain query that is valid regex uses regex matching; '.' matches any char."""
    tasks = [
        Task(title="buy milk"),
        Task(title="buy-milk"),
    ]
    results = search_tasks(tasks, "buy.milk")
    titles = [t.title for t, _ in results]
    assert "buy milk" in titles
    assert "buy-milk" in titles


def test_search_plain_invalid_regex_falls_back_to_substring() -> None:
    """An invalid regex pattern falls back to substring matching."""
    tasks = [Task(title="[invalid test")]
    results = search_tasks(tasks, "[invalid")
    assert len(results) == 1
    assert results[0][0].title == "[invalid test"


def test_search_plain_invalid_regex_no_false_positives() -> None:
    """Substring fallback does not match tasks that don't contain the literal string."""
    tasks = [
        Task(title="[invalid test"),
        Task(title="something else"),
    ]
    results = search_tasks(tasks, "[invalid")
    assert len(results) == 1


def test_search_double_slash_case_sensitive() -> None:
    """//Pattern prefix enables case-sensitive regex matching."""
    tasks = [
        Task(title="Hello World"),
        Task(title="hello world"),
    ]
    results = search_tasks(tasks, "//Hello")
    assert len(results) == 1
    assert results[0][0].title == "Hello World"


def test_search_double_slash_matches_pattern_not_whole_string() -> None:
    """//Pattern performs a search (not full-match); partial string match works."""
    tasks = [Task(title="Hello World")]
    results = search_tasks(tasks, "//World")
    assert len(results) == 1


def test_search_plain_case_insensitive() -> None:
    """A plain query matches regardless of case."""
    tasks = [
        Task(title="Hello World"),
        Task(title="hello world"),
    ]
    results = search_tasks(tasks, "hello")
    assert len(results) == 2


def test_search_double_slash_no_match_wrong_case() -> None:
    """//Pattern does NOT match when the case differs."""
    tasks = [Task(title="hello world")]
    results = search_tasks(tasks, "//Hello")
    assert len(results) == 0


def test_search_regex_dot_star_matches_substring() -> None:
    """Regex '.*' as part of a plain query is applied as regex."""
    tasks = [Task(title="abc123def")]
    results = search_tasks(tasks, "abc.*def")
    assert len(results) == 1


# ---------------------------------------------------------------------------
# is_divider_task
# ---------------------------------------------------------------------------


def test_is_divider_task_single_dash() -> None:
    task = Task(title="-")
    assert is_divider_task(task)


def test_is_divider_task_single_equals() -> None:
    task = Task(title="=")
    assert is_divider_task(task)


def test_is_divider_task_normal_title() -> None:
    task = Task(title="Buy milk")
    assert not is_divider_task(task)


def test_is_divider_task_with_surrounding_spaces_dash() -> None:
    """Whitespace around '-' is stripped; task is still a divider."""
    task = Task(title=" - ")
    assert is_divider_task(task)


def test_is_divider_task_with_surrounding_spaces_equals() -> None:
    """Whitespace around '=' is stripped; task is still a divider."""
    task = Task(title=" = ")
    assert is_divider_task(task)


def test_is_divider_task_double_dash_is_not_divider() -> None:
    task = Task(title="--")
    assert not is_divider_task(task)


def test_is_divider_task_empty_string_is_not_divider() -> None:
    task = Task(title="")
    assert not is_divider_task(task)


# ---------------------------------------------------------------------------
# duplicate_task
# ---------------------------------------------------------------------------


def test_duplicate_task_creates_new_id() -> None:
    """Duplicated task receives a different id from the original."""
    tasks = [Task(title="Original", folder_id="inbox")]
    new_tasks = duplicate_task(tasks, tasks[0].id)
    assert len(new_tasks) == 2
    assert new_tasks[0].id != new_tasks[1].id


def test_duplicate_task_copies_title_and_notes_and_tags() -> None:
    """Duplicate preserves title, notes, and tags from the source."""
    tasks = [
        Task(title="Buy milk", folder_id="inbox", notes="2% please", tags=["@errand"])
    ]
    new_tasks = duplicate_task(tasks, tasks[0].id)
    dup = new_tasks[-1]
    assert dup.title == "Buy milk"
    assert dup.notes == "2% please"
    assert dup.tags == ["@errand"]


def test_duplicate_task_logbook_remapped_to_inbox() -> None:
    """A task in logbook is duplicated into inbox (not logbook)."""
    tasks = [Task(title="Done task", folder_id="logbook")]
    new_tasks = duplicate_task(tasks, tasks[0].id)
    dup = new_tasks[-1]
    assert dup.folder_id == "inbox"


def test_duplicate_task_non_logbook_keeps_folder() -> None:
    """A task in a non-logbook folder keeps its folder_id in the duplicate."""
    tasks = [Task(title="Inbox task", folder_id="inbox")]
    new_tasks = duplicate_task(tasks, tasks[0].id)
    dup = new_tasks[-1]
    assert dup.folder_id == "inbox"


def test_duplicate_nonexistent_task_is_noop() -> None:
    """Duplicating a nonexistent id returns the original list unchanged."""
    tasks = [Task(title="X")]
    result = duplicate_task(tasks, "nonexistent-id")
    assert result == tasks


def test_duplicate_task_original_is_not_mutated() -> None:
    """The original task object is not modified by duplication."""
    tasks = [Task(title="Original", folder_id="inbox")]
    original_id = tasks[0].id
    new_tasks = duplicate_task(tasks, original_id)
    original_in_new = next(t for t in new_tasks if t.id == original_id)
    assert original_in_new.title == "Original"


def test_duplicate_task_duplicate_is_not_complete() -> None:
    """Duplicating a logbook task produces a non-complete duplicate."""
    tasks = [Task(title="Done", folder_id="logbook")]
    # Mark the task as complete manually so completed_at is set
    import dataclasses
    from datetime import datetime

    tasks = [dataclasses.replace(tasks[0], completed_at=datetime.now())]
    new_tasks = duplicate_task(tasks, tasks[0].id)
    dup = new_tasks[-1]
    assert dup.completed_at is None


# ---------------------------------------------------------------------------
# add_tag_to_task
# ---------------------------------------------------------------------------


def test_add_tag_to_task_adds_tag() -> None:
    """Adding a new tag appends it to the task's tag list."""
    tasks = [Task(title="X", tags=["@work"])]
    new_tasks = add_tag_to_task(tasks, tasks[0].id, "@home")
    assert "@home" in new_tasks[0].tags
    assert "@work" in new_tasks[0].tags


def test_add_tag_to_task_no_duplicate() -> None:
    """Adding an already-present tag does not duplicate it."""
    tasks = [Task(title="X", tags=["@work"])]
    new_tasks = add_tag_to_task(tasks, tasks[0].id, "@work")
    assert new_tasks[0].tags.count("@work") == 1


def test_add_tag_empty_string_is_noop() -> None:
    """Adding an empty string does not modify the task's tags."""
    tasks = [Task(title="X", tags=[])]
    new_tasks = add_tag_to_task(tasks, tasks[0].id, "")
    assert new_tasks[0].tags == []


def test_add_tag_whitespace_only_is_noop() -> None:
    """Adding a whitespace-only tag is treated as empty and is a no-op."""
    tasks = [Task(title="X", tags=[])]
    new_tasks = add_tag_to_task(tasks, tasks[0].id, "   ")
    assert new_tasks[0].tags == []


def test_add_tag_nonexistent_task_leaves_list_unchanged() -> None:
    """add_tag_to_task with an unknown task id returns the original list."""
    tasks = [Task(title="X", tags=[])]
    new_tasks = add_tag_to_task(tasks, "nonexistent-id", "@tag")
    assert new_tasks[0].tags == []


def test_add_tag_does_not_affect_other_tasks() -> None:
    """Only the targeted task receives the new tag."""
    tasks = [
        Task(title="A", tags=[]),
        Task(title="B", tags=[]),
    ]
    new_tasks = add_tag_to_task(tasks, tasks[0].id, "@tag")
    assert "@tag" in new_tasks[0].tags
    assert new_tasks[1].tags == []


# ---------------------------------------------------------------------------
# Regression: // prefix enables case-sensitive search
# ---------------------------------------------------------------------------


def test_search_tasks_case_sensitive_double_slash() -> None:
    """// prefix makes search case-sensitive, matching only the exact-case task."""
    tasks = [
        Task(title="Feature Request"),
        Task(title="feature bug"),
    ]
    # Case-sensitive: only "Feature" (capital F) should match
    results = search_tasks(tasks, "//Feature")
    titles = [t.title for t, _ in results]
    assert "Feature Request" in titles
    assert "feature bug" not in titles

    # Case-insensitive (no //): both should match
    results = search_tasks(tasks, "feature")
    titles = [t.title for t, _ in results]
    assert "Feature Request" in titles
    assert "feature bug" in titles
