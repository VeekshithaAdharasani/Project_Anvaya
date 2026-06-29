import logging
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from services.gemini_service import GeminiService
from services.graph_service import GraphService
from agents.memory import MemoryAgent
from agents.understanding import UnderstandingAgent
from agents.reflection import ReflectionAgent
from agents.curiosity import CuriosityAgent

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("anvaya_backend")

app = FastAPI(
    title="Project ANVAYA API",
    description="Backend API for Project ANVAYA - An Understanding-Driven Multi-Agent AI Architecture",
    version="1.0.0",
)

# CORS Middleware config (crucial for React + Vite frontend local development)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router)


@app.on_event("startup")
async def startup_event():
    """Initializes the services and agents, storing them on the app state

    for dependency injection in the routes.
    """
    logger.info("Initializing Project ANVAYA Services & Agents...")

    try:
        # 1. Initialize Services
        gemini_service = GeminiService()
        graph_service = GraphService()

        # 2. Initialize Agents
        memory_agent = MemoryAgent()
        understanding_agent = UnderstandingAgent(gemini_service=gemini_service)
        reflection_agent = ReflectionAgent(gemini_service=gemini_service)
        curiosity_agent = CuriosityAgent(gemini_service=gemini_service)

        from agents.coordinator import CoordinatorAgent

        coordinator = CoordinatorAgent(
            gemini_service=gemini_service,
            graph_service=graph_service,
            memory_agent=memory_agent,
            understanding_agent=understanding_agent,
            reflection_agent=reflection_agent,
            curiosity_agent=curiosity_agent,
        )

        # 3. Store on App State
        app.state.gemini_service = gemini_service
        app.state.graph_service = graph_service
        app.state.memory_agent = memory_agent
        app.state.understanding_agent = understanding_agent
        app.state.reflection_agent = reflection_agent
        app.state.curiosity_agent = curiosity_agent
        app.state.coordinator = coordinator
        app.state.logger = logger

        logger.info("All ANVAYA Services & Agents initialized successfully.")
    except Exception as e:
        logger.critical(
            f"Failed to initialize services and agents during startup: {e}",
            exc_info=True,
        )
        sys.exit(1)


@app.get("/")
async def root():
    return {
        "project": "ANVAYA",
        "status": "running",
        "version": "1.0.0",
        "tagline": "From Memory to Understanding",
    }
