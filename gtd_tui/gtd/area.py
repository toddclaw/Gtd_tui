from __future__ import annotations

import uuid
from dataclasses import dataclass, field


@dataclass
class Area:
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    position: int = 0
