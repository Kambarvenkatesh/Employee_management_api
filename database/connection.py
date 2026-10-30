import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()  # read DATABASE_URL / JWT_SECRET_KEY from .env if present

DATABASE_URL = os.getenv(
    "DATABASE_URL", "mysql+pymysql://root:MySQL@localhost:3306/employee_db"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
