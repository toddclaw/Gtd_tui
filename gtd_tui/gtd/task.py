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
class Task:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    folder_id: str = "today"
    position: int = 0
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[date] = None
    repeat_rule: Optional[RepeatRule] = None

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def complete(self) -> None:
        self.completed_at = datetime.now()
        self.folder_id = "logbook"
