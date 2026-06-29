import logging
from typing import Optional
from pydantic import BaseModel, Field

from ..services.gemini_service import GeminiService

logger = logging.getLogger(__name__)


class ProposedNode(BaseModel):
    id: Optional[str] = Field(
        None,
        description="The ID of the node if it already exists in the graph and is being updated. Otherwise, omit this field to create a new node.",
    )
    node_type: str = Field(
        ...,
        description="The category of the concept. Must be one of: 'dream', 'goal', 'skill', 'interest', 'motivation', 'value', 'learning_style', 'confidence'.",
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
    source_node_id: str = Field(
        ...,
        description="The ID of the source node. Can be an existing node ID or the name/temporary ID of a newly proposed node.",
    )
    target_node_id: str = Field(
        ...,
        description="The ID of the target node. Can be an existing node ID or the name/temporary ID of a newly proposed node.",
    )
    relationship_type: str = Field(
        ...,
        description="The type of link. Must be one of: 'motivates', 'requires', 'supports', 'influences', 'strengthens'.",
    )
    evidence_quote: str = Field(
        ...,
        description="The exact verbatim quote from the user's latest message or recent history that justifies this relationship.",
    )


class UnderstandingExtraction(BaseModel):
    proposed_nodes: list[ProposedNode] = Field(
        default_factory=list,
        description="List of new or updated nodes extracted from the conversation.",
    )
    proposed_relationships: list[ProposedRelationship] = Field(
        default_factory=list,
        description="List of new or updated relationships extracted from the conversation.",
    )


class UnderstandingAgent:
    """The interpreter of the Understanding Layer.

    Analyzes conversations and extracts structured understanding (nodes and
    relationships) using the Gemini API.
    """

    SYSTEM_INSTRUCTION = """You are the core parser for the Understanding Layer of Project ANVAYA.
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
5. **No Hallucinations**: Only extract information explicitly mentioned or strongly implied by the text. If the user doesn't mention any new concepts, return empty lists.
"""

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    def analyze_conversation(
        self,
        user_message: str,
        history: list[dict[str, str]],
        current_graph_json: str,
    ) -> UnderstandingExtraction:
        """Analyzes the latest user message and history against the current graph

        to extract proposed nodes and relationships.
        """
        # Format history for the prompt
        history_str = ""
        for msg in history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        prompt = f"""### Current Understanding Graph (JSON State)
{current_graph_json}

### Conversation History (Recent)
{history_str}
User's Latest Message: {user_message}

### Instructions
Analyze the latest message and history. Extract any new or updated nodes and relationships. Conform strictly to the JSON schema.
"""
        logger.info("Sending conversation analysis request to Gemini...")
        try:
            extraction = self.gemini_service.generate_json(
                prompt=prompt,
                response_schema=UnderstandingExtraction,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.1,  # Low temperature for precise extraction
            )
            logger.info(
                f"Successfully extracted {len(extraction.proposed_nodes)} nodes and {len(extraction.proposed_relationships)} relationships."
            )
            return extraction
        except Exception as e:
            logger.error(f"Failed to analyze conversation: {e}")
            raise
