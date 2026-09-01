from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

connect_args = {}
engine_kwargs = {"echo": False}

db_url = getattr(settings, "DATABASE_URL", "sqlite:///:memory:")

if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False
else:
    pool_size = getattr(settings, "DB_POOL_SIZE", 5)
    max_overflow = getattr(settings, "DB_MAX_OVERFLOW", 10)
    engine_kwargs.update({
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "pool_pre_ping": True,
    })

engine = create_engine(
    db_url,
    connect_args=connect_args,
    **engine_kwargs
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
