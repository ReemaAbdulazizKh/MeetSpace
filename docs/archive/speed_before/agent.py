import json
import re
from datetime import datetime
from pathlib import Path
from urllib.request import Request, urlopen
from pydantic import Field
from .config import OLLAMA_URL, MODEL
from .schemas import Extraction, StrictModel

PROMPT_PATH = Path(__file__).parent / 'prompts' / 'booking_agent.md'


class AgentUnavailable(Exception):
    pass


class NaturalReply(StrictModel):
    reply: str = Field(min_length=1, max_length=600)


def structured(messages, schema):
    payload = {'model': MODEL, 'messages': messages, 'format': schema.model_json_schema(),
               'stream': False, 'keep_alive': -1,
               'options': {'temperature': 0, 'num_predict': 600, 'num_ctx': 4096}}
    try:
        request = Request(f'{OLLAMA_URL}/api/chat', data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
        if not result.get('done') or result.get('done_reason') == 'length':
            raise ValueError('Incomplete generation')
        return schema.model_validate_json(result['message']['content'])
    except Exception:
        raise AgentUnavailable('Local model unavailable or invalid structured response.') from None


def prompt(mode):
    source = PROMPT_PATH.read_text(encoding='utf-8')
    intro, sections = source.split('## EXTRACT', 1)
    extraction, response = sections.split('## RESPOND', 1)
    return intro + '\nMode: ' + mode + '\n' + (extraction if mode == 'EXTRACT' else response)


def extract(message, session, now):
    context = {'mode': 'EXTRACT', 'current_riyadh_datetime': now.isoformat(),
               'draft': session.draft, 'displayed_rooms': [r.model_dump() for r in session.options],
               'pending_offer': session.pending_offer.model_dump() if session.pending_offer else None,
               'recent_messages': session.messages[-6:], 'latest_message': message}
    context.pop('latest_message')
    return structured([{'role': 'system', 'content': prompt('EXTRACT') + '\nServer context:\n' + json.dumps(context, ensure_ascii=False)},
                       {'role': 'user', 'content': message}], Extraction)


def natural_reply(message, language, status, missing, fallback):
    # The model supplies wording, never authoritative booking details or success.
    # Missing fields already have an exact bilingual server question. A second
    # generation only repeats it; extraction still always uses the real model.
    if status in {'missing', 'confirmed', 'already_confirmed', 'unknown', 'error'}:
        return fallback, 'server'
    context = {'mode': 'RESPOND', 'language': language, 'latest_message': message,
               'status': status, 'missing_fields': missing, 'server_facts': fallback}
    try:
        reply = structured([{'role': 'system', 'content': prompt('RESPOND')},
                            {'role': 'user', 'content': json.dumps(context, ensure_ascii=False)}], NaturalReply).reply
        unsafe = r'\d|booked|reserved|confirmed|saved|success|done|تم|حُجز|محجوز|حجزت|أكدت|تأكيدك|سجلت|حفظت'
        if status not in {'options', 'offer'}:
            unsafe += r'|available|متاح|صيانة|maintenance'
        if re.search(unsafe, reply, re.I):
            return fallback, 'server'
        return reply + '\n' + fallback, 'ollama'
    except AgentUnavailable:
        return fallback, 'server'
