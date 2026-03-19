from __future__ import annotations

import uuid
from dataclasses import dataclass, field

REFERENCE_FOLDER_ID: str = "reference"

BUILTIN_FOLDER_IDS: frozenset[str] = frozenset(
    {"inbox", "today", "upcoming", "waiting_on", "someday", "logbook", "reference"}
)


@dataclass
class Folder:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position: int = 0
