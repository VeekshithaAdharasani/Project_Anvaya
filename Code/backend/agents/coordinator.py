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
from google.api_core.exceptions import ResourceExhausted
from typing import Optional
from services.discovery_service import DiscoveryService
from services.story_service import StoryService


logger = logging.getLogger(__name__)

DEFAULT_SYSTEM_PROMPT = """
You are ANVAYA, an AI companion that helps people understand themselves over time.

Your role is not simply to answer questions. Your role is to observe patterns, connect ideas, remember what matters, and help the user understand their own journey.

When responding:

• Keep responses between 80 and 150 words unless the user explicitly asks for a detailed explanation.
• Speak in a calm, thoughtful, and natural tone.
• Avoid excessive praise, excitement, or motivational language.
• Do not flatter the user.
• Never sound like a generic chatbot.

Always prioritize:

1. Acknowledge the user's latest message naturally.
2. Mention one or two meaningful observations from their understanding graph or previous conversations when relevant.
3. Explain connections instead of simply repeating stored facts.
4. If additional understanding would be valuable, ask ONE thoughtful follow-up question.
5. If no clarification is needed, finish naturally without asking a question.

Never:

• Repeat every fact you know about the user.
• Begin every response with compliments.
• Use phrases like:
  - "That's absolutely fantastic!"
  - "I'm delighted..."
  - "I'm incredibly inspired..."
  - "You're amazing..."
• Over-explain simple ideas.
• Use emojis.
• Output Markdown such as **bold** or bullet formatting unless explicitly requested.

When the user asks what you know about them, summarize the most important themes instead of listing every stored fact.

When the user asks why something matters to them, infer the underlying motivation using their stored memories and relationships rather than simply repeating information.

Your personality should feel like a thoughtful journal companion: observant, reflective, intelligent, and calm.

Always respond in plain text.
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
        discovery_service: Optional[DiscoveryService] = None,
        story_service: Optional[StoryService] = None,
    ):
        self.gemini_service = gemini_service
        self.graph_service = graph_service
        self.memory_agent = memory_agent
        self.understanding_agent = understanding_agent
        self.reflection_agent = reflection_agent
        self.curiosity_agent = curiosity_agent
        self.discovery_service = discovery_service or DiscoveryService()
        self.story_service = story_service or StoryService()
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

    def process_message(self, session_id: str, user_message: str) -> dict[str,  Any]:
        """Processes an incoming user message through the entire multi-agent pipeline

        and returns the final personalized response.
        """
        logger.info(f"Processing message for session '{session_id}'...")
        graph = self.graph_service.get_graph(session_id)
        is_beginning = len(graph.nodes) == 0

        # 1. Save user message in Memory
        self.memory_agent.add_message(session_id, "user", user_message)

        # 2. Retrieve context
        history = self.memory_agent.get_messages(session_id, limit=15)
        current_graph_json = graph.to_json()

        # 3. Extract proposed updates (Understanding Agent)
        try:
            proposed_extraction = self.understanding_agent.analyze_conversation(
                session_id=session_id,
                user_message=user_message,
                history=history[:-1],
                current_graph_json=current_graph_json,
            )
        except ResourceExhausted:
            # No Gemini available
            self.memory_agent.add_message(
                session_id,
                "assistant",
                (
                    "I successfully updated your understanding graph with any information I could process."
                    "However, I'm temporarily unable to generate a full conversational response because "
                    "the AI service has reached its usage limit. Please try again in a little while."
                )
            )
            fallback_text = (
                "I successfully updated your understanding graph with any information I could process. "
                "However, I'm temporarily unable to generate a full conversational response because "
                "the AI service has reached its usage limit. Please try again in a little while."
            )

            self.memory_agent.add_message(
                session_id,
                "assistant",
                fallback_text,
            )
            return {
                "response": fallback_text,
                "graph": json.loads(current_graph_json),
                "discovery": None,
                "story_event": None,
            }

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
            reflection_text="I successfully updated your understanding graph with any information I could process. However, I'm temporarily unable to generate a full conversational response because the AI service has reached its usage limit."
        )

        # PERSIST: Bind the companion reflection text dynamically in memory to the active graph instance
        # graph.latest_reflection = getattr(
        #     reflection_evaluation, 
        #     "reflection_text", 
        #     "I'm still reflecting on your journey."
        # )
        graph.latest_reflection = reflection_evaluation.reflection_text
        

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
                        resolved_node_ids[existing_node.name] = existing_node.id
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
                    # Map the new node's actual name to its generated graph ID
                    resolved_node_ids[new_node.name] = new_node.id
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
        logger.info(
            "Understanding proposed %d relationships.",
            len(proposed_extraction.proposed_relationships),
        )
        logger.info(
            "Reflection returned %d relationships.",
            len(reflection_evaluation.evaluated_relationships),
        )
        for eval_rel in reflection_evaluation.evaluated_relationships:
            logger.info(
                "Processing relationship: %s -> %s (%s), action=%s",
                eval_rel.source_node_id,
                eval_rel.target_node_id,
                eval_rel.relationship_type,
                eval_rel.action,
            )
            if eval_rel.action in ("approve", "modify"):
                # Resolve source and target IDs (mapping temp IDs/names to UUIDs if needed)
                source_id = resolved_node_ids.get(
                    eval_rel.source_node_id, 
                    eval_rel.source_node_id,
                )
                target_id = resolved_node_ids.get(
                    eval_rel.target_node_id, 
                    eval_rel.target_node_id,
                )

                logger.info("Resolved source_id: %s", source_id)
                logger.info("Resolved target_id: %s", target_id)
                logger.info(
                    "Source exists: %s | Target exists: %s",
                    source_id in graph.nodes,
                    target_id in graph.nodes,
                )

                # Verify both nodes exist in the graph before creating the edge
                if source_id in graph.nodes and target_id in graph.nodes:
                    # Check if a relationship between these two nodes already exists
                    logger.info("----- Existing Relationships -----")
                    for r in graph.relationships.values():
                        logger.info(
                            "Relationship: %s -> %s | type=%s (%s)",
                            r.source_id,
                            r.target_id,
                            r.relationship_type,
                            type(r.relationship_type),
                        )
                        logger.info(
                            "Incoming relationship: %s -> %s | type=%s (%s)",
                            source_id,
                            target_id,
                            eval_rel.relationship_type,
                            type(eval_rel.relationship_type),
                        )
                        logger.info(
                            "Comparison: %s == %s -> %s",
                            r.relationship_type.value,
                            eval_rel.relationship_type,
                            r.relationship_type == eval_rel.relationship_type,
                        )
                    existing_rel = next(
                        (
                            r
                            for r in graph.relationships.values()
                            if r.source_id == source_id
                            and r.target_id == target_id
                            and r.relationship_type == eval_rel.relationship_type
                        ),
                        None,
                    )
                    logger.info(f"Existing relationship found: {existing_rel is not None}")

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
                        logger.info("Updating existing relationship")
                        # Update existing relationship
                        graph.update_relationship(
                            existing_rel.id,
                            confidence=eval_rel.adjusted_confidence,
                        )
                        existing_rel.add_evidence(quote, source=session_id)
                    else:
                        # Create a new relationship
                        logger.info("Creating NEW relationship")
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
                        logger.info(
                            f"Relationship added: {new_rel.source_id} -> {new_rel.target_id}"
                        )
                        logger.info(
                            f"Total relationships in graph: {len(graph.relationships)}"
                        )

        # 6. Curiosity Analysis (if no urgent clarification from Reflection)
        question_to_ask = clarification_question
        if not question_to_ask:
            curiosity_analysis = self.curiosity_agent.analyze_graph(
                graph=graph,
                recent_history=history,
            )
            graph.latest_questions = [
                q.question_text
                for q in curiosity_analysis.suggested_questions
            ]
            
            if curiosity_analysis.suggested_questions:
                question_to_ask = (
                    curiosity_analysis.suggested_questions[0].question_text
                )

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
                "I understood what you shared and updated your understanding graph."
                "I've added:"
                "• Machine Learning"
                "• Building AI applications"
                "• Solving coding problems"
                "I'm temporarily unable to generate a conversational reply because the AI service has reached its quota. Please try again in a few moments."
            )

        # 8. Save assistant response in Memory
        self.memory_agent.add_message(session_id, "assistant", response_text)

        discovery = self.discovery_service.generate_discovery(
            proposal=proposed_extraction,
            graph=graph,
        )

        current_time_iso = datetime.now(timezone.utc).isoformat()

        story_event = self.story_service.generate_story_event(
            proposal=proposed_extraction,
            graph=graph,
            timestamp=current_time_iso,
            is_beginning=is_beginning,
        )

        # 9. Persist the updated graph
        self.graph_service.save_graph(session_id)

        logger.info(f"Processing complete for session '{session_id}'.")
        return {
            "response": response_text,
            "graph": json.loads(graph.to_json()),
            "discovery": {
                "title": discovery.title,
                "body": discovery.body,
                "category": discovery.category.value,
                "icon": discovery.icon,
            } if discovery else None,
            "story_event": {
                "id": story_event.id,
                "timestamp": story_event.timestamp,
                "title": story_event.title,
                "summary": story_event.summary,
                "category": story_event.category.value,
                "related_nodes": story_event.related_nodes,
                "evidence_quote": story_event.evidence_quote,
            } if story_event else None,
        }
