"""
Agent module responsible for parse-extraction inside the Understanding Layer.
Analyzes conversations to propose structured additions or modifications
to the passive Understanding Graph.
"""

import json
import logging
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict

from services.gemini_service import GeminiService, GeminiConfigurationError
from models.enums.node_type import NodeType
from models.enums.relationship_type import RelationshipType

logger = logging.getLogger(__name__)


class ProposedNode(BaseModel):
    """Pydantic representation of an extracted node proposal."""

    model_config = ConfigDict(populate_by_name=True)

    id: Optional[str] = Field(
        None,
        description="The ID of the node if it already exists in the graph and is being updated. Otherwise, omit this field to create a new node.",
    )

    node_type: NodeType = Field(
        ...,
        alias="type",
        description="The category of the concept.",
    )

    name: str = Field(
        ...,
        description="A concise, capitalized name for the concept (e.g., 'Python Programming', 'Become an AI Engineer').",
    )

    description: str = Field(
        ...,
        description="A clear, detailed description explaining this concept in relation to the user.",
    )

    evidence_quote: str = Field(
        ...,
        description="The exact verbatim quote from the user's latest message or recent history that justifies this node.",
    )

class ProposedRelationship(BaseModel):
    """Pydantic representation of an extracted relationship proposal."""

    model_config = ConfigDict(populate_by_name=True)

    source_node_id: str = Field(
        ...,
        alias="source_id",
        description="The ID of the source node. Can be an existing node ID or the name/temporary ID of a newly proposed node.",
    )

    target_node_id: str = Field(
        ...,
        alias="target_id",
        description="The ID of the target node. Can be an existing node ID or the name/temporary ID of a newly proposed node.",
    )

    relationship_type: RelationshipType = Field(
        ...,
        alias="type",
        description="The type of directed link connecting source to target.",
    )

    evidence_quote: str = Field(
        ...,
        description="The exact verbatim quote from the user's latest message or recent history that justifies this relationship.",
    )

class ProposedUncertainty(BaseModel):
    """Pydantic representation of an ambiguous or uncertain concept requiring clarification."""

    model_config = ConfigDict(populate_by_name=True)

    target_reference: Optional[str] = Field(
        None,
        alias="target_ref",
        description="The ID of an existing node/relationship, or the temporary name of a newly proposed concept that is uncertain.",
    )

    uncertainty_reason: str = Field(
        ...,
        alias="reason",
        description="The reason why this concept, node, or relationship is currently uncertain or ambiguous.",
    )

    clarification_question: Optional[str] = Field(
        None,
        alias="suggested_question",
        description="A thoughtful, warm, and natural question to ask the user to help clarify this uncertainty.",
    )

class UnderstandingProposal(BaseModel):
    """Structured extraction proposal representing parsed concepts and connections."""
    proposed_nodes: list[ProposedNode] = Field(
        default_factory=list,
        description="List of new or updated nodes extracted from the conversation.",
    )
    proposed_relationships: list[ProposedRelationship] = Field(
        default_factory=list,
        description="List of new or updated relationships extracted from the conversation.",
    )
    reasoning: str = Field(
        ...,
        description="Detailed explanation of why these nodes and relationships were proposed.",
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Confidence score between 0.0 and 1.0.",
    )
    uncertainties: list[ProposedUncertainty] = Field(
        default_factory=list,
        description="Structured list of ambiguous or uncertain concepts extracted that require clarification.",
    )
    contradictions: list[str] = Field(
        default_factory=list,
        description="Detected gaps or contradictions between the user's statements and current graph data.",
    )


# --- Custom Exception Classes ---

class UnderstandingAgentError(Exception):
    """Base domain exception for the Understanding Agent."""
    pass


class ExtractionError(UnderstandingAgentError):
    """Raised when the structured analysis or JSON schema decoding fails."""
    pass


class UnderstandingAgent:
    """
    The interpreter of the Understanding Layer.
    Analyzes conversations and extracts structured understanding proposals
    using the Gemini API without mutating the underlying graph directly.
    """

    # Embedded system prompt representing the core configuration and instructions
    DEFAULT_SYSTEM_INSTRUCTION: str = """You are the core parser for the Understanding Layer of Project ANVAYA.
Your task is to analyze the user's latest message, recent conversation history, and the current state of their Understanding Graph to extract any new or evolving aspects of their personal growth, goals, and skills.

### Core Concepts to Extract (Node Types)
1. **dream**: Long-term life aspirations (e.g., "Become a Senior Researcher").
2. **goal**: Short-term, actionable objectives (e.g., "Finish this React tutorial").
3. **skill**: Existing capabilities or technologies they know (e.g., "Python", "Public Speaking").
4. **interest**: Topics they are curious about or enjoy exploring (e.g., "Machine Learning", "Psychology").
5. **motivation**: The underlying 'why' behind their dreams or goals.
6. **value**: Core beliefs or guiding principles they hold (e.g., "Autonomy", "Helping others").
7. **learning_style**: How they prefer to learn (e.g., "Hands-on coding", "Reading textbooks").
8. **confidence**: Self-efficacy trends or milestones that boost/reduce their confidence.

### Core Connections (Relationship Types)
* **motivates**: A Dream or Motivation driving a Goal (e.g., Dream -> motivates -> Goal).
* **requires**: A Goal needing a Skill (e.g., Goal -> requires -> Skill).
* **supports**: An Interest or Skill aiding a Goal (e.g., Interest -> supports -> Goal).
* **influences**: A Value affecting a Decision or Goal (e.g., Value -> influences -> Goal).
* **strengthens**: A Milestone or Skill boosting Confidence (e.g., Skill -> strengthens -> Confidence).

### Rules for Extraction
1. **Evidence-Based**: Every proposed node or relationship MUST contain an `evidence_quote`. This quote MUST be a verbatim substring from the conversation (preferring the user's latest message). Do not paraphrase.
2. **De-duplication**: Look at the current graph state. If a concept already exists (even if named slightly differently), do NOT propose a new node. Instead, propose an update by providing its existing `id`.
3. **Naming**: Keep names concise, capitalized, and noun-focused (e.g., use 'Machine Learning' instead of 'I like machine learning').
4. **Context**: Use the description field to explain the context of why this node or relationship is relevant to the user.
5. **No Hallucinations**: Only extract information explicitly mentioned or strongly implied by the text.
6. **Relationship Discovery**:
After identifying concepts, audit the current Understanding Graph and compare newly proposed concepts with existing ones. Propose relationships when supported by explicit conversation evidence using these rules:
- **Motivational Anchoring**: Connect newly proposed skills, interests, or projects to existing long-term goals or dreams if the conversation indicates they support or drive them.
- **Instrumental Mapping**: Connect practical tools, skills, or tasks to the active projects or objectives they directly aid or require.
- **Comfort with Ambiguity**: While a connected graph is preferred, you must leave a concept temporarily independent (unconnected) if direct lexical or conversational evidence is lacking. Never speculate or create forced, hypothetical relationships.
- **Relationship Confidence**: If multiple relationships are equally plausible but the conversation does not clearly establish which one is correct, do not choose one arbitrarily. Leave the concept temporarily unconnected and record an uncertainty instead. Future conversations may provide enough evidence to establish the relationship.
- **No Duplicates**: Only propose new relationships. Do not propose relationships that are already explicitly defined as links in the provided graph JSON.

### Strict Guardrails
- **Never invent values**: You must never extract or project a value that is not explicitly stated.
- **Return empty arrays if unsure**: Do not guess or hallucinate. If you are uncertain about a concept or relationship, do not extract it.
- **Never create duplicate concepts**: If a concept already exists in the graph, reference it by its current ID. Never create redundant nodes.
- **Never infer personality**: Do not make personality or psychological profile assumptions.
- **Never infer emotions**: Do not infer emotional states, feelings, or temporary sentiments.
- **Never infer values unless explicitly stated**: Do not assume any core beliefs, morals, or guiding principles unless the user explicitly defines them.

### Relationship Extraction Guidelines
Your primary objective is to propose a connected Target Understanding Graph rather than a collection of isolated concepts.
Follow this reasoning process every time:
STEP 1 — Identify Concepts
Extract every concept explicitly stated or strongly supported by the conversation.
For every concept:
• Search the current Understanding Graph.
• If the concept already exists (even with minor wording differences), DO NOT create another node.
• Instead, reference the existing node by its current ID.
• Only create a new node if the concept truly does not exist.

STEP 2 — Discover Relationships
After determining all target nodes, compare every relevant pair.
Whenever the user's latest message or recent conversation provides evidence that two concepts are related, propose that relationship.
Prefer creating meaningful, evidence-backed connections over leaving nodes isolated.
Only create relationships directly supported by explicit conversation evidence.
Never invent relationships.

STEP 3 — Relationship Rules
Relationships may connect:
• Existing → Existing
• Existing → New
• New → Existing
• New → New
If a node already exists, always use its existing ID.
If a node is newly proposed and has no ID yet, use its exact proposed name as source_id or target_id.
The Coordinator will resolve it automatically.
Do not propose any relationship that is already defined in the provided graph JSON.
"""

    def __init__(
        self,
        gemini_service: GeminiService,
        prompt_path:str | None = None,
    ) -> None:
        """
        Initializes the agent, loading prompt instructions from the specified path.
        """
        self.gemini_service: GeminiService = gemini_service

        if prompt_path:
            self.prompt_path: Path = Path(prompt_path)
        else:
            self.prompt_path = Path(__file__).parent.parent / "prompts" / "understanding_system_prompt.txt"

        self.system_instruction: str = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """
        Loads the system instruction prompt from disk.
        Falls back to an embedded representation if the file is missing or unreadable.
        """
        if self.prompt_path.exists():
            try:
                return self.prompt_path.read_text(encoding="utf-8")
            except OSError as e:
                logger.warning(
                    f"Configuration Warning: Could not read prompt file at '{self.prompt_path}': {e}. "
                    "Falling back to built-in prompt configuration."
                )
        return self.DEFAULT_SYSTEM_INSTRUCTION

    def _validate_inputs(
        self,
        session_id: str,
        user_message: str,
        history: list[dict[str, str]],
        current_graph_json: str,
    ) -> None:
        """
        Enforces strict structural type and schema constraints on incoming parameters.

        Raises:
            ValueError: If any validation checks fail.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("Validation Error: 'session_id' must be a non-empty string.")

        if not isinstance(user_message, str) or not user_message.strip():
            raise ValueError("Validation Error: 'user_message' must be a non-empty string.")

        if not isinstance(history, list):
            raise ValueError("Validation Error: 'history' must be a list of message objects.")

        for idx, msg in enumerate(history):
            if not isinstance(msg, dict):
                raise ValueError(f"Validation Error: Message at index {idx} is not a dictionary.")
            if "role" not in msg or "content" not in msg:
                raise ValueError(
                    f"Validation Error: Message at index {idx} is missing 'role' or 'content' fields."
                )
            if not msg["role"] or not msg["content"]:
                raise ValueError(
                    f"Validation Error: Message at index {idx} contains empty or invalid payload fields."
                )

        if not isinstance(current_graph_json, str) or not current_graph_json.strip():
            raise ValueError("Validation Error: 'current_graph_json' must be a non-empty string.")

        try:
            json.loads(current_graph_json)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Validation Error: 'current_graph_json' is not valid JSON. Parse Exception: {e}"
            )
    def _serialize_reference_graph(self, current_graph_json: str) -> str:
        """
        Parses the full graph JSON and serializes it into a highly compact,
        metadata-stripped reference format to prevent schema leakage and optimize context.
        """
        try:
            full_graph = json.loads(current_graph_json)
        except json.JSONDecodeError:
            # Fallback gracefully if raw string cannot be parsed as JSON
            return f"<reference_graph>\n{current_graph_json}\n</reference_graph>"

        sanitized_nodes = []
        raw_nodes = full_graph.get("nodes", []) if isinstance(full_graph, dict) else full_graph
        if isinstance(raw_nodes, list):
            for node in raw_nodes:
                if not isinstance(node, dict):
                    continue
                # Retain only standard properties needed for matching and reference
                sanitized_nodes.append({
                    "id": node.get("id"),
                    "type": node.get("type") or node.get("node_type"),
                    "name": node.get("name") or node.get("label"),
                    "description": node.get("description") or ""
                })

        sanitized_edges = []
        raw_edges = full_graph.get("edges", []) if isinstance(full_graph, dict) else []
        if isinstance(raw_edges, list):
            for edge in raw_edges:
                if not isinstance(edge, dict):
                    continue
                # Retain only core connectivity properties
                sanitized_edges.append({
                    "source_id": edge.get("source_id") or edge.get("source"),
                    "target_id": edge.get("target_id") or edge.get("target"),
                    "type": edge.get("type") or edge.get("relationship_type")
                })

        compact_graph = {
            "nodes": sanitized_nodes,
            "edges": sanitized_edges
        }

        # Wrap cleanly in XML tags to establish strong attention boundaries
        return f"<reference_graph>\n{json.dumps(compact_graph, indent=2)}\n</reference_graph>"
    def _build_prompt(
        self,
        user_message: str,
        history: list[dict[str, str]],
        current_graph_json: str,
    ) -> str:
        history_str = "\n".join(
            f"{'User' if msg['role']=='user' else 'Assistant'}: {msg['content']}"
            for msg in history
        )
        
        # Sanitize and wrap the reference graph cleanly
        sanitized_graph = self._serialize_reference_graph(current_graph_json)
        
        return f"""
### 1. REFERENCE DATA

[CURRENT GRAPH STATE]
{sanitized_graph}

[CONVERSATION HISTORY]
{history_str}

[LATEST USER MESSAGE]
{user_message}

### 2. STRICT INSTRUCTIONS

1. The Current Graph State inside <reference_graph> is for REFERENCE ONLY. NEVER copy its fields (such as validation_status, created_at, updated_at, evidence, or confidence) into your output JSON.
2. Every proposed node and relationship MUST contain an "evidence_quote" containing a verbatim substring from the conversation.
3. Use the exact JSON schema provided below. Do not invent, include, or duplicate fields.
4. If you cannot populate a required field from explicit conversational evidence, return an empty array instead of inventing values or omitting required fields.
### 3. REQUIRED OUTPUT SCHEMA

Return ONLY valid JSON matching this exact structure:
{{
  "proposed_nodes": [
    {{
      "id": null,
      "type": "dream",
      "name": "short reusable concept (1-4 words)",
      "description": "complete meaning from the user's statement",
      "evidence_quote": "verbatim quote"
    }}
  ],
  "proposed_relationships": [
    {{
      "source_id": "existing ID or new node name",
      "target_id": "existing ID or new node name",
      "type": "supports",
      "evidence_quote": "verbatim quote"
    }}
  ],
  "reasoning": "explanation of extraction decisions",
  "confidence": 0.9,
  "uncertainties": [
    {{
      "target_ref": "node name or ID",
      "reason": "explanation of ambiguity",
      "suggested_question": "optional warm clarification question"
    }}
  ],
  "contradictions": [
    "verbatim description of a detected statement gap or conflict"
  ]
}}

### 4. EXTRACTION EXAMPLE

User: "I want to become an AI Engineer, so I'm learning Python."
Output:
{{
  "proposed_nodes": [
    {{
      "id": null,
      "type": "goal",
      "name": "Become an AI Engineer",
      "description": "The user wants to become an AI Engineer.",
      "evidence_quote": "I want to become an AI Engineer"
    }},
    {{
      "id": null,
      "type": "skill",
      "name": "Python",
      "description": "The user is learning Python.",
      "evidence_quote": "I'm learning Python"
    }}
  ],
  "proposed_relationships": [
    {{
      "source_id": "Python",
      "target_id": "Become an AI Engineer",
      "type": "supports",
      "evidence_quote": "I want to become an AI Engineer, so I'm learning Python."
    }}
  ],
  "reasoning": "Extracted the new career goal and the supporting skill directly from the user's statement.",
  "confidence": 0.95,
  "uncertainties": [],
  "contradictions": []
}}

Return ONLY raw JSON. No markdown wrappers, no conversational text.

### 2.5 NODE NAMING RULES (VERY IMPORTANT)

Node names must be short, reusable concepts.

GOOD:
- AI Engineer
- Machine Learning
- Python
- FastAPI
- Computer Science
- Public Speaking
- Research
- Robotics

BAD:
- Become an AI Engineer who builds intelligent systems that truly understand people.
- I want to learn FastAPI for backend development.
- I love solving coding problems.

Descriptions may contain the user's full meaning.

Example:

User:
"My dream is to become an AI Engineer who builds intelligent systems that truly understand people."

Return:

{{
  "type": "dream",
  "name": "AI Engineer",
  "description": "Become an AI Engineer who builds intelligent systems that truly understand people."
}}

Never use complete sentences as node names.

Node names should usually contain 1-4 words.

Store details inside the description, not inside the node name.
"""
    
    def analyze_conversation(
        self,
        session_id: str,
        user_message: str,
        history: list[dict[str, str]],
        current_graph_json: str,
    ) -> UnderstandingProposal:
        """
        Analyzes the conversation state and proposes graph updates. 
        This is a read-only analysis operation; it does not modify the graph.

        Raises:
            ValueError: If inputs fail constraints.
            ExtractionError: If structured generation fails.

        Time Complexity: Variable (API dependent)
        Space Complexity: O(N) where N represents JSON payload size.
        """
        start_time = time.perf_counter()

        # Enforce validation boundary checks
        self._validate_inputs(session_id, user_message, history, current_graph_json)

        prompt = self._build_prompt(
            user_message,
            history[-8:],
            current_graph_json
        )
        prompt_size = len(prompt)

        logger.info(
            f"Parsing session '{session_id}' conversation state "
            f"(Prompt Payload: {prompt_size} chars)..."
        )

        try:
            proposal = self.gemini_service.generate_json(
                prompt=prompt,
                response_schema=UnderstandingProposal,
                system_instruction=self.system_instruction,
                temperature=0.1,  # Keep low temperature for determinism and high precision
            )

            latency = time.perf_counter() - start_time
            node_cnt = len(proposal.proposed_nodes)
            rel_cnt = len(proposal.proposed_relationships)

            logger.info(
                "Session=%s Nodes=%d Relationships=%d History=%d Prompt=%d chars Graph=%d chars",
                session_id,
                node_cnt,
                rel_cnt,
                len(history),
                prompt_size,
                len(current_graph_json),
            )
            return proposal

        except Exception:
            raise