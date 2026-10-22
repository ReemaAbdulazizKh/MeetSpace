"""Fresh-process, read-only Firestore audit after the M3 browser checks."""
import hashlib
import json
from pathlib import Path
from .. import firestore_store as store, booking_service as service


def main(milestone='m3'):
    live=json.loads(Path(f'docs/evidence/{milestone}/{milestone}_live_results.json').read_text(encoding='utf-8'))
    regression=json.loads(Path(f'docs/evidence/{milestone}/{milestone}_booking_regression.json').read_text(encoding='utf-8'))
    browser=json.loads(Path(f'docs/evidence/{milestone}/{milestone}_browser_results.json').read_text(encoding='utf-8'))
    assert live['status']==regression['status']==browser['status']=='passed'
    data={name:{doc.id:doc.to_dict() for doc in store.client().collection(name).stream(timeout=15)} for name in ['rooms','employees','bookings','room_days']}
    for name,hashes in live['initial_record_hashes'].items():
        for key,expected in hashes.items():
            actual=hashlib.sha256(json.dumps(data[name][key],sort_keys=True,default=str).encode()).hexdigest()
            assert actual==expected,(name,key)
    assert data['rooms']['M01']['status']=='available'
    canceled_by_browser=browser['canceled_fixture']
    assert data['bookings'][canceled_by_browser]['status']=='canceled'
    assert data['bookings'][canceled_by_browser]['canceled_at'] is not None
    disclosed=regression['test_bookings']+live['test_bookings']
    fixtures=[]
    for expected in disclosed:
        booking=data['bookings'][expected['booking_id']]
        fixtures.append({'label':expected['label'],'booking_id':expected['booking_id'],'employee_id':booking['employee_id'],
                         'room_id':booking['room_id'],'start_at':booking['start_at'],'end_at':booking['end_at'],'status':booking['status']})
    for key,booking in data['bookings'].items():
        day=booking['start_at'].astimezone(service.RIYADH).date()
        assert day==booking['end_at'].astimezone(service.RIYADH).date()
        assert booking['start_at'].utcoffset().total_seconds()==0
        day_key=f"{booking['room_id']}_{day.strftime('%Y%m%d')}"
        intervals=data['room_days'][day_key]['active_intervals']
        matches=[item for item in intervals if item['booking_id']==key]
        assert len(matches)==(1 if booking['status']=='confirmed' else 0),(key,booking['status'])
        if matches:assert matches[0]['start_at']==booking['start_at'] and matches[0]['end_at']==booking['end_at']
    for day in data['room_days'].values():
        for interval in day['active_intervals']:
            assert data['bookings'][interval['booking_id']]['status']=='confirmed'
    confirmed=[booking for booking in data['bookings'].values() if booking['status']=='confirmed']
    for index,booking in enumerate(confirmed):
        for other in confirmed[index+1:]:
            if booking['room_id']==other['room_id']:
                assert not service.overlap(booking['start_at'],booking['end_at'],[other])
    report={'status':'passed','audited_riyadh':service.now_local().isoformat(),
            'preexisting_records_all_unchanged':True,'preexisting_bookings_preserved':len(live['initial_record_hashes']['bookings']),
            'all_intervals_match_booking_status':True,'no_confirmed_overlaps':True,'tested_room_original_status_restored':True,
            'collection_counts':{name:len(items) for name,items in data.items()},'booking_status_counts':{status:sum(item['status']==status for item in data['bookings'].values()) for status in ['confirmed','canceled']},
            'new_disclosed_test_bookings':fixtures}
    Path(f'docs/evidence/{milestone}/{milestone}_persistence_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    print(json.dumps({key:value for key,value in report.items() if key!='new_disclosed_test_bookings'}))


if __name__=='__main__':main()
