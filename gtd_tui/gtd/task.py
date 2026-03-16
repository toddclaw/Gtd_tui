from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional


@dataclass
class RepeatRule:
    """Calendar-fixed repeat schedule attached to a task.

    On each launch, when next_due <= today a new copy of the task is spawned
    in Today and next_due is advanced by the interval.  The repeat is
    independent of whether previous copies were completed.
    """

    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    next_due: date


@dataclass
class RecurRule:
    """Completion-relative recurrence attached to a task.

    When the task is marked complete, a new copy is spawned in Today with
    scheduled_date = completion_date + interval.  The new copy carries the
    same RecurRule so the pattern continues indefinitely.

    Unlike RepeatRule, the next date floats relative to when the task was
    actually done — a missed week does not pile up extra instances.
    """

    interval: int
    unit: Literal["days", "weeks", "months", "years"]


@dataclass
class Task:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    folder_id: str = "today"
    position: int = 0
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[date] = None
    deadline: Optional[date] = None
    repeat_rule: Optional[RepeatRule] = None
    recur_rule: Optional[RecurRule] = None
    created_at: Optional[datetime] = None

    is_deleted: bool = False

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None and not self.is_deleted

    def complete(self) -> None:
        self.completed_at = datetime.now()
        self.folder_id = "logbook"

    def delete(self) -> None:
        self.completed_at = datetime.now()
        self.folder_id = "logbook"
        self.is_deleted = True
