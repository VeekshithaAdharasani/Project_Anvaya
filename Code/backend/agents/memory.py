"""
Agent module responsible for chronological conversation memory.
Provides secure, validated, and optimized SQLite persistence for system conversations.
"""

import sqlite3
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Set, Optional

logger = logging.getLogger(__name__)


class MemoryAgent:
    """
    Manages chronological conversation history and session contexts.
    Persists chat messages inside SQLite as the system's memory layer.
    """

    # Strictly enforced set of participant roles in system lifecycle
    VALID_ROLES: Set[str] = {"user", "assistant", "system", "tool"}

    def __init__(self, db_path: str = "data/memory.db") -> None:
        """
        Initializes the MemoryAgent and sets up the underlying database schema.
        """
        self.db_path: Path = Path(db_path)
        self._initialize_db()

    def _get_connection(self) -> sqlite3.Connection:
        """
        Establishes and configures a SQLite connection.
        Enforces WAL journaling mode for higher throughput and foreign key checks.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            return conn
        except sqlite3.Error as e:
            logger.exception(f"Database Error: Failed to open connection at '{self.db_path}': {e}")
            raise

    def _initialize_db(self) -> None:
        """
        Ensures storage directories exist and establishes the messages schema if absent.
        """
        # Recursively create base path parent directories if missing
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id TEXT NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        timestamp TEXT NOT NULL
                    )
                    """
                )
                cursor.execute(
                    """
                    CREATE INDEX IF NOT EXISTS idx_session_id ON messages(session_id)
                    """
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.exception(f"Database Initialization Failure: Could not build schema inside '{self.db_path}': {e}")
            raise

    def _validate_inputs(
        self,
        session_id: str,
        role: Optional[str] = None,
        content: Optional[str] = None,
    ) -> None:
        """
        Enforces strict structure and boundary validations for transaction items.

        Raises:
            ValueError: If input constraints or type bounds are broken.
        """
        if not isinstance(session_id, str) or not session_id.strip():
            raise ValueError("Validation Error: 'session_id' must be a non-empty string.")

        if role is not None:
            if role not in self.VALID_ROLES:
                raise ValueError(
                    f"Validation Error: Invalid role '{role}'. Must be one of: {self.VALID_ROLES}"
                )

        if content is not None:
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Validation Error: 'content' must be a non-empty string.")

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """
        Saves a validated message to the conversation history database.

        Time Complexity: O(1)
        Space Complexity: O(1)
        """
        self._validate_inputs(session_id, role, content)
        timestamp = datetime.now(timezone.utc).isoformat()

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO messages (session_id, role, content, timestamp)
                    VALUES (?, ?, ?, ?)
                    """,
                    (session_id, role, content, timestamp),
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to add message for session '{session_id}': {e}")
            raise

    def get_messages(self, session_id: str, limit: int = 20) -> List[Dict[str, str]]:
        """
        Retrieves the most recent messages for a session, ordered chronologically.

        Time Complexity: O(log N + K) where N is total rows, K is limit amount.
        Space Complexity: O(K) memory allocation.
        """
        self._validate_inputs(session_id)
        if not isinstance(limit, int) or limit <= 0:
            raise ValueError("Validation Error: 'limit' parameter must be a positive integer.")

        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # Fetch the latest N elements in descending order, then reverse
                cursor.execute(
                    """
                    SELECT role, content, timestamp FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                    """,
                    (session_id, limit),
                )
                rows = cursor.fetchall()
                return [dict(row) for row in reversed(rows)]
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to fetch recent messages for session '{session_id}': {e}")
            raise

    def get_full_history(self, session_id: str) -> List[Dict[str, str]]:
        """
        Retrieves the complete conversation history for a session in chronological order.

        Time Complexity: O(log N + M) where M represents total messages in the session.
        Space Complexity: O(M) memory allocation.
        """
        self._validate_inputs(session_id)

        try:
            with self._get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT role, content, timestamp FROM messages
                    WHERE session_id = ?
                    ORDER BY id ASC
                    """,
                    (session_id,)
                )
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to fetch complete history for session '{session_id}': {e}")
            raise

    def delete_last_message(self, session_id: str) -> None:
        """
        Deletes the single most recent message for a given session.
        Useful for backtracking or regeneration steps.

        Time Complexity: O(log N)
        Space Complexity: O(1)
        """
        self._validate_inputs(session_id)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT id FROM messages
                    WHERE session_id = ?
                    ORDER BY id DESC
                    LIMIT 1
                    """,
                    (session_id,)
                )
                row = cursor.fetchone()
                if row:
                    cursor.execute("DELETE FROM messages WHERE id = ?", (row[0],))
                    conn.commit()
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to delete last message for session '{session_id}': {e}")
            raise

    def message_count(self, session_id: str) -> int:
        """
        Returns the total number of messages registered under the session.

        Time Complexity: O(log N) via primary/index traversal
        Space Complexity: O(1)
        """
        self._validate_inputs(session_id)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT COUNT(*) FROM messages WHERE session_id = ?",
                    (session_id,)
                )
                count = cursor.fetchone()[0]
                return count
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to retrieve message count for session '{session_id}': {e}")
            raise

    def clear_history(self, session_id: str) -> None:
        """
        Deletes all messages associated with the specified session.

        Time Complexity: O(log N)
        Space Complexity: O(1)
        """
        self._validate_inputs(session_id)

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM messages WHERE session_id = ?", (session_id,)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.exception(f"Database Query Error: Failed to clear history for session '{session_id}': {e}")
            raise