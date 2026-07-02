from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

from models.enums.relationship_type import RelationshipType
from models.evidence import Evidence
from models.utils import parse_datetime


@dataclass
class Relationship:
    """Represents a directed link between two nodes in the Understanding Graph.

    This is a pure domain model implemented as a Python dataclass.
    """

    source_id: str
    target_id: str
    relationship_type: RelationshipType
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 1.0
    evidence: list[Evidence] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def __post_init__(self) -> None:
        """Initializes and validates the relationship."""
        self._initialized = False
        self.validate()
        self.created_at = parse_datetime(self.created_at)
        self.updated_at = parse_datetime(self.updated_at)
        self._initialized = True

    def validate(self) -> None:
        """Validates the type and value constraints of the relationship."""
        if not isinstance(self.relationship_type, RelationshipType):
            if isinstance(self.relationship_type, str):
                self.relationship_type = RelationshipType(
                    self.relationship_type.lower()
                )
            else:
                raise TypeError(
                    f"relationship_type must be an instance of RelationshipType or a valid string, got {type(self.relationship_type)}"
                )

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def __setattr__(self, name: str, value: Any) -> None:
        """Enforces immutability on identity fields after initialization."""
        if getattr(self, "_initialized", False):
            if name in ("id", "source_id", "target_id", "relationship_type"):
                raise AttributeError(
                    f"Field '{name}' is immutable after creation."
                )
        super().__setattr__(name, value)

    def add_evidence(self, quote: str, source: str) -> None:
        """Appends a new Evidence object to the evidence list and updates the timestamp."""
        if quote:
            # Avoid duplicate quotes matching both quote and source
            if not any(
                e.quote == quote and e.source == source for e in self.evidence
            ):
                self.evidence.append(Evidence(quote=quote, source=source))
                self.updated_at = datetime.now(timezone.utc)

    def update_confidence(self, delta: float) -> None:
        """Modifies the confidence score by a delta, clamping it within [0.0, 1.0]."""
        self.confidence = max(0.0, min(1.0, self.confidence + delta))
        self.updated_at = datetime.now(timezone.utc)
        self.validate()

    def to_dict(self) -> dict[str, Any]:
        """Serializes the Relationship instance to a standard Python dictionary."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship_type": self.relationship_type.value,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relationship":
        """Creates a Relationship instance from a dictionary."""
        relationship_type = data["relationship_type"]
        if isinstance(relationship_type, str):
            relationship_type = RelationshipType(relationship_type)

        evidence_list = [
            Evidence.from_dict(e) for e in data.get("evidence", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            source_id=data["source_id"],
            target_id=data["target_id"],
            relationship_type=relationship_type,
            confidence=data.get("confidence", 1.0),
            evidence=evidence_list,
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
        )
