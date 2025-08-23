
#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import click

from .ontogenic_schema import (
    build_simple_survey, score_responses, place_on_continuum,
    post_survey_install_run, json_schema
)

@click.group(name="om")
def om():
    """Ontogenic Machine CLI: survey, score, place, run, schema."""
    pass

@om.command()
@click.option("--model", type=click.Choice(["state","survey","hypergraph","all"]), default="all")
def schema(model):
    """Print Pydantic JSON Schema."""
    print(json.dumps(json_schema(model), indent=2))

@om.command()
def survey():
    """Print survey JSON spec."""
    s = build_simple_survey()
    print(json.dumps(s.to_dict(), indent=2))

def _load_responses(responses: str | None):
    if not responses or responses == "-":
        data = sys.stdin.read()
        return json.loads(data)
    # try file path first
    try:
        with open(responses, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        # then assume inline JSON string
        return json.loads(responses)

@om.command()
@click.option("--responses", "-r", help="Path to JSON file of {item_id:int}, '-' for stdin, or inline JSON")
def score(responses):
    """Score Likert responses into [-1,1] traits/PAD."""
    s = build_simple_survey()
    resp = _load_responses(responses)
    sc = score_responses(s, resp)
    print(json.dumps(sc, indent=2))

@om.command()
@click.option("--responses", "-r", help="Path/JSON/STDIN of responses")
def place(responses):
    """Place on the continuum (2D/3D)."""
    s = build_simple_survey()
    resp = _load_responses(responses)
    sc = score_responses(s, resp)
    placement = place_on_continuum(sc)
    print(json.dumps(placement.model_dump(), indent=2))

@om.command()
@click.option("--responses", "-r", help="Path/JSON/STDIN of responses")
@click.option("--passes", "-p", type=int, default=3)
def run(responses, passes):
    """Immediate post-survey install & run glyph engine."""
    resp = _load_responses(responses)
    out = post_survey_install_run(resp, passes=passes)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    om()
