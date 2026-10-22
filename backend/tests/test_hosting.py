import unittest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.hosting import DemoAccess


class HostingTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI()
        @app.get('/healthz')
        def live(): return {'status':'ok'}
        @app.get('/api/admin/bookings')
        def private(): return {'private':True}
        @app.post('/api/action')
        def write(): return {'accepted':True}
        app.add_middleware(DemoAccess, username='reviewer', password='test-password-only', origin='https://demo.example')
        self.http = TestClient(app)

    def test_all_private_paths_require_credentials(self):
        for path in ['/', '/api/admin/bookings', '/docs', '/openapi.json', '/assets/app.js']:
            self.assertEqual(self.http.get(path).status_code,401)
        self.assertEqual(self.http.get('/healthz').json(),{'status':'ok'})
        self.assertEqual(self.http.get('/api/admin/bookings',auth=('reviewer','wrong')).status_code,401)
        self.assertEqual(self.http.get('/api/admin/bookings',auth=('reviewer','test-password-only')).status_code,200)

    def test_malformed_auth_and_cross_site_writes_rejected(self):
        self.assertEqual(self.http.get('/docs',headers={'Authorization':'Basic invalid'}).status_code,401)
        for origin in [None,'https://attacker.example']:
            headers={} if origin is None else {'Origin':origin}
            self.assertEqual(self.http.post('/api/action',auth=('reviewer','test-password-only'),headers=headers).status_code,403)
        self.assertEqual(self.http.post('/api/action',auth=('reviewer','test-password-only'),headers={'Origin':'https://demo.example'}).status_code,200)
