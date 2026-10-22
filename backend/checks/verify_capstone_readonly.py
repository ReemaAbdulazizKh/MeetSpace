"""Capstone evidence probe. Reads existing records; never confirms or changes data."""
import json
from pathlib import Path
from datetime import timedelta
from fastapi.testclient import TestClient
from .. import booking_service as b
from ..main import app
from .benchmark_m4 import state,sha


def main():
    before=state();original=before['bookings']['2f9692be654b4aaa872eef497c8e72b3']
    assert original['status']=='confirmed'
    start=original['start_at'].astimezone(b.RIYADH)+timedelta(hours=1)
    end=original['end_at'].astimezone(b.RIYADH)+timedelta(hours=1)
    room=before['rooms'][original['room_id']]
    draft={'room_type':room['type'],'date':str(start.date()),'start_time':start.strftime('%H:%M'),
           'end_time':end.strftime('%H:%M'),'attendees':min(5,room['capacity'])}
    options=b.find_rooms(draft)
    assert original['room_id'] not in {r.id for r in options}
    tests={}
    for name,change in [('past',{'date':'2000-01-01'}),('reverse_end',{'start_time':'14:00','end_time':'13:00'})]:
        try:b.validate({**draft,**change});raise AssertionError('Invalid times accepted')
        except b.BookingError as error:tests[name]=error.code
    try:b.check_room(room,room['capacity']+1,room['type']);raise AssertionError('Capacity accepted')
    except b.BookingError as error:tests['capacity']=error.code
    with TestClient(app) as http:
        own=http.get('/api/bookings',params={'employee_id':'sara'});assert own.status_code==200
        assert all(v['employee_id']=='sara' for v in own.json())
        admin=http.get('/api/admin/bookings');assert admin.status_code==200
    after=state();assert before==after
    report={'checked_riyadh':b.now_local().isoformat(),'status':'passed','scope':'Read-only current probe; no new booking or maintenance changes',
            'partial_overlap':{'existing_booking_id':'2f9692be654b4aaa872eef497c8e72b3','room_id':original['room_id'],
              'existing_riyadh_start':original['start_at'].astimezone(b.RIYADH).isoformat(),
              'existing_riyadh_end':original['end_at'].astimezone(b.RIYADH).isoformat(),
              'requested_draft':draft,'requested_employee':'fahad' if original['employee_id']!='fahad' else 'sara',
              'room_excluded':True,'confirmed_transaction_not_attempted':True},
            'invalid_inputs':tests,'employee_view_owned_records_only':True,
            'admin_without_auth_http_status':admin.status_code,'secure_authentication_present':False,
            'database_unchanged':True,'before_hash':sha(before),'after_hash':sha(after)}
    Path('docs/evidence/capstone/readiness_probe.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__=='__main__':main()
