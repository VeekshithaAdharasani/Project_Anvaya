import logging

logger = logging.getLogger(__name__)
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Any

from models.node import Node
from models.relationship import Relationship
from models.enums.node_type import NodeType
from models.enums.relationship_type import RelationshipType
from models.enums.validation_status import ValidationStatus

router = APIRouter(prefix="/api")


# --- API Request / Response Schemas ---
class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Unique user session identifier")
    message: str = Field(..., description="The chat message from the user")


class ChatResponse(BaseModel):
    response: str = Field(..., description="The personalized agent response")
    graph: dict[str, Any]
    discovery: Optional[dict[str, Any]] = None
    story_event: Optional[dict[str, Any]] = None


class NodeEditRequest(BaseModel):
    id: Optional[str] = Field(
        None, description="ID of the node if editing an existing node"
    )
    node_type: str = Field(..., description="The type of the node")
    name: str = Field(..., description="The name of the node")
    description: str = Field(..., description="The description of the node")


class NodeDeleteRequest(BaseModel):
    node_id: str = Field(..., description="ID of the node to delete")


class RelationshipEditRequest(BaseModel):
    id: Optional[str] = Field(
        None, description="ID of the relationship if editing an existing one"
    )
    source_id: str = Field(..., description="ID of the source node")
    target_id: str = Field(..., description="ID of the target node")
    relationship_type: str = Field(
        ..., description="The type of the relationship"
    )


class RelationshipDeleteRequest(BaseModel):
    rel_id: str = Field(..., description="ID of the relationship to delete")


# --- Endpoints ---


@router.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest):
    """Processes a user message through the ANVAYA multi-agent pipeline."""
    coordinator = request.app.state.coordinator
    try:
        result = coordinator.process_message(
            session_id=payload.session_id,
            user_message=payload.message,
        )

        return ChatResponse(**result)
    except Exception as e:
        logger_err = request.app.state.logger
        logger_err.error(f"Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/graph")
async def get_graph(request: Request, session_id: str):
    """Retrieves the current Understanding Graph for a session, formatted for

    React Flow.
    """
    graph_service = request.app.state.graph_service
    try:
        graph = graph_service.get_graph(session_id)
        
        # EXPOSE: Retrieve adjacency list and dynamically inject the user-facing reflection
        adjacency_data = graph.get_adjacency_list()
        adjacency_data["reflection"] = getattr(
            graph, 
            "latest_reflection", 
            "I'm still reflecting on your journey."
        )
        adjacency_data["questions"] = getattr(
            graph,
            "latest_questions",
            []
        )
        return adjacency_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ...


@router.post("/graph/node/edit")
async def edit_node(
    request: Request, session_id: str, payload: NodeEditRequest
):
    """Allows direct manual edits to a node (creation or modification)."""
    graph_service = request.app.state.graph_service
    try:
        graph = graph_service.get_graph(session_id)

        # Validate node_type string matches NodeType enum
        try:
            node_type_enum = NodeType(payload.node_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid node_type. Must be one of {[t.value for t in NodeType]}",
            )

        if payload.id:
            # Update existing node
            if payload.id not in graph.nodes:
                raise HTTPException(status_code=404, detail="Node not found.")
            graph.update_node(
                payload.id,
                name=payload.name,
                description=payload.description,
                node_type=node_type_enum,
                confidence=1.0,
                validation_status=ValidationStatus.USER_EDITED,
            )
        else:
            # Create a new node
            new_node = Node(
                node_type=node_type_enum,
                name=payload.name,
                description=payload.description,
                confidence=1.0,
                validation_status=ValidationStatus.USER_EDITED,
            )
            new_node.add_evidence(
                "Direct user manual entry", source="user_direct"
            )
            graph.add_node(new_node)

        # Persist the change
        graph_service.save_graph(session_id)
        return {"status": "success", "graph": graph.get_adjacency_list()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/node/delete")
async def delete_node(
    request: Request, session_id: str, payload: NodeDeleteRequest
):
    """Allows direct deletion of a node and its connected relationships."""
    graph_service = request.app.state.graph_service
    try:
        graph = graph_service.get_graph(session_id)
        if payload.node_id not in graph.nodes:
            raise HTTPException(status_code=404, detail="Node not found.")

        graph.remove_node(payload.node_id)
        graph_service.save_graph(session_id)
        return {"status": "success", "graph": graph.get_adjacency_list()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/relationship/edit")
async def edit_relationship(
    request: Request, session_id: str, payload: RelationshipEditRequest
):
    """Allows direct manual edits to a relationship (creation or modification)."""
    graph_service = request.app.state.graph_service
    try:
        graph = graph_service.get_graph(session_id)

        # Validate relationship_type string matches RelationshipType enum
        try:
            rel_type_enum = RelationshipType(payload.relationship_type.lower())
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid relationship_type. Must be one of {[r.value for r in RelationshipType]}",
            )

        if payload.id:
            # Update existing relationship
            if payload.id not in graph.relationships:
                raise HTTPException(
                    status_code=404, detail="Relationship not found."
                )
            graph.update_relationship(
                payload.id,
                relationship_type=rel_type_enum,
                confidence=1.0,
            )
        else:
            # Create a new relationship
            new_rel = Relationship(
                source_id=payload.source_id,
                target_id=payload.target_id,
                relationship_type=rel_type_enum,
                confidence=1.0,
            )
            new_rel.add_evidence(
                "Direct user manual entry", source="user_direct"
            )
            graph.add_relationship(new_rel)

        # Persist the change
        graph_service.save_graph(session_id)
        return {"status": "success", "graph": graph.get_adjacency_list()}
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/graph/relationship/delete")
async def delete_relationship(
    request: Request, session_id: str, payload: RelationshipDeleteRequest
):
    """Allows direct deletion of a relationship."""
    graph_service = request.app.state.graph_service
    try:
        graph = graph_service.get_graph(session_id)
        if payload.rel_id not in graph.relationships:
            raise HTTPException(
                status_code=404, detail="Relationship not found."
            )

        graph.remove_relationship(payload.rel_id)
        graph_service.save_graph(session_id)
        return {"status": "success", "graph": graph.get_adjacency_list()}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
