#!/usr/bin/env python3
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Text, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.dialects.sqlite import JSON

# Database URL detection
def get_database_url() -> str:
    """Get database URL from environment or fallback to SQLite"""
    if database_url := os.environ.get("DATABASE_URL"):
        return database_url
    
    # SQLite fallback
    data_dir = "data"
    os.makedirs(data_dir, exist_ok=True)
    return f"sqlite:///{data_dir}/om.db"

# Engine and session factory
engine = create_engine(
    get_database_url(),
    echo=False,  # Set to True for SQL debugging
    connect_args={"check_same_thread": False} if "sqlite" in get_database_url() else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database dependency
def get_db() -> Session:
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# SQLAlchemy Models
class RunORM(Base):
    __tablename__ = "runs"
    
    # Primary key
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # User and survey metadata
    user_id = Column(String, nullable=False, index=True)
    survey_id = Column(String, nullable=False, index=True)
    passes = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    
    # Coordinates
    coords2d_x = Column(Float)
    coords2d_y = Column(Float)
    coords3d_v = Column(Float)  # valence
    coords3d_a = Column(Float)  # arousal  
    coords3d_d = Column(Float)  # dominance
    
    # Results
    stability = Column(Float)
    scores = Column(JSONB if "postgresql" in get_database_url() else JSON)
    final_state = Column(JSONB if "postgresql" in get_database_url() else JSON)
    notes = Column(Text)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_survey_created', 'survey_id', 'created_at'),
    )

def init_db():
    """Initialize database tables"""
    # Enable foreign keys for SQLite
    if "sqlite" in get_database_url():
        with engine.connect() as conn:
            from sqlalchemy import text
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
    
    # Create tables
    Base.metadata.create_all(bind=engine)

# CRUD Operations
def create_run(
    session: Session, 
    user_id: str,
    survey_id: str,
    passes: int,
    responses: Dict[str, int],
    pipeline_result: Dict[str, Any],
    notes: Optional[str] = None
) -> RunORM:
    """Create a new run record"""
    
    # Extract data from pipeline result
    placement = pipeline_result.get("placement", {})
    scores = pipeline_result.get("scores", {})
    final_state = pipeline_result.get("final_state", {})
    
    # Extract coordinates
    coords2d = placement.get("coords2d", [])
    coords3d = placement.get("coords3d", [])
    
    # Extract stability from beliefs
    stability = None
    if final_state and "beliefs" in final_state:
        stability = final_state["beliefs"].get("anti_consistent_stability")
    
    # Create run record
    run = RunORM(
        user_id=user_id,
        survey_id=survey_id,
        passes=passes,
        coords2d_x=coords2d[0] if len(coords2d) > 0 else None,
        coords2d_y=coords2d[1] if len(coords2d) > 1 else None,
        coords3d_v=coords3d[0] if len(coords3d) > 0 else None,
        coords3d_a=coords3d[1] if len(coords3d) > 1 else None,
        coords3d_d=coords3d[2] if len(coords3d) > 2 else None,
        stability=stability,
        scores=scores,
        final_state=final_state,
        notes=notes
    )
    
    session.add(run)
    session.commit()
    session.refresh(run)
    
    # Convert UUID to string for Pydantic compatibility
    run.id = str(run.id)
    
    return run

def list_runs(
    session: Session,
    user_id: Optional[str] = None,
    survey_id: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    include_state: bool = False
) -> tuple[List[RunORM], int]:
    """List runs with filtering and pagination"""
    
    query = session.query(RunORM)
    
    # Apply filters
    if user_id:
        query = query.filter(RunORM.user_id == user_id)
    if survey_id:
        query = query.filter(RunORM.survey_id == survey_id)
    if since:
        query = query.filter(RunORM.created_at >= since)
    if until:
        query = query.filter(RunORM.created_at <= until)
    
    # Get total count
    total = query.count()
    
    # Apply pagination and ordering
    query = query.order_by(RunORM.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    runs = query.all()
    
    # Convert UUIDs to strings and optionally exclude final_state
    for run in runs:
        run.id = str(run.id)
        if not include_state:
            run.final_state = None
    
    return runs, total

def get_run(session: Session, run_id: str) -> Optional[RunORM]:
    """Get a single run by ID"""
    run = session.query(RunORM).filter(RunORM.id == run_id).first()
    if run:
        run.id = str(run.id)
    return run

def compare_runs(
    session: Session,
    user_ids: List[str],
    limit_per_user: int = 50,
    include_state: bool = False
) -> Dict[str, List[RunORM]]:
    """Compare runs across multiple users"""
    
    result = {}
    
    for user_id in user_ids:
        query = session.query(RunORM).filter(RunORM.user_id == user_id)
        query = query.order_by(RunORM.created_at.desc()).limit(limit_per_user)
        runs = query.all()
        
        # Convert UUIDs to strings and optionally exclude final_state
        for run in runs:
            run.id = str(run.id)
            if not include_state:
                run.final_state = None
        
        result[user_id] = runs
    
    return result

def get_runs_for_projection(
    session: Session,
    user_ids: Optional[List[str]] = None,
    survey_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit_per_user: int = 100
) -> List[RunORM]:
    """Get runs for projection analysis with filtering"""
    
    query = session.query(RunORM)
    
    # Apply filters
    if user_ids:
        query = query.filter(RunORM.user_id.in_(user_ids))
    if survey_id:
        query = query.filter(RunORM.survey_id == survey_id)
    if since:
        query = query.filter(RunORM.created_at >= since)
    if until:
        query = query.filter(RunORM.created_at <= until)
    
    # Apply per-user limit
    if user_ids:
        # Use window function to limit per user
        from sqlalchemy import func, text
        query = query.from_self().add_columns(
            func.row_number().over(
                partition_by=RunORM.user_id,
                order_by=RunORM.created_at.desc()
            ).label('rn')
        ).subquery()
        
        query = session.query(RunORM).join(
            query, RunORM.id == query.c.id
        ).filter(query.c.rn <= limit_per_user)
    else:
        query = query.order_by(RunORM.created_at.desc()).limit(limit_per_user * 10)  # Fallback limit
    
    runs = query.all()
    
    # Convert UUIDs to strings
    for run in runs:
        run.id = str(run.id)
    
    return runs

def get_run_stats(
    session: Session,
    user_id: Optional[str] = None,
    survey_id: Optional[str] = None,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None
) -> Dict[str, Any]:
    """Get statistics for runs"""
    
    query = session.query(RunORM)
    
    # Apply filters
    if user_id:
        query = query.filter(RunORM.user_id == user_id)
    if survey_id:
        query = query.filter(RunORM.survey_id == survey_id)
    if since:
        query = query.filter(RunORM.created_at >= since)
    if until:
        query = query.filter(RunORM.created_at <= until)
    
    # Get basic stats
    total_runs = query.count()
    unique_users = query.distinct(RunORM.user_id).count()
    
    # Get date range
    date_range = {}
    if total_runs > 0:
        first_run = query.order_by(RunORM.created_at.asc()).first()
        last_run = query.order_by(RunORM.created_at.desc()).first()
        if first_run and last_run:
            date_range = {
                "start": first_run.created_at,
                "end": last_run.created_at
            }
    
    # Get averages
    from sqlalchemy import func
    avg_stability = query.with_entities(func.avg(RunORM.stability)).scalar()
    
    # Get runs by user
    runs_by_user = {}
    if not user_id:  # Only if not filtering by specific user
        user_counts = query.with_entities(
            RunORM.user_id, func.count(RunORM.id)
        ).group_by(RunORM.user_id).all()
        runs_by_user = {user_id: count for user_id, count in user_counts}
    
    return {
        "total_runs": total_runs,
        "unique_users": unique_users,
        "date_range": date_range,
        "mean_stability": float(avg_stability) if avg_stability else None,
        "runs_by_user": runs_by_user
    } 