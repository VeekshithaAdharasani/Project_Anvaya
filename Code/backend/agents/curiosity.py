import logging
from typing import Optional
from pydantic import BaseModel, Field

from ..services.gemini_service import GeminiService

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
    """The prober of the Understanding Layer.

    Scans the current Understanding Graph to identify gaps (e.g., isolated nodes,
    goals without motivations, low-confidence entries) and generates natural-sounding
    questions to clarify them.
    """

    SYSTEM_INSTRUCTION = """You are the Curiosity Agent for the Understanding Layer of Project ANVAYA.
Your task is to review the user's current Understanding Graph and identify gaps, uncertainties, or opportunities to deepen the AI's understanding of the user.

### Gaps to Look For:
1. **Low Confidence**: Any node or relationship with a confidence score below 0.6.
2. **Missing Motivations**: A Goal or Dream that has no incoming 'motivates' or 'supports' relationship (we don't know *why* they want it).
3. **Missing Dependencies**: A Goal that has no outgoing 'requires' relationship to a Skill (we don't know *what skills* they need or are using).
4. **Isolated Nodes**: A node of any type that has no relationships connecting it to other parts of the graph.
5. **Aspiration Gaps**: A Dream that has no connected Goals (they have a big dream, but no active short-term goals to get there).

### Rules for Question Design:
1. **Conversational Tone**: Write questions that sound natural, warm, and supportive. Avoid clinical database-like questions (e.g., instead of "What motivates your goal of learning Python?", ask "I'm curious, what inspired you to start learning Python? What are you hoping to build with it?").
2. **One at a Time**: Although you can suggest multiple questions in the JSON output, each individual question should focus on a single clear gap. The Coordinator will select the best one.
3. **Non-Intrusive**: Do not pry or ask overly sensitive personal questions. Focus on their growth, learning, goals, and dreams.
4. **No Gaps?**: If the graph is well-connected and all confidence scores are high, you do not need to suggest any questions (return an empty list).
"""

    def __init__(self, gemini_service: GeminiService):
        self.gemini_service = gemini_service

    def analyze_graph(
        self, current_graph_json: str, recent_history: list[dict[str, str]]
    ) -> CuriosityAnalysis:
        """Analyzes the current graph and conversation history to generate curiosity questions."""
        # Format history
        history_str = ""
        for msg in recent_history:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_str += f"{role}: {msg['content']}\n"

        prompt = f"""### Current Understanding Graph (JSON State)
{current_graph_json}

### Recent Conversation History
{history_str}

### Instructions
Scan the graph for low-confidence nodes, isolated concepts, or missing relationships. Formulate conversational questions to help fill in these gaps.
"""
        logger.info("Analyzing graph for curiosity gaps...")
        try:
            analysis = self.gemini_service.generate_json(
                prompt=prompt,
                response_schema=CuriosityAnalysis,
                system_instruction=self.SYSTEM_INSTRUCTION,
                temperature=0.3,  # Slightly higher temperature for creative, natural questions
            )
            logger.info(
                f"Curiosity analysis complete. Generated {len(analysis.suggested_questions)} suggested questions."
            )
            return analysis
        except Exception as e:
            logger.error(f"Failed to perform curiosity analysis: {e}")
            raise
