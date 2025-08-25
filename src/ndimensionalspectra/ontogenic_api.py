
from __future__ import annotations

from typing import Dict, Optional, Any, List
from datetime import datetime
from fastapi import FastAPI, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from .ontogenic_schema import (
    build_simple_survey, score_responses, place_on_continuum,
    post_survey_install_run, json_schema
)
from .db import get_db, init_db, create_run, list_runs, get_run, compare_runs, get_runs_for_projection, get_run_stats
from .models import RunCreate, RunRecord, RunList, CompareResponse, RunRequest, ScoreRequest, ProjectionRequest, ProjectionResult, ProjectionPoint, RunStats

app = FastAPI(title="Ontogenic Machine API", version="0.1.0")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()

@app.get("/health")
def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "ontogenic-machine-api"}

@app.get("/schema/{model}")
def get_schema(model: str):
    return json_schema(model)

@app.get("/survey")
def get_survey():
    return build_simple_survey().to_dict()

@app.post("/score")
def post_score(req: ScoreRequest):
    survey = build_simple_survey()
    scores = score_responses(survey, req.responses)
    return {"scores": scores}

@app.post("/place")
def post_place(req: ScoreRequest):
    survey = build_simple_survey()
    scores = score_responses(survey, req.responses)
    placement = place_on_continuum(scores)
    return {"scores": scores, "placement": placement.model_dump()}

@app.post("/run")
def post_run(req: RunRequest, db: Session = Depends(get_db)):
    """Legacy endpoint - optionally persists if user_id provided"""
    res = post_survey_install_run(req.responses, passes=req.passes)
    
    # Optionally persist if user_id provided
    if req.user_id:
        survey = build_simple_survey()
        create_run(
            session=db,
            user_id=req.user_id,
            survey_id=survey.id,
            passes=req.passes,
            responses=req.responses,
            pipeline_result=res
        )
    
    return res

# New persistent endpoints
@app.post("/runs", response_model=RunRecord)
def create_persistent_run(req: RunCreate, db: Session = Depends(get_db)):
    """Create a new run with persistence"""
    # Run the pipeline
    pipeline_result = post_survey_install_run(req.responses, passes=req.passes)
    
    # Get survey info
    survey = build_simple_survey()
    
    # Persist the run
    run = create_run(
        session=db,
        user_id=req.user_id,
        survey_id=survey.id,
        passes=req.passes,
        responses=req.responses,
        pipeline_result=pipeline_result,
        notes=req.notes
    )
    
    return run

@app.get("/runs", response_model=RunList)
def list_persistent_runs(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    survey_id: Optional[str] = Query(None, description="Filter by survey ID"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    since: Optional[datetime] = Query(None, description="Filter runs since this date"),
    until: Optional[datetime] = Query(None, description="Filter runs until this date"),
    include_state: bool = Query(False, description="Include final_state in response"),
    db: Session = Depends(get_db)
):
    """List runs with filtering and pagination"""
    runs, total = list_runs(
        session=db,
        user_id=user_id,
        survey_id=survey_id,
        page=page,
        page_size=page_size,
        since=since,
        until=until,
        include_state=include_state
    )
    
    return RunList(
        items=runs,
        total=total,
        page=page,
        page_size=page_size
    )

@app.get("/runs/stats", response_model=RunStats)
def get_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    survey_id: Optional[str] = Query(None, description="Filter by survey ID"),
    since: Optional[datetime] = Query(None, description="Filter runs since this date"),
    until: Optional[datetime] = Query(None, description="Filter runs until this date"),
    db: Session = Depends(get_db)
):
    """Get statistics for runs"""
    stats = get_run_stats(db, user_id, survey_id, since, until)
    return RunStats(**stats)

@app.get("/runs/{run_id}", response_model=RunRecord)
def get_persistent_run(run_id: str, db: Session = Depends(get_db)):
    """Get a single run by ID"""
    run = get_run(db, run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run

@app.get("/compare", response_model=CompareResponse)
def compare_persistent_runs(
    user_ids: str = Query(..., description="Comma-separated list of user IDs"),
    limit_per_user: int = Query(50, ge=1, le=100, description="Limit per user"),
    include_state: bool = Query(False, description="Include final_state in response"),
    db: Session = Depends(get_db)
):
    """Compare runs across multiple users"""
    user_id_list = [uid.strip() for uid in user_ids.split(",") if uid.strip()]
    
    if not user_id_list:
        raise HTTPException(status_code=400, detail="At least one user_id required")
    
    results = compare_runs(
        session=db,
        user_ids=user_id_list,
        limit_per_user=limit_per_user,
        include_state=include_state
    )
    
    return CompareResponse(
        results=results,
        total_users=len(user_id_list),
        limit_per_user=limit_per_user
    )

@app.post("/viz/project", response_model=ProjectionResult)
def project_runs(
    request: ProjectionRequest,
    db: Session = Depends(get_db)
):
    """Create projection visualization of runs"""
    try:
        # Get runs for projection
        runs = get_runs_for_projection(
            db, 
            request.user_ids, 
            request.survey_id, 
            request.since, 
            request.until, 
            request.limit_per_user
        )
        
        if not runs:
            return ProjectionResult(
                technique=request.technique,
                dims=request.dims,
                points=[],
                feature_names=[]
            )
        
        # Prepare data for projection
        import numpy as np
        import pandas as pd
        from sklearn.decomposition import PCA
        from sklearn.manifold import TSNE
        try:
            import umap
        except ImportError:
            umap = None
        
        # Extract features from scores
        feature_data = []
        run_metadata = []
        
        for run in runs:
            if run.scores:
                # Use requested features or all available
                if request.features:
                    features = request.features
                else:
                    features = list(run.scores.keys())
                
                # Extract feature values, fill missing with 0
                feature_vector = []
                for feature in features:
                    feature_vector.append(run.scores.get(feature, 0.0))
                
                feature_data.append(feature_vector)
                run_metadata.append({
                    'run_id': run.id,
                    'user_id': run.user_id,
                    'created_at': run.created_at,
                    'stability': run.stability
                })
        
        if not feature_data:
            return ProjectionResult(
                technique=request.technique,
                dims=request.dims,
                points=[],
                feature_names=features if request.features else []
            )
        
        X = np.array(feature_data)
        
        # Apply projection technique
        if request.technique == "pca":
            projector = PCA(n_components=request.dims)
            coords = projector.fit_transform(X)
            explained_variance = projector.explained_variance_ratio_.tolist() if request.dims == 2 else None
        elif request.technique == "tsne":
            projector = TSNE(n_components=request.dims, perplexity=min(30, len(X)-1), random_state=42)
            coords = projector.fit_transform(X)
            explained_variance = None
        elif request.technique == "umap":
            if umap is None:
                raise HTTPException(status_code=400, detail="UMAP not available. Install umap-learn package.")
            projector = umap.UMAP(n_components=request.dims, n_neighbors=min(15, len(X)-1), min_dist=0.1, random_state=42)
            coords = projector.fit_transform(X)
            explained_variance = None
        else:
            raise HTTPException(status_code=400, detail="Invalid technique. Use 'pca', 'tsne', or 'umap'.")
        
        # Create projection points
        points = []
        for i, (coord, metadata) in enumerate(zip(coords, run_metadata)):
            point = ProjectionPoint(
                run_id=metadata['run_id'],
                user_id=metadata['user_id'],
                created_at=metadata['created_at'],
                x=float(coord[0]),
                y=float(coord[1]),
                z=float(coord[2]) if request.dims == 3 else None,
                meta={'stability': metadata['stability']}
            )
            points.append(point)
        
        return ProjectionResult(
            technique=request.technique,
            dims=request.dims,
            points=points,
            explained_variance=explained_variance,
            feature_names=features if request.features else list(runs[0].scores.keys()) if runs and runs[0].scores else []
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Projection failed: {str(e)}")
