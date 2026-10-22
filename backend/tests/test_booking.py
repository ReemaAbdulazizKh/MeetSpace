from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import unittest
from types import SimpleNamespace
from pydantic import ValidationError
from fastapi.testclient import TestClient
from ..main import app
from ..schemas import Extraction, ChatRequest, Offer, RoomOption
from ..sessions import Session, get_session, SessionError
from .. import booking_service as b, chat_service as chat, agent


def draft(**changes):
    result = {'room_type':'training','date':'2090-01-15','start_time':'10:00','end_time':'12:00','attendees':15}
    return {**result, **changes}


def extraction(**changes):
    return Extraction(**{**dict(intent='update',language='en',acknowledgment='I understand.',room_type=None,date=None,start_time=None,
                               end_time=None,end_date=None,attendees=None,selected_room=None,
                               unclear=[],explicit_confirmation=False),**changes})


def offered():
    session=Session('sara', draft=draft())
    session.options=[RoomOption(id='T02',name={'ar':'تدريب','en':'Training'},type='training',capacity=15)]
    b.make_offer(session,'T02')
    return session


class BookingTests(unittest.TestCase):
    def test_utc_and_riyadh(self):
        start,end=b.validate(draft())
        self.assertEqual(start.hour,7)
        self.assertEqual(end.hour,9)
        self.assertEqual(start.utcoffset(),timedelta(0))

    def test_invalid_inputs(self):
        for changes,code in [({'date':'2026-02-30'},'date_time'),({'start_time':'10'},'date_time'),
                             ({'end_time':'10:00'},'end_time'),({'end_time':'09:00'},'end_time'),
                             ({'end_date':'2090-01-16'},'single_day'),({'attendees':0},'attendees'),
                             ({'attendees':True},'attendees'),({'date':'2000-01-01'},'past')]:
            with self.subTest(changes=changes), self.assertRaises(b.BookingError) as caught:
                b.validate(draft(**changes))
            self.assertEqual(caught.exception.code,code)

    def test_boundary_overlap(self):
        start,end=b.validate(draft())
        self.assertFalse(b.overlap(end,end+timedelta(hours=1),[{'start_at':start,'end_at':end}]))
        self.assertTrue(b.overlap(start+timedelta(minutes=1),end,[{'start_at':start,'end_at':end}]))

    def test_capacity_and_maintenance(self):
        for room,code in [({'status':'maintenance','capacity':20,'type':'training'},'maintenance'),
                          ({'status':'available','capacity':10,'type':'training'},'capacity'),
                          ({'status':'available','capacity':20,'type':'meeting'},'room_type')]:
            with self.assertRaises(b.BookingError) as caught: b.check_room(room,15,'training')
            self.assertEqual(caught.exception.code,code)

    def test_alternatives_never_undersized_and_are_labelled(self):
        rooms=[{'id':'T01','name':{'ar':'تدريب','en':'Training'},'type':'training','capacity':10,'status':'available'},
               {'id':'M05','name':{'ar':'اجتماعات','en':'Meeting'},'type':'meeting','capacity':15,'status':'available'},
               {'id':'T04','name':{'ar':'تدريب','en':'Training'},'type':'training','capacity':20,'status':'maintenance'}]
        with patch.object(b.store,'list_records',side_effect=lambda name:rooms if name=='rooms' else []):
            options=b.find_rooms(draft())
        self.assertEqual([r.id for r in options],['M05'])
        self.assertTrue(options[0].alternative_type)

    def test_start_must_be_strictly_future(self):
        start,end=b.validate(draft())
        with self.assertRaises(b.BookingError) as caught:
            b.validate(draft(),now=start)
        self.assertEqual(caught.exception.code,'past')

    def test_transaction_rechecks_current_room_before_any_write(self):
        for current,code in [({'status':'maintenance','capacity':15,'type':'training'},'maintenance'),
                             ({'status':'available','capacity':5,'type':'training'},'capacity'),
                             ({'status':'available','capacity':15,'type':'meeting'},'room_type')]:
            events=[]
            class Reference:
                def __init__(self,collection,key):self.collection=collection
                def get(self,transaction):
                    events.append('read:'+self.collection)
                    data=current if self.collection=='rooms' else {}
                    return SimpleNamespace(exists=self.collection in ['rooms','employees'],to_dict=lambda:data)
            class Collection:
                def __init__(self,name):self.name=name
                def document(self,key):return Reference(self.name,key)
                def where(self,**kwargs):return self
                def stream(self,transaction):events.append('read:query');return []
            class Database:
                def collection(self,name):return Collection(name)
                def transaction(self):return SimpleNamespace(create=lambda *args:events.append('write'),set=lambda *args,**kwargs:events.append('write'))
            session=offered()
            with patch.object(b.store,'client',return_value=Database()), patch.object(
                    b.store.firestore,'transactional',side_effect=lambda fn:fn):
                with self.assertRaises(b.BookingError) as caught:
                    b.store.commit_offer('sara',session.session_id,session.pending_offer)
            self.assertEqual(caught.exception.code,code)
            self.assertIn('read:rooms',events)
            self.assertNotIn('write',events)

    def test_untrusted_json_and_api_inputs(self):
        for data in [{'employee_id':'sara','message':'x','admin':True},
                     {'employee_id':'../rooms','message':'x'}]:
            with self.assertRaises(ValidationError): ChatRequest(**data)
        with self.assertRaises(ValidationError): extraction(attendees='15')
        with self.assertRaises(ValidationError): extraction(explicit_confirmation='true')

    def test_employee_binding(self):
        session=get_session('sara')
        with self.assertRaises(SessionError): get_session('noura',session.session_id)
        with self.assertRaises(SessionError): get_session('sara','f'*32)

    def test_material_correction_invalidates_old_offer(self):
        session=offered()
        old=session.pending_offer.offer_id
        with patch.object(agent,'extract',return_value=extraction(attendees=16)), \
             patch.object(b,'find_rooms',return_value=[]), \
             patch.object(agent,'natural_reply',side_effect=lambda m,l,s,f,x,**kw:(x,'server')):
            response=chat.process(session,'actually 16 people','en')
        self.assertIsNone(response.pending_offer)
        with self.assertRaises(b.BookingError): b.confirm(session,old)

    def test_no_offer_no_write(self):
        with patch.object(agent,'extract',return_value=extraction(intent='confirm',explicit_confirmation=True)), \
             patch.object(b.store,'commit_offer') as write:
            response=chat.process(Session('sara'),'I confirm the booking','en')
        self.assertEqual(response.status,'no_offer')
        write.assert_not_called()

    def test_ambiguous_and_negative_assent(self):
        for message in ['yes','maybe book it','do not book it','هل أؤكد الحجز؟','أؤكد الحجز إذا كانت متاحة','"I confirm the booking"']:
            self.assertFalse(chat.explicit_assent(message),message)
        for message in ['أؤكد الحجز','نعم، احجز','Yes, book it','I confirm the booking']:
            self.assertTrue(chat.explicit_assent(message),message)

    def test_model_outage_invalidates_offer(self):
        session=offered()
        with patch.object(agent,'extract',side_effect=agent.AgentUnavailable()):
            response=chat.process(session,'change my request','en')
        self.assertEqual(response.status,'model_error')
        self.assertIsNone(session.pending_offer)
        self.assertIsNone(response.booking)

    def test_uncertain_commit_reconciles_stable_key(self):
        session=offered();offer=session.pending_offer
        start,end=b.validate(session.draft)
        data={'employee_id':'sara','session_id':session.session_id,'room_id':'T02',
              'start_at':start,'end_at':end,'status':'confirmed'}
        with patch.object(b.store,'commit_offer',side_effect=TimeoutError()), \
             patch.object(b.store,'read_booking',return_value=data):
            result,repeated=b.confirm(session,offer.offer_id)
        self.assertTrue(repeated)
        self.assertEqual(result.booking_id,offer.offer_id)

    def test_unknown_write_never_claims_success(self):
        session=offered();offer=session.pending_offer
        with patch.object(b.store,'commit_offer',side_effect=TimeoutError()), \
             patch.object(b.store,'read_booking',side_effect=TimeoutError()):
            result=chat.confirm_response(session,offer.offer_id,'en')
        self.assertEqual(result.status,'unknown')
        self.assertIsNone(result.booking)
        self.assertEqual(session.pending_offer.offer_id,offer.offer_id)
        self.assertTrue(session.commit_unknown)

    def test_calendar_and_admin_inputs_require_valid_contracts(self):
        with TestClient(app) as http:
            self.assertEqual(http.get('/api/bookings').status_code,422)
            self.assertEqual(http.post('/api/bookings/x/cancel',json={'employee_id':'sara','confirmed':False}).status_code,400)
            self.assertEqual(http.patch('/api/admin/rooms/T01/status',json={'status':'other'}).status_code,422)


class StructuredSelectionTests(unittest.TestCase):
    def test_api_selection_has_no_model_call_or_booking_write(self):
        for language in ['ar','en']:
            session=get_session('sara')
            fixture=offered();session.draft=fixture.draft.copy();session.options=fixture.options.copy()
            with patch.object(b.store,'employee_exists',return_value=True), \
                 patch.object(b,'find_rooms',return_value=session.options.copy()), \
                 patch.object(agent,'structured') as model, \
                 patch.object(b.store,'commit_offer') as commit,TestClient(app) as http:
                result=http.post('/api/chat',json={'employee_id':'sara','session_id':session.session_id,
                    'message':'Select room T02','action':'select_room','room_id':'T02','language':language})
            self.assertEqual(result.status_code,200)
            self.assertEqual(result.json()['status'],'offer')
            self.assertEqual(result.json()['pending_offer']['room']['id'],'T02')
            self.assertIsNone(result.json()['booking'])
            model.assert_not_called();commit.assert_not_called()

    def test_stale_room_invalidates_offer_and_never_commits(self):
        session=offered();old=session.pending_offer.offer_id
        with patch.object(b,'find_rooms',return_value=[]),patch.object(b.store,'commit_offer') as commit:
            result=chat.select_room(session,'T02','en')
            self.assertEqual(result.status,'selection')
            self.assertIsNone(session.pending_offer)
            with self.assertRaises(b.BookingError):b.confirm(session,old)
            commit.assert_not_called()

    def test_selection_read_failure_clears_offer_without_private_details(self):
        session=offered()
        with patch.object(b,'find_rooms',side_effect=RuntimeError('private detail')):
            result=chat.select_room(session,'T02','en')
        self.assertEqual(result.status,'error')
        self.assertIsNone(result.pending_offer)
        self.assertEqual(result.options,[])
        self.assertNotIn('private detail',result.reply)

    def test_unlisted_room_and_unknown_commit_are_not_new_offers(self):
        session=offered()
        with patch.object(b,'find_rooms') as search:
            result=chat.select_room(session,'M03','en')
            self.assertEqual(result.status,'selection');search.assert_not_called()
        session=offered();session.commit_unknown=True;old=session.pending_offer
        with patch.object(b,'find_rooms') as search:
            result=chat.select_room(session,'T02','en')
            self.assertEqual(result.status,'unknown');search.assert_not_called()
            self.assertIs(session.pending_offer,old)

    def test_selection_contract_and_employee_binding(self):
        for payload in [dict(action='select_room',room_id='T02'),
                        dict(action='select_room',session_id='a'*32),
                        dict(action='message',room_id='T02')]:
            with self.assertRaises(ValidationError):ChatRequest(employee_id='sara',message='x',**payload)
        session=get_session('sara')
        with patch.object(b.store,'employee_exists',return_value=True),TestClient(app) as http:
            result=http.post('/api/chat',json={'employee_id':'noura','session_id':session.session_id,
                'message':'x','action':'select_room','room_id':'T02'})
        self.assertEqual(result.status_code,409)


if __name__=='__main__': unittest.main()
