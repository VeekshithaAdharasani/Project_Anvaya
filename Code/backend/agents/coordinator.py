import logging
import json
from typing import Any

from ..services.gemini_service import GeminiService
from ..services.graph_service import GraphService
from .memory import MemoryAgent
from .understanding import UnderstandingAgent
from .reflection import ReflectionAgent
from .curiosity import CuriosityAgent
from ..models.node import Node
from ..models.relationship import Relationship
from ..models.enums.node_type import NodeType
from ..models.enums.relationship_type import RelationshipType
from ..models.enums.validation_status import ValidationStatus

logger = logging.getLogger(__name__)


class CoordinatorAgent:
    """The central orchestrator of Project ANVAYA.

    Coordinates between Memory, the Understanding Layer (agents & graph),
    and generates personalized responses.
    """

    SYSTEM_INSTRUCTION = """You are the conversational interface for Project ANVAYA.
Your task is to respond to the user's latest message in a warm, supportive, and highly personalized manner, leveraging the structured understanding of their journey.

### Your Context:
* **Understanding Graph**: A structured representation of the user's dreams, goals, skills, interests, and motivations. Use this to customize your advice, suggestions, and conversation style.
* **Conversation History**: The recent dialogue context.

### Response Guidelines:
1. **Personalization**: Reference their goals, skills, or interests naturally when relevant. Do not force them into every sentence, but let them guide your perspective.
2. **Supportive Partner**: Act as a growth partner. Encourage their progress and celebrate milestones.
3. **Weave in Questions**: If a clarification or curiosity question is provided, weave it naturally into your response (usually at the end). Do not ask multiple questions; just ask the one provided.
"""

    def __init__(
        self,
        gemini_service: GeminiService,
        graph_service: GraphService,
        memory_agent: MemoryAgent,
        understanding_agent: UnderstandingAgent,
        reflection_agent: ReflectionAgent,
        curiosity_agent: CuriosityAgent,
    ):
        self.gemini_service = gemini_service
        self.graph_service = graph_service
        self.memory_agent = memory_agent
        self.understanding_agent = understanding_agent
        self.reflection_agent = reflection_agent
        self.curiosity_agent = curiosity_agent

    def process_message(self, session_id: str, user_message: str) -> str:
        """Processes an incoming user message through the entire multi-agent pipeline

        and returns the final personalized response.
        """
        logger.info(f"Processing message for session '{session_id}'...")

        # 1. Save user message in Memory
        self.memory_agent.add_message(session_id, "user", user_message)

        # 2. Retrieve context
        history = self.memory_agent.get_messages(session_id, limit=15)
        graph = self.graph_service.get_graph(session_id)
        current_graph_json = graph.to_json()

        # 3. Extract proposed updates (Understanding Agent)
        proposed_extraction = self.understanding_agent.analyze_conversation(
            user_message=user_message,
            history=history[:-1],  # Exclude the message we just added to prevent duplicate analysis
            current_graph_json=current_graph_json,
        )

        # Convert proposed extraction to JSON string for the Reflection Agent
        proposed_updates_json = json.dumps(
            proposed_extraction.model_dump(), indent=2
        )

        # 4. Validate proposed updates (Reflection Agent)
        reflection_evaluation = self.reflection_agent.evaluate_updates(
            proposed_updates_json=proposed_updates_json,
            current_graph_json=current_graph_json,
            recent_history=history,
        )

        # 5. Apply approved/modified updates to the Understanding Graph
        # We maintain a mapping of temporary IDs (or names) of newly created nodes
        # to their generated UUIDs so that relationships can be correctly linked.
        id_mapping: dict[str, str] = {}
        clarification_question: str | None = None

        # A. Process Nodes
        for eval_node in reflection_evaluation.evaluated_nodes:
            if eval_node.action in ("approve", "modify"):
                # If it's an update to an existing node
                if eval_node.id and eval_node.id in graph.nodes:
                    existing_node = graph.get_node(eval_node.id)
                    if existing_node:
                        # Find the corresponding proposed node to get the new description/evidence
                        proposed = next(
                            (
                                n
                                for n in proposed_extraction.proposed_nodes
                                if n.id == eval_node.id
                            ),
                            None,
                        )
                        desc = (
                            proposed.description
                            if proposed
                            else existing_node.description
                        )
                        quote = (
                            proposed.evidence_quote if proposed else user_message
                        )

                        # Update fields
                        graph.update_node(
                            eval_node.id,
                            description=desc,
                            confidence=eval_node.adjusted_confidence,
                            validation_status=ValidationStatus.INFERRED,
                        )
                        existing_node.add_evidence(quote, source=session_id)
                        id_mapping[eval_node.id] = eval_node.id
                else:
                    # It's a newly proposed node
                    # Find the proposed details by matching the name
                    proposed = next(
                        (
                            n
                            for n in proposed_extraction.proposed_nodes
                            if n.name == eval_node.name
                        ),
                        None,
                    )
                    desc = (
                        proposed.description
                        if proposed
                        else f"Inferred {eval_node.name}"
                    )
                    quote = (
                        proposed.evidence_quote if proposed else user_message
                    )

                    new_node = Node(
                        node_type=NodeType(eval_node.node_type),
                        name=eval_node.name,
                        description=desc,
                        confidence=eval_node.adjusted_confidence,
                        validation_status=ValidationStatus.INFERRED,
                    )
                    new_node.add_evidence(quote, source=session_id)
                    graph.add_node(new_node)

                    # Map both the proposed ID (if any) and name to the new UUID
                    if proposed and proposed.id:
                        id_mapping[proposed.id] = new_node.id
                    id_mapping[eval_node.name] = new_node.id

                # Capture clarification question if the Reflection Agent raised one
                if (
                    eval_node.suggested_clarification
                    and not clarification_question
                ):
                    clarification_question = eval_node.suggested_clarification

        # B. Process Relationships
        for eval_rel in reflection_evaluation.evaluated_relationships:
            if eval_rel.action in ("approve", "modify"):
                # Resolve source and target IDs (mapping temp IDs/names to UUIDs if needed)
                source_id = id_mapping.get(
                    eval_rel.source_node_id, eval_rel.source_node_id
                )
                target_id = id_mapping.get(
                    eval_rel.target_node_id, eval_rel.target_node_id
                )

                # Verify both nodes exist in the graph before creating the edge
                if source_id in graph.nodes and target_id in graph.nodes:
                    # Check if a relationship between these two nodes already exists
                    existing_rel = next(
                        (
                            r
                            for r in graph.relationships.values()
                            if r.source_id == source_id
                            and r.target_id == target_id
                            and r.relationship_type.value
                            == eval_rel.relationship_type
                        ),
                        None,
                    )

                    proposed = next(
                        (
                            r
                            for r in proposed_extraction.proposed_relationships
                            if r.source_node_id == eval_rel.source_node_id
                            and r.target_node_id == eval_rel.target_node_id
                            and r.relationship_type == eval_rel.relationship_type
                        ),
                        None,
                    )
                    quote = (
                        proposed.evidence_quote if proposed else user_message
                    )

                    if existing_rel:
                        # Update existing relationship
                        graph.update_relationship(
                            existing_rel.id,
                            confidence=eval_rel.adjusted_confidence,
                        )
                        existing_rel.add_evidence(quote, source=session_id)
                    else:
                        # Create a new relationship
                        new_rel = Relationship(
                            source_id=source_id,
                            target_id=target_id,
                            relationship_type=RelationshipType(
                                eval_rel.relationship_type
                            ),
                            confidence=eval_rel.adjusted_confidence,
                        )
                        new_rel.add_evidence(quote, source=session_id)
                        graph.add_relationship(new_rel)

        # 6. Curiosity Analysis (if no urgent clarification from Reflection)
        question_to_ask: str | None = clarification_question
        if not question_to_ask:
            curiosity_analysis = self.curiosity_agent.analyze_graph(
                current_graph_json=graph.to_json(),
                recent_history=history,
            )
            if curiosity_analysis.suggested_questions:
                # Select the highest priority curiosity question
                question_to_ask = curiosity_analysis.suggested_questions[
                    0
                ].question_text

        # 7. Generate Personalized Response
        history_str = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        prompt = f"""### Current Understanding Graph (JSON)
{graph.to_json()}

### Recent Conversation History
{history_str}
User's Latest Message: {user_message}
"""
        if question_to_ask:
            prompt += f"\n### Instruction\nGenerate your response. You must naturally weave in the following question at the end: \"{question_to_ask}\"\n"

        logger.info("Generating personalized response via Gemini...")
        response_text = self.gemini_service.generate_text(
            prompt=prompt,
            system_instruction=self.SYSTEM_INSTRUCTION,
            temperature=0.7,
        )

        # 8. Save assistant response in Memory
        self.memory_agent.add_message(session_id, "assistant", response_text)

        # 9. Persist the updated graph
        self.graph_service.save_graph(session_id)

        logger.info(f"Processing complete for session '{session_id}'.")
        return response_text
