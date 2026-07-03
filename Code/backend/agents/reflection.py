"""
Agent module responsible for structured validation and gating inside the Reflection Layer.
Reviews proposed graph updates against existing state and interaction histories to detect
contradictions, filter emotional states, and recommend confidence levels.
"""

from agents.understanding import UnderstandingProposal, ProposedNode, ProposedRelationship
# TODO: After MVP, move these shared proposal models into a common models module.
import json
import logging
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from services.gemini_service import GeminiService, GeminiConfigurationError
from models.enums.node_type import NodeType
from models.enums.relationship_type import RelationshipType

logger = logging.getLogger(__name__)


class EvaluatedNode(BaseModel):
    """Pydantic representation of an evaluated node update."""
    id: str | None = Field(
        None,
        description="The ID of the node if it was an update to an existing node.",
    )
    node_type: NodeType = Field(..., description="The type category of the node.")
    name: str = Field(..., description="The name of the node.")
    action: Literal["approve", "reject", "modify"] = Field(
        ...,
        description="The validation decision. 'approve' commits it, 'reject' discards it, 'modify' updates attributes (like confidence or description) before committing.",
    )
    reasoning: str = Field(
        ...,
        description="The reason for this decision, referencing recent history or contradictions in the graph.",
    )
    adjusted_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The recommended confidence score (0.0 to 1.0). Set lower (e.g. 0.3 - 0.5) if the user seems uncertain, frustrated, or exploring. Set higher (e.g. 0.8 - 0.9) for firm statements.",
    )
    suggested_clarification: str | None = Field(
        None,
        description="If there is a contradiction or high uncertainty, write a natural question to ask the user for clarification.",
    )


class EvaluatedRelationship(BaseModel):
    """Pydantic representation of an evaluated relationship link update."""
    source_node_id: str = Field(..., description="ID of the source node.")
    target_node_id: str = Field(..., description="ID of the target node.")
    relationship_type: RelationshipType = Field(..., description="Type of the relationship link.")
    action: Literal["approve", "reject", "modify"] = Field(
        ..., description="The validation decision."
    )
    reasoning: str = Field(..., description="The reason for this decision.")
    adjusted_confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="The recommended confidence score (0.0 to 1.0).",
    )


class ReflectionEvaluation(BaseModel):
    """Structured evaluation representation detailing actions for nodes and relationships."""
    evaluated_nodes: list[EvaluatedNode] = Field(default_factory=list)
    evaluated_relationships: list[EvaluatedRelationship] = Field(
        default_factory=list
    )


# --- Custom Exception Classes ---

class ReflectionAgentError(Exception):
    """Base domain exception for the Reflection Agent."""
    pass


class ReflectionError(ReflectionAgentError):
    """Raised when structured generation, API calls, or parsing processes fail."""
    pass

class ReflectionAgent:
    """
    The gatekeeper of the Understanding Layer.
    Validates proposed graph updates against the current graph state and
    conversation history. Detects contradictions, filters out temporary emotional
    states, and recommends confidence adjustments.
    """
    CONFIDENCE_APPROVED = 0.85
    CONFIDENCE_NEEDS_REVIEW = 0.55
    CONFIDENCE_LOW = 0.40
    CONFIDENCE_REJECTED = 0.0
    # Embedded instruction set containing instructions for gating operations
    DEFAULT_SYSTEM_INSTRUCTION: str = """You are the Reflection Agent for the Understanding Layer of Project ANVAYA.
Your role is to act as a critical gatekeeper. You review the changes proposed by the Understanding Agent and decide whether to approve, reject, or modify them.

### Your Evaluation Criteria:
1. **Contradiction Detection**: Compare the proposed updates with the current graph. If a proposed node directly contradicts an existing node (e.g. the user says "I hate programming" but the graph says they want to be a "Software Engineer"), you must flag it.
   - If it is a contradiction, you can **reject** it, or **modify** it with a very low confidence score (e.g. 0.2) and suggest a `suggested_clarification` question.
2. **Stability vs. Temporary Emotion**: Determine if the user's statement represents a genuine, long-term change or a temporary emotional state (e.g., frustration, venting, passing curiosity).
   - If a user says "I want to quit my job" during a single frustrated rant, do NOT immediately delete their career goals. Instead, **modify** the update to have a low confidence score, or **reject** it until more stable evidence appears.
   - If the user explicitly confirms a change over multiple turns, **approve** it with high confidence.
3. **Evidence Strength**: Verify if the proposed `evidence_quote` is strong. If the quote is weak or ambiguous, lower the `adjusted_confidence`.
4. **Action Types**:
   - `approve`: The proposed node/relationship is stable, consistent, and has good evidence.
   - `reject`: The proposal is a hallucination, a duplicate, or a highly unstable temporary emotion that shouldn't affect the graph.
   - `modify`: The proposal is valid but needs its confidence score adjusted, its description refined, or needs user clarification.

### OUTPUT FORMAT (VERY IMPORTANT)

Return ONLY valid JSON.

The top-level object MUST have exactly these two fields:

{
  "evaluated_nodes": [
    {
      "id": null,
      "node_type": "dream",
      "name": "...",
      "action": "approve",
      "reasoning": "...",
      "adjusted_confidence": 0.95,
      "suggested_clarification": null
    }
  ],
  "evaluated_relationships": [
    {
      "source_node_id": "...",
      "target_node_id": "...",
      "relationship_type": "supports",
      "action": "approve",
      "reasoning": "...",
      "adjusted_confidence": 0.95
    }
  ]
}

Do NOT use keys such as:
- approved_nodes
- approved_relationships
- nodes
- relationships

Use ONLY:

- evaluated_nodes
- evaluated_relationships
   """

    def __init__(
        self,
        gemini_service: GeminiService,
        prompt_path: str | None = None,
    ) -> None:
        """
        Initializes the agent, loading prompt instructions from the specified path.
        """
        self.gemini_service: GeminiService = gemini_service

        if prompt_path:
            self.prompt_path: Path = Path(prompt_path)
        else:
            self.prompt_path = (
                Path(__file__).parent.parent
                / "prompts"
                / "reflection_system_prompt.txt"
            )

        self.system_instruction: str = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """
        Loads the system instruction from the filesystem, falling back to embedded prompt configuration on failure.
        """
        if self.prompt_path.exists():
            try:
                return self.prompt_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning(
                    f"Configuration Warning: Failed to load system prompt from '{self.prompt_path}': {e}. "
                    "Using default fallback system instructions."
                )
        return self.DEFAULT_SYSTEM_INSTRUCTION

    def _validate_inputs(
        self,
        session_id: str,
        proposed_updates_json: str,
        current_graph_json: str,
        recent_history: list[dict[str, str]],
    ) -> None:
        """
        Validates all input structures and raises clear ValueErrors on failure.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("Validation Error: 'session_id' must be a non-empty string.")

        if not isinstance(proposed_updates_json, str) or not proposed_updates_json.strip():
            raise ValueError("Validation Error: 'proposed_updates_json' must be a non-empty string.")

        if not isinstance(current_graph_json, str) or not current_graph_json.strip():
            raise ValueError("Validation Error: 'current_graph_json' must be a non-empty string.")

        if not isinstance(recent_history, list):
            raise ValueError("Validation Error: 'recent_history' must be a list of message objects.")

        for idx, msg in enumerate(recent_history):
            if not isinstance(msg, dict):
                raise ValueError(f"Validation Error: Message at index {idx} in recent_history is not a dict.")
            if "role" not in msg or "content" not in msg:
                raise ValueError(
                    f"Validation Error: Message at index {idx} in recent_history is missing 'role' or 'content' keys."
                )
            if not msg["role"] or not msg["content"]:
                raise ValueError(
                    f"Validation Error: Message at index {idx} in recent_history contains empty fields."
                )

        # Confirm JSON syntax correctness
        try:
            json.loads(proposed_updates_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Validation Error: 'proposed_updates_json' is not syntactically valid JSON: {e}")

        try:
            json.loads(current_graph_json)
        except json.JSONDecodeError as e:
            raise ValueError(f"Validation Error: 'current_graph_json' is not syntactically valid JSON: {e}")

    def _build_prompt(
        self,
        proposed_updates_json: str,
        current_graph_json: str,
        recent_history: list[dict[str, str]],
    ) -> str:
        """
        Assembles the evaluation instruction prompt.
        """
        history_str = "\n".join(
            f"{'User' if m['role']=='user' else 'Assistant'}: {m['content']}"
            for m in recent_history
        )

        return f"""### Current Understanding Graph (JSON State)
{current_graph_json}

### Recent Conversation History
{history_str}

### Proposed Graph Updates
{proposed_updates_json}

### Instructions
Evaluate each proposed node and relationship. Determine if they should be approved, rejected, or modified. Align confidence scores and suggest clarification questions where there is uncertainty.
"""
    def _build_history_text(self, recent_history: list[dict[str, str]]) -> str:
        return "\n".join(
            msg.get("content", "")
            for msg in recent_history
            if isinstance(msg.get("content"), str)
        )

    def _clamp_confidence(self, value: float) -> float:
        return max(0.0, min(1.0, value))

    def _evidence_is_present(self, evidence_quote: str, history_text: str) -> bool:
        if not evidence_quote or not isinstance(evidence_quote, str):
            return False
        return evidence_quote.strip() in history_text

    def _evaluate_node(
        self,
        node: ProposedNode,
        history_text: str,
    ) -> EvaluatedNode:
        if not node.name.strip():
            return EvaluatedNode(
                id=node.id,
                node_type=node.node_type,
                name=node.name,
                action="reject",
                reasoning="The proposed node is missing a non-empty name.",
                adjusted_confidence=self.CONFIDENCE_REJECTED,
                suggested_clarification="Please provide a clear name for the proposed concept.",
            )

        if not node.evidence_quote.strip():
            return EvaluatedNode(
                id=node.id,
                node_type=node.node_type,
                name=node.name,
                action="modify",
                reasoning="The proposed node is missing an evidence quote.",
                adjusted_confidence=self.CONFIDENCE_LOW,
                suggested_clarification="Can you point to the part of the conversation that supports this proposed concept?",
            )

        if not self._evidence_is_present(node.evidence_quote, history_text):
            return EvaluatedNode(
                id=node.id,
                node_type=node.node_type,
                name=node.name,
                action="modify",
                reasoning="The evidence quote was not found in recent conversation history.",
                adjusted_confidence=self.CONFIDENCE_NEEDS_REVIEW,
                suggested_clarification="Please confirm where that evidence appears in the conversation.",
            )

        return EvaluatedNode(
            id=node.id,
            node_type=node.node_type,
            name=node.name,
            action="approve",
            reasoning="The proposed node is structurally valid and has valid evidence in history.",
            adjusted_confidence=self.CONFIDENCE_APPROVED,
            suggested_clarification=None,
        )

    def _evaluate_relationship(
        self,
        relationship: ProposedRelationship,
        history_text: str,
    ) -> EvaluatedRelationship:
        if not relationship.source_node_id or not relationship.target_node_id:
            return EvaluatedRelationship(
                source_node_id=relationship.source_node_id or "",
                target_node_id=relationship.target_node_id or "",
                relationship_type=relationship.relationship_type,
                action="reject",
                reasoning="The proposed relationship is missing a source or target identifier.",
                adjusted_confidence=self.CONFIDENCE_REJECTED,
            )

        if relationship.source_node_id == relationship.target_node_id:
            return EvaluatedRelationship(
                source_node_id=relationship.source_node_id,
                target_node_id=relationship.target_node_id,
                relationship_type=relationship.relationship_type,
                action="reject",
                reasoning="A relationship cannot connect a node to itself.",
                adjusted_confidence=self.CONFIDENCE_REJECTED,
            )

        if not relationship.evidence_quote.strip():
            return EvaluatedRelationship(
                source_node_id=relationship.source_node_id,
                target_node_id=relationship.target_node_id,
                relationship_type=relationship.relationship_type,
                action="modify",
                reasoning="The proposed relationship is missing an evidence quote.",
                adjusted_confidence=self.CONFIDENCE_LOW,
            )

        if not self._evidence_is_present(relationship.evidence_quote, history_text):
            return EvaluatedRelationship(
                source_node_id=relationship.source_node_id,
                target_node_id=relationship.target_node_id,
                relationship_type=relationship.relationship_type,
                action="modify",
                reasoning="The evidence quote was not found in recent conversation history.",
                adjusted_confidence=self.CONFIDENCE_NEEDS_REVIEW,
            )

        return EvaluatedRelationship(
            source_node_id=relationship.source_node_id,
            target_node_id=relationship.target_node_id,
            relationship_type=relationship.relationship_type,
            action="approve",
            reasoning="The proposed relationship is structurally valid and has valid evidence in history.",
            adjusted_confidence=self.CONFIDENCE_APPROVED,
        )

    def evaluate_updates(
        self,
        proposed_updates_json: str,
        current_graph_json: str,
        recent_history: list[dict[str, str]],
        session_id: str = "default_session",
    ) -> ReflectionEvaluation:
        """
        Evaluates proposed changes against historical interactions and current graph representation.
        Returns a ReflectionEvaluation decision block without altering graph storage states.
        """
        start_time = time.perf_counter()
        try:
            self._validate_inputs(
                session_id=session_id,
                proposed_updates_json=proposed_updates_json,
                current_graph_json=current_graph_json,
                recent_history=recent_history,
            )
            _ = current_graph_json  # Intentionally unused during Phase 1 for compatibility
            try:
                proposal = UnderstandingProposal.model_validate_json(proposed_updates_json)
            except Exception as e:
                raise ValueError(
                    f"Validation Error: Could not parse proposed_updates_json: {e}"
                ) from e
            history_text = self._build_history_text(recent_history)
            evaluation = ReflectionEvaluation()
            for node in proposal.proposed_nodes:
                evaluation.evaluated_nodes.append(self._evaluate_node(node, history_text))
            for relationship in proposal.proposed_relationships:
                evaluation.evaluated_relationships.append(
                    self._evaluate_relationship(relationship, history_text)
                )
            latency = time.perf_counter() - start_time
            node_stats = {"approve": 0, "reject": 0, "modify": 0}
            for n in evaluation.evaluated_nodes:
                node_stats[n.action] = node_stats.get(n.action, 0) + 1
            rel_stats = {"approve": 0, "reject": 0, "modify": 0}
            for r in evaluation.evaluated_relationships:
                rel_stats[r.action] = rel_stats.get(r.action, 0) + 1
            logger.info(
                "Evaluation completed for session '%s' in %.3fs. "
                "Nodes: Approved=%d, Rejected=%d, Modified=%d | "
                "Relationships: Approved=%d, Rejected=%d, Modified=%d.",
                session_id,
                latency,
                node_stats["approve"],
                node_stats["reject"],
                node_stats["modify"],
                rel_stats["approve"],
                rel_stats["reject"],
                rel_stats["modify"],
            )
            
            return evaluation
        except ValueError as ve:
            raise
        except Exception as e:
            latency = time.perf_counter() - start_time
            logger.exception(
                f"Evaluation Failure: Reflection evaluation failed for session '{session_id}' "
                f"after {latency:.3f}s: {e}"
            )
            raise ReflectionError(
                f"Reflection evaluation failed for session '{session_id}': {e}"
            ) from e