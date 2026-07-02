"""
Service layer managing persistence operations for the UnderstandingGraph.
Provides atomic file-based JSON serialization, schema validation, session indexing,
and in-memory lifecycle caching of active user sessions.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List

from models.understanding_graph import UnderstandingGraph

logger = logging.getLogger(__name__)


class GraphService:
    """
    Manages the lifecycle, in-memory caching, and atomic file-based serialization
    of the UnderstandingGraph. Keeps the domain models decoupled from persistence
    and I/O layers.
    """

    def __init__(self, storage_dir: str = "data/graphs") -> None:
        """
        Initializes the GraphService and ensures the base storage directory exists.
        """
        self.storage_dir = Path(storage_dir)
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.critical(
                f"Initialization Failure: Could not create storage directory '{storage_dir}': {e}"
            )
            raise
        self._active_graphs: Dict[str, UnderstandingGraph] = {}

    def _get_file_path(self, session_id: str) -> Path:
        """
        Returns the absolute file path for a session's serialized graph.
        """
        return self.storage_dir / f"{session_id}.json"

    def has_graph(self, session_id: str) -> bool:
        """
        Checks if a graph exists for the given session ID, either in memory or on disk.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        if session_id in self._active_graphs:
            return True
        return self._get_file_path(session_id).exists()

    def get_graph(self, session_id: str) -> UnderstandingGraph:
        """
        Retrieves the UnderstandingGraph for the given session.
        Checks the in-memory cache first, falling back to loading and validating from disk.
        If no serialized graph exists, an empty graph is initialized.
        """
        if session_id in self._active_graphs:
            return self._active_graphs[session_id]

        file_path = self._get_file_path(session_id)
        if file_path.exists():
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Reconstruct graph structure
                graph = UnderstandingGraph.from_dict(data)

                # Explicitly validate integrity post-loading
                graph.validate()

                self._active_graphs[session_id] = graph
                logger.info(
                    f"Successfully loaded and validated graph for session '{session_id}' from disk."
                )
                return graph

            except json.JSONDecodeError as e:
                logger.error(
                    f"Corrupted Serialization: JSON decoding failed for session '{session_id}' at line {e.lineno}: {e.msg}. "
                    "Creating new graph to prevent interruption."
                )
            except OSError as e:
                logger.error(
                    f"I/O Exception: Failed to read graph file for session '{session_id}' from disk: {e}. "
                    "Creating new graph."
                )
            except ValueError as e:
                logger.error(
                    f"Validation Exception: Graph loaded for session '{session_id}' failed structural integrity tests: {e}. "
                    "Creating new graph."
                )
            except Exception as e:
                logger.error(
                    f"Unexpected Exception: Failed to load graph for session '{session_id}': {e}. "
                    "Creating new graph."
                )

        # Initialize and register a new graph if none exists or loading failed
        graph = UnderstandingGraph()
        self._active_graphs[session_id] = graph
        return graph

    def save_graph(self, session_id: str) -> None:
        """
        Serializes and saves the session's graph to disk atomically.
        Performs structural graph validation prior to persisting payload.

        Raises:
            ValueError: If the session does not have an active graph in memory, or fails validation.
            OSError: If writing to disk or atomic replacement fails.
        """
        if session_id not in self._active_graphs:
            raise ValueError(
                f"No active graph in memory found for session '{session_id}' to save."
            )

        graph = self._active_graphs[session_id]

        # Call domain validation to check and guarantee invariants before writing
        graph.validate()

        file_path = self._get_file_path(session_id)
        temp_path = file_path.with_suffix(".tmp")

        try:
            # Extract serialized representation from the domain container
            graph_data = graph.to_dict()

            # Perform atomic write sequence via a temporary file in the same directory
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(graph_data, f, indent=2)
                f.flush()

            # Atomic swap replacing the original target destination
            temp_path.replace(file_path)
            logger.info(
                f"Successfully saved and validated graph for session '{session_id}' to disk."
            )

        except OSError as e:
            logger.error(
                f"I/O Failure: Failed to write graph data to disk for session '{session_id}': {e}"
            )
            # Cleanup temporary file if it was left behind
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass
            raise

    def close_graph(self, session_id: str) -> None:
        """
        Saves the graph for the given session to disk, validates it, and
        safely evicts it from the active cache memory.
        """
        if session_id not in self._active_graphs:
            logger.warning(
                f"Cache Warning: Attempted to close graph for session '{session_id}', "
                "but it is not currently active in memory."
            )
            return

        self.save_graph(session_id)
        self._active_graphs.pop(session_id, None)
        logger.info(
            f"Successfully flushed and evicted graph for session '{session_id}' from memory cache."
        )

    def delete_graph(self, session_id: str) -> None:
        """
        Removes the graph from the in-memory cache and deletes its file on disk.
        """
        self._active_graphs.pop(session_id, None)
        file_path = self._get_file_path(session_id)
        if file_path.exists():
            try:
                file_path.unlink()
                logger.info(
                    f"Deleted serialized graph file for session '{session_id}'."
                )
            except OSError as e:
                logger.error(
                    f"I/O Exception: Failed to delete graph file on disk for session '{session_id}': {e}"
                )
                raise

    def list_sessions(self) -> List[str]:
        """
        Lists all session IDs with existing graphs, combining in-memory and on-disk files.
        """
        sessions = set(self._active_graphs.keys())
        try:
            for path in self.storage_dir.glob("*.json"):
                sessions.add(path.stem)
        except OSError as e:
            logger.error(
                f"I/O Exception: Failed to search directory '{self.storage_dir}' for sessions: {e}"
            )

        return sorted(list(sessions))

    def clear_cache(self) -> None:
        """
        Clears the in-memory cache of all active graphs.
        """
        self._active_graphs.clear()