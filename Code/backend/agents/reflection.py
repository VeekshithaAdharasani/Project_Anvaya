import logging
from typing import Optional, Literal
from pydantic import BaseModel, Field

from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class EvaluatedNode(BaseModel):
    id: Optional[str] = Field(
        None,
        description="The ID of the node if it was an update to an existing node.",
    )
    node_type: str = Field(..., description="The type of the node.")
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
        description="The recommended confidence score (0.0 to 1.0). Set lower (e.g. 0.3 - 0.5) if the user seems uncertain, frustrated, or exploring. Set higher (e.g. 0.8 - 0.9) for firm statements.",
    )
    suggested_clarification: Optional[str] = Field(
        None,
        description="If there is a contradiction or high uncertainty, write a natural question to ask the user for clarification.",
    )


class EvaluatedRelationship(BaseModel):
    source_node_id: str = Field(..., description="ID of the source node.")
    target_node_id: str = Field(..., description="ID of the target node.")
    relationship_type: str = Field(..., description="Type of the relationship.")
    action: Literal["approve", "reject", "modify"] = Field(
        ..., description="The validation decision."
    )
    reasoning: str = Field(..., description="The reason for this decision.")
    adjusted_confidence: float = Field(
        ..., description="The recommended confidence score (0.0 to 1.0)."
    )


class ReflectionEvaluation(BaseModel):
    evaluated_nodes: list[EvaluatedNode] = Field(default_factory=list)
    evaluated_relationships: list[EvaluatedRelationship] = Field(
        default_factory=list
    )


class ReflectionAgent:
    """The gatekeeper of the Understanding Layer.

    Validates proposed graph updates against the current graph state and
    conversation history. Detects contradictions, filters out temporary emotional
    states, and recommends confidence adjustments.
    """

    SYSTEM_INSTRUCTION = """You are the Reflection Agent for the Understanding Layer of Project ANVAYA.
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
"""

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    def evaluate_updates(
        self,
        proposed_updates_json: str,
        current_graph_json: str,
        recent_history: list[dict[str, str]],
    ) -> ReflectionEvaluation:
        """Evaluates the proposed updates against the current graph state and recent history."""
        # Format history
        history_str = ""
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        prompt = f"""### Current Understanding Graph (JSON State)
{current_graph_json}

### Recent Conversation History
{history_str}

### Proposed Graph Updates
{proposed_updates_json}

### Instructions
Evaluate each proposed node and relationship. Determine if they should be approved, rejected, or modified. Align confidence scores and suggest clarification questions where there is uncertainty.
"""
        logger.info("Sending updates to Reflection Agent for evaluation...")
        try:
            evaluation = self.gemini_service.generate_json(
                prompt=prompt,
                response_schema=ReflectionEvaluation,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.1,  # Low temperature for analytical validation
            )
            logger.info(
                f"Reflection complete. Evaluated {len(evaluation.evaluated_nodes)} nodes and {len(evaluation.evaluated_relationships)} relationships."
            )
            return evaluation
        except Exception as e:
            logger.error(f"Failed to evaluate updates: {e}")
            raise
