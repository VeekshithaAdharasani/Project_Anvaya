import json
import logging
from pathlib import Path

from ..models.understanding_graph import UnderstandingGraph

logger = logging.getLogger(__name__)


class GraphService:
    """Manages the lifecycle, in-memory caching, and file-based serialization

    of the UnderstandingGraph. Keeps the domain models decoupled from the database
    and I/O layers.
    """

    def __init__(self, storage_dir: str = "data/graphs"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._active_graphs: dict[str, UnderstandingGraph] = {}

    def _get_file_path(self, session_id: str) -> Path:
        """Returns the file path for a session's serialized graph."""
        return self.storage_dir / f"{session_id}.json"

    def get_graph(self, session_id: str) -> UnderstandingGraph:
        """Retrieves the UnderstandingGraph for the given session.

        Checks the in-memory cache first, then falls back to loading from disk.
        If no serialized graph exists, a new empty graph is initialized.
        """
        if session_id in self._active_graphs:
            return self._active_graphs[session_id]

        file_path = self._get_file_path(session_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # Reconstruct graph from primitive dictionary
                graph = UnderstandingGraph.from_dict(data)
                self._active_graphs[session_id] = graph
                logger.info(
                    f"Successfully loaded graph for session '{session_id}' from disk."
                )
                return graph
            except Exception as e:
                logger.error(
                    f"Failed to load graph for session '{session_id}': {e}. Creating new graph."
                )

        # Initialize a new graph if none exists or loading failed
        graph = UnderstandingGraph()
        self._active_graphs[session_id] = graph
        return graph

    def save_graph(self, session_id: str) -> None:
        """Serializes and saves the session's graph to disk.

        Raises:
            ValueError: If the session does not have an active graph in memory.
        """
        if session_id not in self._active_graphs:
            raise ValueError(
                f"No active graph in memory found for session '{session_id}' to save."
            )

        graph = self._active_graphs[session_id]
        file_path = self._get_file_path(session_id)

        try:
            # Extract primitive dictionary from domain, then encode to JSON
            graph_data = graph.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2)
            logger.info(
                f"Successfully saved graph for session '{session_id}' to disk."
            )
        except Exception as e:
            logger.error(
                f"Failed to save graph for session '{session_id}' to disk: {e}"
            )
            raise

    def delete_graph(self, session_id: str) -> None:
        """Removes the graph from the in-memory cache and deletes its file on disk."""
        self._active_graphs.pop(session_id, None)
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(
                    f"Deleted serialized graph file for session '{session_id}'."
                )
            except Exception as e:
                logger.error(
                    f"Failed to delete graph file for session '{session_id}': {e}"
                )
                raise

    def clear_cache(self) -> None:
        """Clears the in-memory cache of all active graphs."""
        self._active_graphs.clear()
