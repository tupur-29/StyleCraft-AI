import os
from sqlalchemy import create_engine, Column, String, Text, DateTime, func
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.dialects.postgresql import UUID as PG_UUID 
import uuid as py_uuid # For generating UUIDs
from dotenv import load_dotenv


dotenv_path_explicit = os.path.join(os.path.dirname(__file__), '..', '.env')
if os.path.exists(dotenv_path_explicit):
    load_dotenv(dotenv_path=dotenv_path_explicit)
else:
    load_dotenv() # Fallback

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables. Ensure it's in backend/.env")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class PromptInteraction(Base):
    __tablename__ = "prompts"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=py_uuid.uuid4)
    user_id = Column(String(255), index=True, nullable=False) # Added length for String
    query = Column(Text, nullable=False)
    casual_response = Column(Text)
    formal_response = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_db_tables(): 
    Base.metadata.create_all(bind=engine)
    print("Database tables checked/created.")

if __name__ == "__main__":
    print("Attempting to create database tables (if they don't exist)...")
    
    try:
        create_db_tables()
        print("Successfully connected and checked/created tables.")
        print(f"Connected to: {DATABASE_URL.split('@')[-1]}") 
    except Exception as e:
        print(f"Error connecting to database or creating tables: {e}")
        print(f"Please ensure your PostgreSQL server is running and accessible at: {DATABASE_URL}")
        print("If using Docker, run 'docker-compose up -d' in the project root.") 
