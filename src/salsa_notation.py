"""
salsa_notation.py – Datenmodelle und Kern-Logik für die Salsa-Notation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set, Tuple
import yaml


# ---------------------------------------------------------------------------
# Datenmodelle
# ---------------------------------------------------------------------------

@dataclass
class SalsaState:
    """Vollständiger Übergabezustand zwischen zwei Elementen."""
    hand_hold: Set[str]   # mögliche Werte (mehrere = kompatibel mit mehreren)
    position: Set[str]
    slot: Set[str]
    leader_weight: Set[str]
    follower_weight: Set[str]

    def state_str(self) -> str:
        parts: List[str] = []
        if self.hand_hold:
            parts.append(f"Handverbindung: {', '.join(sorted(self.hand_hold))}")
        if self.position:
            parts.append(f"Position: {', '.join(sorted(self.position))}")
        if self.slot:
            parts.append(f"Slot: {', '.join(sorted(self.slot))}")
        if self.leader_weight:
            parts.append(f"Leader-Gewicht: {', '.join(sorted(self.leader_weight))}")
        if self.follower_weight:
            parts.append(f"Follower-Gewicht: {', '.join(sorted(self.follower_weight))}")
        return " · ".join(parts)

    def compatible_with(self, other: "SalsaState") -> bool:
        """Prüft ob dieser Zustand als Post mit 'other' als Pre kompatibel ist."""
        return bool(
            self.hand_hold & other.hand_hold and
            self.position & other.position and
            self.slot & other.slot and
            self.leader_weight & other.leader_weight and
            self.follower_weight & other.follower_weight
        )

    def resolve_same(self, pre: "SalsaState") -> "SalsaState":
        """'same' in hand_hold bedeutet: Wert aus Pre übernehmen."""
        hh = pre.hand_hold if "same" in self.hand_hold else self.hand_hold
        return SalsaState(
            hand_hold=hh,
            position=self.position,
            slot=self.slot,
            leader_weight=self.leader_weight,
            follower_weight=self.follower_weight,
        )


@dataclass
class LeaderAction:
    beat: str
    foot: Optional[str] = None
    direction: Optional[str] = None
    action: Optional[str] = None
    hand: Optional[str] = None
    description: str = ""


@dataclass
class FollowerAction:
    beat: str
    foot: Optional[str] = None
    direction: Optional[str] = None
    action: Optional[str] = None
    description: str = ""


@dataclass
class Signal:
    type: str
    description: str = ""
    beat: Optional[str] = None
    hand: Optional[str] = None
    direction: Optional[str] = None


@dataclass
class Element:
    id: str
    name: str
    description: str
    counts: int
    level: int
    tags: List[str]
    pre: SalsaState
    post: SalsaState  # bereits resolved (kein 'same' mehr)
    leader_actions: List[LeaderAction]
    follower_actions: List[FollowerAction]
    signals: List[Signal]
    notes: str = ""

    def can_follow(self, other: "Element") -> bool:
        """Kann self direkt nach 'other' kommen?"""
        return other.post.compatible_with(self.pre)

    def explain_compatibility_error(self, other: "Element") -> str:
        """Erklärt benutzerfreundlich, warum dieses Element nicht auf 'other' folgen kann."""
        post = other.post
        pre = self.pre
        
        reasons = []
        if not (post.hand_hold & pre.hand_hold):
            reasons.append(f"die Handverbindung nicht passt (Ende: {', '.join(sorted(post.hand_hold))} vs. Start: {', '.join(sorted(pre.hand_hold))})")
        if not (post.position & pre.position):
            reasons.append(f"die Position im Raum unterschiedlich ist")
        if not (post.slot & pre.slot):
            reasons.append(f"die Ausrichtung im Slot nicht übereinstimmt")
        if not (post.leader_weight & pre.leader_weight):
            reasons.append(f"das Gewicht des Leaders auf dem falschen Fuß ist")
        if not (post.follower_weight & pre.follower_weight):
            reasons.append(f"das Gewicht des Followers auf dem falschen Fuß ist")
            
        if not reasons:
            return "Unbekannter Grund"
        return f"weil " + " und ".join(reasons)


@dataclass
class Figure:
    id: str
    name: str
    description: str
    level: int
    sequence: List[str]   # Element-IDs
    total_counts: int
    tags: List[str]
    notes: str = ""
    # Nach Laden befüllt:
    elements: List[Element] = field(default_factory=list)
    valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def is_executable_with(self, known_ids: Set[str]) -> bool:
        """Kann diese Figur mit dem bekannten Repertoire ausgeführt werden?"""
        return all(eid in known_ids for eid in self.sequence)

    def missing_elements(self, known_ids: Set[str]) -> List[str]:
        return [eid for eid in self.sequence if eid not in known_ids]

    def is_almost_executable(self, known_ids: Set[str]) -> bool:
        """Fehlt genau ein Element aus dem Repertoire?"""
        missing = self.missing_elements(known_ids)
        return len(missing) == 1


# ---------------------------------------------------------------------------
# Laden & Validieren
# ---------------------------------------------------------------------------

def _parse_state(raw: dict, key: str = None) -> SalsaState:
    """Wandelt ein YAML-Dict in ein SalsaState-Objekt um."""
    def as_set(val) -> Set[str]:
        if val is None:
            return {"any"}
        if isinstance(val, list):
            return set(str(v) for v in val)
        return {str(val)}

    return SalsaState(
        hand_hold=as_set(raw.get("hand_hold")),
        position=as_set(raw.get("position")),
        slot=as_set(raw.get("slot")),
        leader_weight=as_set(raw.get("leader_weight", ["L", "R"])),
        follower_weight=as_set(raw.get("follower_weight", ["L", "R"])),
    )


def _parse_actions(raw_list: list) -> List[LeaderAction]:
    if not raw_list:
        return []
    result = []
    for item in raw_list:
        result.append(LeaderAction(
            beat=str(item.get("beat", "?")),
            foot=item.get("foot"),
            direction=item.get("direction"),
            action=item.get("action"),
            hand=item.get("hand"),
            description=item.get("description", ""),
        ))
    return result


def _parse_follower_actions(raw_list: list) -> List[FollowerAction]:
    if not raw_list:
        return []
    result = []
    for item in raw_list:
        result.append(FollowerAction(
            beat=str(item.get("beat", "?")),
            foot=item.get("foot"),
            direction=item.get("direction"),
            action=item.get("action"),
            description=item.get("description", ""),
        ))
    return result


def _parse_signals(raw_list: list) -> List[Signal]:
    if not raw_list:
        return []
    result = []
    for item in raw_list:
        result.append(Signal(
            type=str(item.get("type", "unknown")),
            description=item.get("description", ""),
            beat=str(item.get("beat", "")) if "beat" in item else None,
            hand=item.get("hand"),
            direction=item.get("direction"),
        ))
    return result


def load_elements(path: Path) -> Dict[str, Element]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    elements: Dict[str, Element] = {}
    for raw in data["elements"]:
        pre = _parse_state(raw.get("pre", {}))
        post_raw = _parse_state(raw.get("post", {}))
        post = post_raw.resolve_same(pre)

        elem = Element(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description", "").strip(),
            counts=int(raw.get("counts", 8)),
            level=int(raw.get("level", 1)),
            tags=raw.get("tags", []),
            pre=pre,
            post=post,
            leader_actions=_parse_actions(raw.get("leader_actions", [])),
            follower_actions=_parse_follower_actions(raw.get("follower_actions", [])),
            signals=_parse_signals(raw.get("signals", [])),
            notes=raw.get("notes", "").strip(),
        )
        elements[elem.id] = elem

    return elements


def load_figures(path: Path, elements: Dict[str, Element]) -> Dict[str, Figure]:
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    figures: Dict[str, Figure] = {}
    for raw in data["figures"]:
        fig = Figure(
            id=raw["id"],
            name=raw["name"],
            description=raw.get("description", "").strip(),
            level=int(raw.get("level", 1)),
            sequence=raw.get("sequence", []),
            total_counts=int(raw.get("total_counts", 0)),
            tags=raw.get("tags", []),
            notes=raw.get("notes", "").strip(),
        )

        # Elemente auflösen und Kompatibilität prüfen
        errors = []
        elem_list = []
        for eid in fig.sequence:
            if eid not in elements:
                errors.append(f"Element '{eid}' nicht gefunden")
            else:
                elem_list.append(elements[eid])

        if not errors:
            for i in range(len(elem_list) - 1):
                a, b = elem_list[i], elem_list[i + 1]
                if not b.can_follow(a):
                    errors.append(
                        f"Zustandskonflikt: '{a.id}' → '{b.id}' "
                        f"(post={a.post} / pre={b.pre})"
                    )

        fig.elements = elem_list
        fig.valid = len(errors) == 0
        fig.validation_errors = errors

        # total_counts berechnen wenn nicht angegeben
        if fig.total_counts == 0 and elem_list:
            fig.total_counts = sum(e.counts for e in elem_list)

        figures[fig.id] = fig

    return figures


# ---------------------------------------------------------------------------
# Empfehlungs-Logik
# ---------------------------------------------------------------------------

def get_executable_figures(
    known_ids: Set[str],
    figures: Dict[str, Figure],
    only_valid: bool = True,
) -> List[Figure]:
    """Alle Figuren, die mit dem aktuellen Repertoire ausgeführt werden können."""
    result = []
    for fig in figures.values():
        if only_valid and not fig.valid:
            continue
        if fig.is_executable_with(known_ids):
            result.append(fig)
    return sorted(result, key=lambda f: f.level)


def score_element_to_learn(
    candidate_id: str,
    known_ids: Set[str],
    figures: Dict[str, Figure],
    elements: Dict[str, Element],
) -> Dict:
    """
    Berechnet einen Lernwert für ein Element.
    Kriterien:
      - Wie viele neue Figuren werden freigeschaltet?
      - Wie viele dieser Figuren fehlen danach nur noch 0 Elemente?
      - Level-Angemessenheit (nahe am aktuellen Level)
    """
    if candidate_id not in elements:
        return {"score": 0, "new_figures": [], "partially_unlocked": []}

    candidate = elements[candidate_id]
    hypothetical = known_ids | {candidate_id}

    currently_executable = {
        fig.id for fig in get_executable_figures(known_ids, figures)
    }
    new_executable = [
        fig for fig in get_executable_figures(hypothetical, figures)
        if fig.id not in currently_executable
    ]

    # Figuren die noch 1 Element fehlen (fast fertig)
    almost_done = []
    for fig in figures.values():
        if not fig.valid:
            continue
        missing = fig.missing_elements(hypothetical)
        if len(missing) == 1:
            almost_done.append(fig)

    score = len(new_executable) * 10 + len(almost_done) * 3

    return {
        "score": score,
        "element": candidate,
        "new_figures": new_executable,
        "almost_unlocked": almost_done,
    }


def recommend_elements_to_learn(
    known_ids: Set[str],
    figures: Dict[str, Figure],
    elements: Dict[str, Element],
    current_level: int,
    top_n: int = 5,
) -> List[Dict]:
    """
    Empfiehlt die nächsten zu lernenden Elemente.
    Filtert auf Level current_level und current_level+1.
    """
    candidates = [
        eid for eid, e in elements.items()
        if eid not in known_ids and e.level <= current_level + 1
    ]

    scored = []
    for eid in candidates:
        result = score_element_to_learn(eid, known_ids, figures, elements)
        scored.append(result)

    scored.sort(key=lambda x: -x["score"])
    return scored[:top_n]
