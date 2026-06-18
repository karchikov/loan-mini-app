from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.dashboard import router as dashboard_router
from app.api.loans import router as loans_router
from app.api.telegram import router as telegram_router
from app.api.users import router as users_router
from app.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_scheduler()

    try:
        yield
    finally:
        shutdown_scheduler()


app = FastAPI(
    title="Loan Mini App API",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://loan-mini-app.vercel.app",
        "https://loan-mini-app-r657.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(loans_router)
app.include_router(dashboard_router)
app.include_router(telegram_router)


@app.get("/")
def root():
    return {"message": "Loan Mini App API"}
