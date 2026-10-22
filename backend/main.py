from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .config import FRONTEND_ORIGIN, ROOT, HOSTED, DEMO_USERNAME, DEMO_PASSWORD
from .hosting import DemoAccess
from .routes import router

app = FastAPI(title='MeetSpace — Local Booking Assistant', version='0.3.0')
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN],
                   allow_methods=['GET', 'POST', 'PATCH'], allow_headers=['Content-Type'])
app.include_router(router)


@app.get('/healthz', include_in_schema=False)
def liveness():
    return {'status': 'ok'}


# Same-origin hosting preserves the frontend's existing /api requests. Never
# serve the repository root: credentials and source files remain inaccessible.
dist = ROOT / 'frontend' / 'dist'
if HOSTED and not (dist / 'index.html').is_file():
    raise RuntimeError('Frontend build missing. Run the Render build command first.')
if dist.is_dir():
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
if HOSTED:
    app.add_middleware(DemoAccess, username=DEMO_USERNAME, password=DEMO_PASSWORD, origin=FRONTEND_ORIGIN)
