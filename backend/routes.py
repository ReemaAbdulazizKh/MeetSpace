from concurrent.futures import ThreadPoolExecutor
from typing import Literal
from fastapi import APIRouter, HTTPException, Query, Path
from pydantic import BaseModel
from .connectivity import check_ollama
from . import firestore_store
from .schemas import ChatRequest, ConfirmRequest, ChatResponse, CancelRequest, RoomStatusRequest, BookingView
from .sessions import get_session, SessionError
from . import chat_service
from . import booking_service
from .config import MODEL_PROVIDER

router = APIRouter(prefix='/api')


class ServiceStatus(BaseModel):
    status: Literal['ok', 'unavailable']
    message: str
    model: str | None = None


class HealthResponse(BaseModel):
    status: Literal['ok', 'degraded']
    backend: Literal['ok'] = 'ok'
    model_provider: Literal['ollama', 'groq'] = 'ollama'
    ollama: ServiceStatus
    firestore: ServiceStatus


class LocalizedName(BaseModel):
    ar: str
    en: str


class Employee(BaseModel):
    id: str
    display_name: LocalizedName


class Room(BaseModel):
    id: str
    name: LocalizedName
    type: Literal['training', 'meeting']
    capacity: int
    status: Literal['available', 'maintenance']


def database_status():
    try:
        firestore_store.check_connection()
        return {'status': 'ok', 'message': 'Firestore server read succeeded.'}
    except Exception:
        return {'status': 'unavailable', 'message': 'Check server credentials, Firestore access and network.'}


def model_status():
    try:
        return check_ollama()
    except Exception:
        return {'status': 'unavailable', 'message': 'Configured model service is unreachable or returned invalid data.'}


@router.get('/health', response_model=HealthResponse)
def health():
    with ThreadPoolExecutor(max_workers=2) as executor:
        model = executor.submit(model_status)
        database = executor.submit(database_status)
        ollama, firestore = model.result(), database.result()
    return {'status': 'ok' if ollama['status'] == firestore['status'] == 'ok' else 'degraded',
            'model_provider': MODEL_PROVIDER, 'ollama': ollama, 'firestore': firestore}


def records(collection):
    try:
        schema = Employee if collection == 'employees' else Room
        return [schema.model_validate(item) for item in firestore_store.list_records(collection)]
    except Exception:
        raise HTTPException(503, detail='Firestore unavailable. Check local server configuration.') from None


@router.get('/employees', response_model=list[Employee])
def employees():
    return records('employees')


@router.get('/rooms', response_model=list[Room])
def rooms():
    return records('rooms')


def session_for(employee_id, session_id):
    try:
        if not firestore_store.employee_exists(employee_id):
            raise HTTPException(404, detail='Employee not found.')
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail='Firestore unavailable; no booking action executed.') from None
    try:
        return get_session(employee_id, session_id)
    except SessionError:
        raise HTTPException(409, detail='Session expired or employee mismatch. Start a new conversation.') from None


@router.post('/chat', response_model=ChatResponse)
def chat(request: ChatRequest):
    session = session_for(request.employee_id, request.session_id)
    with session.lock:
        if request.action == 'select_room':
            return chat_service.select_room(session, request.room_id, request.language)
        if request.action == 'discard_offer':
            if session.commit_unknown:
                return chat_service.response(session, 'unknown', chat_service.text('unknown', request.language), request.language, model=False)
            session.pending_offer = None
            session.last_offer = None
            session.options = []
            session.draft.pop('selected_room', None)
            return chat_service.response(session, 'offer_discarded', 'Offer cleared. No booking action executed.', request.language, model=False)
        return chat_service.process(session, request.message, request.language)


@router.post('/bookings/confirm', response_model=ChatResponse)
def confirm(request: ConfirmRequest):
    session = session_for(request.employee_id, request.session_id)
    with session.lock:
        return chat_service.confirm_response(session, request.offer_id, request.language)


def require_employee(employee_id):
    if not firestore_store.employee_exists(employee_id):
        raise HTTPException(404, detail='Employee not found.')


@router.get('/bookings', response_model=list[BookingView])
def my_bookings(employee_id: str = Query(pattern=r'^[a-zA-Z0-9_-]{1,64}$')):
    try:
        require_employee(employee_id)
        return booking_service.booking_views(employee_id)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(503, detail='Booking data unavailable. Please retry.') from None


@router.get('/admin/bookings', response_model=list[BookingView])
def all_bookings():
    try:
        return booking_service.booking_views()
    except Exception:
        raise HTTPException(503, detail='Booking data unavailable. Please retry.') from None


@router.post('/bookings/{booking_id}/cancel', response_model=BookingView)
def cancel_booking(request: CancelRequest, booking_id: str = Path(pattern=r'^[a-zA-Z0-9_-]{1,128}$')):
    if not request.confirmed:
        raise HTTPException(400, detail='Explicit cancellation confirmation is required.')
    try:
        require_employee(request.employee_id)
        firestore_store.cancel_booking(booking_id, request.employee_id)
        return next(item for item in booking_service.booking_views(request.employee_id) if item.booking_id == booking_id)
    except HTTPException:
        raise
    except booking_service.BookingError as error:
        codes = {'ownership': 403, 'not_found': 404, 'booking_status': 409}
        raise HTTPException(codes.get(error.code, 409), detail='Booking does not exist, is not owned by this employee, or cannot be canceled.') from None
    except Exception:
        raise HTTPException(503, detail='Cancellation outcome unverified. Refresh bookings before retrying the same cancellation.') from None


@router.patch('/admin/rooms/{room_id}/status', response_model=Room)
def change_room_status(request: RoomStatusRequest, room_id: str = Path(pattern=r'^[a-zA-Z0-9_-]{1,64}$')):
    try:
        return firestore_store.set_room_status(room_id, request.status)
    except booking_service.BookingError:
        raise HTTPException(404, detail='Room not found.') from None
    except Exception:
        raise HTTPException(503, detail='Room status outcome unverified. Refresh the inventory before retrying.') from None
