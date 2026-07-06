"""
Service module responsible for generating deterministic, warm, and story-driven
discoveries from session proposals without using LLMs.
"""

import hashlib
import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, List, Optional

# Set up clean logging
logger = logging.getLogger(__name__)


class DiscoveryCategory(str, Enum):
    """
    StrEnum representing the semantic categories of journal discoveries.
    """
    CONTRADICTION = "contradiction"
    DREAM = "dream"
    GOAL = "goal"
    RELATIONSHIP = "relationship"
    SKILL = "skill"
    INTEREST = "interest"
    MOTIVATION = "motivation"
    LEARNING_STYLE = "learning_style"
    CONFIDENCE = "confidence"
    QUIET_DAY = "quiet_day"


@dataclass(frozen=True)
class Discovery:
    """
    Immutable representation of a structured journal discovery entry.
    """
    title: str
    body: str
    category: DiscoveryCategory
    icon: str  # Semantic identifier (e.g., "goal", "relationship", "skill", "interest")


class DiscoveryService:
    """
    DiscoveryService generates an immutable, structured Discovery object
    summarizing the most semantically important change in the user's graph state
    using stable, SHA-256 deterministic template pools.
    """

    # ==========================================
    # DETERMINISTIC TEMPLATE POOLS
    # ==========================================

    _TEMPLATES = {
        DiscoveryCategory.CONTRADICTION: {
            "titles": ["A Shift in Focus", "Evolving Perspective", "A New Direction"],
            "bodies": [
                "Today your understanding evolved as you revised your focus regarding {ref}.",
                "I noticed a meaningful shift in your perspective regarding {ref}.",
                "Your path took a new turn today as you adjusted your direction regarding {ref}."
            ]
        },
        DiscoveryCategory.DREAM: {
            "titles": ["A Deeper Vision", "Aspirational Whispers", "Your Horizon"],
            "bodies": [
                "Today your long-term vision became clearer through your dream of {names}.",
                "I noticed your aspirations crystallizing around your dream of {names}.",
                "A beautiful horizon emerged today through your dream of {names}."
            ]
        },
        DiscoveryCategory.GOAL: {
            "titles": ["A Clearer Path", "Intentional Steps", "Focusing the Lens"],
            "bodies": [
                "Today your direction became more focused with your goal of {names}.",
                "I noticed your immediate focus anchoring around your goal of {names}.",
                "A new milestone was set today as you clarified your goal of {names}."
            ]
        },
        DiscoveryCategory.RELATIONSHIP: {
            "titles": ["Woven Connections", "Linked Pathways", "Finding the Threads"],
            "bodies": [
                "Today a new connection emerged between {source} and {target}.",
                "I noticed a quiet thread forming between {source} and {target}.",
                "A new relationship became clear today, linking {source} and {target}."
            ]
        },
        DiscoveryCategory.SKILL: {
            "titles": ["New Capabilities", "A Growing Toolset", "Expanding Tools"],
            "bodies": [
                "Today you strengthened your journey by adding {names} to your growing skills.",
                "Your toolbox expanded today as you integrated {names}.",
                "I noticed your capability growing as you developed {names}."
            ]
        },
        DiscoveryCategory.INTEREST: {
            "titles": ["Expanding Curiosity", "Active Sparks", "Fields of Interest"],
            "bodies": [
                "Your curiosity expanded today as you explored {names}.",
                "A new spark of curiosity emerged as you explored {names}.",
                "I noticed you diving into new spaces today, exploring {names}."
            ]
        },
        DiscoveryCategory.MOTIVATION: {
            "titles": ["Finding Your Why", "The Underlying Drive", "Core Motivations"],
            "bodies": [
                "Today you uncovered another reason that drives your learning journey.",
                "We touched upon the underlying reasons that drive your current focus.",
                "A quiet motivation surfaced today, illuminating why you pursue this path."
            ]
        },
        DiscoveryCategory.LEARNING_STYLE: {
            "titles": ["Discovering Your Method", "The Rhythm of Learning", "Your Learning Flow"],
            "bodies": [
                "Today you discovered a learning approach that works well for you.",
                "We uncovered another rhythm that helps you learn most effectively.",
                "I noticed a specific learning pattern that seems to suit your journey."
            ]
        },
        DiscoveryCategory.CONFIDENCE: {
            "titles": ["Quiet Confidence", "Self-Belief Growing", "Sensing Strength"],
            "bodies": [
                "Today your confidence grew through another positive learning milestone.",
                "I noticed a quiet boost in your confidence as you reflected on your progress.",
                "Your self-belief strengthened today through your recent efforts."
            ]
        },
        DiscoveryCategory.QUIET_DAY: {
            "titles": ["A Quieter Chapter", "Quiet Reflection", "A Calm Space"],
            "bodies": [
                "It's a quieter day in your journey. Today's conversation helped reinforce your existing understanding.",
                "Today was a gentle chapter in your journal, helping stabilize and ground your existing focus.",
                "A calm day for your understanding map, reinforcing the landmarks we've already discovered."
            ]
        }
    }

    def __init__(self) -> None:
        pass

    def generate_discovery(self, proposal: Any, graph: Any) -> Discovery:
        """
        Analyzes the UnderstandingProposal and returns exactly one structured,
        immutable Discovery object representing the highest-priority graph event.
        """
        if not proposal:
            return self._generate_empty_fallback()

        # Step 1: Check highest priority (Contradictions / Gaps)
        contradictions = getattr(proposal, "contradictions", [])
        if contradictions:
            body = self._generate_contradiction_discovery(contradictions[0])
            title = self._select_template(body, self._TEMPLATES[DiscoveryCategory.CONTRADICTION]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.CONTRADICTION,
                icon="contradiction"
            )

        # Step 2: Extract and index proposed nodes into lists by category/type
        proposed_nodes = getattr(proposal, "proposed_nodes", [])
        nodes_by_type: dict[str, List[Any]] = {}
        for node in proposed_nodes:
            node_type = getattr(node, "node_type", None) or getattr(node, "type", None)
            if node_type:
                type_str = str(node_type.value).lower() if hasattr(node_type, "value") else str(node_type).lower()
                nodes_by_type.setdefault(type_str, []).append(node)

        # Step 3: Check Dreams
        if "dream" in nodes_by_type:
            names = self._format_names(nodes_by_type["dream"])
            raw_body = self._select_template(names, self._TEMPLATES[DiscoveryCategory.DREAM]["bodies"])
            body = raw_body.format(names=names)
            title = self._select_template(names, self._TEMPLATES[DiscoveryCategory.DREAM]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.DREAM,
                icon="dream"
            )

        # Step 4: Check Goals
        if "goal" in nodes_by_type:
            names = self._format_names(nodes_by_type["goal"])
            raw_body = self._select_template(names, self._TEMPLATES[DiscoveryCategory.GOAL]["bodies"])
            body = raw_body.format(names=names)
            title = self._select_template(names, self._TEMPLATES[DiscoveryCategory.GOAL]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.GOAL,
                icon="goal"
            )

        # Step 5: Check Relationships
        proposed_relationships = getattr(proposal, "proposed_relationships", [])
        if proposed_relationships:
            body = self._generate_relationship_discovery(
                proposed_relationships[0],
                proposal,
                graph,
            )
            title = self._select_template(body, self._TEMPLATES[DiscoveryCategory.RELATIONSHIP]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.RELATIONSHIP,
                icon="relationship"
            )

        # Step 6: Check Skills
        if "skill" in nodes_by_type:
            names = self._format_names(nodes_by_type["skill"])
            raw_body = self._select_template(names, self._TEMPLATES[DiscoveryCategory.SKILL]["bodies"])
            body = raw_body.format(names=names)
            title = self._select_template(names, self._TEMPLATES[DiscoveryCategory.SKILL]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.SKILL,
                icon="skill"
            )

        # Step 7: Check Interests
        if "interest" in nodes_by_type:
            names = self._format_names(nodes_by_type["interest"])
            raw_body = self._select_template(names, self._TEMPLATES[DiscoveryCategory.INTEREST]["bodies"])
            body = raw_body.format(names=names)
            title = self._select_template(names, self._TEMPLATES[DiscoveryCategory.INTEREST]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.INTEREST,
                icon="interest"
            )

        # Step 8: Check Motivations
        if "motivation" in nodes_by_type:
            seed = getattr(proposal, "reasoning", "")
            body = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.MOTIVATION]["bodies"])
            title = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.MOTIVATION]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.MOTIVATION,
                icon="motivation"
            )

        # Step 9: Check Learning Style
        if "learning_style" in nodes_by_type:
            seed = getattr(proposal, "reasoning", "")
            body = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.LEARNING_STYLE]["bodies"])
            title = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.LEARNING_STYLE]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.LEARNING_STYLE,
                icon="learning_style"
            )

        # Step 10: Check Confidence
        if "confidence" in nodes_by_type:
            seed = getattr(proposal, "reasoning", "")
            body = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.CONFIDENCE]["bodies"])
            title = self._select_template(seed, self._TEMPLATES[DiscoveryCategory.CONFIDENCE]["titles"])
            return Discovery(
                title=title,
                body=body,
                category=DiscoveryCategory.CONFIDENCE,
                icon="confidence"
            )

        # Step 11: Fallback (Quiet Day)
        return self._generate_empty_fallback(proposal)

    def _select_template(self, seed_text: str, templates: List[str]) -> str:
        """
        Deterministically selects a template from a pool based on the SHA-256 hash of a seed string.
        Guarantees stable, identical outputs for identical graph state inputs while preventing collisions.
        """
        if not seed_text:
            return templates[0]
        
        # Generate a stable, collision-resistant SHA-256 hex digest
        sha = hashlib.sha256(seed_text.encode("utf-8")).hexdigest()
        
        # Convert first 8 hex characters into an integer index safely
        hash_int = int(sha[:8], 16)
        return templates[hash_int % len(templates)]

    def _format_names(self, nodes: List[Any]) -> str:
        """
        Formats a list of node names into a clean, grammatically correct list.
        E.g. ["Python", "Machine Learning"] -> "Python and Machine Learning"
        """
        names = [node.name for node in nodes if hasattr(node, "name") and node.name]
        if not names:
            return "new themes"
        if len(names) == 1:
            return names[0]
        if len(names) == 2:
            return f"{names[0]} and {names[1]}"
        return ", ".join(names[:-1]) + f", and {names[-1]}"

    def _generate_contradiction_discovery(self, contradiction: Any) -> str:
        """
        Generates a thoughtful contradiction narrative when the user shifts focus.
        """
        if isinstance(contradiction, str):
            ref = contradiction
        else:
            ref = (
                getattr(contradiction, "existing_reference", None) or 
                getattr(contradiction, "existing_ref", None) or 
                ""
            )

        if ref:
            templates = self._TEMPLATES[DiscoveryCategory.CONTRADICTION]["bodies"]
            raw_body = self._select_template(ref, templates)
            return raw_body.format(ref=ref)

        return "Today your understanding evolved as you adjusted your direction regarding one of your earlier goals."

    def _generate_relationship_discovery(self, relationship: Any, proposal: Any, graph: Any) -> str:
        """
        Generates an organic connection narrative linking two concepts.
        If the target concept is a Goal or a Dream, personalizes the phrasing accordingly.
        """
        source_id = (
            getattr(relationship, "source_node_id", None)
            or getattr(relationship, "source_id", None)
            or ""
        )

        target_id = (
            getattr(relationship, "target_node_id", None)
            or getattr(relationship, "target_id", None)
            or ""
        )

        source_node = graph.get_node(source_id) if hasattr(graph, "get_node") else None
        target_node = graph.get_node(target_id) if hasattr(graph, "get_node") else None

        source = source_node.name if source_node else source_id
        target = target_node.name if target_node else target_id

        if source and target:
            # Audit proposed nodes to identify if the target is a Goal or Dream for personalization
            target_node = None
            proposed_nodes = getattr(proposal, "proposed_nodes", [])
            for node in proposed_nodes:
                node_id = getattr(node, "id", None)
                node_name = getattr(node, "name", None)
                if (node_id and node_id == target) or (node_name and node_name == target):
                    target_node = node
                    break

            target_phrase = target
            if target_node:
                node_type = getattr(target_node, "node_type", None) or getattr(target_node, "type", None)
                if node_type:
                    type_str = str(node_type.value).lower() if hasattr(node_type, "value") else str(node_type).lower()
                    if "goal" in type_str:
                        target_phrase = f"your goal of {target}"
                    elif "dream" in type_str:
                        target_phrase = f"your dream of {target}"

            templates = self._TEMPLATES[DiscoveryCategory.RELATIONSHIP]["bodies"]
            raw_body = self._select_template(source + target, templates)
            return raw_body.format(source=source, target=target_phrase)

        return "Today a quiet thread emerged in your journal, weaving different facets of your story closer together."

    def _generate_empty_fallback(self, proposal: Any = None) -> Discovery:
        """
        Warm, reflective fallback when no meaningful transitions occur in the session.
        Uses the reasoning of the empty proposal to select template variants deterministically.
        """
        bodies = self._TEMPLATES[DiscoveryCategory.QUIET_DAY]["bodies"]
        titles = self._TEMPLATES[DiscoveryCategory.QUIET_DAY]["titles"]
        
        # Derive a stable hash seed from proposal reasoning or default context
        seed = getattr(proposal, "reasoning", "") if proposal else "quiet_day"
        
        body = self._select_template(seed, bodies)
        title = self._select_template(seed, titles)
        
        return Discovery(
            title=title,
            body=body,
            category=DiscoveryCategory.QUIET_DAY,
            icon="quiet_day"
        )