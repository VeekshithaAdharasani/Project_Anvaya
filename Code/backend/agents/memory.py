import os
import sqlite3
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class MemoryAgent:
    """Manages the chronological conversation history and session context.

    Persists chat logs in SQLite as the system's memory.
    """

    def __init__(self, db_path: str = "data/memory.db"):
        self.db_path = db_path
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initializes the SQLite database and creates the messages table if it doesn't exist."""
        # Ensure the parent directory exists
        db_dir = os.path.dirname(self.db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)

        try:
            with sqlite3.connect(self.db_path) as conn:
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
            logger.error(f"Failed to initialize memory database: {e}")
            raise

    def add_message(self, session_id: str, role: str, content: str) -> None:
        """Saves a message to the conversation history.

        Args:
            session_id: The active session identifier.
            role: The sender's role ('user', 'assistant', etc.).
            content: The text content of the message.
        """
        timestamp = datetime.now(timezone.utc).isoformat()
        try:
            with sqlite3.connect(self.db_path) as conn:
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
            logger.error(f"Failed to add message to database: {e}")
            raise

    def get_messages(
        self, session_id: str, limit: int = 20
    ) -> list[dict[str, str]]:
        """Retrieves the recent conversation history for a session.

        Args:
            session_id: The active session identifier.
            limit: The maximum number of recent messages to retrieve.

        Returns:
            A list of message dictionaries (containing 'role', 'content', 'timestamp')
            ordered chronologically.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                # Fetch the latest N messages in descending order, then reverse them
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
                messages = [dict(row) for row in reversed(rows)]
                return messages
        except sqlite3.Error as e:
            logger.error(f"Failed to retrieve messages from database: {e}")
            raise

    def clear_history(self, session_id: str) -> None:
        """Deletes all messages in the conversation history for a session."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM messages WHERE session_id = ?", (session_id,)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(
                f"Failed to clear history for session '{session_id}': {e}"
            )
            raise
