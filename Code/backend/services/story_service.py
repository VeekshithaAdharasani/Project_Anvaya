"""
Service module responsible for generating deterministic, immutable, and story-driven
journal milestones (StoryEvents) from session proposals without using LLMs.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

# Set up clean logging
logger = logging.getLogger(__name__)


class StoryCategory(str, Enum):
    """
    StrEnum representing the semantic categories of permanent journal story events.
    """
    BEGINNING = "beginning"
    DISCOVERY = "discovery"
    GROWTH = "growth"
    CONNECTION = "connection"
    SHIFT = "shift"
    MILESTONE = "milestone"


@dataclass(frozen=True)
class StoryEvent:
    """
    Immutable representation of a permanent Story of Understanding timeline event.
    """
    id: str
    timestamp: str       # ISO 8601 string passed from the Coordinator
    title: str
    summary: str
    category: StoryCategory
    related_nodes: List[str]
    evidence_quote: str


class StoryService:
    """
    StoryService inspects the session proposal and decides whether a permanent,
    historic StoryEvent should be recorded in the journal.
    """

    # ==========================================
    # DETERMINISTIC STORY TEMPLATES
    # ==========================================

    _TEMPLATES = {
        StoryCategory.BEGINNING: {
            "titles": ["The First Page", "Weaving the First Thread", "An Understanding Begins"],
            "summaries": [
                "Our journey began today with the first understanding of {nodes}.",
                "The first page of your understanding journal was written today with {nodes}.",
                "Today we created the first foundation of your understanding through {nodes}."
            ]
        },
        StoryCategory.SHIFT: {
            "titles": ["A True Shift", "Redefining Your Focus", "A Meaningful Turn"],
            "summaries": [
                "You adapted your focus regarding {nodes}. This mental shift reflects the natural evolution of your path.",
                "A new direction emerged today as you adjusted your perspective on {nodes}.",
                "Your map took a bold, adaptive turn today as you decided to pivot regarding {nodes}."
            ]
        },
        StoryCategory.DISCOVERY: {
            "titles": ["A New Direction","A Defining Goal","A Guiding Dream"],
            "summaries": [
                "Today your long-term direction became clearer with the discovery of {nodes}.",
                "Your understanding deepened as {nodes} became an important part of your journey.",
                "We uncovered a meaningful aspiration today: {nodes}."
            ]
        },
        StoryCategory.GROWTH: {
            "titles": [
                "Learning Something New",
                "Growing Your Skills",
                "A New Capability"
            ],

            "summaries": [
                "Today you added {nodes} to your growing skill set.",
                "Your understanding expanded as you began learning {nodes}.",
                "{nodes} became another building block toward your long-term goals."
            ]
        },
        StoryCategory.CONNECTION: {
            "titles": ["Connecting Ideas","Building a Bridge","A Meaningful Connection"],
            "summaries": [
                "Today you connected {source} with {target}, making your understanding map more complete.",
                "{source} now supports your journey toward {target}.",
                "A meaningful relationship emerged between {source} and {target}."
            ]
        },
        StoryCategory.MILESTONE: {
            "titles": ["An Active Milestone", "Securing a Landmark", "A Meaningful Milestone"],
            "summaries": [
                "You reached an important milestone involving {nodes}.",
                "Today's conversation marked meaningful progress around {nodes}.",
                "We captured an important moment in your journey involving {nodes}."
            ]
        }
    }

    def __init__(self) -> None:
        pass

    def generate_story_event(
        self,
        proposal: Any,
        graph: Any,
        timestamp: str,
        is_beginning: bool = False
    ) -> Optional[StoryEvent]:
        """
        Analyzes the UnderstandingProposal and returns an immutable, reproducible 
        StoryEvent if a meaningful transition occurred. Returns None if it is a quiet day.
        """
        if not proposal:
            return None

        proposed_nodes = getattr(proposal, "proposed_nodes", [])

        # Step 1: Detect "Shift" category (Contradiction/Pivots)
        contradictions = getattr(proposal, "contradictions", [])
        if contradictions:
            ref_names = []
            for c in contradictions:
                ref = getattr(c, "existing_reference", None) or getattr(c, "existing_ref", None) or str(c)
                if ref:
                    ref_names.append(ref)
            
            if ref_names:
                evidence = getattr(contradictions[0], "evidence_quote", None) or (
                    proposed_nodes[0].evidence_quote if proposed_nodes else "revising previous focus"
                )
                return self._build_event(
                    nodes_list=ref_names,
                    category=StoryCategory.SHIFT,
                    evidence=evidence,
                    timestamp=timestamp,
                    is_beginning=is_beginning
                )

        # Step 2: Index proposed nodes by category
        nodes_by_type: dict[str, List[Any]] = {}
        for node in proposed_nodes:
            node_type = getattr(node, "node_type", None) or getattr(node, "type", None)
            if node_type:
                type_str = str(node_type.value).lower() if hasattr(node_type, "value") else str(node_type).lower()
                nodes_by_type.setdefault(type_str, []).append(node)

        # Step 3: Detect "Discovery" (New Dreams or Goals)
        if "dream" in nodes_by_type or "goal" in nodes_by_type:
            target_nodes = nodes_by_type.get("dream", []) + nodes_by_type.get("goal", [])
            names = [n.name for n in target_nodes if getattr(n, "name", None)]
            if names:
                return self._build_event(
                    nodes_list=names,
                    category=StoryCategory.DISCOVERY,
                    evidence=target_nodes[0].evidence_quote,
                    timestamp=timestamp,
                    is_beginning=is_beginning
                )

        # Step 4: Detect "Growth" (New Skills)
        if "skill" in nodes_by_type:
            target_nodes = nodes_by_type["skill"]
            names = [n.name for n in target_nodes if getattr(n, "name", None)]
            if names:
                return self._build_event(
                    nodes_list=names,
                    category=StoryCategory.GROWTH,
                    evidence=target_nodes[0].evidence_quote,
                    timestamp=timestamp,
                    is_beginning=is_beginning
                )

        # Step 5: Detect "Connection" (New Relationships)
        proposed_relationships = getattr(proposal, "proposed_relationships", [])
        if proposed_relationships:
            rel = proposed_relationships[0]

            source = getattr(rel, "source_node_id", None) or getattr(rel, "source_id", None)
            target = getattr(rel, "target_node_id", None) or getattr(rel, "target_id", None)

            evidence = getattr(rel, "evidence_quote", None) or "linking concepts"

            if source and target:
                source_node = graph.get_node(source) if hasattr(graph, "get_node") else None
                target_node = graph.get_node(target) if hasattr(graph, "get_node") else None

                source_name = source_node.name if source_node else source
                target_name = target_node.name if target_node else target

                return self._build_connection_event(
                    source=source_name,
                    target=target_name,
                    evidence=evidence,
                    timestamp=timestamp,
                    is_beginning=is_beginning,
                )

        # Step 6: Detect "Milestone" (Confidence Boosts)
        if "confidence" in nodes_by_type:
            target_nodes = nodes_by_type["confidence"]
            names = [n.name for n in target_nodes if getattr(n, "name", None)]
            if names:
                return self._build_event(
                    nodes_list=names,
                    category=StoryCategory.MILESTONE,
                    evidence=target_nodes[0].evidence_quote,
                    timestamp=timestamp,
                    is_beginning=is_beginning
                )

        # Fallback: No permanent structural shifts occurred (Minor Conversation)
        return None

    def _select_template(self, seed_text: str, templates: List[str]) -> str:
        """
        Deterministically selects a template from a pool based on the SHA-256 hash of a seed string.
        """
        if not seed_text:
            return templates[0]
        sha = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
        hash_int = int(sha[:8], 16)
        return templates[hash_int % len(templates)]

    def _format_nodes_prose(self, names: List[str]) -> str:
        """
        Formats node list grammatically into natural prose without surrounding quotation marks.
        """
        if not names:
            return "new concepts"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ", ".join(names[:-1]) + f", and {names[-1]}"

    def _build_event(
        self, 
        nodes_list: List[str], 
        category: StoryCategory, 
        evidence: str, 
        timestamp: str,
        is_beginning: bool
    ) -> StoryEvent:
        """
        Helper method to construct a standard StoryEvent with stable, deterministic hashes.
        """
        prose_nodes = self._format_nodes_prose(nodes_list)
        
        # If Coordinator signals this is the first entry, wrap it as the Beginning chapter
        category_to_use = StoryCategory.BEGINNING if is_beginning else category
        
        templates_pool = self._TEMPLATES[category_to_use]["summaries"]
        titles_pool = self._TEMPLATES[category_to_use]["titles"]

        seed = f"{category_to_use.value}:{prose_nodes}"

        raw_summary = self._select_template(seed, templates_pool)
        summary = raw_summary.format(nodes=prose_nodes)
        title = self._select_template(seed, titles_pool)

        # Generate a stable, reproducible UUID namespace based strictly on stable semantic parameters
        semantic_key = f"{category_to_use.value}:{','.join(sorted(nodes_list))}:{evidence}"
        event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, semantic_key))

        return StoryEvent(
            id=event_id,
            timestamp=timestamp,
            title=title,
            summary=summary,
            category=category_to_use,
            related_nodes=nodes_list,
            evidence_quote=evidence
        )

    def _build_connection_event(
        self, 
        source: str, 
        target: str, 
        evidence: str, 
        timestamp: str,
        is_beginning: bool
    ) -> StoryEvent:
        """
        Helper method to construct connection-based StoryEvents.
        """
        category = StoryCategory.CONNECTION
        category_to_use = StoryCategory.BEGINNING if is_beginning else category
        
        templates_pool = self._TEMPLATES[category_to_use]["summaries"]
        titles_pool = self._TEMPLATES[category_to_use]["titles"]

        seed = f"{category_to_use.value}:{source}:{target}"

        raw_summary = self._select_template(seed, templates_pool)
        nodes = f"{source} and {target}"

        summary = raw_summary.format(
            source=source,
            target=target,
            nodes=nodes
        )
        title = self._select_template(seed, titles_pool)

        # Generate a stable, reproducible UUID namespace based strictly on stable semantic parameters
        related_nodes = [source, target]
        semantic_key = f"{category_to_use.value}:{','.join(sorted(related_nodes))}:{evidence}"
        event_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, semantic_key))

        return StoryEvent(
            id=event_id,
            timestamp=timestamp,
            title=title,
            summary=summary,
            category=category_to_use,
            related_nodes=related_nodes,
            evidence_quote=evidence
        )