from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

FieldName = Literal['room_type', 'date', 'start_time', 'end_time', 'end_date', 'attendees', 'selected_room']


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Extraction(StrictModel):
    intent: Literal['request', 'update', 'select', 'confirm', 'reject', 'other', 'unsupported']
    language: Literal['ar', 'en']
    room_type: Literal['training', 'meeting'] | None
    date: str | None
    start_time: str | None
    end_time: str | None
    end_date: str | None
    attendees: int | None
    selected_room: str | None
    unclear: list[FieldName]
    explicit_confirmation: bool


class ChatRequest(StrictModel):
    employee_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    session_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')
    message: str = Field(min_length=1, max_length=2000)
    language: Literal['ar', 'en'] = 'ar'
    action: Literal['message', 'discard_offer'] = 'message'


class ConfirmRequest(StrictModel):
    employee_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    session_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    offer_id: str = Field(pattern=r'^[a-f0-9]{32}$')
    language: Literal['ar', 'en'] = 'ar'


class CancelRequest(StrictModel):
    employee_id: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,64}$')
    confirmed: bool


class RoomStatusRequest(StrictModel):
    status: Literal['available', 'maintenance']


class BookingView(BaseModel):
    booking_id: str
    employee_id: str
    employee_name: dict[str, str]
    room_id: str
    room_name: dict[str, str]
    start_at: datetime
    end_at: datetime
    status: Literal['confirmed', 'canceled']
    created_at: datetime | None = None
    canceled_at: datetime | None = None
    attendees: int | None = None


class RoomOption(BaseModel):
    id: str
    name: dict[str, str]
    type: Literal['training', 'meeting']
    capacity: int
    alternative_type: bool = False


class Offer(BaseModel):
    offer_id: str
    room: RoomOption
    date: str
    start_time: str
    end_time: str
    attendees: int
    requested_type: Literal['training', 'meeting']


class BookingReceipt(BaseModel):
    booking_id: str
    employee_id: str
    room_id: str
    start_at: datetime
    end_at: datetime
    status: Literal['confirmed']


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    status: str
    draft: dict
    missing: list[str] = Field(default_factory=list)
    options: list[RoomOption] = Field(default_factory=list)
    pending_offer: Offer | None = None
    booking: BookingReceipt | None = None
    response_source: Literal['ollama', 'server'] = 'server'
