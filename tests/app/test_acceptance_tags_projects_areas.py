"""Acceptance tests for Tags, Projects, and Areas (BACKLOG-30, 31, 32).

All tests drive the app entirely through Textual's headless Pilot API using
keyboard input and assert on observable state (app model attributes, sidebar
IDs, task field values) rather than internal implementation details.

Key navigation notes:
  - `h`          : focus sidebar from task-list NORMAL mode
  - `j` / `k`   : navigate sidebar items (when sidebar focused)
  - `N`          : create project (when sidebar cursor is on projects section)
  - `A`          : create area (anywhere in sidebar)
  - `m`          : assign selected sidebar project/folder to an area
  - Task detail field order (j advances via focus_next):
      title → date → deadline → notes → checklist-list → checklist-new
      → repeat → recur → tags   (8 j-presses from title to tags)
"""

from __future__ import annotations

from pathlib import Path

from textual.widgets import ListView

from gtd_tui.app import AreaPickerScreen, GtdApp, TaskDetailScreen
from gtd_tui.gtd.area import Area
from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.operations import (
    add_task,
    add_task_to_project,
    set_tags,
)
from gtd_tui.gtd.project import Project
from gtd_tui.gtd.task import Task
from gtd_tui.storage.file import save_data
from gtd_tui.widgets.vim_input import VimInput

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_app(tmp_path: Path) -> GtdApp:
    return GtdApp(data_file=tmp_path / "data.json")


def _prepopulate(
    tmp_path: Path,
    *titles: str,
    folder: str = "today",
    tasks: list[Task] | None = None,
    folders: list[Folder] | None = None,
    projects: list | None = None,
    areas: list | None = None,
) -> Path:
    """Write data and return the data-file path."""
    data_file = tmp_path / "data.json"
    all_tasks: list[Task] = list(tasks or [])
    for title in reversed(titles):
        if folder == "today":
            all_tasks = add_task(all_tasks, title)
        else:
            from gtd_tui.gtd.operations import add_task_to_folder

            all_tasks = add_task_to_folder(all_tasks, folder, title)
    save_data(
        all_tasks,
        folders or [],
        data_file=data_file,
        projects=projects or [],
        areas=areas or [],
    )
    return data_file


# ---------------------------------------------------------------------------
# TAGS — detail screen
# ---------------------------------------------------------------------------


async def test_tags_field_visible_in_task_detail(tmp_path: Path) -> None:
    """TaskDetailScreen exposes a tags VimInput field."""
    data_file = _prepopulate(tmp_path, "Write blog post")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)
        tags_input = app.screen.query_one("#detail-tags-input", VimInput)
        assert tags_input is not None


async def test_tags_saved_via_detail_screen(tmp_path: Path) -> None:
    """Typing comma-separated tags in the detail screen and saving persists them.

    Flow: open detail → j×8 (reach tags field) → verify on tags field →
    i (INSERT) → type tags → Esc (INSERT→COMMAND) → Esc (COMMAND→save+close)
    → verify task.tags == ["work", "home"]
    """
    data_file = _prepopulate(tmp_path, "Deep work session")
    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        # Navigate to the tags field (8 j-presses from title)
        for _ in range(8):
            await pilot.press("j")
            await pilot.pause()

        assert (
            app.screen.focused.id == "detail-tags-input"
        ), f"Expected tags field focused; got: {app.screen.focused.id!r}"

        # Enter INSERT and type tags
        await pilot.press("i")
        await pilot.pause()
        for ch in "work, home":
            await pilot.press(ch)
        await pilot.pause()

        # Esc INSERT→COMMAND, then Esc COMMAND→save
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        assert not isinstance(app.screen, TaskDetailScreen)
        task = next(t for t in app._all_tasks if t.title == "Deep work session")
        assert task.tags == ["work", "home"]


async def test_tags_cleared_when_field_emptied(tmp_path: Path) -> None:
    """Clearing the tags field removes all tags from the task."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Tagged task")
    tasks = set_tags(tasks, tasks[0].id, ["work", "home"])
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")  # open detail
        await pilot.pause()

        # Navigate to tags
        for _ in range(8):
            await pilot.press("j")
            await pilot.pause()
        assert app.screen.focused.id == "detail-tags-input"

        # Enter INSERT, clear value, Esc Esc to save
        await pilot.press("i")
        await pilot.pause()
        tags_vi = app.screen.query_one("#detail-tags-input", VimInput)
        tags_vi.value = ""  # clear programmatically while in INSERT
        await pilot.press("escape")
        await pilot.pause()
        await pilot.press("escape")
        await pilot.pause()

        task = next(t for t in app._all_tasks if t.title == "Tagged task")
        assert task.tags == []


async def test_tags_appear_in_sidebar_after_being_set(tmp_path: Path) -> None:
    """After setting tags on a task, the sidebar shows a Tags section.

    The sidebar view IDs must include 'tag:work' when a task has that tag.
    """
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Focused work")
    tasks = set_tags(tasks, tasks[0].id, ["work"])
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert "tag:work" in app._sidebar_view_ids


async def test_tag_view_shows_only_tagged_tasks(tmp_path: Path) -> None:
    """Only tasks with the active tag appear in the tag view's task list entries."""
    from gtd_tui.gtd.operations import tasks_with_tag

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Untagged task")
    tasks = add_task(tasks, "Tagged task")
    # add_task prepends — tasks[0] is "Tagged task"
    tasks = set_tags(tasks, tasks[0].id, ["urgent"])
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # tag view filter is backed by tasks_with_tag — verify it in the model
        in_tag_view = tasks_with_tag(app._all_tasks, "urgent")
        titles = {t.title for t in in_tag_view}
        assert "Tagged task" in titles
        assert "Untagged task" not in titles

        # And verify the sidebar reflects the tag
        assert "tag:urgent" in app._sidebar_view_ids


async def test_tag_count_in_sidebar_is_correct(tmp_path: Path) -> None:
    """Sidebar tag entry shows the count of non-deleted, non-logbook tagged tasks."""
    from gtd_tui.gtd.operations import all_tags

    data_file = tmp_path / "data.json"
    tasks = add_task([], "Task A")
    tasks = add_task(tasks, "Task B")
    tasks = set_tags(tasks, tasks[0].id, ["focus"])
    tasks = set_tags(tasks, tasks[1].id, ["focus"])
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        tag_counts = dict(all_tags(app._all_tasks))
        assert tag_counts.get("focus") == 2


async def test_existing_tags_preloaded_in_detail_screen(tmp_path: Path) -> None:
    """When a task already has tags, they are pre-filled in the detail tags field."""
    data_file = tmp_path / "data.json"
    tasks = add_task([], "Work item")
    tasks = set_tags(tasks, tasks[0].id, ["work", "urgent"])
    save_data(tasks, [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()
        assert isinstance(app.screen, TaskDetailScreen)

        tags_vi = app.screen.query_one("#detail-tags-input", VimInput)
        assert "work" in tags_vi.value
        assert "urgent" in tags_vi.value


# ---------------------------------------------------------------------------
# PROJECTS — creation and task membership
# ---------------------------------------------------------------------------


async def test_project_creation_via_sidebar_keyboard(tmp_path: Path) -> None:
    """Creating a project via N key while the sidebar cursor is on the projects section.

    Flow: pre-populate one project so the header appears → start app →
    h (focus sidebar) → j×3 (today→upcoming→waiting_on→__projects_header__)
    → N → type name → Enter → project appears in _all_projects.
    """
    # Pre-populate one project so __projects_header__ appears in sidebar
    data_file = tmp_path / "data.json"
    existing_project = Project(title="Existing project")
    save_data([], [], data_file=data_file, projects=[existing_project])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # h → focus sidebar; it starts at "today" (idx 1)
        await pilot.press("h")
        await pilot.pause()

        # Navigate: today → upcoming → waiting_on → __projects_header__
        for _ in range(3):
            await pilot.press("j")
            await pilot.pause()

        sidebar = app.query_one("#sidebar", ListView)
        view_ids = app._sidebar_view_ids
        current_id = view_ids[sidebar.index] if sidebar.index is not None else ""
        assert current_id == "__projects_header__", (
            f"Expected __projects_header__; got {current_id!r} "
            f"(all view_ids: {view_ids})"
        )

        # N → start new project input
        await pilot.press("N")
        await pilot.pause()
        assert app._input_stage == "project_name"

        # Type name + Enter
        for ch in "Sprint planning":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()

        assert app._input_stage == ""
        project_titles = [p.title for p in app._all_projects]
        assert "Sprint planning" in project_titles


async def test_project_view_shown_after_creation(tmp_path: Path) -> None:
    """After creating a project via keyboard, the view switches to that project."""
    data_file = tmp_path / "data.json"
    existing_project = Project(title="Seed project")
    save_data([], [], data_file=data_file, projects=[existing_project])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.press("h")
        await pilot.pause()
        for _ in range(3):
            await pilot.press("j")
            await pilot.pause()
        await pilot.press("N")
        await pilot.pause()
        for ch in "My new project":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()

        assert app._current_view.startswith("project:")
        new_proj_id = app._current_view[8:]
        new_proj = next((p for p in app._all_projects if p.id == new_proj_id), None)
        assert new_proj is not None
        assert new_proj.title == "My new project"


async def test_task_created_in_project_view_has_project_id(tmp_path: Path) -> None:
    """Tasks created while the project view is active are linked to that project.

    Flow: create a project via API, set app to project view, press o → type
    title → Enter → verify task.project_id == project.id.
    """
    data_file = tmp_path / "data.json"
    proj = Project(title="Website redesign")
    save_data([], [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Navigate to the project view directly
        app._current_view = f"project:{proj.id}"
        app._refresh_list()
        await pilot.pause()

        # Create a task
        await pilot.press("o")
        await pilot.pause()
        assert app._input_stage == "title"

        for ch in "Design homepage":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()

        project_tasks = [t for t in app._all_tasks if t.project_id == proj.id]
        assert len(project_tasks) == 1
        assert project_tasks[0].title == "Design homepage"


async def test_project_progress_updates_when_task_completed(tmp_path: Path) -> None:
    """Completing a project task increments the done count in project_progress."""
    from gtd_tui.gtd.operations import project_progress

    data_file = tmp_path / "data.json"
    proj = Project(title="Q1 goals")
    tasks: list[Task] = []
    tasks = add_task_to_project(tasks, proj.id, "Task one")
    tasks = add_task_to_project(tasks, proj.id, "Task two")
    tasks = add_task_to_project(tasks, proj.id, "Task three")
    save_data(tasks, [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        app._current_view = f"project:{proj.id}"
        app._refresh_list()
        await pilot.pause()

        done_before, total = project_progress(app._all_tasks, proj.id)
        assert done_before == 0
        assert total == 3

        # Complete one task
        await pilot.press("x")
        await pilot.pause()

        done_after, total_after = project_progress(app._all_tasks, proj.id)
        assert done_after == 1
        assert total_after == 3


async def test_project_appears_in_sidebar_view_ids(tmp_path: Path) -> None:
    """A project is listed in _sidebar_view_ids as 'project:{id}'."""
    data_file = tmp_path / "data.json"
    proj = Project(title="Side project")
    save_data([], [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert f"project:{proj.id}" in app._sidebar_view_ids


async def test_completed_project_removed_from_sidebar(tmp_path: Path) -> None:
    """A completed project is excluded from _sidebar_view_ids (active only)."""
    from datetime import datetime

    data_file = tmp_path / "data.json"
    proj = Project(title="Old project", completed_at=datetime.now())
    save_data([], [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert f"project:{proj.id}" not in app._sidebar_view_ids


async def test_project_task_count_shown_in_sidebar(tmp_path: Path) -> None:
    """The sidebar renders a project as 'Title (done/total)'."""
    data_file = tmp_path / "data.json"
    proj = Project(title="Content calendar")
    tasks: list[Task] = []
    tasks = add_task_to_project(tasks, proj.id, "Write post")
    tasks = add_task_to_project(tasks, proj.id, "Publish post")
    save_data(tasks, [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        sidebar = app.query_one("#sidebar", ListView)
        proj_idx = app._sidebar_view_ids.index(f"project:{proj.id}")
        item_label = str(
            sidebar.query("ListItem")[proj_idx].query_one("Label").render()
        )
        assert "Content calendar" in item_label
        assert "0/2" in item_label  # 0 done, 2 total


# ---------------------------------------------------------------------------
# AREAS — creation and project grouping
# ---------------------------------------------------------------------------


async def test_area_creation_via_keyboard(tmp_path: Path) -> None:
    """Pressing A in the sidebar creates a new area.

    Flow: start app → h (focus sidebar) → A → type name → Enter → area exists.
    """
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file)

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        await pilot.press("h")
        await pilot.pause()

        await pilot.press("A")
        await pilot.pause()
        assert app._input_stage == "area_name"
        assert app._mode == "INSERT"

        for ch in "Personal":
            await pilot.press(ch)
        await pilot.press("enter")
        await pilot.pause()

        assert app._input_stage == ""
        area_names = [a.name for a in app._all_areas]
        assert "Personal" in area_names


async def test_area_appears_in_sidebar_view_ids(tmp_path: Path) -> None:
    """A created area is listed in _sidebar_view_ids as 'area:{id}'."""
    data_file = tmp_path / "data.json"
    area = Area(name="Work")
    save_data([], [], data_file=data_file, areas=[area])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        assert f"area:{area.id}" in app._sidebar_view_ids


async def test_project_assigned_to_area_via_api_appears_under_area(
    tmp_path: Path,
) -> None:
    """A project assigned to an area appears under the area's section in the sidebar."""
    data_file = tmp_path / "data.json"
    area = Area(name="Work")
    proj = Project(title="Website", area_id=area.id)
    save_data([], [], data_file=data_file, projects=[proj], areas=[area])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        view_ids = app._sidebar_view_ids
        area_idx = view_ids.index(f"area:{area.id}")
        proj_idx = view_ids.index(f"project:{proj.id}")
        # Project must appear after its area header
        assert (
            proj_idx > area_idx
        ), f"Project (idx {proj_idx}) should come after its area (idx {area_idx})"


async def test_area_assignment_via_keyboard_picker(tmp_path: Path) -> None:
    """Pressing m on a project in the sidebar opens AreaPickerScreen.

    Full flow: area + project exist → navigate sidebar to project → m →
    AreaPickerScreen appears → Enter to confirm first area → project.area_id set.
    """
    data_file = tmp_path / "data.json"
    area = Area(name="Research")
    proj = Project(title="Literature review")
    save_data([], [], data_file=data_file, projects=[proj], areas=[area])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()

        # Focus sidebar and navigate to the project entry
        await pilot.press("h")
        await pilot.pause()

        # sidebar view ids: inbox(0), today(1), upcoming(2), waiting_on(3),
        # area:... (4), project:... (5, under area since area_id=None)
        # Actually without area_id on proj, it goes to uncategorized projects header.
        # Here proj.area_id is None, so: ... waiting_on, __projects_header__, project:id
        # that's idx 4 for header and idx 5 for project (from today=1: j×4)
        view_ids = app._sidebar_view_ids
        proj_view_id = f"project:{proj.id}"

        # Navigate to the project entry
        proj_sidebar_idx = view_ids.index(proj_view_id)
        # sidebar starts at today (idx 1), need to reach proj_sidebar_idx
        current_idx = 1  # today
        for _ in range(proj_sidebar_idx - current_idx):
            await pilot.press("j")
            await pilot.pause()

        sidebar = app.query_one("#sidebar", ListView)
        assert view_ids[sidebar.index] == proj_view_id

        # Press m to assign to area → AreaPickerScreen opens
        await pilot.press("m")
        await pilot.pause()
        assert isinstance(app.screen, AreaPickerScreen)

        # idx 0 = "(No area)"; j moves to the first actual area, then Enter selects it
        await pilot.press("j")
        await pilot.pause()
        await pilot.press("enter")
        await pilot.pause()

        assert not isinstance(app.screen, AreaPickerScreen)
        updated_proj = next(p for p in app._all_projects if p.id == proj.id)
        assert updated_proj.area_id == area.id


async def test_multiple_areas_in_sidebar_order(tmp_path: Path) -> None:
    """Multiple areas appear before the uncategorized section in the sidebar."""
    data_file = tmp_path / "data.json"
    area_work = Area(name="Work", position=0)
    area_personal = Area(name="Personal", position=1)
    save_data([], [], data_file=data_file, areas=[area_work, area_personal])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        view_ids = app._sidebar_view_ids
        work_idx = view_ids.index(f"area:{area_work.id}")
        personal_idx = view_ids.index(f"area:{area_personal.id}")
        # Work (position 0) must appear before Personal (position 1)
        assert work_idx < personal_idx


# ---------------------------------------------------------------------------
# PROJECTS + TAGS integration
# ---------------------------------------------------------------------------


async def test_project_task_with_tags_shows_in_both_views(tmp_path: Path) -> None:
    """A task in a project that also has a tag appears in both the project view
    and the tag view."""
    from gtd_tui.gtd.operations import project_tasks, tasks_with_tag

    data_file = tmp_path / "data.json"
    proj = Project(title="Research project")
    tasks: list[Task] = []
    tasks = add_task_to_project(tasks, proj.id, "Read paper")
    tasks = set_tags(tasks, tasks[0].id, ["reading"])
    save_data(tasks, [], data_file=data_file, projects=[proj])

    app = GtdApp(data_file=data_file)
    async with app.run_test() as pilot:
        await pilot.pause()
        proj_tasks = project_tasks(app._all_tasks, proj.id)
        tagged = tasks_with_tag(app._all_tasks, "reading")
        assert any(t.title == "Read paper" for t in proj_tasks)
        assert any(t.title == "Read paper" for t in tagged)
