"""Actual Qwen selection/consent/correction checks; Firestore writes forbidden."""
import json
import time
from pathlib import Path
from unittest.mock import patch
from .. import agent, booking_service as b, chat_service
from ..sessions import Session
from .benchmark_m4 import Observe, state, sha, fixtures


def main():
    before=state();fixture=fixtures()
    report={'status':'running','scope':'Real Qwen + Firestore reads; commit forbidden; positive consent extraction only',
            'initial_state_hash':sha(before),'checks':[]}
    path=Path('docs/evidence/m4/speed_readonly_regression.json')
    def save():path.write_text(json.dumps(report,ensure_ascii=False,indent=2,default=str)+'\n',encoding='utf-8')
    def observed(label,operation):
        observer=Observe();started=time.perf_counter()
        with patch.object(agent,'urlopen',observer):result=operation()
        report['checks'].append({'name':label,'elapsed_seconds':time.perf_counter()-started,
                                 'model_call_count':len(observer.calls),'model_calls':observer.calls,
                                 'result':result.model_dump(mode='json')})
        save();print(label,len(observer.calls),'model call(s)',flush=True)
        assert len(observer.calls)==1
        return result
    save()
    try:
        with patch.object(b,'confirm',side_effect=AssertionError('Read-only verification forbids commit')) as commit:
            for language,select,consent,correction,negative in [
                ('en','Select room T02','Yes, book it','Change the attendee count to 20','Do not book it'),
                ('ar','أختار القاعة T02','أؤكد الحجز','غير عدد الحضور إلى 20 شخصًا','لا تحجز')]:
                session=Session('sara',draft={'room_type':'training','date':fixture['typical_date'],
                                             'start_time':'10:00','end_time':'12:00','attendees':15})
                session.options=b.find_rooms(session.draft)
                selected=observed(language+'_select',lambda:chat_service.process(session,select,language))
                assert selected.status=='offer' and selected.pending_offer.room.id=='T02'
                positive=observed(language+'_explicit_consent_extraction',lambda:agent.extract(consent,session,b.now_local()))
                assert positive.intent=='confirm' and positive.explicit_confirmation and chat_service.explicit_assent(consent)
                assert positive.language==language
                negative_result=observed(language+'_negative_consent_extraction',lambda:agent.extract(negative,session,b.now_local()))
                assert not negative_result.explicit_confirmation and not chat_service.explicit_assent(negative)
                changed=observed(language+'_material_correction',lambda:chat_service.process(session,correction,language))
                assert changed.draft['attendees']==20 and session.pending_offer is None
                assert all(option.capacity>=20 for option in changed.options)
                no_offer=observed(language+'_confirmation_after_invalidated_offer',lambda:chat_service.process(session,consent,language))
                assert no_offer.status=='no_offer' and no_offer.booking is None
            commit.assert_not_called()
        after=state();report.update(status='passed',database_unchanged=before==after,final_state_hash=sha(after))
        assert report['database_unchanged']
        save()
    except Exception as error:
        report.update(status='failed',error_type=type(error).__name__,error=str(error));save();raise


if __name__=='__main__':main()
