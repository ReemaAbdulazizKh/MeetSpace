import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')
PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID') or 'smart-room-booking-agent'
OLLAMA_URL = (os.getenv('OLLAMA_BASE_URL') or 'http://127.0.0.1:11434').rstrip('/')
MODEL = os.getenv('OLLAMA_MODEL') or 'qwen2:7b'
MODEL_PROVIDER = (os.getenv('MODEL_PROVIDER') or 'ollama').lower()
if MODEL_PROVIDER not in {'ollama', 'groq'}:
    raise ValueError('MODEL_PROVIDER must be ollama or groq.')
GROQ_API_KEY = os.getenv('GROQ_API_KEY') or ''
GROQ_MODEL = os.getenv('GROQ_MODEL') or 'qwen/qwen3.8-27b'
HOSTED = os.getenv('RENDER') == 'true' or os.getenv('APP_ENV') == 'production'
FRONTEND_ORIGIN = (os.getenv('FRONTEND_ORIGIN') or os.getenv('RENDER_EXTERNAL_URL') or 'http://127.0.0.1:5173').rstrip('/')
DEMO_USERNAME = os.getenv('DEMO_USERNAME') or ''
DEMO_PASSWORD = os.getenv('DEMO_PASSWORD') or ''
if HOSTED and (not DEMO_USERNAME or len(DEMO_PASSWORD) < 16):
    raise ValueError('Hosted demo requires DEMO_USERNAME and DEMO_PASSWORD (at least 16 characters).')
if HOSTED and (MODEL_PROVIDER != 'groq' or not GROQ_API_KEY):
    raise ValueError('Hosted demo requires Groq provider and API key.')

for address in (OLLAMA_URL,) + (() if HOSTED else (FRONTEND_ORIGIN,)):
    if urlparse(address).hostname not in {'localhost', '127.0.0.1', '::1'}:
        raise ValueError('MeetSpace services must use local addresses.')
if HOSTED:
    origin = urlparse(FRONTEND_ORIGIN)
    if origin.scheme != 'https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment:
        raise ValueError('Hosted FRONTEND_ORIGIN must be an HTTPS origin without a path.')
