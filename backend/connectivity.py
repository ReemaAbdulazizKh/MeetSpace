import json
from urllib.request import Request, urlopen
from .config import MODEL, OLLAMA_URL, MODEL_PROVIDER, GROQ_API_KEY, GROQ_MODEL


def check_ollama():
    # Legacy name retained for the existing health API; reports selected provider.
    if MODEL_PROVIDER == 'groq':
        if not GROQ_API_KEY:
            return {'status': 'unavailable', 'message': 'Groq API key is not configured.', 'model': GROQ_MODEL}
        request = Request('https://api.groq.com/openai/v1/models',
                          headers={'Authorization': f'Bearer {GROQ_API_KEY}',
                                   'User-Agent': 'MeetSpace/0.3'})
        with urlopen(request, timeout=10) as response:
            available = {item['id'] for item in json.load(response)['data']}
        return {'status': 'ok' if GROQ_MODEL in available else 'unavailable',
                'message': 'Groq reachable; model listed.' if GROQ_MODEL in available else 'Groq model is not listed.',
                'model': GROQ_MODEL}
    with urlopen(f'{OLLAMA_URL}/api/tags', timeout=5) as response:
        installed = json.load(response)['models']
    if MODEL not in {model['name'] for model in installed}:
        return {'status': 'unavailable', 'message': 'Configured model is not installed.', 'model': MODEL}
    return {'status': 'ok', 'message': 'Ollama reachable; configured model installed.', 'model': MODEL}
