from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
from typing import Any

from .enums.node_type import NodeType
from .enums.validation_status import ValidationStatus
from .evidence import Evidence
from .utils import parse_datetime


@dataclass
class Node:
    """Represents a single understanding concept about the user in the Understanding Graph.

    This is a pure domain model implemented as a Python dataclass.
    """

    node_type: NodeType
    name: str
    description: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    confidence: float = 1.0
    evidence: list[Evidence] = field(default_factory=list)
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    validation_status: ValidationStatus = ValidationStatus.INFERRED

    def __post_init__(self) -> None:
        """Initializes and validates the node."""
        self._initialized = False
        self.validate()
        self.created_at = parse_datetime(self.created_at)
        self.updated_at = parse_datetime(self.updated_at)
        self._initialized = True

    def validate(self) -> None:
        """Validates the type and value constraints of the node."""
        if not isinstance(self.node_type, NodeType):
            if isinstance(self.node_type, str):
                self.node_type = NodeType(self.node_type.lower())
            else:
                raise TypeError(
                    f"node_type must be an instance of NodeType or a valid string, got {type(self.node_type)}"
                )

        if not isinstance(self.validation_status, ValidationStatus):
            if isinstance(self.validation_status, str):
                self.validation_status = ValidationStatus(
                    self.validation_status.lower()
                )
            else:
                raise TypeError(
                    f"validation_status must be an instance of ValidationStatus or a valid string, got {type(self.validation_status)}"
                )

        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(
                f"Confidence must be between 0.0 and 1.0, got {self.confidence}"
            )

    def __setattr__(self, name: str, value: Any) -> None:
        """Enforces immutability on identity fields after initialization."""
        if getattr(self, "_initialized", False):
            if name in ("id", "node_type"):
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
        """Serializes the Node instance to a standard Python dictionary."""
        return {
            "id": self.id,
            "node_type": self.node_type.value,
            "name": self.name,
            "description": self.description,
            "confidence": self.confidence,
            "evidence": [e.to_dict() for e in self.evidence],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "validation_status": self.validation_status.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Node":
        """Creates a Node instance from a dictionary."""
        node_type = data["node_type"]
        if isinstance(node_type, str):
            node_type = NodeType(node_type)

        validation_status = data.get("validation_status", "inferred")
        if isinstance(validation_status, str):
            validation_status = ValidationStatus(validation_status)

        evidence_list = [
            Evidence.from_dict(e) for e in data.get("evidence", [])
        ]

        return cls(
            id=data.get("id", str(uuid.uuid4())),
            node_type=node_type,
            name=data["name"],
            description=data["description"],
            confidence=data.get("confidence", 1.0),
            evidence=evidence_list,
            created_at=parse_datetime(data.get("created_at")),
            updated_at=parse_datetime(data.get("updated_at")),
            validation_status=validation_status,
        )
