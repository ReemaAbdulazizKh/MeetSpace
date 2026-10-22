import unittest
from unittest.mock import patch
from .. import agent, chat_service
from ..sessions import Session
from .test_booking import offered


class ModelContractTests(unittest.TestCase):
    def test_invalid_llm_json_fails_closed(self):
        for content in ['not-json','{"intent":"confirm","explicit_confirmation":"true"}']:
            class FakeResponse:
                def __enter__(self): return self
                def __exit__(self,*args): pass
                def read(self,*args):
                    import json
                    return json.dumps({'done':True,'message':{'content':content}}).encode()
            with patch.object(agent,'urlopen',return_value=FakeResponse()):
                with self.assertRaises(agent.AgentUnavailable):
                    agent.structured([],agent.Extraction)

    def test_reply_cannot_announce_unverified_success(self):
        with patch.object(agent,'structured') as model:
            reply,source=agent.natural_reply('x','en','options',[],'Choose a room.',
                                            acknowledgment='Booking confirmed and saved.')
        model.assert_not_called()
        self.assertEqual(reply,'Choose a room.')
        self.assertEqual(source,'server')

    def test_recurring_request_invalidates_offer(self):
        session=offered()
        response=chat_service.process(session,'Book it every week','en')
        self.assertEqual(response.status,'unsupported')
        self.assertIsNone(session.pending_offer)

    def test_missing_question_preserves_server_fields_without_second_generation(self):
        question='I only need these details: end time with AM/PM, attendee count'
        with patch.object(agent,'structured') as model:
            reply,source=agent.natural_reply('training tomorrow','en','missing',
                                             ['end_time','attendees'],question)
        model.assert_not_called()
        self.assertEqual((reply,source),(question,'server'))

    def test_acknowledgment_is_not_a_second_call_or_database_fact(self):
        with patch.object(agent,'structured') as model:
            for unsafe in ['Room available.', 'تم الحجز', 'Which date?', 'Found a suitable room.']:
                self.assertEqual(agent.natural_reply('x','en','options',[],'Actual result',unsafe),
                                 ('Actual result','server'))
            self.assertEqual(agent.natural_reply('x','en','options',[],'Actual result','I understand your request.'),
                             ('I understand your request.\nActual result',agent.MODEL_PROVIDER))
            self.assertEqual(agent.natural_reply('x','en','confirmed',[],'Verified receipt','I understand.'),
                             ('Verified receipt','server'))
        model.assert_not_called()


if __name__=='__main__':unittest.main()
