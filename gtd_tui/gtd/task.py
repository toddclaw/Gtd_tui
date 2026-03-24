from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Literal, Optional


@dataclass
class ChecklistItem:
    label: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    checked: bool = False


@dataclass
class RepeatRule:
    """Calendar-fixed repeat schedule attached to a task.

    On each launch, when next_due <= today a new copy of the task is spawned
    in Today and next_due is advanced by the interval.  The repeat is
    independent of whether previous copies were completed.

    Advanced scheduling (mutually exclusive with simple interval):
      days_of_week  — non-empty list of weekday ints (Mon=0..Sun=6).
                      interval acts as a week-stride multiplier (1=weekly,
                      2=biweekly).  E.g. MWF = [0,2,4] with interval=1.
      nth_weekday   — (nth, weekday) pair, e.g. (4, 3) = 4th Thursday.
                      Fires on that occurrence in the next calendar month.
    """

    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    next_due: date
    days_of_week: list[int] = field(default_factory=list)
    nth_weekday: Optional[tuple[int, int]] = None


@dataclass
class RecurRule:
    """Completion-relative recurrence attached to a task.

    When the task is marked complete, a new copy is spawned in Today with
    scheduled_date computed from the completion date.  The new copy carries
    the same RecurRule so the pattern continues indefinitely.

    Unlike RepeatRule, the next date floats relative to when the task was
    actually done — a missed week does not pile up extra instances.

    Advanced scheduling fields mirror RepeatRule: days_of_week and
    nth_weekday work identically but are applied relative to the completion
    date rather than a fixed calendar.
    """

    interval: int
    unit: Literal["days", "weeks", "months", "years"]
    days_of_week: list[int] = field(default_factory=list)
    nth_weekday: Optional[tuple[int, int]] = None


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
    checklist: list[ChecklistItem] = field(default_factory=list)

    is_deleted: bool = False
    tags: list[str] = field(default_factory=list)
    project_id: Optional[str] = None

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
