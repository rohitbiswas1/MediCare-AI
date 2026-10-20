from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(settings().database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(engine, expire_on_commit=False)


def get_db():
    with SessionLocal() as session:
        yield session


def set_owner(db, owner_id):
    if engine.dialect.name == "postgresql":
        db.execute(text("SELECT set_config('app.user_id', :owner, true)"), {"owner": str(owner_id)})
