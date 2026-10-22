"""Live concurrency recheck; leaves one identified fictional booking in place."""
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path
from .. import booking_service as b, firestore_store as store
from ..sessions import Session


def main():
    before={d.id:d.to_dict() for d in store.client().collection('bookings').stream()}
    day=(b.now_local()+timedelta(days=42)).date()
    used={r['start_at'].astimezone(b.RIYADH).date() for r in before.values()}
    while day in used:day+=timedelta(days=1)
    sessions=[]
    for employee in ['sara','fahad']:
        session=Session(employee,draft={'room_type':'training','date':str(day),'start_time':'10:00','end_time':'11:00','attendees':15})
        session.options=b.find_rooms(session.draft);b.make_offer(session,'T02');sessions.append(session)
    failures=[]
    original=store.commit_offer
    def observed(*args):
        try:return original(*args)
        except Exception as error:
            failures.append({'type':type(error).__name__,'context_type':type(error.__context__).__name__ if error.__context__ else None})
            raise
    store.commit_offer=observed
    def attempt(session):
        try:
            result,repeated=b.confirm(session,session.pending_offer.offer_id)
            return {'status':'confirmed','booking':result.model_dump(mode='json')}
        except b.BookingError as error:return {'status':error.code}
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(attempt,sessions))
    after={d.id:d.to_dict() for d in store.client().collection('bookings').stream()}
    report={'test':'real simultaneous same-slot transactions','date':str(day),'results':results,'exception_types':failures,
            'new_bookings':len(after)-len(before),'preexisting_bookings_unchanged':all(after.get(k)==v for k,v in before.items())}
    winner=next((r for r in results if r['status']=='confirmed'),None)
    if winner:
        booking=winner['booking'];key=f"{booking['room_id']}_{day.strftime('%Y%m%d')}"
        intervals=store.client().collection('room_days').document(key).get().to_dict()['active_intervals']
        report['matching_intervals']=sum(i['booking_id']==booking['booking_id'] for i in intervals)
    # Other authorized browser tests may write a different date simultaneously.
    # Count only this slot's new bookings, not the entire shared collection.
    report['new_slot_bookings']=sum(key not in before and value.get('room_id')=='T02' and value['start_at'].astimezone(b.RIYADH).date()==day for key,value in after.items())
    report['passed']=sorted(r['status'] for r in results)==['confirmed','conflict'] and report['new_slot_bookings']==1 and report['preexisting_bookings_unchanged'] and report.get('matching_intervals')==1
    Path('docs/evidence/m2/m2_concurrency_results.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report),flush=True)
    assert report['passed']


if __name__=='__main__':main()
