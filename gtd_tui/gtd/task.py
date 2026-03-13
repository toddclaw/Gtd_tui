from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional
import uuid


@dataclass
class Task:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    folder_id: str = "today"
    position: int = 0
    completed_at: Optional[datetime] = None
    scheduled_date: Optional[date] = None

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def complete(self) -> None:
        self.completed_at = datetime.now()
        self.folder_id = "logbook"
