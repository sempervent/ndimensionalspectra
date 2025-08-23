
from __future__ import annotations

from typing import Dict, Optional, Any
from fastapi import FastAPI
from pydantic import BaseModel, Field

from .ontogenic_schema import (
    build_simple_survey, score_responses, place_on_continuum,
    post_survey_install_run, json_schema
)

app = FastAPI(title="Ontogenic Machine API", version="0.1.0")

@app.get("/health")
def health_check():
    """Health check endpoint for Docker and load balancers."""
    return {"status": "healthy", "service": "ontogenic-machine-api"}

class RunRequest(BaseModel):
    responses: Dict[str, int] = Field(..., description="Map of survey item id -> Likert 1..7")
    passes: int = Field(3, ge=1, le=20)

class ScoreRequest(BaseModel):
    responses: Dict[str, int]

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
def post_run(req: RunRequest):
    res = post_survey_install_run(req.responses, passes=req.passes)
    return res
