import json
import re
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from .config import OLLAMA_URL, MODEL, MODEL_PROVIDER, GROQ_API_KEY, GROQ_MODEL
from .schemas import Extraction

PROMPT_PATH = Path(__file__).parent / 'prompts' / 'booking_agent.md'


class AgentUnavailable(Exception):
    pass


def structured(messages, schema):
    if MODEL_PROVIDER == 'groq':
        return structured_groq(messages, schema)
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


def structured_groq(messages, schema):
    if not GROQ_API_KEY:
        raise AgentUnavailable('Groq API key is not configured.')
    # JSON mode guarantees syntax only. The same strict Python schema remains
    # authoritative; never fall back to fabricated or partially parsed fields.
    contract = {'role': 'system', 'content': 'Return only a JSON object matching this schema: '
                + json.dumps(schema.model_json_schema())}
    payload = {'model': GROQ_MODEL, 'messages': [contract, *messages],
               'response_format': {'type': 'json_object'}, 'temperature': 0,
               'max_completion_tokens': 600, 'reasoning_effort': 'none', 'stream': False}
    try:
        request = Request('https://api.groq.com/openai/v1/chat/completions',
                          data=json.dumps(payload).encode(),
                          headers={'Content-Type': 'application/json',
                                   'User-Agent': 'MeetSpace/0.3',
                                   'Authorization': f'Bearer {GROQ_API_KEY}'})
        with urlopen(request, timeout=45) as response:
            result = json.load(response)
        choice = result['choices'][0]
        if choice.get('finish_reason') != 'stop':
            raise ValueError('Incomplete generation')
        return schema.model_validate_json(choice['message']['content'])
    except HTTPError as error:
        # Never return provider response bodies, request headers or keys to UI/logs.
        raise AgentUnavailable(f'Groq request failed (HTTP {error.code}).') from None
    except Exception:
        raise AgentUnavailable('Groq unavailable or invalid structured response.') from None


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


def natural_reply(message, language, status, missing, fallback, acknowledgment=None):
    # Wording arrives with the extraction in ONE model call. The server appends
    # actual results; an optional acknowledgment never decides or describes them.
    if status not in {'options', 'offer'} or not acknowledgment:
        return fallback, 'server'
    unsafe = (r'\d|[?؟]|book|reserv|confirm|sav|success|done|creat|available|availability|'
              r'capacity|suitable|found|checked|maintenance|تم|حجز|احجز|أحجز|أكد|تأكيد|'
              r'سجل|سجّل|حفظ|نجاح|نجح|أنش|انش|متاح|توفر|توفّر|مناسب|سعة|صيانة|وجدت|بحثت')
    if re.search(unsafe, acknowledgment, re.I):
        return fallback, 'server'
    return acknowledgment.strip() + '\n' + fallback, MODEL_PROVIDER
