"""Real Firestore selection reads, zero model calls, no booking confirmation."""
import json
import time
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from ..main import app
from .. import agent, booking_service as b
from ..sessions import get_session
from .benchmark_m4 import state, sha, fixtures, Observe


def main():
    before=state();fixture=fixtures();checks=[]
    with TestClient(app) as http:
        for language in ['ar','en']:
            session=get_session('sara')
            session.draft={'room_type':'meeting','date':fixture['typical_date'],
                           'start_time':'10:00','end_time':'12:00','attendees':8}
            session.options=b.find_rooms(session.draft)
            assert session.options
            room_id=session.options[0].id;observer=Observe();started=time.perf_counter()
            with patch.object(agent,'urlopen',observer):
                result=http.post('/api/chat',json={'employee_id':'sara','session_id':session.session_id,
                    'message':'Select room '+room_id,'action':'select_room','room_id':room_id,'language':language})
            elapsed=time.perf_counter()-started;data=result.json()
            assert result.status_code==200 and data['status']=='offer' and data['booking'] is None
            assert data['pending_offer']['room']['id']==room_id and not observer.calls
            checks.append({'language':language,'room_id':room_id,'elapsed_seconds':elapsed,
                           'model_calls':len(observer.calls),'status':data['status'],'booking':data['booking']})
    after=state();assert before==after
    report={'status':'passed','scope':'Real Firestore reads, prepared search sessions, no confirmation',
            'checks':checks,'database_unchanged':True,'initial_hash':sha(before),'final_hash':sha(after)}
    Path('docs/evidence/m4/structured_selection_checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
