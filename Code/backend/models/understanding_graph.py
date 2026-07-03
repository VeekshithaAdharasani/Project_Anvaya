"""
Domain container representing the passive Understanding Graph structure.
This model is responsible for storing, organizing, validating, and traversing
nodes and relationships representing the user's cognitive state.

It contains zero business reasoning, agent state, or database persistence logic.
"""

import json
from typing import Dict, List, Optional, Any, Set, Callable, Iterator
import types
from datetime import datetime, timezone

from models.node import Node
from models.relationship import Relationship
from models.evidence import Evidence
from models.enums.node_type import NodeType
from models.enums.relationship_type import RelationshipType
from models.enums.validation_status import ValidationStatus


class UnderstandingGraph:
    """
    A passive domain model representing the Understanding Graph.
    Manages structural integrity, basic CRUD operations, and graph traversals.
    """

    # Constant declaration for schema and format evolution tracking
    SERIALIZATION_VERSION: int = 1

    def __init__(
        self,
        nodes: Optional[Dict[str, Node]] = None,
        relationships: Optional[Dict[str, Relationship]] = None,
    ) -> None:
        """
        Initializes the Understanding Graph with optional pre-existing nodes and relationships.

        Time Complexity: O(V + E) where V is the number of nodes, E is the number of relationships.
        Space Complexity: O(V + E) to store elements in internal dictionaries.
        """
        self._nodes: Dict[str, Node] = {}
        self._relationships: Dict[str, Relationship] = {}

        if nodes:
            for node in nodes.values():
                self.add_node(node)

        if relationships:
            for rel in relationships.values():
                self.add_relationship(rel)

    # --- Read-Only Properties ---

    @property
    def nodes(self) -> types.MappingProxyType:
        """
        Returns a read-only proxy of the nodes dictionary.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return types.MappingProxyType(self._nodes)

    @property
    def relationships(self) -> types.MappingProxyType:
        """
        Returns a read-only proxy of the relationships dictionary.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return types.MappingProxyType(self._relationships)

    # --- Pythonic Interfaces ---

    def __len__(self) -> int:
        """
        Returns the total number of nodes in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return len(self._nodes)

    def __iter__(self) -> Iterator[Node]:
        """
        Iterates over all nodes in the graph.

        Time Complexity: O(V) where V is the total number of nodes.
        Space Complexity: O(1)
        """
        return iter(self._nodes.values())

    def __contains__(self, node_id: str) -> bool:
        """
        Checks if a node with the specified ID exists in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return node_id in self._nodes

    # --- Node CRUD ---

    def add_node(self, node: Node) -> None:
        """
        Adds a new node to the graph.

        Raises:
            ValueError: If a node with the same ID already exists, or if input is invalid.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if not node or not getattr(node, "id", None):
            raise ValueError("Cannot add an invalid or identifier-less Node.")
        if node.id in self._nodes:
            raise ValueError(
                f"Duplicate Node Violation: Node with ID '{node.id}' already exists. "
                "Use update_node() to modify mutable properties on an existing node."
            )
        self._nodes[node.id] = node

    def get_node(self, node_id: str) -> Optional[Node]:
        """
        Retrieves a node by its unique identifier.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return self._nodes.get(node_id)

    def update_node(
        self,
        node_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        confidence: Optional[float] = None,
        validation_status: Optional[ValidationStatus] = None,
        evidence: Optional[List[Evidence]] = None,
    ) -> None:
        """
        Updates the mutable fields of an existing node and verifies node invariants.
        Identity fields (id, node_type) are strictly immutable.

        Raises:
            ValueError: If the node does not exist, or if properties fail validation.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        node = self._nodes.get(node_id)
        if not node:
            raise ValueError(
                f"Update Violation: Node with ID '{node_id}' does not exist in the graph."
            )
        updated=False
        if name is not None:
            node.name = name
            updated=True
        if description is not None:
            node.description = description
            updated=True
        if confidence is not None:
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(
                    f"Validation Error: Confidence {confidence} must be between 0.0 and 1.0."
                )
            node.confidence = confidence
            updated=True
        if validation_status is not None:
            node.validation_status = validation_status
            updated=True
        if evidence is not None:
            node.evidence = evidence
            updated=True

        # Keep invariants centralized inside the domain models
        node.validate()
        if updated:
            node.updated_at=datetime.now(timezone.utc)

    def remove_node(self, node_id: str) -> Optional[Node]:
        """
        Removes a node from the graph.
        Cascades deletion to any relationships connected to this node to maintain integrity.

        Time Complexity: O(E) where E is the total number of relationships in the graph.
        Space Complexity: O(E_dangling) where E_dangling represents the deleted relationships.
        """
        if node_id not in self._nodes:
            return None

        # Identify and remove all dangling relationships associated with this node
        dangling_ids = [
            rel_id
            for rel_id, rel in self._relationships.items()
            if rel.source_id == node_id or rel.target_id == node_id
        ]
        for rel_id in dangling_ids:
            self.remove_relationship(rel_id)

        return self._nodes.pop(node_id)

    def has_node(self, node_id: str) -> bool:
        """
        Checks if a node exists in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return node_id in self._nodes

    def get_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        """
        Retrieves all nodes of a specific NodeType.

        Time Complexity: O(V) where V is the total number of nodes.
        Space Complexity: O(V_type) where V_type is the number of matching nodes.
        """
        return [node for node in self._nodes.values() if node.node_type == node_type]

    # --- Query Helpers ---

    def find_node_by_name(self, name: str) -> Optional[Node]:
        """
        Finds a node using a normalized, case-insensitive comparison of the name field.

        Time Complexity: O(V) where V is the total number of nodes.
        Space Complexity: O(1)
        """
        if not name:
            return None
        target_normalized = name.strip().lower()
        for node in self._nodes.values():
            if node.name and node.name.strip().lower() == target_normalized:
                return node
        return None

    def find_nodes(self, predicate: Callable[[Node], bool]) -> List[Node]:
        """
        Retrieves all nodes matching a specific predicate filter function.

        Time Complexity: O(V) where V is the total number of nodes.
        Space Complexity: O(V_matches) where V_matches is the number of filtered nodes.
        """
        return [node for node in self._nodes.values() if predicate(node)]

    # --- Relationship CRUD ---

    def add_relationship(self, relationship: Relationship) -> None:
        """
        Adds a new directed relationship to the graph.

        Raises:
            ValueError: If the relationship ID already exists, or if the source
                        or target nodes do not exist.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if not relationship or not getattr(relationship, "id", None):
            raise ValueError("Cannot add an invalid or identifier-less Relationship.")
        if relationship.id in self._relationships:
            raise ValueError(
                f"Duplicate Relationship Violation: Relationship with ID '{relationship.id}' "
                "already exists. Use update_relationship() to modify mutable fields on an existing edge."
            )

        # Enforce referential integrity
        if not self.has_node(relationship.source_id):
            raise ValueError(
                f"Referential Integrity Violation: Source node '{relationship.source_id}' "
                f"does not exist in the graph."
            )
        if not self.has_node(relationship.target_id):
            raise ValueError(
                f"Referential Integrity Violation: Target node '{relationship.target_id}' "
                f"does not exist in the graph."
            )

        self._relationships[relationship.id] = relationship

    def get_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Retrieves a relationship by its unique identifier.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return self._relationships.get(relationship_id)

    def update_relationship(
        self,
        relationship_id: str,
        confidence: Optional[float] = None,
        evidence: Optional[List[Evidence]] = None,
    ) -> None:
        """
        Updates the mutable fields of an existing relationship and verifies relationship invariants.
        Identity fields (id, source_id, target_id, relationship_type) are strictly immutable.

        Raises:
            ValueError: If the relationship does not exist, or if validation checks fail.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        rel = self._relationships.get(relationship_id)
        if not rel:
            raise ValueError(
                f"Update Violation: Relationship with ID '{relationship_id}' does not exist in the graph."
            )

        if confidence is not None:
            if not (0.0 <= confidence <= 1.0):
                raise ValueError(
                    f"Validation Error: Confidence {confidence} must be between 0.0 and 1.0."
                )
            rel.confidence = confidence
        if evidence is not None:
            rel.evidence = evidence

        # Keep invariants centralized inside the domain models
        rel.validate()

    def remove_relationship(self, relationship_id: str) -> Optional[Relationship]:
        """
        Removes a relationship from the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return self._relationships.pop(relationship_id, None)

    def has_relationship(self, relationship_id: str) -> bool:
        """
        Checks if a relationship exists in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return relationship_id in self._relationships

    # --- Graph Traversal Utilities ---

    def get_outgoing_relationships(self, node_id: str) -> List[Relationship]:
        """
        Retrieves all relationships originating from the specified node.

        Time Complexity: O(E) where E is the total number of relationships.
        Space Complexity: O(E_out) where E_out is the number of outgoing relationships.
        """
        if not self.has_node(node_id):
            return []
        return [
            rel for rel in self._relationships.values() if rel.source_id == node_id
        ]

    def get_incoming_relationships(self, node_id: str) -> List[Relationship]:
        """
        Retrieves all relationships pointing to the specified node.

        Time Complexity: O(E) where E is the total number of relationships.
        Space Complexity: O(E_in) where E_in is the number of incoming relationships.
        """
        if not self.has_node(node_id):
            return []
        return [
            rel for rel in self._relationships.values() if rel.target_id == node_id
        ]

    def get_neighbors(self, node_id: str) -> List[Node]:
        """
        Retrieves all unique neighbor nodes directly connected to the specified node
        (either via outgoing or incoming relationships).

        Time Complexity: O(E) where E is the total number of relationships.
        Space Complexity: O(V_neighbors) where V_neighbors is the number of unique neighbor nodes.
        """
        if not self.has_node(node_id):
            return []

        neighbor_ids: Set[str] = set()

        for rel in self._relationships.values():
            if rel.source_id == node_id:
                neighbor_ids.add(rel.target_id)
            elif rel.target_id == node_id:
                neighbor_ids.add(rel.source_id)

        return [self._nodes[n_id] for n_id in neighbor_ids if n_id in self._nodes]

    # --- Structural Utilities ---

    def clear(self) -> None:
        """
        Clears all nodes and relationships from the graph.

        Time Complexity: O(V + E) where V is node count, E is relationship count.
        Space Complexity: O(1)
        """
        self._nodes.clear()
        self._relationships.clear()

    def node_count(self) -> int:
        """
        Returns the total number of nodes in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return len(self._nodes)

    def relationship_count(self) -> int:
        """
        Returns the total number of relationships in the graph.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        return len(self._relationships)

    # --- Integrity Validation ---

    def validate(self) -> bool:
        """
        Validates the integrity of the graph structure.
        Checks:
          1. Key Alignment: No dictionary keys are mismatched with node/relationship IDs.
          2. No Orphan/Dangling Relationships: Source and target nodes referenced by
             relationships exist inside the graph.
          3. Value Domains: Ensures Node and Relationship confidence is between [0.0, 1.0].
          4. Enum Validity: Verifies node_type, relationship_type, and validation_status adhere to Enums.
          5. Structural Loops: Forbids self-loops (relationships connecting a node to itself).
          6. Logic Deduplication: Verifies there are no duplicate semantic relationships
             sharing the same source, target, and relationship_type.

        Raises:
            ValueError: If any integrity constraint is violated.

        Time Complexity: O(V + E) where V is the node count and E is the relationship count.
        Space Complexity: O(E) to keep track of seen logical edges during cycle/multi-graph validation.
        """
        # 1. Validate node keys, enums, and properties
        for key, node in self._nodes.items():
            if key != node.id:
                raise ValueError(
                    f"Integrity Violation: Node dictionary key '{key}' "
                    f"does not match internal Node ID '{node.id}'."
                )
            if not isinstance(node.node_type, NodeType):
                raise ValueError(
                    f"Integrity Violation: Node '{node.id}' has invalid node_type '{node.node_type}'."
                )
            if node.confidence is not None:
                if not (0.0 <= node.confidence <= 1.0):
                    raise ValueError(
                        f"Integrity Violation: Node '{node.id}' confidence ({node.confidence}) "
                        f"is outside acceptable boundaries [0.0, 1.0]."
                    )
            if node.validation_status is not None:
                if not isinstance(node.validation_status, ValidationStatus):
                    raise ValueError(
                        f"Integrity Violation: Node '{node.id}' has invalid validation_status '{node.validation_status}'."
                    )

        # 2. Validate relationship keys, enums, loops, and duplicates
        seen_logical_relationships: Set[tuple] = set()

        for key, rel in self._relationships.items():
            if key != rel.id:
                raise ValueError(
                    f"Integrity Violation: Relationship dictionary key '{key}' "
                    f"does not match internal Relationship ID '{rel.id}'."
                )
            
            # Type and enum safety
            if not isinstance(rel.relationship_type, RelationshipType):
                raise ValueError(
                    f"Integrity Violation: Relationship '{rel.id}' has invalid "
                    f"relationship_type '{rel.relationship_type}'."
                )

            # Referential integrity checks
            if rel.source_id not in self._nodes:
                raise ValueError(
                    f"Integrity Violation: Relationship '{rel.id}' refers to a "
                    f"non-existent source node '{rel.source_id}'."
                )
            if rel.target_id not in self._nodes:
                raise ValueError(
                    f"Integrity Violation: Relationship '{rel.id}' refers to a "
                    f"non-existent target node '{rel.target_id}'."
                )

            # No self-loops
            if rel.source_id == rel.target_id:
                raise ValueError(
                    f"Integrity Violation: Forbidden self-loop detected in relationship '{rel.id}' "
                    f"connecting node '{rel.source_id}' to itself."
                )

            # Deduplicate logical edges
            logical_identity = (rel.source_id, rel.target_id, rel.relationship_type)
            if logical_identity in seen_logical_relationships:
                raise ValueError(
                    f"Integrity Violation: Duplicate logical relationship detected from '{rel.source_id}' "
                    f"to '{rel.target_id}' with type '{rel.relationship_type}'."
                )
            seen_logical_relationships.add(logical_identity)

            # Property constraints
            if rel.confidence is not None:
                if not (0.0 <= rel.confidence <= 1.0):
                    raise ValueError(
                        f"Integrity Violation: Relationship '{rel.id}' confidence ({rel.confidence}) "
                        f"is outside acceptable boundaries [0.0, 1.0]."
                    )

        return True

    # --- Serialization ---

    def to_json(self) -> str:
        """Serializes the graph to a JSON string for agent prompts and debugging."""
        return json.dumps(self.to_dict())

    def get_adjacency_list(self) -> Dict[str, Any]:
        """Returns a frontend-friendly adjacency list style representation of the graph."""
        return {
            "nodes": [
                {
                    "id": node.id,
                    "label": node.name,
                    "type": node.node_type.value,
                    "data": node.to_dict(),
                }
                for node in self._nodes.values()
            ],
            "edges": [
                {
                    "id": rel.id,
                    "source": rel.source_id,
                    "target": rel.target_id,
                    "type": rel.relationship_type.value,
                    "data": rel.to_dict(),
                }
                for rel in self._relationships.values()
            ],
        }

    def to_dict(self) -> Dict[str, Any]:
        """
        Serializes the graph structure into a standard dictionary.

        Time Complexity: O(V + E) where V is the node count and E is the relationship count.
        Space Complexity: O(V + E) to build the serialized structure.
        """
        return {
            "version": self.SERIALIZATION_VERSION,
            "nodes": [node.to_dict() for node in self._nodes.values()],
            "relationships": [rel.to_dict() for rel in self._relationships.values()],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnderstandingGraph":
        """
        Constructs an UnderstandingGraph instance from a serialized dictionary representation,
        validating structure and logic integrity rules before returning.

        Time Complexity: O(V + E) where V is the node count and E is the relationship count.
        Space Complexity: O(V + E) to allocate graph structure and child elements.
        """
        if not data:
            return cls()

        graph = cls()

        # Reconstruct nodes
        nodes_data = data.get("nodes", [])
        for node_raw in nodes_data:
            node = Node.from_dict(node_raw)
            graph.add_node(node)

        # Reconstruct relationships
        relationships_data = data.get("relationships", [])
        for rel_raw in relationships_data:
            rel = Relationship.from_dict(rel_raw)
            graph.add_relationship(rel)

        # Verify entire graph consistency prior to returning
        graph.validate()

        return graph