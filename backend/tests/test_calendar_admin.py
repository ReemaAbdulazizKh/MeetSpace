"""Isolated transaction/HTTP tests, separate from live Firestore evidence."""
import copy
import unittest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from .. import firestore_store as store, booking_service as service
from ..main import app
from .test_booking import offered


class MemoryTransactionFixture:
    def __init__(self):
        start=datetime(2090,1,15,7,tzinfo=timezone.utc)
        end=datetime(2090,1,15,8,tzinfo=timezone.utc)
        self.state={('bookings','one'):{'employee_id':'sara','room_id':'T02','start_at':start,'end_at':end,'status':'confirmed','canceled_at':None},
                    ('bookings','two'):{'employee_id':'noura','room_id':'T02','start_at':end,'end_at':end,'status':'confirmed'},
                    ('rooms','T02'):{'name':{'ar':'تدريب','en':'Training'},'type':'training','capacity':15,'status':'available'},
                    ('room_days','T02_20900115'):{'room_id':'T02','day':'2090-01-15','active_intervals':[{'booking_id':'one','start_at':start,'end_at':end},{'booking_id':'two','start_at':end,'end_at':end}]}}
        self.events=[]
    def collection(self,name):
        fixture=self
        class Reference:
            def __init__(self,key):self.key=(name,key);self.id=key
            def get(self,transaction=None,**kwargs):
                fixture.events.append('transaction_read' if transaction else 'verification_read')
                value=copy.deepcopy(fixture.state.get(self.key))
                return SimpleNamespace(exists=value is not None,to_dict=lambda:value,id=self.id)
        return SimpleNamespace(document=lambda key:Reference(key))
    def transaction(self):
        fixture=self
        class Transaction:
            def update(self,reference,data):
                fixture.events.append('write')
                changes={key:datetime(2089,1,1,tzinfo=timezone.utc) if value is store.firestore.SERVER_TIMESTAMP else value for key,value in data.items()}
                fixture.state[reference.key].update(changes)
        return Transaction()


class CalendarAdminTests(unittest.TestCase):
    def execute(self,fixture,operation):
        with patch.object(store,'client',return_value=fixture),patch.object(store.firestore,'transactional',side_effect=lambda fn:fn):
            return operation()

    def test_cancel_atomic_owned_interval_and_idempotency(self):
        fixture=MemoryTransactionFixture()
        result=self.execute(fixture,lambda:store.cancel_booking('one','sara'))
        self.assertEqual(result['status'],'canceled')
        self.assertIsNotNone(result['canceled_at'])
        self.assertEqual(fixture.events[:4],['transaction_read','transaction_read','write','write'])
        self.assertEqual([x['booking_id'] for x in fixture.state[('room_days','T02_20900115')]['active_intervals']],['two'])
        before=copy.deepcopy(fixture.state);fixture.events.clear()
        self.execute(fixture,lambda:store.cancel_booking('one','sara'))
        self.assertEqual(before,fixture.state)
        self.assertNotIn('write',fixture.events)

    def test_foreign_cancel_never_writes_or_reads_foreign_day(self):
        fixture=MemoryTransactionFixture();before=copy.deepcopy(fixture.state)
        with self.assertRaises(service.BookingError) as caught:
            self.execute(fixture,lambda:store.cancel_booking('one','noura'))
        self.assertEqual(caught.exception.code,'ownership')
        self.assertEqual(fixture.events,['transaction_read'])
        self.assertEqual(before,fixture.state)

    def test_missing_booking_never_writes(self):
        fixture=MemoryTransactionFixture()
        with self.assertRaises(service.BookingError) as caught:self.execute(fixture,lambda:store.cancel_booking('missing','sara'))
        self.assertEqual(caught.exception.code,'not_found')
        self.assertNotIn('write',fixture.events)

    def test_maintenance_changes_only_status(self):
        fixture=MemoryTransactionFixture();before=copy.deepcopy(fixture.state)
        self.execute(fixture,lambda:store.set_room_status('T02','maintenance'))
        expected=copy.deepcopy(before);expected[('rooms','T02')]['status']='maintenance'
        self.assertEqual(expected,fixture.state)
        fixture.events.clear()
        self.execute(fixture,lambda:store.set_room_status('T02','maintenance'))
        self.assertNotIn('write',fixture.events)

    def test_unknown_cancel_ack_reconciles_actual_records(self):
        fixture=MemoryTransactionFixture();original=store.run_transaction
        def lost_ack(db,operation):
            original(db,operation)
            raise TimeoutError('private detail')
        with patch.object(store,'run_transaction',side_effect=lost_ack):
            result=self.execute(fixture,lambda:store.cancel_booking('one','sara'))
        self.assertEqual(result['status'],'canceled')

    def test_failed_transaction_never_claims_cancellation(self):
        fixture=MemoryTransactionFixture()
        with patch.object(store,'run_transaction',side_effect=TimeoutError('private detail')):
            with self.assertRaises(RuntimeError):self.execute(fixture,lambda:store.cancel_booking('one','sara'))
        self.assertEqual(fixture.state[('bookings','one')]['status'],'confirmed')

    def test_employee_view_filters_and_omits_internal_fields(self):
        fixture=MemoryTransactionFixture()
        items=[{'id':key[1],**value,'session_id':'private-session'} for key,value in fixture.state.items() if key[0]=='bookings']
        with patch.object(store,'list_bookings',return_value=items) as query,patch.object(store,'list_records',side_effect=lambda name:[{'id':'T02',**fixture.state[('rooms','T02')]}] if name=='rooms' else [{'id':'sara','display_name':{'ar':'سارة','en':'Sarah'}}]):
            result=service.booking_views('sara')
        query.assert_called_once_with('sara')
        self.assertEqual([booking.employee_id for booking in result],['sara'])
        self.assertNotIn('session_id',result[0].model_dump())

    def test_api_outage_and_invalid_inputs(self):
        with TestClient(app) as http,patch.object(store,'employee_exists',return_value=True),patch.object(service,'booking_views',side_effect=RuntimeError('private detail')):
            for url in ['/api/bookings?employee_id=sara','/api/admin/bookings']:
                response=http.get(url);self.assertEqual(response.status_code,503);self.assertNotIn('private detail',response.text)
            self.assertEqual(http.post('/api/bookings/one/cancel',json={'employee_id':'sara','confirmed':1}).status_code,422)
            self.assertEqual(http.patch('/api/admin/rooms/T02/status',json={'status':'deleted'}).status_code,422)

    def test_reconfirming_canceled_offer_never_recreates_it(self):
        session=offered();offer=session.pending_offer
        session.last_offer=offer;session.pending_offer=None
        with patch.object(store,'read_booking',return_value={'employee_id':'sara','session_id':session.session_id,'status':'canceled'}),patch.object(store,'commit_offer') as write:
            with self.assertRaises(service.BookingError) as caught:service.confirm(session,offer.offer_id)
        self.assertEqual(caught.exception.code,'no_offer');write.assert_not_called()


if __name__=='__main__':unittest.main()
