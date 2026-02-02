from fastapi import FastAPI
from routes.posting import router as posting_router
from routes.getPages import router as get_pages_router
from routes.getSession import router as get_session_router
from routes.login import router as login_router

app = FastAPI()
app.include_router(posting_router)
app.include_router(get_pages_router)
app.include_router(get_session_router)
app.include_router(login_router)