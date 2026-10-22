import re
from datetime import date, datetime, time, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo
from .schemas import RoomOption, Offer, BookingReceipt
from . import firestore_store as store

RIYADH = ZoneInfo('Asia/Riyadh')
REQUIRED = ['room_type', 'date', 'start_time', 'end_time', 'attendees']


class BookingError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def now_local():
    return datetime.now(RIYADH)


def validate(draft, now=None):
    if any(draft.get(key) is None for key in REQUIRED):
        raise BookingError('missing')
    if draft['room_type'] not in {'training', 'meeting'}:
        raise BookingError('room_type')
    if type(draft['attendees']) is not int or draft['attendees'] <= 0:
        raise BookingError('attendees')
    try:
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', draft['date']):
            raise ValueError()
        day = date.fromisoformat(draft['date'])
        end_day = date.fromisoformat(draft.get('end_date') or draft['date'])
        parsed = []
        for key in ['start_time', 'end_time']:
            if not re.fullmatch(r'\d{2}:\d{2}', draft[key]):
                raise ValueError()
            parsed.append(time.fromisoformat(draft[key]))
    except (ValueError, TypeError):
        raise BookingError('date_time') from None
    if day != end_day:
        raise BookingError('single_day')
    start = datetime.combine(day, parsed[0], RIYADH)
    end = datetime.combine(end_day, parsed[1], RIYADH)
    if end <= start:
        raise BookingError('end_time')
    if start <= (now or now_local()):
        raise BookingError('past')
    return start.astimezone(timezone.utc), end.astimezone(timezone.utc)


def overlap(start, end, intervals):
    return any(start < item['end_at'] and end > item['start_at'] for item in intervals)


def check_room(room, attendees, requested_type, accepted_alternative=False):
    if not room or room.get('status') != 'available':
        raise BookingError('maintenance')
    if type(room.get('capacity')) is not int or attendees > room['capacity']:
        raise BookingError('capacity')
    if room.get('type') not in {'training', 'meeting'}:
        raise BookingError('room_type')
    if room['type'] != requested_type and not accepted_alternative:
        raise BookingError('room_type')


def find_rooms(draft, employee_id=None):
    start, end = validate(draft)
    rooms = store.list_records('rooms')
    bookings = store.list_records('bookings')
    if employee_id and overlap(start, end, [b for b in bookings if b.get('employee_id') == employee_id and b.get('status') == 'confirmed']):
        raise BookingError('employee_conflict')
    options = []
    for room in rooms:
        try:
            check_room(room, draft['attendees'], draft['room_type'], accepted_alternative=True)
        except BookingError:
            continue
        occupied = [b for b in bookings if b.get('room_id') == room['id'] and b.get('status') == 'confirmed']
        if overlap(start, end, occupied):
            continue
        options.append(RoomOption(id=room['id'], name=room['name'], type=room['type'],
                                  capacity=room['capacity'], alternative_type=room['type'] != draft['room_type']))
    matching = [r for r in options if not r.alternative_type]
    selected = draft.get('selected_room')
    # Same type alternatives first; only offer another type when none match.
    result = matching or options
    return sorted(result, key=lambda r: (r.id != selected, r.capacity, r.id))


def make_offer(session, room_id):
    validate(session.draft)
    room = next((room for room in session.options if room.id == room_id), None)
    if room is None:
        raise BookingError('selection')
    session.pending_offer = Offer(offer_id=uuid4().hex, room=room,
                                  date=session.draft['date'], start_time=session.draft['start_time'],
                                  end_time=session.draft['end_time'], attendees=session.draft['attendees'],
                                  requested_type=session.draft['room_type'])
    session.receipt = None
    session.last_offer = None
    return session.pending_offer


def offer_draft(offer):
    return {'room_type': offer.requested_type, 'date': offer.date, 'start_time': offer.start_time,
            'end_time': offer.end_time, 'attendees': offer.attendees}


def receipt(data, booking_id):
    return BookingReceipt(booking_id=booking_id, employee_id=data['employee_id'], room_id=data['room_id'],
                          start_at=data['start_at'], end_at=data['end_at'], status=data['status'])


def confirm(session, offer_id):
    offer = session.pending_offer
    if offer is None:
        if session.last_offer and session.last_offer.offer_id == offer_id:
            persisted = store.read_booking(offer_id)
            if persisted and persisted.get('status') == 'confirmed' and persisted.get('employee_id') == session.employee_id and persisted.get('session_id') == session.session_id:
                return receipt(persisted, offer_id), True
        raise BookingError('no_offer')
    if offer.offer_id != offer_id:
        raise BookingError('no_offer')
    try:
        data, repeated = store.commit_offer(session.employee_id, session.session_id, offer)
    except BookingError:
        session.pending_offer = None
        session.options = []
        raise
    except Exception:
        # A failed response may hide a successful commit. Resolve the stable ID
        # before telling the user to retry. Never create another confirmation key.
        try:
            data = store.read_booking(offer.offer_id)
            if not data or data.get('employee_id') != session.employee_id or data.get('session_id') != session.session_id:
                raise ValueError()
            repeated = True
        except Exception:
            session.commit_unknown = True
            raise BookingError('unknown') from None
    if data.get('status') != 'confirmed':
        session.pending_offer = None
        session.options = []
        session.commit_unknown = False
        raise BookingError('no_offer')
    result = receipt(data, offer.offer_id)
    session.last_offer = offer
    session.receipt = result
    session.pending_offer = None
    session.options = []
    session.commit_unknown = False
    return result, repeated


def booking_views(employee_id=None):
    from .schemas import BookingView
    records = store.list_bookings(employee_id)
    rooms = {room['id']: room for room in store.list_records('rooms')}
    employees = {employee['id']: employee for employee in store.list_records('employees')}
    result = []
    for item in records:
        # Enforce the employee boundary again before constructing any response.
        if employee_id is not None and item['employee_id'] != employee_id:
            continue
        room = rooms.get(item['room_id'], {})
        employee = employees.get(item['employee_id'], {})
        result.append(BookingView(booking_id=item['id'], employee_id=item['employee_id'],
                                  employee_name=employee.get('display_name', {'ar': item['employee_id'], 'en': item['employee_id']}),
                                  room_id=item['room_id'], room_name=room.get('name', {'ar': item['room_id'], 'en': item['room_id']}),
                                  start_at=item['start_at'], end_at=item['end_at'], status=item['status'],
                                  created_at=item.get('created_at'), canceled_at=item.get('canceled_at'),
                                  attendees=item.get('attendees')))
    return sorted(result, key=lambda booking: (booking.start_at, booking.booking_id))
