"""Read-only actual A/B benchmark: real FastAPI/Ollama/Firestore, no bookings.
Instrumentation is harness-only; prompt path is patched without altering runtime
code. Never caches model output or skips a model call in A/B prompt comparison.
"""
import argparse
import hashlib
import io
import json
import platform
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from urllib.request import Request, urlopen
from fastapi.testclient import TestClient
from ..main import app
from .. import agent, booking_service as b, firestore_store as store
from ..config import MODEL, OLLAMA_URL


def state():
    return {name:{doc.id:doc.to_dict() for doc in store.client().collection(name).stream(timeout=15)} for name in ['rooms','employees','bookings','room_days']}


def sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,default=str).encode()).hexdigest()


def fixtures():
    path=Path('docs/evidence/m4/benchmark_fixtures.json')
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    before=state()
    day=(b.now_local()+timedelta(days=100)).date()
    used={item['start_at'].astimezone(b.RIYADH).date() for item in before['bookings'].values()}
    while day in used or day+timedelta(days=1) in used:day+=timedelta(days=2)
    edge=before['bookings']['2f9692be654b4aaa872eef497c8e72b3']
    assert edge['status']=='confirmed'
    result={'fixed_context_time':b.now_local().replace(microsecond=0).isoformat(),
            'typical_date':str(day),'messy_date':str(day+timedelta(days=1)),
            'edge_booking_id':'2f9692be654b4aaa872eef497c8e72b3','edge_room_id':edge['room_id'],
            'edge_date':edge['start_at'].astimezone(b.RIYADH).date().isoformat(),
            'initial_counts':{k:len(v) for k,v in before.items()},'initial_state_hash':sha(before)}
    path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');return result


class Observe:
    def __init__(self):self.calls=[];self.original=agent.urlopen
    def __call__(self,request,**kwargs):
        started=time.perf_counter();payload=json.loads(request.data)
        item={'schema':payload.get('format',{}).get('title'),'input_characters':sum(len(m['content']) for m in payload['messages']),
              'options':payload.get('options'),'started_riyadh':b.now_local().isoformat()}
        try:
            with self.original(request,**kwargs) as response:raw=response.read()
            parsed=json.loads(raw)
            for key in ['total_duration','load_duration','prompt_eval_count','prompt_eval_duration','eval_count','eval_duration','done_reason']:
                item[key]=parsed.get(key)
            item['output']=parsed.get('message',{}).get('content')
            item['wall_seconds']=time.perf_counter()-started;self.calls.append(item)
            return io.BytesIO(raw)
        except Exception as error:
            item.update(error_type=type(error).__name__,wall_seconds=time.perf_counter()-started)
            self.calls.append(item);raise


def warmup():
    payload={'model':MODEL,'messages':[{'role':'user','content':'Return JSON {"ready":true} only.'}],
             'format':'json','stream':False,'options':{'temperature':0,'num_predict':24,'num_ctx':4096}}
    started=time.perf_counter()
    with urlopen(Request(f'{OLLAMA_URL}/api/chat',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'}),timeout=120) as response:
        data=json.load(response)
    return {'excluded_from_comparison':True,'wall_seconds':time.perf_counter()-started,
            **{key:data.get(key) for key in ['total_duration','load_duration','prompt_eval_duration','eval_duration','eval_count']}}


def expected_options(draft,current):
    start,end=b.validate(draft)
    result=[]
    for key,room in current['rooms'].items():
        if room['status']!='available' or room['capacity']<draft['attendees']:continue
        if any(item['room_id']==key and item['status']=='confirmed' and start<item['end_at'] and end>item['start_at'] for item in current['bookings'].values()):continue
        result.append((key,room['type']))
    matching=[key for key,kind in result if kind==draft['room_type']]
    return set(matching or [key for key,_ in result])


def main(label,prompt_path,trials,output):
    prompt_path=Path(prompt_path);output=Path(output);output.parent.mkdir(exist_ok=True,parents=True)
    fixture=fixtures();before=state();fixed=datetime.fromisoformat(fixture['fixed_context_time'])
    report={'label':label,'prompt_path':prompt_path.as_posix(),'prompt_sha256':hashlib.sha256(prompt_path.read_bytes()).hexdigest(),
            'started_riyadh':b.now_local().isoformat(),'model':MODEL,'python':platform.python_version(),
            'code_sha256':{name:hashlib.sha256(Path(f'backend/{name}.py').read_bytes()).hexdigest() for name in ['agent','chat_service','schemas','booking_service']},
            'endpoint':'FastAPI TestClient POST /api/chat; server HTTP end-to-end, not browser/human time',
            'scope':'provisional room search / missing-details resolution only; confirmation is separately regression-tested',
            'fixture':fixture,'initial_state_hash':sha(before),'trials':[],'status':'running'}
    def save():output.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    save();report['warmup']=warmup();save()
    cases=[('Typical','en',[f"I need a training room on {fixture['typical_date']} from 10:00 to 12:00 for 15 people."],
            {'room_type':'training','date':fixture['typical_date'],'start_time':'10:00','end_time':'12:00','attendees':15}),
           ('Messy','ar',[f"أحتاج قاعة تدريب يوم {fixture['messy_date']} الساعة 10 صباحًا",'عدد الحضور 15 شخصًا والنهاية الساعة 12 ظهرًا'],
            {'room_type':'training','date':fixture['messy_date'],'start_time':'10:00','end_time':'12:00','attendees':15}),
           ('Edge','en',[f"I need training room {fixture['edge_room_id']} on {fixture['edge_date']} from 10:00 to 12:00 for 15 people."],
            {'room_type':'training','date':fixture['edge_date'],'start_time':'10:00','end_time':'12:00','attendees':15,'selected_room':fixture['edge_room_id']})]
    with patch.object(agent,'PROMPT_PATH',prompt_path),patch.object(b,'now_local',return_value=fixed),TestClient(app) as http:
        for repeat in range(1,trials+1):
            for name,language,messages,expected in cases:
                trial={'scenario':name,'repeat':repeat,'turns':[],'expected_draft':expected,'correct':True,'errors':[]}
                session_id=None
                for index,message in enumerate(messages):
                    observer=Observe();started=time.perf_counter()
                    with patch.object(agent,'urlopen',observer):
                        response=http.post('/api/chat',json={'employee_id':'sara','session_id':session_id,'message':message,'language':language})
                    elapsed=time.perf_counter()-started;data=response.json();session_id=data.get('session_id')
                    turn={'input':message,'http_status':response.status_code,'elapsed_seconds':elapsed,'model_calls':observer.calls,'model_call_count':len(observer.calls),'response':data}
                    errors=[]
                    expected_fields=expected.copy()
                    if name=='Messy' and index==0:
                        expected_fields.pop('end_time');expected_fields.pop('attendees')
                        if data.get('status')!='missing' or set(data.get('missing',[]))!={'end_time','attendees'}:errors.append('wrong/missing clarification fields')
                        if data.get('options'):errors.append('offered rooms before required fields')
                    else:
                        if data.get('status')!='options':errors.append('expected provisional room options')
                        expected_ids=expected_options(expected,before)
                        if {room['id'] for room in data.get('options',[])}!=expected_ids:errors.append('incorrect recommendations')
                    for key,value in expected_fields.items():
                        if data.get('draft',{}).get(key)!=value:errors.append(f'incorrect extracted/retained {key}')
                    if data.get('booking') is not None:errors.append('unexpected booking write')
                    turn['correct']=not errors;turn['errors']=errors
                    trial['correct']&=not errors;trial['errors'].extend(errors);trial['turns'].append(turn)
                    trial['elapsed_seconds']=sum(item['elapsed_seconds'] for item in trial['turns'])
                    trial['model_call_count']=sum(item['model_call_count'] for item in trial['turns'])
                    trial['conversation_turns']=len(trial['turns'])
                    report['trials']=[item for item in report['trials'] if (item['scenario'],item['repeat'])!=(name,repeat)]+[trial]
                    save();print(label,name,repeat,index+1,round(elapsed,2),'seconds','calls',len(observer.calls),'correct',not errors,flush=True)
    after=state();report['final_state_hash']=sha(after);report['database_unchanged']=after==before
    report['status']='passed' if report['database_unchanged'] and all(trial['correct'] for trial in report['trials']) else 'failed'
    report['finished_riyadh']=datetime.now(b.RIYADH).isoformat();save()
    assert report['database_unchanged'],'Read-only benchmark changed Firestore state'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--label',required=True);parser.add_argument('--prompt',required=True);parser.add_argument('--trials',type=int,default=2);parser.add_argument('--output',required=True)
    args=parser.parse_args();main(args.label,args.prompt,args.trials,args.output)
