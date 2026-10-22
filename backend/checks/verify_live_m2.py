"""Explicit owner-authorized live M2 verification. Creates labelled-in-report test
bookings in real Firestore; never deletes, cancels, or edits preexisting records.
Run from workspace root: python -m backend.checks.verify_live_m2
"""
import json
import time
from datetime import timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from ..main import app
from .. import firestore_store as store, booking_service as b
from ..sessions import Session
from ..schemas import RoomOption

REPORT = Path('docs/evidence/m2/m2_live_results.json')


def snapshot(collection):
    return {item.id:item.to_dict() for item in store.client().collection(collection).stream(timeout=15)}


def main(report_path=None):
    global REPORT
    if report_path is not None:
        REPORT=Path(report_path)
    report={'started_riyadh':b.now_local().isoformat(),'tests':[],'test_bookings':[],'status':'running'}
    def save(): REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def record(name,result):
        report['tests'].append({'name':name,**result});save();print(name,json.dumps(result,ensure_ascii=False,default=str),flush=True)
    before={name:snapshot(name) for name in ['rooms','employees','bookings','room_days']}
    day=(b.now_local()+timedelta(days=35)).date()
    occupied_dates={item['start_at'].astimezone(b.RIYADH).date() for item in before['bookings'].values() if 'start_at' in item}
    while any(day+timedelta(days=i) in occupied_dates for i in range(4)): day+=timedelta(days=4)
    report['test_dates']=[str(day+timedelta(days=i)) for i in range(4)];save()
    with TestClient(app) as http:
        def say(message,previous=None,employee='sara',language='en'):
            started=time.monotonic()
            result=http.post('/api/chat',json={'employee_id':employee,'session_id':previous['session_id'] if previous else None,'message':message,'language':language})
            assert result.status_code==200,result.text
            data=result.json()
            record('chat',{'input':message,'employee':employee,'elapsed_seconds':round(time.monotonic()-started,2),'result':data})
            return data
        def persisted(data,label):
            assert data['status'] in ['confirmed','already_confirmed'],data
            booking=data['booking'];item=store.read_booking(booking['booking_id'])
            assert item and item['status']=='confirmed' and item['room_id']==booking['room_id']
            day_key=f"{item['room_id']}_{item['start_at'].astimezone(b.RIYADH).strftime('%Y%m%d')}"
            coordination=store.client().collection('room_days').document(day_key).get().to_dict()
            assert sum(x['booking_id']==booking['booking_id'] for x in coordination['active_intervals'])==1
            report['test_bookings'].append({'label':label,**booking,'room_day':day_key});save()
            return item
        try:
            health=http.get('/api/health').json();assert health['status']=='ok';record('health',health)
            initial_count=len(snapshot('bookings'))
            typical=say(f'I need a training room on {day} from 10:00 to 12:00 for 15 people.')
            assert typical['status']=='options' and typical['draft']['end_time']=='12:00',typical
            assert all(r['capacity']>=15 and r['type']=='training' for r in typical['options'])
            assert len(snapshot('bookings'))==initial_count
            room=typical['options'][0]['id']
            selected=say(f'Select room {room}',typical)
            assert selected['status']=='offer' and selected['pending_offer']['room']['id']==room
            assert len(snapshot('bookings'))==initial_count
            offer=selected['pending_offer']
            # Prepare a second stale offer while the same slot is still free.
            stale=Session('noura',draft=typical['draft'].copy())
            stale.options=[RoomOption.model_validate(typical['options'][0])]
            b.make_offer(stale,room)
            confirmed=say('Yes, book it',selected)
            persisted(confirmed,'Typical — English natural confirmation')
            assert len(snapshot('bookings'))==initial_count+1
            repeated=http.post('/api/bookings/confirm',json={'employee_id':'sara','session_id':selected['session_id'],'offer_id':offer['offer_id'],'language':'en'}).json()
            assert repeated['status']=='already_confirmed' and repeated['booking']['booking_id']==confirmed['booking']['booking_id']
            assert len(snapshot('bookings'))==initial_count+1
            record('duplicate_confirmation',{'passed':True,'booking_id':confirmed['booking']['booking_id']})
            try:
                b.confirm(stale,stale.pending_offer.offer_id)
                raise AssertionError('Stale conflict accepted')
            except b.BookingError as error: assert error.code=='conflict',error.code
            assert len(snapshot('bookings'))==initial_count+1
            record('stale_offer_transaction_conflict',{'passed':True})
            messy=say(f'أحتاج قاعة تدريب يوم {day+timedelta(days=1)} الساعة 10 صباحًا',employee='noura',language='ar')
            assert messy['status']=='missing' and set(messy['missing'])=={'attendees','end_time'},messy
            assert messy['draft']['room_type']=='training' and messy['draft']['start_time']=='10:00'
            follow=say('عدد الحضور 15 شخصًا والنهاية الساعة 12 ظهرًا',messy,employee='noura',language='ar')
            assert follow['status']=='options' and follow['draft']['date']==messy['draft']['date'] and follow['draft']['start_time']=='10:00',follow
            assert len(snapshot('bookings'))==initial_count+1
            chosen=say(f"أختار القاعة {follow['options'][0]['id']}",follow,employee='noura',language='ar')
            assert chosen['status']=='offer',chosen
            saved=say('أؤكد الحجز',chosen,employee='noura',language='ar');persisted(saved,'Messy — Arabic follow-up and natural confirmation')
            edge=say(f'I need training room {room} on {day} from 10:00 to 12:00 for 15 people.',employee='fahad')
            assert edge['status']=='options' and all(r['id']!=room for r in edge['options']),edge
            assert not edge['pending_offer'] and len(snapshot('bookings'))==initial_count+2
            record('edge_conflict_alternatives',{'passed':True,'blocked_room':room,'alternative_ids':[r['id'] for r in edge['options']]})
            no_offer=say('I confirm the booking',employee='fahad')
            assert no_offer['status']=='no_offer' and no_offer['booking'] is None,no_offer
            for message in [f'I need a training room on 2000-01-01 from 10:00 to 12:00 for 15 people.',
                            f'I need a training room on {day+timedelta(days=2)} from 14:00 to 13:00 for 15 people.',
                            f'I need a training room on {day+timedelta(days=2)} from 23:00 until 01:00 the next day for 15 people.']:
                invalid=say(message,employee='fahad')
                assert not invalid['pending_offer'] and not invalid['booking'] and invalid['status'] not in ['options','offer','confirmed'],invalid
            # Two genuinely simultaneous real transactions, distinct offers/sessions.
            concurrent=[]
            for employee in ['sara','fahad']:
                session=Session(employee,draft={'room_type':'training','date':str(day+timedelta(days=3)),
                                               'start_time':'10:00','end_time':'11:00','attendees':15})
                session.options=b.find_rooms(session.draft)
                b.make_offer(session,'T02');concurrent.append(session)
            def attempt(session):
                try:
                    result,repeated=b.confirm(session,session.pending_offer.offer_id)
                    return {'status':'confirmed','booking':result.model_dump(mode='json')}
                except b.BookingError as error:return {'status':error.code}
            with ThreadPoolExecutor(max_workers=2) as pool: results=list(pool.map(attempt,concurrent))
            assert sorted(r['status'] for r in results)==['confirmed','conflict'],results
            winner=next(r for r in results if r['status']=='confirmed');persisted(winner,'Concurrency — one winning transaction')
            record('concurrent_same_slot',{'passed':True,'results':results})
            after={name:snapshot(name) for name in before}
            for collection,records in before.items():
                assert all(after[collection].get(key)==value for key,value in records.items()),collection
            assert len(after['bookings'])==initial_count+3
            report['status']='passed';report['preexisting_records_preserved']=True
            report['final_counts']={key:len(value) for key,value in after.items()};save()
        except Exception as error:
            report['status']='failed';report['failure_type']=type(error).__name__;report['failure']=str(error);save()
            raise


if __name__=='__main__':main()
