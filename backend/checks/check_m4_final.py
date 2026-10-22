"""Read-only final checks after restarting the local backend. Never reads secrets."""
import csv
import hashlib
import json
import subprocess
from pathlib import Path
from urllib.request import urlopen
from ..config import PROJECT_ID


def main():
    def api(route):
        with urlopen(f'http://127.0.0.1:8000/api/{route}',timeout=30) as response:
            return json.load(response)
    health=api('health');assert health['status']=='ok'
    bookings=api('admin/bookings');rooms=api('rooms');employees=api('employees')
    audit=json.loads(Path('docs/evidence/m4/m4_persistence_audit.json').read_text(encoding='utf-8'))
    live=json.loads(Path('docs/evidence/m4/m4_live_results.json').read_text(encoding='utf-8'))
    expected=set(live['initial_record_hashes']['bookings'])|{b['booking_id'] for b in audit['new_disclosed_test_bookings']}
    assert {b['booking_id'] for b in bookings}==expected
    assert len(bookings)==audit['collection_counts']['bookings']==17
    assert len(rooms)==10 and len(employees)==3
    assert {s:sum(b['status']==s for b in bookings) for s in ['confirmed','canceled']}==audit['booking_status_counts']
    assert PROJECT_ID=='smart-room-booking-agent'
    credential_paths=list(Path('backend').glob('*firebase-adminsdk*.json'))
    assert credential_paths and Path('.env').is_file()
    for path in [Path('.env'),*credential_paths]:
        assert subprocess.run(['git','check-ignore','--quiet','--',str(path)],capture_output=True).returncode==0
        assert not subprocess.run(['git','ls-files','--',str(path)],capture_output=True,text=True).stdout.strip()
    rows=list(csv.reader(Path('docs/m4/productivity_results.csv').open(encoding='utf-8',newline='')))
    assert len(rows)==13 and all(len(row)==len(rows[0]) and not any(row[3:]) for row in rows[1:])
    a=json.loads(Path('docs/evidence/m4/baseline_A.json').read_text(encoding='utf-8'))
    c=json.loads(Path('docs/evidence/m4/technical_C.json').read_text(encoding='utf-8'))
    assert hashlib.sha256(Path('docs/archive/prompt_versions/m4_A_baseline.md').read_bytes()).hexdigest()==a['prompt_sha256']
    assert hashlib.sha256(Path('backend/prompts/booking_agent.md').read_bytes()).hexdigest()==c['prompt_sha256']
    report={'status':'passed','health_after_backend_restart':health,'persisted_booking_ids_and_statuses_match_audit':True,
            'collection_counts':audit['collection_counts'],'booking_status_counts':audit['booking_status_counts'],
            'credentials_and_env_ignored_untracked':True,'manual_measurement_result_cells_all_blank':True,
            'baseline_preserved_and_production_prompt_matches_C':True,'firestore_project':PROJECT_ID}
    Path('docs/evidence/m4/m4_final_checks.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
