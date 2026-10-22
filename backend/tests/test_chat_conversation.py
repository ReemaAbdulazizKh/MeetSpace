import unittest
from unittest.mock import patch
from backend import chat_service as chat, agent, booking_service as b
from backend.sessions import Session
from .test_booking import extraction, offered


class ConversationTests(unittest.TestCase):
    def test_greeting_is_not_a_missing_booking_and_keeps_offer(self):
        session=offered();offer=session.pending_offer
        with patch.object(agent,'extract') as model,patch.object(b.store,'commit_offer') as commit:
            result=chat.process(session,'هاي','ar')
        self.assertEqual(result.status,'greeting')
        self.assertIn('هلا فيك',result.reply)
        self.assertIs(session.pending_offer,offer)
        model.assert_not_called();commit.assert_not_called()

    def test_available_today_retains_date_and_asks_one_question(self):
        session=Session('sara')
        with patch.object(agent,'extract',return_value=extraction(language='ar',date='2090-01-15')),patch.object(b,'find_rooms') as search:
            result=chat.process(session,'ايش القاعات المتوفرة اليوم؟','ar')
        self.assertEqual(result.draft['date'],'2090-01-15')
        self.assertIn('اجتماعات أو تدريب',result.reply)
        self.assertNotIn('وقت النهاية',result.reply)
        self.assertIn('حسب وقت الحجز',result.reply)
        search.assert_not_called()

    def test_flexible_time_never_invents_a_slot_or_promises_availability(self):
        session=Session('sara',draft=dict(room_type='meeting',date='2090-01-15',attendees=8))
        with patch.object(agent,'extract',return_value=extraction(language='ar')),patch.object(b,'find_rooms') as search,patch.object(b.store,'commit_offer') as commit:
            result=chat.process(session,'مافيه وقت معين ابي المتوفر','ar')
        self.assertIsNone(result.draft.get('start_time'))
        self.assertIn('فترة مبدئية',result.reply)
        self.assertIn('ما بحثت',result.reply)
        self.assertNotIn('نوع القاعة',result.reply)
        search.assert_not_called();commit.assert_not_called()

    def test_only_missing_end_time_is_asked_for(self):
        question=chat.missing_question(['end_time'],'en','until when?')
        self.assertIn('end time',question)
        self.assertNotIn('start time',question)
