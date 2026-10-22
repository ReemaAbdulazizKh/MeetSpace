import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from backend import agent


class GroqContractTests(unittest.TestCase):
    def call(self, content, finish='stop'):
        class Response:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, *args):
                return json.dumps({'choices': [{'finish_reason': finish,
                    'message': {'content': content}}]}).encode()
        return patch.object(agent, 'urlopen', return_value=Response())

    def test_valid_json_and_auth_sent_only_to_groq(self):
        data = dict(intent='request', language='en', room_type='meeting', date='2027-02-15',
                    start_time='10:00', end_time='12:00', end_date=None, attendees=8,
                    selected_room=None, unclear=[], explicit_confirmation=False)
        with patch.object(agent, 'MODEL_PROVIDER', 'groq'), patch.object(agent, 'GROQ_API_KEY', 'test-only'), self.call(json.dumps(data)) as http:
            value = agent.structured([], agent.Extraction)
        self.assertEqual(value.attendees, 8)
        request = http.call_args.args[0]
        self.assertEqual(request.full_url, 'https://api.groq.com/openai/v1/chat/completions')
        self.assertEqual(request.get_header('Authorization'), 'Bearer test-only')
        self.assertNotIn('keep_alive', json.loads(request.data))

    def test_malformed_typed_and_truncated_output_fail_closed(self):
        for content, finish in [('not-json', 'stop'), ('{"explicit_confirmation":"true"}', 'stop'), ('{}', 'length')]:
            with patch.object(agent, 'GROQ_API_KEY', 'test-only'), self.call(content, finish):
                with self.assertRaises(agent.AgentUnavailable):
                    agent.structured_groq([], agent.Extraction)

    def test_missing_key_makes_no_request(self):
        with patch.object(agent, 'GROQ_API_KEY', ''), patch.object(agent, 'urlopen') as http:
            with self.assertRaises(agent.AgentUnavailable): agent.structured_groq([], agent.Extraction)
        http.assert_not_called()

    def test_rate_limit_error_does_not_expose_key_or_provider_body(self):
        with patch.object(agent, 'GROQ_API_KEY', 'test-secret'), patch.object(agent, 'urlopen', side_effect=HTTPError('https://api.groq.com',429,'private provider detail',{},None)):
            with self.assertRaises(agent.AgentUnavailable) as failure:
                agent.structured_groq([], agent.Extraction)
        self.assertEqual(str(failure.exception), 'Groq request failed (HTTP 429).')
