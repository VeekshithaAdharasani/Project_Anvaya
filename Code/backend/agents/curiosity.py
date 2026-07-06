import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from models.understanding_graph import UnderstandingGraph
from models.enums.node_type import NodeType

logger = logging.getLogger(__name__)


class CuriosityQuestion(BaseModel):
    target_node_id: Optional[str] = Field(
        None,
        description="The ID of the node this question is trying to clarify or expand upon, if applicable.",
    )
    target_relationship_type: Optional[str] = Field(
        None,
        description="The type of relationship this question is trying to uncover (e.g., 'motivates', 'requires', 'supports').",
    )
    reasoning: str = Field(
        ...,
        description="The reason why this question is being asked, explaining the gap identified in the graph.",
    )
    question_text: str = Field(
        ...,
        description="A warm, natural, and conversational question to ask the user. It must not sound clinical or like a database form. It should fit smoothly into a chat.",
    )


class CuriosityAnalysis(BaseModel):
    suggested_questions: list[CuriosityQuestion] = Field(
        default_factory=list,
        description="List of suggested questions to help fill in gaps or clarify low-confidence areas in the graph.",
    )


class CuriosityAgent:
    """
    Deterministic, rule-based Curiosity Agent.

    - Does NOT call any LLM or Gemini service.
    - Is read-only: it never modifies the graph or saves data.
    - Returns at most ONE suggestion in a CuriosityAnalysis.
    - Public API remains `analyze_graph(current_graph_json: str, recent_history: list[dict])`.
    """

    # Relationship keywords considered "supporting"
    _SUPPORTING_REL_TYPES = {
    "supports",
    "motivates",
    "requires",
}

    def __init__(self, gemini_service: Any = None) -> None:
        # Accept gemini_service only for compatibility with existing startup code.
        # It is intentionally ignored to ensure no LLM usage.
        self._ignored = gemini_service

    # Public API preserved
    def analyze_graph(
        self, 
        graph: UnderstandingGraph,
        recent_history: List[Dict[str, str]]
    ) -> CuriosityAnalysis:
        """
        Analyze the provided graph JSON and recent conversation deterministically.

        Returns at most one CuriosityQuestion according to the priority order:
          1. Low-confidence nodes (confidence < 0.6)
          2. Dreams without supporting skills/goals
          3. Goals without motivation
          4. Isolated nodes
          5. Nodes with only one evidence item
          6. Missing important relationships (e.g., goals without required skills)

        The function is defensive against malformed input and logs errors instead
        of raising, returning an empty suggestion list on failure.
        """
        all_nodes = sorted(
            graph.nodes.values(),
            key=lambda n: (n.name or "").lower(),
        )

        # Helper predicates
        def incoming_rels(node_id: str):
            try:
                return graph.get_incoming_relationships(node_id)
            except Exception:
                return []

        def outgoing_rels(node_id: str):
            try:
                return graph.get_outgoing_relationships(node_id)
            except Exception:
                return []

        def is_isolated(node_id: str) -> bool:
            return len(incoming_rels(node_id)) == 0 and len(outgoing_rels(node_id)) == 0

        def rel_types_of(rels: List[Any]) -> List[str]:
            # relationship_type may be enum or object; coerce to string values deterministically
            types = []
            for r in rels:
                try:
                    v = getattr(r, "relationship_type")
                    types.append(v.value if hasattr(v, "value") else str(v))
                except Exception:
                    # Fallback: try dict access
                    try:
                        types.append(r.get("relationship_type", ""))
                    except Exception:
                        types.append("")
            return [t.lower() for t in types if isinstance(t, str)]

        def description_text(node) -> str:
            desc = node.description or ""
            # include evidence quotes for simple heuristics
            try:
                quotes = " ".join([e.quote for e in (node.evidence or []) if hasattr(e, "quote")])
            except Exception:
                quotes = ""
            return f"{desc} {quotes}".strip()

        def has_timeline(text: str) -> bool:
            if not text:
                return False
            # Deterministic, conservative timeline detection
            patterns = [
                r"\b\d{4}\b",  # year like 2026
                r"\b(in|by|within|before|after)\b.*\b(year|month|week|day|month|years|months)\b",
                r"\b\d+\s+(years|year|months|month|weeks|weeks|days|day)\b",
            ]
            for p in patterns:
                if re.search(p, text, flags=re.IGNORECASE):
                    return True
            return False

        def has_experience_indicator(text: str) -> bool:
            if not text:
                return False
            return bool(re.search(r"\b(experience|experienced|years?|yrs|projects?)\b", text, flags=re.IGNORECASE))

        # Priority 1: Low-confidence nodes (< 0.6), deterministic ordering by confidence then name
        try:
            low_conf_nodes = sorted(
                [n for n in graph.nodes.values() if getattr(n, "confidence", None) is not None and n.confidence < 0.6],
                key=lambda n: (n.confidence if n.confidence is not None else 0.0, (n.name or "").lower()),
            )
            if low_conf_nodes:
                node = low_conf_nodes[0]
                question_text = (
                    f"I'd like to understand your experience with {node.name} a little better. "
                    f"Could you tell me more about how it fits into your journey?"
                )
                q = CuriosityQuestion(
                    target_node_id=node.id,
                    target_relationship_type=None,
                    reasoning=f"Low-confidence node detected: '{node.name}' (confidence={node.confidence:.2f}).",
                    question_text=question_text,
                )
                logger.info("CuriosityAgent: selected low-confidence node '%s'", node.name)
                return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during low-confidence check: %s", e)

        # Priority 2: Dreams without supporting skills/goals
        try:
            dreams = sorted(graph.get_nodes_by_type(NodeType.DREAM), key=lambda n: (n.name or "").lower())
            for dream in dreams:
                # Check for incoming supporting relationships OR outgoing links to goals/skills
                inc_types = rel_types_of(incoming_rels(dream.id))
                out_rels = outgoing_rels(dream.id)
                out_types = rel_types_of(out_rels)
                # Determine if there is any support/motivation or connections to skills/goals
                has_supporting = any(t in self._SUPPORTING_REL_TYPES for t in inc_types)
                has_goal_or_skill = any(
                    (graph.get_node(r.target_id).node_type == NodeType.GOAL or graph.get_node(r.target_id).node_type == NodeType.SKILL)
                    for r in out_rels
                    if graph.get_node(r.target_id) is not None
                )
                if not has_supporting and not has_goal_or_skill:
                    question_text = (
                        f"What first inspired your dream of becoming {dream.name}? "
                        "I'd love to understand what started that journey."
                    )
                    q = CuriosityQuestion(
                        target_node_id=dream.id,
                        target_relationship_type="requires",
                        reasoning=f"Dream '{dream.name}' has no supporting skills/goals connected.",
                        question_text=question_text,
                    )
                    logger.info("CuriosityAgent: selected dream without support '%s'", dream.name)
                    return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during dream-support check: %s", e)

        # Priority 3: Goals without motivation (no incoming 'motivates' or 'supports')
        try:
            goals = sorted(graph.get_nodes_by_type(NodeType.GOAL), key=lambda n: (n.name or "").lower())
            for goal in goals:
                inc_types = rel_types_of(incoming_rels(goal.id))
                if not any(t in ("motivates", "supports", "influences") for t in inc_types):
                    question_text = (
                        f"What motivates you to keep pursuing {goal.name}, even when it becomes challenging?"
                    )
                    q = CuriosityQuestion(
                        target_node_id=goal.id,
                        target_relationship_type="motivates",
                        reasoning=f"Goal '{goal.name}' lacks incoming motivation/support relationships.",
                        question_text=question_text,
                    )
                    logger.info("CuriosityAgent: selected goal without motivation '%s'", goal.name)
                    return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during goal-motivation check: %s", e)

        # Priority 4: Isolated nodes (no incoming or outgoing relationships)
        try:
            for node in all_nodes:
                if is_isolated(node.id):
                    question_text = (
                        f"How does {node.name} connect with the other parts of your journey?"
                    )
                    q = CuriosityQuestion(
                        target_node_id=node.id,
                        target_relationship_type=None,
                        reasoning=f"Isolated node detected: '{node.name}'.",
                        question_text=question_text,
                    )
                    logger.info("CuriosityAgent: selected isolated node '%s'", node.name)
                    return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during isolation check: %s", e)

        # Priority 5: Nodes with only one evidence item (ask for more evidence/context)
        try:
            for node in all_nodes:
                evidence_count = 0
                try:
                    evidence_count = len(node.evidence or [])
                except Exception:
                    # Fallback: attempt to inspect as iterable
                    try:
                        evidence_count = sum(1 for _ in (node.evidence or []))
                    except Exception:
                        evidence_count = 0
                if evidence_count <= 1:
                    question_text = (
                        f"What role does {node.name} play in your life or learning?"
                    )
                    q = CuriosityQuestion(
                        target_node_id=node.id,
                        target_relationship_type=None,
                        reasoning=f"Node '{node.name}' has only {evidence_count} evidence item(s).",
                        question_text=question_text,
                    )
                    logger.info("CuriosityAgent: selected node with sparse evidence '%s' (evidence_count=%d)", node.name, evidence_count)
                    return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during evidence-sparsity check: %s", e)

        # Priority 6: Missing important relationships (e.g., goals without required skills)
        try:
            for goal in goals:
                # Check for outgoing 'requires' relationships to SKILL nodes
                out_rels = outgoing_rels(goal.id)
                required_skill_linked = False
                for r in out_rels:
                    try:
                        rel_type = getattr(r, "relationship_type")
                        rel_val = rel_type.value if hasattr(rel_type, "value") else str(rel_type)
                        if str(rel_val).lower() == "requires":
                            target = graph.get_node(r.target_id)
                            if target and target.node_type == NodeType.SKILL:
                                required_skill_linked = True
                                break
                    except Exception:
                        continue
                if not required_skill_linked:
                    question_text = (
                        f"Which skills do you think will be most important for achieving {goal.name}?"
                    )
                    q = CuriosityQuestion(
                        target_node_id=goal.id,
                        target_relationship_type="requires",
                        reasoning=f"Goal '{goal.name}' has no outgoing 'requires' relationship to a skill.",
                        question_text=question_text,
                    )
                    logger.info("CuriosityAgent: selected goal missing required-skill relationship '%s'", goal.name)
                    return CuriosityAnalysis(suggested_questions=[q])
        except Exception as e:
            logger.exception("CuriosityAgent: error during missing-relationship check: %s", e)

        # If we reach here, no curiosity question is necessary
        logger.debug("CuriosityAgent: no gaps found; returning empty suggestion list.")
        return CuriosityAnalysis(suggested_questions=[])