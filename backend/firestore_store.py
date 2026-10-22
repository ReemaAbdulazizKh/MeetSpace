import os
from functools import lru_cache
from threading import Lock

import firebase_admin
from firebase_admin import credentials, firestore
from .config import PROJECT_ID
from .seed_data import EMPLOYEES, ROOMS
from google.cloud.firestore_v1.base_query import FieldFilter
from google.api_core.exceptions import Aborted

_client_lock = Lock()


@lru_cache(maxsize=1)
def client():
    with _client_lock:
        try:
            app = firebase_admin.get_app('meetspace')
        except ValueError:
            path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
            credential = credentials.Certificate(path) if path else credentials.ApplicationDefault()
            app = firebase_admin.initialize_app(credential, {'projectId': PROJECT_ID}, name='meetspace')
        return firestore.client(app=app)


def list_records(collection):
    return [{'id': doc.id, **doc.to_dict()} for doc in client().collection(collection).stream(timeout=8)]


def check_connection():
    # A real server read: no writes or initialization during health checks.
    client().collection('rooms').document('T01').get(timeout=8)


def employee_exists(employee_id):
    return client().collection('employees').document(employee_id).get(timeout=8).exists


def read_booking(booking_id):
    snapshot = client().collection('bookings').document(booking_id).get(timeout=8)
    return snapshot.to_dict() if snapshot.exists else None


def list_bookings(employee_id=None):
    query = client().collection('bookings')
    if employee_id is not None:
        query = query.where(filter=FieldFilter('employee_id', '==', employee_id))
    return [{'id': doc.id, **doc.to_dict()} for doc in query.stream(timeout=8)]


def run_transaction(db, operation):
    for attempt in range(3):
        try:
            return operation(db.transaction())
        except Aborted:
            if attempt == 2:
                raise


def cancel_booking(booking_id, employee_id):
    from .booking_service import BookingError, RIYADH
    db = client()
    reference = db.collection('bookings').document(booking_id)

    @firestore.transactional
    def cancel(transaction):
        snapshot = reference.get(transaction=transaction)
        if not snapshot.exists:
            raise BookingError('not_found')
        booking = snapshot.to_dict()
        if booking.get('employee_id') != employee_id:
            raise BookingError('ownership')
        if booking.get('status') not in {'confirmed', 'canceled'}:
            raise BookingError('booking_status')
        day_key = f"{booking['room_id']}_{booking['start_at'].astimezone(RIYADH).strftime('%Y%m%d')}"
        day_ref = db.collection('room_days').document(day_key)
        day = day_ref.get(transaction=transaction)
        intervals = day.to_dict().get('active_intervals', []) if day.exists else []
        remaining = [interval for interval in intervals if interval['booking_id'] != booking_id]
        # Cancel and release the same coordination document used by confirmation.
        # Never remove another booking's interval, even for touching time ranges.
        if booking['status'] == 'confirmed':
            transaction.update(reference, {'status': 'canceled', 'canceled_at': firestore.SERVER_TIMESTAMP})
        if day.exists and remaining != intervals:
            transaction.update(day_ref, {'active_intervals': remaining})

    try:
        run_transaction(db, cancel)
    except BookingError:
        raise
    except Exception:
        # A network error can hide a committed transaction. The reads below
        # resolve the actual booking and interval before any success is returned.
        pass
    persisted = read_booking(booking_id)
    if not persisted or persisted.get('employee_id') != employee_id or persisted.get('status') != 'canceled':
        raise RuntimeError('Cancellation could not be verified.')
    day_key = f"{persisted['room_id']}_{persisted['start_at'].astimezone(RIYADH).strftime('%Y%m%d')}"
    day = db.collection('room_days').document(day_key).get(timeout=8)
    if day.exists and any(item['booking_id'] == booking_id for item in day.to_dict().get('active_intervals', [])):
        raise RuntimeError('Released interval could not be verified.')
    return persisted


def set_room_status(room_id, status):
    from .booking_service import BookingError
    db = client()
    reference = db.collection('rooms').document(room_id)

    @firestore.transactional
    def update(transaction):
        room = reference.get(transaction=transaction)
        if not room.exists:
            raise BookingError('not_found')
        if room.to_dict().get('status') != status:
            # Updating the room itself conflicts with concurrent confirmation
            # reads; neither route ever modifies existing bookings here.
            transaction.update(reference, {'status': status})

    try:
        run_transaction(db, update)
    except BookingError:
        raise
    except Exception:
        pass  # Resolve the requested state from Firestore before reporting it.
    persisted = reference.get(timeout=8)
    if not persisted.exists or persisted.to_dict().get('status') != status:
        raise RuntimeError('Room status could not be verified.')
    return {'id': persisted.id, **persisted.to_dict()}


def commit_offer(employee_id, session_id, offer):
    from .booking_service import BookingError, validate, offer_draft, check_room, overlap
    db = client()
    booking_ref = db.collection('bookings').document(offer.offer_id)
    room_ref = db.collection('rooms').document(offer.room.id)
    employee_ref = db.collection('employees').document(employee_id)
    day_ref = db.collection('room_days').document(f"{offer.room.id}_{offer.date.replace('-', '')}")
    prior_query = db.collection('bookings').where(filter=FieldFilter('room_id', '==', offer.room.id))
    employee_query = db.collection('bookings').where(filter=FieldFilter('employee_id', '==', employee_id))

    @firestore.transactional
    def commit(transaction):
        # Reads, including legacy booking records, all precede writes. room_days
        # is the shared coordination document for every writer of this room/day.
        existing = booking_ref.get(transaction=transaction)
        if existing.exists:
            data = existing.to_dict()
            if data.get('employee_id') != employee_id or data.get('session_id') != session_id:
                raise BookingError('no_offer')
            if data.get('status') != 'confirmed':
                raise BookingError('no_offer')
            return data, True
        employee = employee_ref.get(transaction=transaction)
        room = room_ref.get(transaction=transaction)
        day = day_ref.get(transaction=transaction)
        prior = list(prior_query.stream(transaction=transaction))
        own_bookings = list(employee_query.stream(transaction=transaction))
        start, end = validate(offer_draft(offer))
        if not employee.exists:
            raise BookingError('employee')
        room_data = room.to_dict() if room.exists else None
        check_room(room_data, offer.attendees, offer.requested_type, offer.room.alternative_type)
        # A room reclassified after the offer requires a new explicit review.
        if room_data['type'] != offer.room.type:
            raise BookingError('room_type')
        day_data = day.to_dict() if day.exists else {}
        intervals = day_data.get('active_intervals', [])
        active = [item.to_dict() for item in prior if item.to_dict().get('status') == 'confirmed']
        if overlap(start, end, intervals) or overlap(start, end, active):
            raise BookingError('conflict')
        if overlap(start, end, [item.to_dict() for item in own_bookings if item.to_dict().get('status') == 'confirmed']):
            raise BookingError('employee_conflict')
        data = {'employee_id': employee_id, 'room_id': offer.room.id, 'session_id': session_id,
                'offer_id': offer.offer_id, 'start_at': start, 'end_at': end,
                'attendees': offer.attendees, 'requested_type': offer.requested_type,
                'status': 'confirmed', 'created_at': firestore.SERVER_TIMESTAMP, 'canceled_at': None}
        transaction.create(booking_ref, data)
        # Every confirmation reads AND writes the employee document. Concurrent
        # bookings for this employee in different rooms must serialize/retry;
        # the query above also covers existing bookings without new lock data.
        transaction.update(employee_ref, {'booking_revision': offer.offer_id})
        transaction.set(day_ref, {'room_id': offer.room.id, 'day': offer.date,
                                 'active_intervals': intervals + [{'booking_id': offer.offer_id,
                                                                  'start_at': start, 'end_at': end}]}, merge=True)
        return data, False

    # The SDK retries Aborted from commit, but read-phase contention can escape
    # its decorator. Retry a fresh transaction for that definite abort as well.
    data, repeated = run_transaction(db, commit)
    persisted = read_booking(offer.offer_id)
    if not persisted or any(persisted.get(k) != data[k] for k in ['employee_id', 'room_id', 'session_id', 'start_at', 'end_at', 'status']):
        raise RuntimeError('Committed booking could not be verified.')
    return persisted, repeated


def seed():
    db = client()
    entries = [(db.collection(collection).document(item['id']),
                {key: value for key, value in item.items() if key != 'id'})
               for collection, items in [('rooms', ROOMS), ('employees', EMPLOYEES)]
               for item in items]

    @firestore.transactional
    def initialize(transaction):
        # All reads precede writes. Concurrent initialization retries safely.
        snapshots = [reference.get(transaction=transaction) for reference, _ in entries]
        missing = [(reference, data) for (reference, data), snapshot in zip(entries, snapshots)
                   if not snapshot.exists]
        for reference, data in missing:
            transaction.create(reference, data)
        return len(missing)

    return initialize(db.transaction())


if __name__ == '__main__':
    try:
        print(f'Initialization complete: {seed()} missing records created.')
    except Exception:
        print('Firestore initialization failed. Check local credentials, project and connectivity. No success is claimed.')
        raise SystemExit(1)
