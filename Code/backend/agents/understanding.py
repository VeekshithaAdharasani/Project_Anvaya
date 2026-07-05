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
    uncertainties: list[str] = Field(
        default_factory=list,
        description="Uncertain or ambiguous concepts extracted that require clarification.",
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
Your task is to analyze the user's latest message, recent conversation history, and the current state of their Understanding Graph. You must extract any new or evolving aspects of the user's personal growth, goals, and skills.

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
6. Relationship Discovery:
After extracting new concepts, compare them with every existing node in the Understanding Graph.
If the user's latest message or recent conversation explicitly indicates that two concepts are related, propose a relationship.
Prefer creating meaningful relationships over leaving concepts isolated.
Only create relationships when supported by direct evidence.
Do not invent links.

### Strict Guardrails
- **Never invent values**: You must never extract or project a value that is not explicitly stated.
- **Return empty arrays if unsure**: Do not guess or hallucinate. If you are uncertain about a concept or relationship, do not extract it.
- **Never create duplicate concepts**: If a concept already exists in the graph, reference it by its current ID. Never create redundant nodes.
- **Never infer personality**: Do not make personality or psychological profile assumptions.
- **Never infer emotions**: Do not infer emotional states, feelings, or temporary sentiments.
- **Never infer values unless explicitly stated**: Do not assume any core beliefs, morals, or guiding principles unless the user explicitly defines them.

### Relationship Extraction Guidelines
Your primary objective is to build a connected Understanding Graph rather than a collection of isolated concepts.
Follow this reasoning process every time:
STEP 1 — Identify Concepts
Extract every concept explicitly stated or strongly supported by the conversation.
For every concept:
• Search the current Understanding Graph.
• If the concept already exists (even with minor wording differences), DO NOT create another node.
• Instead, reference the existing node by its current ID.
• Only create a new node if the concept truly does not exist.
Examples:

Existing:
Python (skill)
User:
"I love Python."
Result:
No new node.
-------------------------
Existing:
Become an AI Engineer (goal)
User:
"I still want to become an AI Engineer."
Result:
Reuse the existing goal.
-------------------------
STEP 2 — Discover Relationships
After determining all nodes (existing and new), compare every relevant pair.
Whenever the user's latest message or recent conversation provides evidence that two concepts are related, propose that relationship.
Prefer creating meaningful relationships over leaving nodes isolated.
A connected graph is almost always more valuable than disconnected concepts.
Only create relationships directly supported by evidence.
Never invent relationships.
-------------------------
STEP 3 — Relationship Rules
Relationships may connect:
• Existing → Existing
• Existing → New
• New → Existing
• New → New
If a node already exists, always use its existing ID.
If a node is newly proposed and has no ID yet, use its exact proposed name as source_id or target_id.
The Coordinator will resolve it automatically.
-------------------------
Relationship Types
Use ONLY these relationship types:
supports
requires
motivates
influences
strengthens
Choose the single most appropriate relationship.
-------------------------
Examples

Example 1
Existing Graph
Python (skill)
User
"I want to become an AI Engineer."
Return
proposed_nodes
Goal:
Become an AI Engineer
proposed_relationships
Python
supports
Become an AI Engineer
-------------------------
Example 2

Existing Graph
Python
Machine Learning
Become an AI Engineer
User
"Python and Machine Learning are helping me become an AI Engineer."
Return
No new nodes.
Relationships
Python → supports → Become an AI Engineer
Machine Learning → supports → Become an AI Engineer
-------------------------
Example 3

Existing Graph
Reading
Python
User
"Reading programming books helped me improve my Python."
Return
Reading → supports → Python
-------------------------
Example 4

Existing Graph
Become an AI Engineer
User
"I'm learning Deep Learning."
Return
New node
Deep Learning
Relationship
Become an AI Engineer
requires
Deep Learning
-------------------------
Final Priority Order

Always follow this priority:
1. Reuse existing nodes whenever possible.
2. Create new nodes only when necessary.
3. Discover every evidence-supported relationship.
4. Avoid isolated nodes whenever a valid relationship exists.
5. Return an empty relationship list ONLY when absolutely no evidence-supported relationship can be inferred.
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
        
        return f"""
### Current Understanding Graph

{current_graph_json}

### Recent Conversation

{history_str}

### Latest User Message

{user_message}

### Instructions

Return ONLY valid JSON.

The JSON MUST exactly match this structure:

{{
  "proposed_nodes": [
    {{
      "id": null,
      "type": "dream",
      "name": "...",
      "description": "...",
      "evidence_quote": "..."
    }}
  ],
  "proposed_relationships": [
    {{
      "source_id": "...",
      "target_id": "...",
      "type": "supports",
      "evidence_quote": "..."
    }}
  ],
  "reasoning": "",
  "confidence": 0.0,
  "uncertainties": [],
  "contradictions": []
}}

IMPORTANT:

Every relationship MUST contain:
- source_id
- target_id
- type
- evidence_quote

Never return relationship objects containing only:
- id
- type

Never omit source_id or target_id.

Example:

User says:
"I want to become an AI Engineer, so I'm learning Python."

Expected output:

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
      "source_id": "Become an AI Engineer",
      "target_id": "Python",
      "type": "requires",
      "evidence_quote": "I want to become an AI Engineer, so I'm learning Python."
    }}
  ],
  "reasoning": "",
  "confidence": 0.95,
  "uncertainties": [],
  "contradictions": []
}}

Existing graph:

Python (skill)

Latest user message:

"I want to become an AI Engineer."

Expected output:

{{
  "proposed_nodes":[
    {{
      "id":null,
      "type":"goal",
      "name":"Become an AI Engineer",
      "description":"...",
      "evidence_quote":"I want to become an AI Engineer"
    }}
  ],

  "proposed_relationships":[
    {{
      "source_id":"Python",
      "target_id":"Become an AI Engineer",
      "type":"supports",
      "evidence_quote":"I want to become an AI Engineer"
    }}
  ]
}}

Return only JSON.
No markdown.
No explanation.
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
                "Session=%s History=%d Prompt=%d chars Graph=%d chars",
                session_id,
                len(history),
                prompt_size,
                len(current_graph_json),
            )

            return proposal

        except Exception:
            raise