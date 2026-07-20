"""Run this script once to create all DB tables that don't exist yet."""
from app.database import Base, engine
import app.models  # noqa: F401 — ensures all models are registered

Base.metadata.create_all(bind=engine)
print("All tables created (or already exist).")
