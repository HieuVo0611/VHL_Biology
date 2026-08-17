"""In-memory per-analysis session state, keyed by UUID, lazy TTL expiry."""
import time
import uuid


class SessionStore:
    def __init__(self, ttl_seconds: float = 7200):
        self._sessions: dict[str, dict] = {}
        self._created_at: dict[str, float] = {}
        self.ttl_seconds = ttl_seconds

    def create(self) -> str:
        session_id = str(uuid.uuid4())
        self._sessions[session_id] = {}
        self._created_at[session_id] = time.time()
        return session_id

    def get(self, session_id: str) -> dict:
        if session_id not in self._sessions:
            raise KeyError(session_id)
        if time.time() - self._created_at[session_id] > self.ttl_seconds:
            self.delete(session_id)
            raise KeyError(session_id)
        return self._sessions[session_id]

    def update(self, session_id: str, **fields) -> None:
        session = self.get(session_id)
        session.update(fields)

    def delete(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)
        self._created_at.pop(session_id, None)


store = SessionStore()
