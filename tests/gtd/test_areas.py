"""Tests for BACKLOG-32: Areas of responsibility."""

from __future__ import annotations

import json

from gtd_tui.gtd.area import Area
from gtd_tui.gtd.folder import Folder
from gtd_tui.gtd.operations import (
    add_area,
    add_project,
    assign_folder_to_area,
    assign_project_to_area,
    delete_area,
    rename_area,
)


def test_add_area() -> None:
    areas = add_area([], "Work")
    assert len(areas) == 1
    assert areas[0].name == "Work"


def test_add_area_assigns_id() -> None:
    areas = add_area([], "Work")
    assert areas[0].id != ""


def test_add_area_increments_position() -> None:
    areas = add_area([], "Work")
    areas = add_area(areas, "Personal")
    assert areas[0].position < areas[1].position


def test_delete_area() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    areas = delete_area(areas, aid)
    assert areas == []


def test_delete_area_unknown_id_is_noop() -> None:
    areas = add_area([], "Work")
    areas = delete_area(areas, "nonexistent")
    assert len(areas) == 1


def test_rename_area() -> None:
    areas = add_area([], "Old")
    aid = areas[0].id
    areas = rename_area(areas, aid, "New")
    assert areas[0].name == "New"


def test_rename_area_unknown_id_is_noop() -> None:
    areas = add_area([], "Work")
    areas = rename_area(areas, "nonexistent", "Other")
    assert areas[0].name == "Work"


def test_assign_folder_to_area() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    folder = Folder(name="Projects", id="f1")
    folders = assign_folder_to_area([folder], "f1", aid)
    assert folders[0].area_id == aid


def test_unassign_folder_from_area() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    folder = Folder(name="Projects", id="f1", area_id=aid)
    folders = assign_folder_to_area([folder], "f1", None)
    assert folders[0].area_id is None


def test_assign_folder_to_area_unknown_folder_is_noop() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    folder = Folder(name="Projects", id="f1")
    folders = assign_folder_to_area([folder], "unknown", aid)
    assert folders[0].area_id is None


def test_assign_project_to_area() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    projects = add_project([], "Deploy v2")
    pid = projects[0].id
    projects = assign_project_to_area(projects, pid, aid)
    assert projects[0].area_id == aid


def test_unassign_project_from_area() -> None:
    areas = add_area([], "Work")
    aid = areas[0].id
    projects = add_project([], "Deploy v2")
    pid = projects[0].id
    projects = assign_project_to_area(projects, pid, aid)
    projects = assign_project_to_area(projects, pid, None)
    assert projects[0].area_id is None


def test_folder_area_id_default_none() -> None:
    folder = Folder(name="Test")
    assert folder.area_id is None


def test_project_area_id_default_none() -> None:
    projects = add_project([], "New project")
    assert projects[0].area_id is None


def test_area_dataclass_fields() -> None:
    area = Area(name="Personal")
    assert area.name == "Personal"
    assert isinstance(area.id, str)
    assert area.id != ""
    assert area.position == 0


def test_storage_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_areas, save_data

    areas = add_area([], "Work")
    areas = add_area(areas, "Personal")
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, areas=areas)
    loaded = load_areas(data_file=data_file)
    assert len(loaded) == 2
    assert loaded[0].name == "Work"
    assert loaded[1].name == "Personal"


def test_storage_round_trip_preserves_ids(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_areas, save_data

    areas = add_area([], "Work")
    original_id = areas[0].id
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, areas=areas)
    loaded = load_areas(data_file=data_file)
    assert loaded[0].id == original_id


def test_folder_area_id_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_folders, save_data

    areas = add_area([], "Work")
    aid = areas[0].id
    folder = Folder(name="Projects", id="f1", area_id=aid)
    data_file = tmp_path / "data.json"
    save_data([], [folder], data_file=data_file, areas=areas)
    loaded_folders = load_folders(data_file=data_file)
    assert loaded_folders[0].area_id == aid


def test_folder_area_id_default_none_for_old_data(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_folders

    data_file = tmp_path / "data.json"
    raw = {
        "tasks": [],
        "folders": [{"id": "f1", "name": "Old folder", "position": 0}],
    }
    data_file.write_text(json.dumps(raw))
    folders = load_folders(data_file=data_file)
    assert folders[0].area_id is None


def test_area_default_none_for_old_data(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_areas

    data_file = tmp_path / "data.json"
    raw: dict = {"tasks": [], "folders": []}
    data_file.write_text(json.dumps(raw))
    areas = load_areas(data_file=data_file)
    assert areas == []


def test_load_areas_missing_file(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_areas

    data_file = tmp_path / "nonexistent.json"
    areas = load_areas(data_file=data_file)
    assert areas == []


def test_project_area_id_round_trip(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from gtd_tui.storage.file import load_projects, save_data

    areas = add_area([], "Work")
    aid = areas[0].id
    projects = add_project([], "Big project")
    pid = projects[0].id
    projects = assign_project_to_area(projects, pid, aid)
    data_file = tmp_path / "data.json"
    save_data([], [], data_file=data_file, projects=projects, areas=areas)
    loaded = load_projects(data_file=data_file)
    assert loaded[0].area_id == aid
