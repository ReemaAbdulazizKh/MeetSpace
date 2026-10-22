import re
from . import agent, booking_service as bookings
from .schemas import ChatResponse

MESSAGES = {
    'no_offer': ('لا يوجد عرض صالح ينتظر التأكيد. اختاري قاعة من الخيارات أولًا.', 'There is no valid pending offer. Select a displayed room first.'),
    'missing': ('أحتاج هذه التفاصيل فقط: ', 'I only need these details: '),
    'date_time': ('التاريخ أو الوقت غير صالح. اكتبي تاريخًا واضحًا ووقتًا بنظام 24 ساعة.', 'The date or time is invalid. Provide an unambiguous date and 24-hour times.'),
    'single_day': ('يجب أن يبدأ الحجز وينتهي في اليوم نفسه بتوقيت الرياض؛ لا يمكن عبور منتصف الليل.', 'Bookings must start and end on the same Riyadh calendar day; overnight bookings are not supported.'),
    'end_time': ('وقت النهاية يجب أن يكون بعد البداية وفي اليوم نفسه. صححي الموعد.', 'End time must be later than start time on the same day. Please correct the time.'),
    'past': ('وقت البداية يجب أن يكون في المستقبل عند تنفيذ الحجز.', 'The start time must be strictly in the future when booking is committed.'),
    'attendees': ('عدد الحضور يجب أن يكون عددًا صحيحًا موجبًا.', 'Attendee count must be a positive integer.'),
    'capacity': ('سعة القاعة لا تكفي عدد الحضور. اختاري قاعة أخرى.', 'The room cannot fit this attendee count. Please choose another room.'),
    'maintenance': ('القاعة غير متاحة أو تحت الصيانة. لم يُنشأ حجز جديد.', 'The room is unavailable or under maintenance. No new booking was created.'),
    'room_type': ('نوع القاعة غير مناسب أو تغير منذ العرض. راجعي خيارًا جديدًا.', 'The room type is unsuitable or changed since the offer. Please review a new option.'),
    'conflict': ('الفترة أصبحت متعارضة. لم يُنشأ حجز؛ اطلبي خيارات محدثة.', 'The slot now conflicts with another booking. No booking was created; request updated options.'),
    'selection': ('هذه القاعة ليست ضمن الخيارات الصالحة المعروضة. اختاري من البطاقات الحالية.', 'That room is not a valid displayed option. Select from the current cards.'),
    'employee': ('الموظف غير موجود. اختاري موظفًا من القائمة الفعلية.', 'Employee not found. Select an employee from the actual list.'),
    'unknown': ('لم يتأكد الحفظ بسبب مشكلة اتصال. احتفظت بمعرّف العرض؛ أعيدي تأكيد العرض نفسه للتحقق بأمان دون حجز مكرر.', 'The write outcome could not be verified. The same offer key is retained; retry confirming this offer to safely verify it without duplication.'),
    'ambiguous_confirmation': ('لم أستلم تأكيدًا صريحًا. راجعي العرض ثم اكتبي «أؤكد الحجز» أو استخدمي زر التأكيد.', 'I need explicit consent. Review the offer, then type “I confirm the booking” or use its confirmation button.'),
    'unsupported': ('المحادثة تدعم حجزًا واحدًا خلال يوم واحد فقط. الطلبات المتكررة أو المتعددة غير متاحة. يمكنك إلغاء حجوزاتك من تقويم حجوزاتي.', 'Chat supports one single-day booking only. Recurring or multiple bookings are not available. You can cancel your bookings from My calendar.'),
    'error': ('تعذر الوصول إلى Firestore. لم يتأكد تنفيذ أي حجز جديد؛ حاولي مجددًا.', 'Firestore could not be reached. No new booking is verified; please try again.'),
    'model_error': ('تعذر فهم الرسالة عبر النموذج المحلي. لم يُنفذ حجز؛ أعيدي المحاولة.', 'The local model could not interpret the message. No booking was executed; please retry.'),
}
LABELS = {'room_type': ('نوع القاعة', 'room type'), 'date': ('التاريخ', 'date'),
          'start_time': ('وقت البداية مع صباحًا/مساءً', 'start time with AM/PM'),
          'end_time': ('وقت النهاية مع صباحًا/مساءً', 'end time with AM/PM'),
          'attendees': ('عدد الحضور', 'attendee count'), 'end_date': ('تاريخ النهاية', 'end date'),
          'selected_room': ('القاعة المختارة', 'selected room')}


def text(code, language):
    return MESSAGES[code][0 if language == 'ar' else 1]


def explicit_assent(message):
    if any(character in message for character in ['?', '؟', '"', '“', '”', '«', '»']):
        return False
    value = re.sub(r'[\u064b-\u065f\u0640]', '', message.lower())
    value = re.sub('[أإآ]', 'ا', value)
    value = value.replace('ؤ', 'و')
    value = re.sub(r'[^\w\s]', ' ', value)
    value = ' '.join(value.split())
    patterns = [r'(?:نعم )?(?:انا )?اوكد(?: (?:هذا )?الحجز)?', r'(?:نعم )?احجز(?:ها| القاعه| القاعة| الحجز)?(?: الان)?',
                r'(?:yes )?(?:please )?book (?:it|the room|this room)(?: please)?',
                r'(?:yes )?i confirm(?: the booking| this booking| the reservation)?',
                r'(?:please )?confirm (?:the |this )?booking(?: please)?']
    return any(re.fullmatch(pattern, value) for pattern in patterns)


def response(session, status, fallback, language, message='', missing=None, model=True, booking=None):
    reply, source = (agent.natural_reply(message, language, status, missing or [], fallback,
                                       acknowledgment=session.acknowledgment)
                     if model else (fallback, 'server'))
    session.messages.append({'role': 'assistant', 'content': reply})
    session.messages[:] = session.messages[-12:]
    return ChatResponse(session_id=session.session_id, reply=reply, status=status,
                        draft=session.draft.copy(), missing=missing or [], options=session.options,
                        pending_offer=session.pending_offer, booking=booking, response_source=source)


def offer_response(session, offer, language, message='', model=True):
    room = offer.room
    fallback = ('راجعي العرض ثم أكدي صراحةً.' if language == 'ar' else 'Review this offer, then explicitly confirm.')
    fallback += f'\n{room.name[language]} · {offer.date} · {offer.start_time}–{offer.end_time} · {offer.attendees}'
    if room.alternative_type:
        fallback += '\n' + ('تنبيه: نوع القاعة بديل عن النوع المطلوب.' if language == 'ar' else 'Note: this is a different room type from your request.')
    return response(session, 'offer', fallback, language, message, model=model)


def select_room(session, room_id, language):
    """A card identifies a room, not consent. Recheck eligibility, never commit."""
    if session.commit_unknown:
        return response(session, 'unknown', text('unknown', language), language, model=False)
    if room_id not in {room.id for room in session.options}:
        session.pending_offer = None
        if not session.receipt:
            session.last_offer = None
        return response(session, 'selection', text('selection', language), language, model=False)
    session.pending_offer = None
    session.last_offer = None
    session.receipt = None
    session.acknowledgment = None
    session.draft['selected_room'] = room_id
    message = f'أختار القاعة {room_id}' if language == 'ar' else f'Select room {room_id}'
    session.messages.append({'role': 'user', 'content': message})
    try:
        session.options = bookings.find_rooms(session.draft)
        if room_id not in {room.id for room in session.options}:
            return response(session, 'selection', text('selection', language), language, model=False)
        offer = bookings.make_offer(session, room_id)
        return offer_response(session, offer, language, model=False)
    except bookings.BookingError as error:
        session.pending_offer = None
        session.options = []
        return response(session, error.code, text(error.code, language), language, model=False)
    except Exception:
        session.pending_offer = None
        session.options = []
        return response(session, 'error', text('error', language), language, model=False)


def confirm_response(session, offer_id, language):
    try:
        result, repeated = bookings.confirm(session, offer_id)
        if language == 'ar':
            message = ('هذا العرض محفوظ بالفعل؛ لم يُنشأ حجز مكرر.' if repeated else 'تم حفظ الحجز والتحقق منه في Firestore.')
        else:
            message = ('This offer is already persisted; no duplicate was created.' if repeated else 'Booking persisted and verified in Firestore.')
        message += f'\n{result.booking_id} · {result.room_id}'
        return response(session, 'already_confirmed' if repeated else 'confirmed', message, language,
                        model=False, booking=result)
    except bookings.BookingError as error:
        return response(session, error.code, text(error.code, language), language, model=False)
    except Exception:
        return response(session, 'error', text('error', language), language, model=False)


def process(session, message, ui_language):
    session.acknowledgment = None
    if re.search(r'\b(recurring|repeating|weekly|daily|every\s+(?:day|week|month))\b|متكرر|كل\s+(?:يوم|أسبوع|اسبوع|شهر)', message, re.I):
        if session.commit_unknown:
            return response(session, 'unknown', text('unknown', ui_language), ui_language, model=False)
        session.pending_offer = None
        session.last_offer = None
        session.options = []
        return response(session, 'unsupported', text('unsupported', ui_language), ui_language, model=False)
    try:
        extraction = agent.extract(message, session, bookings.now_local())
    except agent.AgentUnavailable:
        # Fail closed: an unparsed correction must never leave an old offer confirmable.
        if not session.commit_unknown:
            session.pending_offer = None
            session.options = []
        return response(session, 'model_error', text('model_error', ui_language), ui_language, model=False)
    language = extraction.language
    session.acknowledgment = extraction.acknowledgment
    session.messages.append({'role': 'user', 'content': message})
    values = extraction.model_dump()
    changed = {key: values[key] for key in LABELS if values[key] is not None and values[key] != session.draft.get(key)}
    if session.commit_unknown and (extraction.intent != 'confirm' or changed or extraction.unclear):
        return response(session, 'unknown', text('unknown', language), language, model=False)
    if extraction.intent == 'unsupported':
        session.pending_offer = None
        session.options = []
        session.last_offer = None
        return response(session, 'unsupported', text('unsupported', language), language, message)
    if changed or extraction.unclear or extraction.intent == 'request':
        session.pending_offer = None
        session.last_offer = None
        session.receipt = None
        session.options = []
    session.draft.update(changed)
    for key in extraction.unclear:
        session.draft.pop(key, None)
    if extraction.intent == 'reject':
        session.pending_offer = None
        session.options = []
        session.last_offer = None
        session.draft.pop('selected_room', None)
        return response(session, 'rejected', 'لم يُنشأ حجز. يمكنك تعديل الطلب.' if language == 'ar' else 'No booking was made. You can revise the request.', language, message)
    if extraction.intent == 'confirm' and not changed and not extraction.unclear:
        if not extraction.explicit_confirmation or not explicit_assent(message):
            return response(session, 'ambiguous_confirmation', text('ambiguous_confirmation', language), language, model=False)
        offer = session.pending_offer or session.last_offer
        if not offer:
            return response(session, 'no_offer', text('no_offer', language), language, model=False)
        return confirm_response(session, offer.offer_id, language)
    missing = [key for key in bookings.REQUIRED if session.draft.get(key) is None]
    if missing:
        names = [LABELS[key][0 if language == 'ar' else 1] for key in missing]
        return response(session, 'missing', text('missing', language) + '، '.join(names), language, message, missing)
    try:
        bookings.validate(session.draft)
        session.options = bookings.find_rooms(session.draft)
        selected = session.draft.get('selected_room')
        if selected and selected in [room.id for room in session.options]:
            # Material correction + confirmation never commits; it yields a fresh review.
            offer = bookings.make_offer(session, selected)
            return offer_response(session, offer, language, message)
        session.pending_offer = None
        if not session.options:
            fallback = ('لا توجد قاعة متاحة تناسب النوع أو البدائل والسعة في هذه الفترة. جرّبي موعدًا أو عدد حضور مختلفًا.' if language == 'ar' else 'No matching or alternative room fits the capacity and slot. Please try a different time or attendee count.')
            return response(session, 'unavailable', fallback, language, message)
        fallback = ('هذه خيارات مستوفية للسعة والتوفر الآن. اختاري قاعة؛ البحث لا ينشئ حجزًا.' if language == 'ar' else 'These rooms currently fit the capacity and availability checks. Select one; searching does not create a booking.')
        if selected:
            fallback = ('القاعة المطلوبة غير مناسبة أو غير متاحة للفترة. ' if language == 'ar' else 'The requested room is unsuitable or unavailable for the slot. ') + fallback
        if any(room.alternative_type for room in session.options):
            fallback += '\n' + ('القاعات المعروضة من نوع بديل؛ الاختلاف مبيّن على البطاقات.' if language == 'ar' else 'These are a different room type; the difference is labelled on each card.')
        return response(session, 'options', fallback, language, message)
    except bookings.BookingError as error:
        session.pending_offer = None
        session.options = []
        return response(session, error.code, text(error.code, language), language, message)
    except Exception:
        session.pending_offer = None
        session.options = []
        return response(session, 'error', text('error', language), language, model=False)
