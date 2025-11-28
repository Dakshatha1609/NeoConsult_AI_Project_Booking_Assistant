from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite database path (adjust if needed)
DATABASE_URL = "sqlite:///bookings.db"

# SQLAlchemy engine and session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
