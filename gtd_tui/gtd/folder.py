from __future__ import annotations

import uuid
from dataclasses import dataclass, field

BUILTIN_FOLDER_IDS: frozenset[str] = frozenset({"today", "waiting_on", "logbook"})


@dataclass
class Folder:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position: int = 0
