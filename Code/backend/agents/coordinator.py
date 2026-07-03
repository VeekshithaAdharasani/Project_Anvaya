import logging
import json
from typing import Any
from datetime import datetime, timezone

from services.gemini_service import GeminiService
from services.graph_service import GraphService
from agents.memory import MemoryAgent
from agents.understanding import UnderstandingAgent
from agents.reflection import ReflectionAgent
from agents.curiosity import CuriosityAgent
from models.node import Node
from models.relationship import Relationship
from models.enums.node_type import NodeType
from models.enums.relationship_type import RelationshipType
from models.enums.validation_status import ValidationStatus
from models.understanding_graph import UnderstandingGraph
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """
You are the conversational interface for Project ANVAYA.

Your task is to respond to the user's latest message in a warm, supportive, and highly personalized manner.

(keep the same prompt here)
"""

class CoordinatorAgent:
    """The central orchestrator of Project ANVAYA.

    Coordinates between Memory, the Understanding Layer (agents & graph),
    and generates personalized responses.
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
        self.prompt_path = (
            Path(__file__).parent.parent
            / "prompts"
            / "coordinator_system_prompt.txt"
        )
        self.system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """Loads the coordinator system prompt from disk."""
        try:
            return self.prompt_path.read_text(encoding="utf-8")
        except Exception:
            logger.warning(
                "Failed to load coordinator prompt file. Using embedded default."
            )
            return DEFAULT_SYSTEM_PROMPT
    def _normalize_node_name(self, name: str) -> str:
        """Normalizes node names for deterministic entity resolution."""
        if not isinstance(name, str):
            return ""
        return " ".join(name.lower().split())
    
    def _find_existing_node(
        self,
        graph: UnderstandingGraph,
        node_type: NodeType,
        name: str,
    ) -> Node | None:
        normalized_target = self._normalize_node_name(name)
        logger.info(
            "Searching for node '%s' (%s)",
            normalized_target,
            node_type,
        )
        for candidate in graph.nodes.values():
            logger.info(
                "Candidate: '%s' (%s)",
                self._normalize_node_name(candidate.name),
                candidate.node_type,
            )
            if (
                candidate.node_type == node_type
                and self._normalize_node_name(candidate.name) == normalized_target
            ):
                logger.info("MATCH FOUND: %s", candidate.id)
                return candidate
        logger.info("NO MATCH FOUND")
        return None    

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
        try:
            proposed_extraction = self.understanding_agent.analyze_conversation(
                session_id=session_id,
                user_message=user_message,
                history=history[:-1],
                current_graph_json=current_graph_json,
            )
        except Exception:
            # No Gemini available
            self.memory_agent.add_message(
                session_id,
                "assistant",
                "I'm currently unable to analyze new information because the AI service has reached its quota. Please try again later."
            )
            return "I'm currently unable to analyze new information because the AI service has reached its quota. Please try again later."

        # Convert proposed extraction to JSON string for the Reflection Agent
        proposed_updates_json = proposed_extraction.model_dump_json(indent=2)

        # 4. Validate proposed updates (Reflection Agent)
        try:
            reflection_evaluation = self.reflection_agent.evaluate_updates(
                proposed_updates_json=proposed_updates_json,
                current_graph_json=current_graph_json,
                recent_history=history,
            )
        except Exception as e:
            logger.warning(f"Skipping Reflection Agent: {e}")
            from agents.reflection import (
                ReflectionEvaluation,
                EvaluatedNode,
                EvaluatedRelationship,
            )
            reflection_evaluation = ReflectionEvaluation(
                evaluated_nodes=[
                    EvaluatedNode(
                        id=node.id,
                        node_type=node.node_type,
                        name=node.name,
                        action="approve",
                        reasoning="Reflection skipped because Gemini quota exceeded.",
                        adjusted_confidence=0.95,
                        suggested_clarification=None,
                    )
                    for node in proposed_extraction.proposed_nodes
                ],
                evaluated_relationships=[
                    EvaluatedRelationship(
                        source_node_id=rel.source_node_id,
                        target_node_id=rel.target_node_id,
                        relationship_type=rel.relationship_type,
                        action="approve",
                        reasoning="Reflection skipped because Gemini quota exceeded.",
                        adjusted_confidence=0.95,
                    )
                for rel in proposed_extraction.proposed_relationships
            ],
        )

        # 5. Apply approved/modified updates to the Understanding Graph
        # We maintain a mapping of proposed node IDs to canonical graph node IDs.
        resolved_node_ids: dict[str, str] = {}
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
                        
                        resolved_node_ids[eval_node.id] = eval_node.id
                        if proposed and proposed.id:
                            resolved_node_ids[proposed.id] = eval_node.id
                else:
                    # It's a newly proposed node
                    # Search the existing graph for the same node_type + normalized name
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
                    existing_node = self._find_existing_node(
                        graph,
                        NodeType(eval_node.node_type),
                        eval_node.name,
                    )

                    if existing_node:
                        if eval_node.id:
                            resolved_node_ids[eval_node.id] = existing_node.id
                        if proposed and proposed.id:
                            resolved_node_ids[proposed.id] = existing_node.id

                        old_confidence = existing_node.confidence
                        update_kwargs: dict[str, Any] = {}

                        old_desc = existing_node.description or ""
                        if len(desc.strip()) > len(old_desc.strip()):
                            update_kwargs["description"] = desc

                        new_confidence = max(
                            existing_node.confidence,
                            eval_node.adjusted_confidence,
                        )
                        if new_confidence != existing_node.confidence:
                            update_kwargs["confidence"] = new_confidence

                        if update_kwargs:
                            graph.update_node(existing_node.id, **update_kwargs)

                        evidence_count_before = len(existing_node.evidence)
                        existing_node.add_evidence(quote, source=session_id)
                        evidence_count_after = len(existing_node.evidence)

                        logger.info(
                            "Resolved existing node '%s' (%s) for proposed node id '%s'.",
                            existing_node.name,
                            existing_node.id,
                            eval_node.id,
                        )
                        if "description" in update_kwargs:
                            logger.info(
                                "Updated description for existing node '%s' (%s).",
                                existing_node.name,
                                existing_node.id,
                            )
                        if "confidence" in update_kwargs:
                            logger.info(
                                "Updated confidence for existing node '%s' (%s) from %.2f to %.2f.",
                                existing_node.name,
                                existing_node.id,
                                old_confidence,
                                new_confidence,
                            )
                        if evidence_count_after > evidence_count_before:
                            logger.info(
                                "Merged evidence into existing node '%s' (%s).",
                                existing_node.name,
                                existing_node.id,
                            )
                        continue

                    new_node = Node(
                        node_type=NodeType(eval_node.node_type),
                        name=eval_node.name,
                        description=desc,
                        confidence=eval_node.adjusted_confidence,
                        validation_status=ValidationStatus.INFERRED,
                    )
                    new_node.add_evidence(quote, source=session_id)
                    graph.add_node(new_node)

                    
                    if proposed and proposed.id:
                        resolved_node_ids[proposed.id] = new_node.id
                    if eval_node.id:
                        resolved_node_ids[eval_node.id] = new_node.id
                    logger.info(
                        "Created new node '%s' (%s) for proposed node id '%s'.",
                        new_node.name,
                        new_node.id,
                        eval_node.id,
                    )


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
                source_id = resolved_node_ids.get(
                    eval_rel.source_node_id, eval_rel.source_node_id
                )
                target_id = resolved_node_ids.get(
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
        question_to_ask = clarification_question

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
        try:
            response_text = self.gemini_service.generate_text(
                prompt=prompt,
                system_instruction=self.system_prompt,
                temperature=0.7,
            )
            
        except Exception:
            response_text = (
                "Your message has been processed successfully. "
                "The Understanding Graph has been updated."
            )

        # 8. Save assistant response in Memory
        self.memory_agent.add_message(session_id, "assistant", response_text)

        # 9. Persist the updated graph
        self.graph_service.save_graph(session_id)

        logger.info(f"Processing complete for session '{session_id}'.")
        return response_text
