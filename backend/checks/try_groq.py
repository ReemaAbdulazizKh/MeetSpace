"""Real Groq extraction checks only: fictional context, no Firestore imports/writes.

Run: .venv/Scripts/python -m backend.checks.try_groq
This does not switch the running app's provider or create/confirm a booking.
"""
import json
from datetime import datetime
from pathlib import Path
from time import perf_counter
from zoneinfo import ZoneInfo
from .. import agent
from ..config import GROQ_API_KEY, GROQ_MODEL
from ..sessions import Session
from ..schemas import RoomOption


def main():
    output = Path(__file__).resolve().parents[2] / 'docs/evidence/groq/trial.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {'provider': 'groq', 'model': GROQ_MODEL,
              'scope': 'Live extraction only with fictional context; no database access or booking actions.',
              'checked_riyadh': datetime.now(ZoneInfo('Asia/Riyadh')).isoformat(), 'cases': []}
    if not GROQ_API_KEY:
        report.update(status='not_run', reason='GROQ_API_KEY is not configured; no API request sent.')
    else:
        # Only this short-lived check uses Groq; no mutation of .env or running app.
        agent.MODEL_PROVIDER = 'groq'
        now = datetime(2026, 10, 22, 12, tzinfo=ZoneInfo('Asia/Riyadh'))
        known = dict(room_type='meeting', date='2027-02-15', start_time='10:00', end_time='12:00', attendees=8)
        missing = Session('sara', draft={'room_type': 'meeting', 'date': '2027-02-15'})
        selected = Session('sara', draft=known.copy())
        selected.options = [RoomOption(id='M03', name={'ar': 'قاعة تجريبية', 'en': 'Fictional room'},type='meeting',capacity=10)]
        cases = [
            ('typical_ar', 'أحتاج قاعة اجتماعات يوم 2027-02-15 من الساعة 10:00 صباحًا إلى 12:00 ظهرًا لعدد 8 أشخاص', Session('sara'), lambda x: all(getattr(x,k)==v for k,v in known.items()) and x.language=='ar' and not x.explicit_confirmation),
            ('typical_en', 'I need a meeting room on 2027-02-15 from 10:00 AM to 12:00 noon for 8 attendees.', Session('sara'), lambda x: all(getattr(x,k)==v for k,v in known.items()) and x.language=='en' and not x.explicit_confirmation),
            ('missing_ar', 'أحتاج قاعة اجتماعات يوم 2027-02-15', Session('sara'), lambda x: x.attendees is None and x.start_time is None and x.end_time is None and x.date=='2027-02-15'),
            ('complete_missing_ar', 'من الساعة 10 صباحًا إلى 12 ظهرًا وعددنا 8 أشخاص', missing, lambda x: x.start_time=='10:00' and x.end_time=='12:00' and x.attendees==8),
            ('select_displayed_room_ar', 'أختار القاعة M03', selected, lambda x: x.intent=='select' and x.selected_room=='M03' and not x.explicit_confirmation),
            ('negative_consent_ar', 'لا تحجز', selected, lambda x: not x.explicit_confirmation),
        ]
        for name, message, session, accepts in cases:
            started = perf_counter()
            try:
                value = agent.extract(message, session, now)
                item = {'case': name, 'input': message, 'session_draft': session.draft,
                        'elapsed_seconds': round(perf_counter()-started,3),
                        'observed': value.model_dump(), 'acceptance_met': bool(accepts(value))}
            except agent.AgentUnavailable as failure:
                item = {'case': name, 'elapsed_seconds': round(perf_counter()-started,3),
                        'acceptance_met': False, 'safe_error': str(failure)}
            report['cases'].append(item)
            if 'safe_error' in item:
                break  # No automatic retries or fallback; preserve real failure.
        report['status'] = 'passed' if len(report['cases'])==len(cases) and all(x['acceptance_met'] for x in report['cases']) else 'failed'
    output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'status': report['status'], 'cases_run': len(report['cases']),
                      'evidence': str(output), 'reason': report.get('reason')},ensure_ascii=False))


if __name__ == '__main__':
    main()
