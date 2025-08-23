
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple, Callable
from dataclasses import asdict, is_dataclass
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationError
from pydantic.functional_validators import model_validator

# ---------- Pydantic Models (Schema) ----------

class PresemanticModel(BaseModel):
    id: str
    payload: Optional[Dict[str, Any]] = None

class HyperEdgeModel(BaseModel):
    src: Set[str] = Field(default_factory=set)
    dst: Set[str] = Field(default_factory=set)
    meta: Dict[str, Any] = Field(default_factory=dict)

class HypergraphModel(BaseModel):
    nodes: Dict[str, PresemanticModel] = Field(default_factory=dict)
    edges: List[HyperEdgeModel] = Field(default_factory=list)

    def add_node(self, node: PresemanticModel) -> None:
        self.nodes[node.id] = node

    def add_edge(self, src: Set[str], dst: Set[str], meta: Optional[Dict[str, Any]] = None) -> None:
        self.edges.append(HyperEdgeModel(src=set(src), dst=set(dst), meta=meta or {}))

class StateModel(BaseModel):
    """
    Formal, validated state for the Ontogenic Machine.
    - beliefs: Dict[str, Optional[Any]] (None = structured absence)
    - traits: Dict[str, float] constrained to [-1, 1]
    - dual_traits: derived mirror of traits (values also in [-1, 1])
    - counterfactuals: free-form dicts (validated shallowly)
    - rules: names only (callables live in the runtime engine, not the schema)
    - tensions: Dict[str, float] (>= 0 recommended by convention)
    - ontologies: list of modality strings
    - hyper: presemantic hypergraph
    - history, memories: lists of strings
    """
    model_config = ConfigDict(extra='forbid')

    beliefs: Dict[str, Optional[Any]] = Field(default_factory=dict)
    traits: Dict[str, float] = Field(default_factory=dict)
    dual_traits: Dict[str, float] = Field(default_factory=dict)
    counterfactuals: List[Dict[str, Any]] = Field(default_factory=list)
    rules: List[str] = Field(default_factory=list)
    tensions: Dict[str, float] = Field(default_factory=dict)
    ontologies: List[str] = Field(default_factory=list)
    hyper: HypergraphModel = Field(default_factory=HypergraphModel)
    history: List[str] = Field(default_factory=list)
    memories: List[str] = Field(default_factory=list)

    @field_validator('traits')
    @classmethod
    def _validate_traits(cls, v: Dict[str, float]) -> Dict[str, float]:
        for k, x in v.items():
            if not isinstance(x, (int, float)):
                raise ValueError(f"trait {k} must be numeric")
            if x < -1.0 or x > 1.0:
                raise ValueError(f"trait {k} out of bounds [-1,1]: {x}")
        return v

    @field_validator('dual_traits')
    @classmethod
    def _validate_dual(cls, v: Dict[str, float]) -> Dict[str, float]:
        for k, x in v.items():
            if x < -1.0 or x > 1.0:
                raise ValueError(f"dual_trait {k} out of bounds [-1,1]: {x}")
        return v

    @model_validator(mode='after')
    def _mirror_dual_if_empty(self) -> 'StateModel':
        if self.dual_traits == {} and self.traits:
            self.dual_traits = {k: -float(v) for k, v in self.traits.items()}
        return self

# ---------- Continuum Placement ----------

class ContinuumPlacement(BaseModel):
    """2D/3D placement on a continuum surface with explanation."""
    coords2d: Tuple[float, float]
    coords3d: Tuple[float, float, float]
    axes: Tuple[str, str, str] = ("valence", "arousal", "dominance")
    notes: str

# ---------- Survey Models ----------

class SurveyItem(BaseModel):
    id: str
    prompt: str
    reverse: bool = False
    maps_to: str  # which trait/pad axis
    weight: float = 1.0

class Survey(BaseModel):
    id: str = "ontogenic_simple_v1"
    scale_min: int = 1
    scale_max: int = 7
    items: List[SurveyItem]

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

# ---------- Survey Construction ----------

def build_simple_survey() -> Survey:
    """A compact 15-item survey mapping to PAD and 5 broad traits."""
    items = [
        # PAD core (6)
        SurveyItem(id="pad_valence_1", prompt="Right now, I feel content and at ease.", maps_to="valence"),
        SurveyItem(id="pad_valence_2", prompt="I feel weighed down by negativity.", reverse=True, maps_to="valence"),
        SurveyItem(id="pad_arousal_1", prompt="I feel alert and energized.", maps_to="arousal"),
        SurveyItem(id="pad_arousal_2", prompt="I feel sluggish and low-energy.", reverse=True, maps_to="arousal"),
        SurveyItem(id="pad_dominance_1", prompt="I feel in control of my situation.", maps_to="dominance"),
        SurveyItem(id="pad_dominance_2", prompt="I feel pushed around by circumstances.", reverse=True, maps_to="dominance"),
        # Big Five proxy (9)
        SurveyItem(id="o_curiosity", prompt="I enjoy exploring unfamiliar ideas and experiences.", maps_to="curiosity"),
        SurveyItem(id="c_orderliness", prompt="I like to keep things organized and on schedule.", maps_to="orderliness"),
        SurveyItem(id="e_extraversion", prompt="I feel energized by social interaction.", maps_to="extraversion"),
        SurveyItem(id="a_agreeableness", prompt="I try to be considerate and cooperative.", maps_to="agreeableness"),
        SurveyItem(id="n_neuroticism", prompt="I have trouble relaxing when stressed.", maps_to="neuroticism"),
        SurveyItem(id="d_detachment", prompt="I prefer emotional distance from others.", maps_to="detachment"),
        SurveyItem(id="dis_disinhibition", prompt="I act on impulse without much planning.", maps_to="disinhibition"),
        SurveyItem(id="ant_antagonism", prompt="I push back hard when challenged.", maps_to="antagonism"),
        SurveyItem(id="ag_aggression", prompt="I can be confrontational when needed.", maps_to="aggression"),
    ]
    return Survey(items=items)

# ---------- Scoring ----------

def _normalize_likert(x: int, lo: int, hi: int) -> float:
    """Map Likert [lo..hi] to [-1,1]."""
    if x < lo or x > hi:
        raise ValueError(f"Likert response {x} out of bounds [{lo},{hi}]")
    # center at midpoint, scale to [-1,1]
    mid = (lo + hi) / 2.0
    rng = (hi - lo) / 2.0
    return (x - mid) / rng

def score_responses(survey: Survey, responses: Dict[str, int]) -> Dict[str, float]:
    """Aggregate item responses into trait/PAD scores in [-1,1]."""
    acc: Dict[str, float] = {}
    wsum: Dict[str, float] = {}
    for item in survey.items:
        if item.id not in responses:
            continue
        raw = responses[item.id]
        val = _normalize_likert(raw, survey.scale_min, survey.scale_max)
        if item.reverse:
            val = -val
        acc[item.maps_to] = acc.get(item.maps_to, 0.0) + val * item.weight
        wsum[item.maps_to] = wsum.get(item.maps_to, 0.0) + item.weight
    # average and clamp
    for k in list(acc.keys()):
        acc[k] = max(-1.0, min(1.0, acc[k] / max(wsum[k], 1e-6)))
    return acc

# ---------- Continuum Placement from Scores ----------

def place_on_continuum(scores: Dict[str, float]) -> ContinuumPlacement:
    """Project to PAD 3D (valence, arousal, dominance) and a 2D surface.

    2D projection uses a simple, transparent linear map from PAD + extraversion/ neuroticism.

    """
    v = float(scores.get("valence", 0.0))
    a = float(scores.get("arousal", 0.0))
    d = float(scores.get("dominance", 0.0))

    # Transparent 2D mapping (tunable):
    # x: positive affect & sociability vs. withdrawal
    # y: activation vs. calm modulated by stability
    extr = float(scores.get("extraversion", 0.0))
    neur = float(scores.get("neuroticism", 0.0))
    x = 0.6*v + 0.4*extr - 0.3*neur
    y = 0.7*a + 0.2*d - 0.2*neur

    notes = (
        f"PAD=(v={v:.2f}, a={a:.2f}, d={d:.2f}); "
        f"2D derived from valence/extraversion/neuroticism & arousal/dominance"    )
    return ContinuumPlacement(coords2d=(x, y), coords3d=(v, a, d), notes=notes)

# ---------- Bridge to Runtime Ontogenic Machine (optional) ----------

def to_state_model(traits: Dict[str, float], beliefs: Optional[Dict[str, Optional[Any]]] = None) -> StateModel:
    """Create a validated StateModel from scored traits/beliefs."""
    return StateModel(traits=traits, beliefs=beliefs or {})

# ---------- Example: Build Survey & Score a Mock Response ----------

def demo_survey_and_place() -> Dict[str, Any]:
    survey = build_simple_survey()
    # Example mock responses on 1..7 scale
    mock = {
        "pad_valence_1": 6,
        "pad_valence_2": 2,
        "pad_arousal_1": 6,
        "pad_arousal_2": 2,
        "pad_dominance_1": 5,
        "pad_dominance_2": 3,
        "o_curiosity": 7,
        "c_orderliness": 4,
        "e_extraversion": 6,
        "a_agreeableness": 6,
        "n_neuroticism": 3,
        "d_detachment": 2,
        "dis_disinhibition": 4,
        "ant_antagonism": 4,
        "ag_aggression": 4,
    }
    scores = score_responses(survey, mock)
    placement = place_on_continuum(scores)
    state = to_state_model(scores, beliefs={"survey_version": survey.id})
    return {
        "survey": survey.to_dict(),
        "scores": scores,
        "placement": placement.model_dump(),
        "state": state.model_dump(),
    }


# ---------- Post-Survey Install & Run ----------

def post_survey_install_run(responses: Dict[str, int], passes: int = 3) -> Dict[str, Any]:
    """Immediate pipeline: survey -> scores -> placement -> runtime machine."""
    survey = build_simple_survey()
    scores = score_responses(survey, responses)
    placement = place_on_continuum(scores)
    state = to_state_model(scores, beliefs={
        "survey_version": survey.id,
        "coords2d": placement.coords2d,
        "coords3d": placement.coords3d,
        "notes": placement.notes,
    })
    # Bridge to runtime engine
    from ontogenic_machine import State as RuntimeState, OntogenicMachine
    rt = RuntimeState(
        beliefs=dict(state.beliefs),
        traits=dict(state.traits),
        memories=["install::post_survey"]
    )
    m = OntogenicMachine()
    final_state = m.run(rt, passes=passes)
    return {
        "scores": scores,
        "placement": placement.model_dump(),
        "final_state": final_state.snapshot(),
        "history": final_state.history,
        "pipeline": {
            "survey_id": survey.id,
            "passes": passes,
            "glyphs": m.schema()["glyph_pipeline"],
        }
    }


def demo_post_install() -> Dict[str, Any]:
    """Demo with mock responses."""
    mock = {
        "pad_valence_1": 6, "pad_valence_2": 2,
        "pad_arousal_1": 6, "pad_arousal_2": 2,
        "pad_dominance_1": 5, "pad_dominance_2": 3,
        "o_curiosity": 7, "c_orderliness": 4, "e_extraversion": 6,
        "a_agreeableness": 6, "n_neuroticism": 3,
        "d_detachment": 2, "dis_disinhibition": 4,
        "ant_antagonism": 4, "ag_aggression": 4,
    }
    return post_survey_install_run(mock, passes=3)


# ---------- JSON Schema & Factories ----------

def json_schema(model: str = "state") -> Dict[str, Any]:
    """Return Pydantic JSON Schema for a given model or a merged bundle.
    model in {"state", "survey", "hypergraph", "all"}
    """
    if model == "state":
        return StateModel.model_json_schema()
    if model == "survey":
        return Survey.model_json_schema()
    if model == "hypergraph":
        return HypergraphModel.model_json_schema()
    if model == "all":
        return {
            "StateModel": StateModel.model_json_schema(),
            "Survey": Survey.model_json_schema(),
            "SurveyItem": SurveyItem.model_json_schema(),
            "HypergraphModel": HypergraphModel.model_json_schema(),
            "HyperEdgeModel": HyperEdgeModel.model_json_schema(),
            "PresemanticModel": PresemanticModel.model_json_schema(),
        }
    raise ValueError(f"unknown model: {model}")

def to_runtime_state(state: StateModel):
    """Factory: Pydantic StateModel -> runtime ontogenic_machine.State"""
    from ontogenic_machine import State as RuntimeState
    return RuntimeState(
        beliefs=dict(state.beliefs),
        traits=dict(state.traits),
        memories=list(state.memories) + [f"survey::{str(state.beliefs.get('survey_version',''))}"]
    )

def from_runtime_state(rt) -> StateModel:
    """Factory: runtime State -> Pydantic StateModel"""
    return StateModel(
        beliefs=dict(rt.beliefs),
        traits=dict(rt.traits),
        dual_traits=dict(getattr(rt, "dual_traits", {})),
        tensions=dict(getattr(rt, "tensions", {})),
        ontologies=list(getattr(rt, "ontologies", [])),
        history=list(getattr(rt, "history", [])),
        memories=list(getattr(rt, "memories", [])),
    )
