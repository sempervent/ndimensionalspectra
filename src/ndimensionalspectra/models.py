#!/usr/bin/env python3
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

class RunCreate(BaseModel):
    """Request model for creating a new run"""
    user_id: str = Field(..., description="User identifier")
    responses: Dict[str, int] = Field(..., description="Map of survey item id -> Likert 1..7")
    passes: int = Field(3, ge=1, le=20, description="Number of pipeline passes")
    notes: Optional[str] = Field(None, description="Optional notes for this run")

class RunRecord(BaseModel):
    """Response model for a run record"""
    id: str
    user_id: str
    survey_id: str
    passes: int
    created_at: datetime
    coords2d_x: Optional[float] = None
    coords2d_y: Optional[float] = None
    coords3d_v: Optional[float] = None
    coords3d_a: Optional[float] = None
    coords3d_d: Optional[float] = None
    stability: Optional[float] = None
    scores: Optional[Dict[str, float]] = None
    final_state: Optional[Dict[str, Any]] = None
    notes: Optional[str] = None
    
    class Config:
        from_attributes = True
        json_encoders = {
            'uuid.UUID': lambda v: str(v)
        }

class RunList(BaseModel):
    """Response model for paginated run list"""
    items: List[RunRecord]
    total: int
    page: int
    page_size: int

class CompareResponse(BaseModel):
    """Response model for run comparison"""
    results: Dict[str, List[RunRecord]]
    total_users: int
    limit_per_user: int

# Backward compatibility models
class RunRequest(BaseModel):
    """Legacy request model for /run endpoint"""
    responses: Dict[str, int] = Field(..., description="Map of survey item id -> Likert 1..7")
    passes: int = Field(3, ge=1, le=20)
    user_id: Optional[str] = Field(None, description="Optional user ID for persistence")

class ScoreRequest(BaseModel):
    """Request model for scoring responses"""
    responses: Dict[str, int]

# Visualization models
class ProjectionRequest(BaseModel):
    """Request model for projection visualization"""
    user_ids: Optional[List[str]] = None
    survey_id: Optional[str] = None
    since: Optional[datetime] = None
    until: Optional[datetime] = None
    dims: int = Field(2, ge=2, le=3, description="Number of dimensions (2 or 3)")
    technique: str = Field(..., description="Projection technique: pca, umap, or tsne")
    features: Optional[List[str]] = None
    limit_per_user: int = Field(100, ge=1, le=1000, description="Maximum runs per user")

class ProjectionPoint(BaseModel):
    """A single point in a projection"""
    run_id: str
    user_id: str
    created_at: datetime
    x: float
    y: float
    z: Optional[float] = None
    meta: Dict[str, Any] = Field(default_factory=dict)

class ProjectionResult(BaseModel):
    """Response model for projection visualization"""
    technique: str
    dims: int
    points: List[ProjectionPoint]
    explained_variance: Optional[List[float]] = None
    feature_names: List[str] = Field(default_factory=list)

class RunStats(BaseModel):
    """Statistics for runs"""
    total_runs: int
    unique_users: int
    date_range: Dict[str, datetime]
    mean_stability: Optional[float] = None
    mean_pad: Optional[Dict[str, float]] = None
    runs_by_user: Dict[str, int] = Field(default_factory=dict) 