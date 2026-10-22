"""Employee overlap rule: isolated service and transaction assertions."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from backend import booking_service as b, firestore_store as store
from .test_booking import draft, offered


class EmployeeConflictTests(unittest.TestCase):
    def test_search_rejects_own_overlap_but_allows_other_employee_cancelled_and_boundary(self):
        start, end = b.validate(draft())
        room = {'id':'T02','name':{'ar':'قاعة','en':'Room'},'type':'training','capacity':30,'status':'available'}
        for owner,status,begin,finish,rejected in [
            ('sara','confirmed',start,end,True),
            ('noura','confirmed',start,end,False),
            ('sara','canceled',start,end,False),
            ('sara','confirmed',end,end+(end-start),False)]:
            booking = dict(room_id='T01',employee_id=owner,status=status,start_at=begin,end_at=finish)
            with patch.object(store,'list_records',side_effect=lambda name:[room] if name=='rooms' else [booking]):
                if rejected:
                    with self.assertRaises(b.BookingError) as error:b.find_rooms(draft(),'sara')
                    self.assertEqual(error.exception.code,'employee_conflict')
                else:self.assertEqual([x.id for x in b.find_rooms(draft(),'sara')],['T02'])

    def test_commit_rechecks_own_other_room_and_uses_shared_employee_write(self):
        for conflict in (True,False):
            session=offered();offer=session.pending_offer
            start,end=b.validate(b.offer_draft(offer));events=[];persisted={}
            prior=dict(employee_id='sara',room_id='T01',status='confirmed',start_at=start,end_at=end)
            class Reference:
                def __init__(self,name,key):self.name,self.key=name,key
                def get(self,transaction):
                    events.append('read:'+self.name)
                    data={'status':'available','type':offer.room.type,'capacity':30} if self.name=='rooms' else {}
                    return SimpleNamespace(exists=self.name in ('rooms','employees'),to_dict=lambda:data)
            class Collection:
                def __init__(self,name):self.name=name;self.field=None
                def document(self,key):return Reference(self.name,key)
                def where(self,filter):self.field=filter.field_path;return self
                def stream(self,transaction):
                    events.append('query:'+str(self.field))
                    return [SimpleNamespace(to_dict=lambda:prior)] if conflict and self.field=='employee_id' else []
            class Transaction:
                def create(self,ref,data):events.append('write:booking');persisted.update(data)
                def update(self,ref,data):events.append('write:'+ref.name)
                def set(self,*args,**kwargs):events.append('write:room_days')
            db=SimpleNamespace(collection=lambda name:Collection(name),transaction=lambda:Transaction())
            with patch.object(store,'client',return_value=db),patch.object(store.firestore,'transactional',side_effect=lambda fn:fn),patch.object(store,'read_booking',side_effect=lambda key:persisted):
                if conflict:
                    with self.assertRaises(b.BookingError) as error:store.commit_offer('sara',session.session_id,offer)
                    self.assertEqual(error.exception.code,'employee_conflict')
                    self.assertFalse(any(x.startswith('write:') for x in events))
                else:
                    store.commit_offer('sara',session.session_id,offer)
                    self.assertIn('write:employees',events)
                    self.assertLess(events.index('query:employee_id'),events.index('write:booking'))
