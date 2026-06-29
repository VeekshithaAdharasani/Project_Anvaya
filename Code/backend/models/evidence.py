from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from .utils import parse_datetime


@dataclass
class Evidence:
    """Represents a piece of supporting evidence for a node or relationship in the Understanding Graph.

    This is a pure domain model implemented as a Python dataclass.
    """

    quote: str
    source: str  # e.g., "conversation_id", "user_direct", "reflection_agent"
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        self.timestamp = parse_datetime(self.timestamp)

    def to_dict(self) -> dict[str, Any]:
        """Serializes the Evidence instance to a standard Python dictionary."""
        return {
            "quote": self.quote,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Evidence":
        """Creates an Evidence instance from a dictionary."""
        return cls(
            quote=data["quote"],
            source=data["source"],
            timestamp=parse_datetime(data.get("timestamp")),
        )
