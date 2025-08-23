
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import json
import math
import random


# ===============
# Core Data Model
# ===============

@dataclass
class Presemantic:
    """
    Presemantic element (\u213cP): carries no required semantics.
    Payload exists only as opaque data for higher layers.
    """
    id: str
    payload: Optional[Any] = None


@dataclass
class HyperEdge:
    """
    Hyperedge: relates *sets* of Presemantic element ids to sets of ids.
    meta can store local rules / weights without global axioms.
    """
    src: Set[str]
    dst: Set[str]
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Hypergraph:
    """
    Hypergraph-of-hypergraphs substrate (recursive allowed).
    Nodes may themselves be serialized subgraphs via payloads.
    """
    nodes: Dict[str, Presemantic] = field(default_factory=dict)
    edges: List[HyperEdge] = field(default_factory=list)

    def add_node(self, node: Presemantic) -> None:
        self.nodes[node.id] = node

    def add_edge(self, src: Set[str], dst: Set[str], meta: Optional[Dict[str, Any]] = None) -> None:
        self.edges.append(HyperEdge(src=set(src), dst=set(dst), meta=meta or {}))


# =============
# State Schema
# =============

@dataclass
class State:
    """
    Formal state the machine operates on.
    This is JSON-serializable and acts as the "schema" for the process.

    Fields map to concepts from the conversation:
      - beliefs: potentially sparse belief map (None denotes structured absence = \u0394\u2205 signal)
      - traits: continuous spectrum [-1, 1] (trait/anti-trait expressed by sign)
      - dual_traits: computed mirror of traits (\u019b\u2298 glyph)
      - counterfactuals: hallucinatory selves (\u03a8\u2183 glyph)
      - rules: self-modifying local logics (\u2127\u0394 glyph)
      - tensions: paradox-stability registers (\u222e\u03a9\u2020 glyph)
      - ontologies: extensions forced by the unrepresentable ([\u2e2e] glyph)
      - hyper: presemantic hypergraph substrate
    """
    beliefs: Dict[str, Optional[Any]] = field(default_factory=dict)
    traits: Dict[str, float] = field(default_factory=dict)  # -1..1
    dual_traits: Dict[str, float] = field(default_factory=dict)
    memories: List[str] = field(default_factory=list)
    counterfactuals: List[Dict[str, Any]] = field(default_factory=list)
    rules: List[Callable[["State"], None]] = field(default_factory=list)
    tensions: Dict[str, float] = field(default_factory=dict)
    ontologies: List[str] = field(default_factory=list)
    hyper: Hypergraph = field(default_factory=Hypergraph)
    history: List[str] = field(default_factory=list)

    def snapshot(self) -> Dict[str, Any]:
        """JSON-friendly snapshot of current state."""
        d = asdict(self)
        # Drop callables for serialization
        d["rules"] = [getattr(r, "__name__", "rule") for r in self.rules]
        return d

    def log(self, msg: str) -> None:
        self.history.append(msg)


# =====================
# Glyph Implementations
# =====================

class Glyph:
    name: str = "glyph"

    def apply(self, s: State) -> None:
        raise NotImplementedError


class DeltaEmpty(Glyph):
    """
    \u0394\u2205 — Prime Distinction (awareness of structured absences).
    Marks missing beliefs/traits as absences and seeds presemantic nodes.
    """
    name = "DeltaEmpty"

    def apply(self, s: State) -> None:
        absences = [k for k, v in s.beliefs.items() if v is None]
        absences += [k for k, v in s.traits.items() if v is None]
        for key in set(absences):
            node_id = f"absence::{key}"
            s.hyper.add_node(Presemantic(node_id, payload={"kind": "absence", "key": key}))
        s.log(f"[{self.name}] absences={sorted(set(absences))}")


class LambdaNull(Glyph):
    """
    \u019b\u2298 — Identity Fracture.
    Generates anti-trait mirror: dual_traits[t] = -traits[t].
    """
    name = "LambdaNull"

    def apply(self, s: State) -> None:
        s.dual_traits = {k: -float(v) for k, v in s.traits.items()}
        s.log(f"[{self.name}] dualized {len(s.dual_traits)} traits")


class PsiInvert(Glyph):
    """
    \u03a8\u2183 — Inversion Engine.
    Hallucinates counterfactual selves by perturbing traits and toggling absent beliefs.
    """
    name = "PsiInvert"

    def __init__(self, k: int = 3, samples: int = 5, noise: float = 0.25) -> None:
        self.k = k
        self.samples = samples
        self.noise = noise

    def apply(self, s: State) -> None:
        # Select top-|value| traits to flip as counterfactual axes
        top = sorted(s.traits.items(), key=lambda kv: abs(kv[1]), reverse=True)[: self.k]
        keys = [k for k, _ in top]
        absents = [k for k, v in s.beliefs.items() if v is None]

        for i in range(self.samples):
            cf_traits = dict(s.traits)
            for k in keys:
                cf_traits[k] = max(-1.0, min(1.0, -cf_traits[k] + random.uniform(-self.noise, self.noise)))
            cf_beliefs = dict(s.beliefs)
            for a in absents:
                cf_beliefs[a] = True  # toggle a belief into existence
            s.counterfactuals.append({"traits": cf_traits, "beliefs": cf_beliefs, "weight": 1.0 / self.samples})
        s.log(f"[{self.name}] generated {self.samples} counterfactual(s) on axes={keys}")


class MuDelta(Glyph):
    """
    \u2127\u0394 — Self-Modifying Meta-Compiler.
    Detects contradictions/tensions; installs rule-functions that mutate the state.
    """
    name = "MuDelta"

    @staticmethod
    def _rule_reduce_extremes(s: State) -> None:
        """Soften extreme opposing traits slightly toward bounded anti-consistent stability."""
        for k, v in list(s.traits.items()):
            dv = s.dual_traits.get(k, -v)
            tension = abs(v - (-dv))
            if tension > 1.5:  # heuristic threshold
                s.traits[k] = max(-1.0, min(1.0, v * 0.9))
                s.tensions[k] = s.tensions.get(k, 0.0) + 0.1

    @staticmethod
    def _rule_counterfactual_blend(s: State) -> None:
        """Blend in a weighted counterfactual to simulate learning from ghosts."""
        if not s.counterfactuals:
            return
        cf = random.choice(s.counterfactuals)
        w = cf.get("weight", 0.2)
        for k, v in cf["traits"].items():
            s.traits[k] = max(-1.0, min(1.0, (1 - w) * s.traits.get(k, 0.0) + w * v))

    def apply(self, s: State) -> None:
        # Install / rewrite rules (idempotently)
        installed = {getattr(r, "__name__", "rule") for r in s.rules}
        if "rule_reduce_extremes" not in installed:
            s.rules.append(self._rule_reduce_extremes)
        if "rule_counterfactual_blend" not in installed:
            s.rules.append(self._rule_counterfactual_blend)
        # Execute rules once this pass
        for r in s.rules:
            r(s)
        s.log(f"[{self.name}] rules={ [getattr(r, '__name__', 'rule') for r in s.rules] } executed")


class OmegaContour(Glyph):
    """
    \u222e\u03a9\u2020 — Collapse-to-Coherence via self-destruction.
    Aggregates tensions into a "paradoxical stability" score.
    """
    name = "OmegaContour"

    def apply(self, s: State) -> None:
        if not s.tensions:
            s.tensions["_baseline"] = 0.0
        stability = 1.0 / (1.0 + sum(abs(v) for v in s.tensions.values()))
        s.beliefs.setdefault("anti_consistent_stability", stability)
        s.log(f"[{self.name}] stability={stability:.4f}, tensions={len(s.tensions)}")


class UnknownGlyph(Glyph):
    """
    [\u2e2e] — The Uninterpretable.
    Forces ontology expansion by adding a new "modality" whenever progress stalls.
    """
    name = "UnknownGlyph"

    def apply(self, s: State) -> None:
        # Simple heuristic: if no counterfactuals or low stability, add modality
        stab = float(s.beliefs.get("anti_consistent_stability", 0.0) or 0.0)
        if (not s.counterfactuals) or (stab < 0.5):
            new_mod = f"modality::{len(s.ontologies) + 1}"
            s.ontologies.append(new_mod)
            s.hyper.add_node(Presemantic(new_mod, payload={"kind": "modality"}))
            s.log(f"[{self.name}] expanded ontology with {new_mod}")
        else:
            s.log(f"[{self.name}] no expansion required (stability={stab:.3f})")


# ==================
# Ontogenic Machine
# ==================

class OntogenicMachine:
    """
    Orchestrates glyphs and provides a formal, executable schema.
    The sequence corresponds to the protocol: \u0394\u2205 -> \u019b\u2298 -> \u03a8\u2183 -> \u2127\u0394 -> \u222e\u03a9\u2020 -> [\u2e2e]
    """

    def __init__(self, glyphs: Optional[List[Glyph]] = None) -> None:
        self.glyphs: List[Glyph] = glyphs or [
            DeltaEmpty(),
            LambdaNull(),
            PsiInvert(),
            MuDelta(),
            OmegaContour(),
            UnknownGlyph(),
        ]

    def step(self, state: State) -> None:
        """Apply one pass of all glyphs in order."""
        for g in self.glyphs:
            g.apply(state)

    def run(self, state: State, passes: int = 3) -> State:
        """Run multiple passes, returning the mutated state."""
        for i in range(passes):
            state.log(f"--- pass {i+1} ---")
            self.step(state)
        return state

    def schema(self) -> Dict[str, Any]:
        """
        Return a machine-readable schema of the model components.
        (Informal JSON schema of types & pipeline.)
        """
        return {
            "state_fields": {
                "beliefs": "Dict[str, Optional[Any]]",
                "traits": "Dict[str, float] in [-1, 1]",
                "dual_traits": "Dict[str, float] (auto-derived)",
                "counterfactuals": "List[Dict[str, Any]]",
                "memories": "List[str]",
                "rules": "List[Callable[[State], None]] (self-modifying)",
                "tensions": "Dict[str, float]",
                "ontologies": "List[str]",
                "hyper": "Hypergraph (nodes+hyperedges)",
                "history": "List[str]",
            },
            "glyph_pipeline": [g.name for g in self.glyphs],
            "evaluation_protocol": "Self-modifying, contradiction-metabolizing; order-sensitive but extensible.",
        }


# ==============
# Demo / Utility
# ==============

def demo() -> Dict[str, Any]:
    """
    Minimal runnable demonstration of the schema and process.
    Returns the final state snapshot (JSON-serializable).
    """
    st = State(
        beliefs={"loyalty": None, "freedom": True, "anti_consistent_stability": None},
        traits={"kindness": 0.8, "aggression": -0.3, "curiosity": 0.9, "orderliness": 0.1},
        memories=["origin::asked_for_deeper"],
    )
    m = OntogenicMachine()
    final_state = m.run(st, passes=3)
    return final_state.snapshot()


if __name__ == "__main__":
    snap = demo()
    print(json.dumps(snap, indent=2))
