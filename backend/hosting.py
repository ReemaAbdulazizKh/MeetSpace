"""Access gate for a private educational demo; not employee authentication."""
import base64
import binascii
import secrets
from starlette.responses import PlainTextResponse


class DemoAccess:
    def __init__(self, app, username, password, origin, require_auth=True):
        self.app, self.username, self.password, self.origin = app, username, password, origin
        self.require_auth = require_auth

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        # Infrastructure liveness only: no database/model checks or metadata.
        if scope['path'] == '/healthz' and scope['method'] in {'GET', 'HEAD'}:
            return await self.app(scope, receive, send)
        headers = dict(scope.get('headers', []))
        valid = False
        try:
            scheme, encoded = headers.get(b'authorization', b'').decode('ascii').split(' ', 1)
            user, sep, password = base64.b64decode(encoded, validate=True).decode('utf-8').partition(':')
            valid = (scheme.lower() == 'basic' and bool(sep)
                     and secrets.compare_digest(user.encode(), self.username.encode())
                     and secrets.compare_digest(password.encode(), self.password.encode()))
        except (ValueError, UnicodeError, binascii.Error):
            pass
        if self.require_auth and not valid:
            return await PlainTextResponse('Private educational demo. Sign in to continue.', status_code=401,
                headers={'WWW-Authenticate': 'Basic realm="MeetSpace demo", charset="UTF-8"',
                         'Cache-Control': 'no-store'})(scope, receive, send)
        if scope['method'] not in {'GET', 'HEAD', 'OPTIONS'}:
            # Basic credentials can be sent automatically by browsers. Require
            # the known frontend origin on every write to prevent cross-site use.
            if headers.get(b'origin', b'').decode('latin1') != self.origin:
                return await PlainTextResponse('Request origin rejected.', status_code=403)(scope, receive, send)
        await self.app(scope, receive, send)
