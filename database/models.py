"""
Database models for Thai ALPR system.
"""

from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Column, DateTime, Float, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()


class ProcessingStatus(str, Enum):
    """Processing status for vehicle logs."""

    PENDING = "PENDING"  # Low confidence, needs manual review
    ALPR = "ALPR"  # High confidence automatic detection
    MLPR = "MLPR"  # Manually verified/corrected


class VehicleLog(Base):
    """
    Vehicle detection log with Thai license plate information.
    
    Stores full detection data including images, plate information, and verification status.
    """

    __tablename__ = "vehicle_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    image_path = Column(String, nullable=False)  # Full frame image path
    crop_path = Column(String, nullable=False)  # Cropped plate image path
    plate_category = Column(String, nullable=True)  # e.g., "1กก", "2กก", "นย"
    plate_number = Column(String, nullable=True)  # e.g., "1234"
    province = Column(String, nullable=True)  # e.g., "กรุงเทพมหานคร"
    confidence = Column(Float, nullable=False)  # OCR confidence score
    status = Column(String, nullable=False, default=ProcessingStatus.PENDING.value, index=True)
    
    # Store raw detection data for reference
    raw_text = Column(String, nullable=True)  # Original OCR output
    detection_confidence = Column(Float, nullable=True)  # Detection model confidence
    bounding_box = Column(String, nullable=True)  # JSON string of bbox coordinates

    def __repr__(self) -> str:
        return f"<VehicleLog(id={self.id}, plate='{self.plate_category} {self.plate_number}', status={self.status})>"


def get_engine(database_url: str):
    """Create database engine."""
    return create_engine(database_url, echo=False)


def create_tables(engine):
    """Create all tables in the database."""
    Base.metadata.create_all(bind=engine)


def get_session_maker(engine):
    """Get session maker for database operations."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)