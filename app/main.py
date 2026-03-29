from fastapi import FastAPI

from app.api.routes import router
from app.db.session import create_db_and_tables


def create_app() -> FastAPI:
    app = FastAPI(title="Caregiver Support AI")
    app.include_router(router)

    @app.on_event("startup")
    def on_startup() -> None:
        create_db_and_tables()

    return app


app = create_app()
