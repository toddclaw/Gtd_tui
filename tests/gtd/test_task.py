from datetime import datetime

from gtd_tui.gtd.task import Task


def test_new_task_defaults():
    task = Task(title="Buy milk")
    assert task.title == "Buy milk"
    assert task.notes == ""
    assert task.folder_id == "today"
    assert task.position == 0
    assert task.completed_at is None
    assert task.scheduled_date is None
    assert not task.is_complete


def test_task_ids_are_unique():
    t1 = Task(title="A")
    t2 = Task(title="B")
    assert t1.id != t2.id


def test_task_id_is_set():
    task = Task(title="Something")
    assert task.id
    assert len(task.id) > 0


def test_complete_sets_completed_at():
    task = Task(title="Do thing")
    before = datetime.now()
    task.complete()
    after = datetime.now()
    assert task.is_complete
    assert task.completed_at is not None
    assert before <= task.completed_at <= after


def test_complete_moves_to_logbook():
    task = Task(title="Do thing")
    task.complete()
    assert task.folder_id == "logbook"


def test_task_with_notes():
    task = Task(title="Call dentist", notes="Number: 555-1234")
    assert task.notes == "Number: 555-1234"


def test_task_is_not_complete_by_default():
    task = Task(title="Pending")
    assert not task.is_complete
