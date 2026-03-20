from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Project:
    title: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    notes: str = ""
    folder_id: str = "today"
    position: int = 0
    deadline: Optional[date] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    area_id: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.completed_at is not None

    def complete(self) -> None:
        self.completed_at = datetime.now()
