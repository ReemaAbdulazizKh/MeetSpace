from dataclasses import dataclass, field
from threading import Lock, RLock
from uuid import uuid4
from .schemas import Offer, RoomOption, BookingReceipt


class SessionError(Exception):
    pass


@dataclass
class Session:
    employee_id: str
    session_id: str = field(default_factory=lambda: uuid4().hex)
    draft: dict = field(default_factory=dict)
    messages: list = field(default_factory=list)
    options: list[RoomOption] = field(default_factory=list)
    pending_offer: Offer | None = None
    last_offer: Offer | None = None
    receipt: BookingReceipt | None = None
    commit_unknown: bool = False
    acknowledgment: str | None = None
    lock: RLock = field(default_factory=RLock)


_sessions: dict[str, Session] = {}
_lock = Lock()


def get_session(employee_id, session_id=None):
    with _lock:
        if session_id:
            session = _sessions.get(session_id)
            if session is None or session.employee_id != employee_id:
                raise SessionError('Session expired or belongs to another employee.')
            return session
        session = Session(employee_id)
        _sessions[session.session_id] = session
        return session
