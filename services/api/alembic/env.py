from alembic import context
from sqlalchemy import create_engine
from app.config import settings

engine = create_engine(settings().migration_database_url or settings().database_url)
from app.models import Base

if context.is_offline_mode():
    context.configure(url=str(engine.url), target_metadata=Base.metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()
else:
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
