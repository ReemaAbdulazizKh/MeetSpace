"""Summarize observed benchmark files without inventing missing observations."""
import json
import statistics
from pathlib import Path


def main(filenames=None,output='docs/evidence/m4/comparison.json'):
    reports=[]
    for filename in (filenames or ['baseline_A','optimized_B','optimized_B2','technical_C']):
        path=Path(f'docs/evidence/m4/{filename}.json')
        if not path.exists():continue
        data=json.loads(path.read_text(encoding='utf-8'))
        if data['status']=='running':continue
        rows=[]
        for scenario in ['Typical','Messy','Edge']:
            trials=[t for t in data['trials'] if t['scenario']==scenario]
            turns=[turn for trial in trials for turn in trial['turns']]
            calls=[call for turn in turns for call in turn['model_calls']]
            extra=0;languages=0;fully_correct=0
            for trial in trials:
                language_ok=True
                for index,turn in enumerate(trial['turns']):
                    if not(scenario=='Messy' and index==0) and turn['response'].get('status')=='missing':extra+=1
                    extraction=next((c.get('output') for c in turn['model_calls'] if c.get('schema')=='Extraction'),None)
                    try:wrong=json.loads(extraction)['language']!=('ar' if scenario=='Messy' else 'en')
                    except (ValueError,TypeError,KeyError):wrong=True
                    languages+=wrong;language_ok&=not wrong
                fully_correct+=trial['correct'] and language_ok
            rows.append({'scenario':scenario,'trials':len(trials),'correct_trials':sum(t['correct'] for t in trials),
                         'fully_correct_trials_including_language':fully_correct,
                         'individual_seconds':[t['elapsed_seconds'] for t in trials],
                         'mean_seconds':statistics.mean(t['elapsed_seconds'] for t in trials),
                         'median_seconds':statistics.median(t['elapsed_seconds'] for t in trials),
                         'calls_per_trial':[t['model_call_count'] for t in trials],
                         'turns_per_trial':[t['conversation_turns'] for t in trials],
                         'unnecessary_clarification_turns':extra,'extraction_language_errors':languages,
                         'discarded_wording_calls':sum(turn['response'].get('response_source')=='server' and any(c.get('schema')=='NaturalReply' for c in turn['model_calls']) for turn in turns),
                         'mean_model_seconds_per_trial':sum(c.get('total_duration',0)/1e9 for c in calls)/len(trials),
                         'mean_load_seconds_per_trial':sum(c.get('load_duration',0)/1e9 for c in calls)/len(trials),
                         'mean_prompt_eval_seconds_per_trial':sum(c.get('prompt_eval_duration',0)/1e9 for c in calls)/len(trials),
                         'mean_decode_seconds_per_trial':sum(c.get('eval_duration',0)/1e9 for c in calls)/len(trials)})
        reports.append({'label':data['label'],'status':data['status'],'database_unchanged':data['database_unchanged'],
                        'prompt_sha256':data['prompt_sha256'],'warmup':data['warmup'],'scenarios':rows})
    Path(output).write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for report in reports:
        for row in report['scenarios']:
            print(report['label'],row['scenario'],round(row['mean_seconds'],2),f"{row['correct_trials']}/{row['trials']}",row['calls_per_trial'],row['unnecessary_clarification_turns'])


if __name__=='__main__':main()
