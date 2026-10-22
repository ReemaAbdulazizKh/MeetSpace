"""Owner-authorized real M3 checks; no deletes or edits of the five M2 bookings.
Creates identified fictional fixtures, cancels only a newly created fixture, and
restores the tested room's original maintenance state in finally.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from fastapi.testclient import TestClient
from .. import booking_service as b, firestore_store as store
from ..main import app
from ..sessions import get_session
from .verify_live_m2 import main as booking_regression


def snapshot(name):
    return {doc.id:doc.to_dict() for doc in store.client().collection(name).stream(timeout=15)}


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def main(report_path='docs/evidence/m3/m3_live_results.json', regression_path='docs/evidence/m3/m3_booking_regression.json'):
    before={name:snapshot(name) for name in ['rooms','employees','bookings','room_days']}
    report={'status':'running','started_riyadh':b.now_local().isoformat(),'initial_counts':{k:len(v) for k,v in before.items()},
            'initial_record_hashes':{k:{key:digest(value) for key,value in records.items()} for k,records in before.items()},'checks':[],'test_bookings':[]}
    path=Path(report_path)
    def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def record(name,**values):
        report['checks'].append({'name':name,**values});save();print(name,json.dumps(values,default=str),flush=True)
    save()
    # Actual model regression first, so API/UI mutations cannot contaminate its
    # exact write counts or provisional room searches.
    booking_regression(regression_path)
    record('Typical_Messy_Edge_regression',passed=True)
    day=(b.now_local()+timedelta(days=80)).date()
    used={value['start_at'].astimezone(b.RIYADH).date() for value in snapshot('bookings').values()}
    while day in used:day+=timedelta(days=1)
    report['fixture_day']=str(day)
    original_status=before['rooms']['M01']['status']
    assert original_status=='available','The verification requires an initially available M01; no state was reset.'
    def prepare(employee,room,start,end):
        session=get_session(employee)
        session.draft={'room_type':'meeting','date':str(day),'start_time':start,'end_time':end,'attendees':4}
        session.options=b.find_rooms(session.draft);b.make_offer(session,room)
        return session
    def create(employee,room,start,end,label):
        session=prepare(employee,room,start,end)
        result,_=b.confirm(session,session.pending_offer.offer_id)
        report['test_bookings'].append({'label':label,**result.model_dump(mode='json')});save()
        return result
    with TestClient(app) as http:
        try:
            all_data=http.get('/api/admin/bookings');assert all_data.status_code==200
            assert set(before['bookings']).issubset({item['booking_id'] for item in all_data.json()})
            for employee in before['employees']:
                response=http.get('/api/bookings',params={'employee_id':employee});assert response.status_code==200
                assert all(item['employee_id']==employee for item in response.json())
                assert {key for key,value in before['bookings'].items() if value['employee_id']==employee}.issubset({item['booking_id'] for item in response.json()})
            record('existing_calendar_records_and_employee_isolation',passed=True,existing_bookings=len(before['bookings']))
            first=create('fahad','M01','00:30','01:30','M3 API cancellation fixture')
            neighbor=create('noura','M01','01:30','02:30','M3 adjacent interval preservation fixture')
            ui=create('sara','M02','14:00','15:00','M3 browser cancellation fixture — not an M2 record')
            report['ui_cancel_fixture']=ui.model_dump(mode='json');save()
            first_before=store.read_booking(first.booking_id)
            rejected=http.post(f'/api/bookings/{first.booking_id}/cancel',json={'employee_id':'sara','confirmed':True})
            assert rejected.status_code==403 and store.read_booking(first.booking_id)==first_before
            no_consent=http.post(f'/api/bookings/{first.booking_id}/cancel',json={'employee_id':'fahad','confirmed':False})
            assert no_consent.status_code==400 and store.read_booking(first.booking_id)==first_before
            record('foreign_cancellation_and_missing_consent_rejected',passed=True,statuses=[403,400])
            canceled=http.post(f'/api/bookings/{first.booking_id}/cancel',json={'employee_id':'fahad','confirmed':True})
            assert canceled.status_code==200 and canceled.json()['status']=='canceled'
            actual=store.read_booking(first.booking_id);assert actual['status']=='canceled' and actual['canceled_at'] is not None
            key=f"M01_{day.strftime('%Y%m%d')}"
            interval=store.client().collection('room_days').document(key).get().to_dict()['active_intervals']
            assert [item['booking_id'] for item in interval]==[neighbor.booking_id]
            repeated=http.post(f'/api/bookings/{first.booking_id}/cancel',json={'employee_id':'fahad','confirmed':True})
            assert repeated.status_code==200 and store.read_booking(first.booking_id)==actual
            free=prepare('fahad','M01','00:30','01:30')
            neighbor_draft={**free.draft,'start_time':'01:30','end_time':'02:30'}
            assert 'M01' not in [room.id for room in b.find_rooms(neighbor_draft)]
            # API date remains UTC; this fixture's local day is the next UTC day.
            assert first.start_at.date().isoformat()!=str(day)
            record('cancellation_persisted_interval_released_and_neighbor_preserved',passed=True,booking_id=first.booking_id,utc_start=first.start_at,riyadh_day=str(day))
            before_maintenance=snapshot('bookings')
            enabled=http.patch('/api/admin/rooms/M01/status',json={'status':'maintenance'})
            assert enabled.status_code==200 and enabled.json()['status']=='maintenance'
            assert snapshot('bookings')==before_maintenance
            assert 'M01' not in [room.id for room in b.find_rooms(free.draft)]
            attempt=http.post('/api/bookings/confirm',json={'employee_id':'fahad','session_id':free.session_id,'offer_id':free.pending_offer.offer_id,'language':'en'})
            assert attempt.status_code==200 and attempt.json()['status']=='maintenance' and attempt.json()['booking'] is None
            assert snapshot('bookings')==before_maintenance
            restored=http.patch('/api/admin/rooms/M01/status',json={'status':'available'})
            assert restored.status_code==200 and restored.json()['status']=='available'
            assert 'M01' in [room.id for room in b.find_rooms(free.draft)]
            record('maintenance_blocks_search_and_pending_confirmation_preserves_all_bookings',passed=True)
            # Race a real maintenance update with an already-reviewed real offer.
            race=prepare('fahad','M01','12:00','13:00');offer_id=race.pending_offer.offer_id
            def confirm_race():
                return http.post('/api/bookings/confirm',json={'employee_id':'fahad','session_id':race.session_id,'offer_id':offer_id,'language':'en'}).json()
            with ThreadPoolExecutor(max_workers=2) as pool:
                confirmation=pool.submit(confirm_race)
                maintenance=pool.submit(http.patch,'/api/admin/rooms/M01/status',json={'status':'maintenance'})
                result=confirmation.result();changed=maintenance.result()
            assert changed.status_code==200 and changed.json()['status']=='maintenance'
            assert result['status'] in ['confirmed','maintenance'],result
            if result['status']=='confirmed':
                report['test_bookings'].append({'label':'M3 maintenance/confirmation race — commit preceded maintenance',**result['booking']});save()
                assert store.read_booking(result['booking']['booking_id'])['status']=='confirmed'
            else:assert store.read_booking(offer_id) is None
            record('concurrent_maintenance_and_confirmation',passed=True,result=result['status'],room_status='maintenance')
            response=http.get('/api/admin/bookings');assert response.status_code==200
            assert len(response.json())==len(snapshot('bookings'))
            record('admin_calendar_includes_all_persisted_statuses',passed=True,count=len(response.json()))
        except Exception as error:
            report['status']='failed';report['failure_type']=type(error).__name__;report['failure']=str(error);save();raise
        finally:
            restored=http.patch('/api/admin/rooms/M01/status',json={'status':original_status})
            report['tested_room_original_status_restored']=restored.status_code==200 and restored.json()['status']==original_status;save()
    after={name:snapshot(name) for name in before}
    for collection,records in before.items():
        assert all(after[collection].get(key)==value for key,value in records.items()),collection
    report['all_preexisting_records_unchanged']=True
    report['final_counts']={k:len(v) for k,v in after.items()};report['status']='passed';save()
    print('M3 LIVE CHECKS PASSED',json.dumps(report['final_counts']),flush=True)


if __name__=='__main__':
    try:
        main()
    except Exception as error:
        path=Path('docs/evidence/m3/m3_live_results.json')
        report=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        report.update(status='failed',failure_type=type(error).__name__,failure=str(error))
        path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
        raise
