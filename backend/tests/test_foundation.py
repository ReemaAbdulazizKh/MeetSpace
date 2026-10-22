"""Isolated checks, not live Firestore persistence evidence."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.main import app
from backend import firestore_store


class FoundationTests(unittest.TestCase):
    def test_outage_is_explicit_and_confirmation_requires_contract(self):
        with patch.object(firestore_store, 'list_records', side_effect=RuntimeError('private detail')):
            with TestClient(app) as http:
                for route in ('rooms', 'employees'):
                    response = http.get(f'/api/{route}')
                    self.assertEqual(response.status_code, 503)
                    self.assertNotIn('private detail', response.text)
                self.assertEqual(http.post('/api/bookings/confirm', json={}).status_code, 422)

    def test_seed_is_additive_and_reads_before_writes(self):
        state = {('rooms', 'T01'): {'status': 'maintenance'},
                 ('bookings', 'existing'): {'status': 'confirmed'}}
        events = []

        class Reference:
            def __init__(self, collection, key): self.key = (collection, key)
            def get(self, transaction):
                events.append('read')
                return SimpleNamespace(exists=self.key in state)

        class Transaction:
            def create(self, reference, data):
                events.append('write')
                assert reference.key not in state
                state[reference.key] = data

        class Database:
            def collection(self, name):
                return SimpleNamespace(document=lambda key: Reference(name, key))
            def transaction(self): return Transaction()

        with patch.object(firestore_store, 'client', return_value=Database()), patch.object(
                firestore_store.firestore, 'transactional', side_effect=lambda fn: fn):
            self.assertEqual(firestore_store.seed(), 12)
            self.assertEqual(events[:13], ['read'] * 13)
            self.assertEqual(events[13:], ['write'] * 12)
            events.clear()
            self.assertEqual(firestore_store.seed(), 0)
            self.assertNotIn('write', events)
        self.assertEqual(state[('rooms', 'T01')], {'status': 'maintenance'})
        self.assertEqual(state[('bookings', 'existing')], {'status': 'confirmed'})
        self.assertEqual(sum(key[0] == 'rooms' for key in state), 10)
        self.assertEqual(sum(key[0] == 'employees' for key in state), 3)


if __name__ == '__main__': unittest.main()
