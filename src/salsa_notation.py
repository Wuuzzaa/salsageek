"""
salsa_notation.py – Data models and core logic for Salsa notation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set, Any
import yaml


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SalsaState:
    """
    Represents the physical configuration of the couple (hand hold, position, weight, etc.) 
    at a specific point in time (usually between elements).
    
    Fields are Sets to allow for multiple compatible configurations.
    """
    hand_hold: Set[str]   # e.g., {'open', 'closed', 'left-to-right'}
    position: Set[str]    # e.g., {'closed', 'open', 'side-by-side'}
    slot: Set[str]        # e.g., {'center', 'left', 'right'}
    leader_weight: Set[str]   # {'L', 'R'}
    follower_weight: Set[str] # {'L', 'R'}
    connection: Set[str] = field(default_factory=lambda: {"neutral"})

    def state_str(self) -> str:
        """Returns a human-readable representation of the state for tooltips/debug."""
        parts: List[str] = []
        def fmt(s):
            if isinstance(s, (set, list)):
                # Filter out 'neutral' if there are other meaningful values
                cleaned = [str(v) for v in s if str(v) != "neutral"]
                if not cleaned and "neutral" in [str(x) for x in s]:
                    cleaned = ["neutral"]
                return ", ".join(sorted(cleaned))
            return str(s)

        if self.hand_hold:
            parts.append(f"Hand: {fmt(self.hand_hold)}")
        if self.position:
            parts.append(f"Pos: {fmt(self.position)}")
        if self.slot:
            parts.append(f"Slot: {fmt(self.slot)}")
        if self.connection and "neutral" not in [str(x) for x in self.connection]:
            parts.append(f"Conn: {fmt(self.connection)}")
        if self.leader_weight:
            parts.append(f"L-Weight: {fmt(self.leader_weight)}")
        if self.follower_weight:
            parts.append(f"F-Weight: {fmt(self.follower_weight)}")
        return " · ".join(parts)

    def resolve_same(self, pre: "SalsaState") -> "SalsaState":
        """
        Resolves 'same' markers in the state by taking the actual values from the preceding state.
        
        Args:
            pre: The preceding state to inherit values from.
            
        Returns:
            A new SalsaState with 'same' values replaced.
        """
        def resolve(post_val, pre_val):
            # Check for 'same' in string, set or list
            if isinstance(post_val, (set, list)):
                if "same" in post_val:
                    return pre_val
            elif str(post_val).lower() == "same":
                return pre_val
            return post_val

        return SalsaState(
            hand_hold=resolve(self.hand_hold, pre.hand_hold),
            position=resolve(self.position, pre.position),
            slot=resolve(self.slot, pre.slot),
            leader_weight=resolve(self.leader_weight, pre.leader_weight),
            follower_weight=resolve(self.follower_weight, pre.follower_weight),
            connection=resolve(self.connection, pre.connection),
        )

    def compatible_with(self, other: "SalsaState") -> bool:
        """
        Checks if this state (acting as post-condition) is compatible with 'other' 
        (acting as pre-condition) by checking for non-empty intersections of all fields.
        """
        return bool(
            self.hand_hold & other.hand_hold and
            self.position & other.position and
            self.slot & other.slot and
            self.leader_weight & other.leader_weight and
            self.follower_weight & other.follower_weight and
            (not self.connection or not other.connection or self.connection & other.connection)
        )


@dataclass
class LeaderAction:
    """Represents an action performed by the leader on a specific beat."""
    beat: str
    foot: Optional[str] = None
    direction: Optional[str] = None
    turn_type: Optional[str] = None
    action: Optional[str] = None
    hand: Optional[str] = None
    description: str = ""


@dataclass
class FollowerAction:
    """Represents an action performed by the follower on a specific beat."""
    beat: str
    foot: Optional[str] = None
    direction: Optional[str] = None
    turn_type: Optional[str] = None
    action: Optional[str] = None
    description: str = ""


@dataclass
class Signal:
    """Represents a lead signal given by the leader."""
    type: str # e.g., 'visual', 'tension', 'physical'
    description: str = ""
    beat: Optional[str] = None
    hand: Optional[str] = None
    direction: Optional[str] = None


@dataclass
class Element:
    """
    The building block of a salsa figure. 
    Defines what happens during a specific number of beats.
    """
    id: str
    name: str
    description: str
    counts: int
    level: int
    tags: List[str]
    pre: SalsaState
    post: SalsaState  # already resolved (no 'same' anymore)
    leader_actions: List[LeaderAction]
    follower_actions: List[FollowerAction]
    signals: List[Signal]
    videos: List[Dict[str, str]] = field(default_factory=list)
    notes: str = ""

    def can_follow(self, other: "Element") -> bool:
        """Checks if this element can be performed directly after the given 'other' element."""
        return other.post.compatible_with(self.pre)

    def explain_compatibility_error(self, other: "Element") -> str:
        """Provides a user-friendly explanation of why this element cannot follow 'other'."""
        post = other.post
        pre = self.pre
        
        reasons = []
        if not (post.hand_hold & pre.hand_hold):
            reasons.append(f"hand hold doesn't match (End: {', '.join(sorted(post.hand_hold))} vs. Start: {', '.join(sorted(pre.hand_hold))})")
        if not (post.position & pre.position):
            reasons.append(f"position in space differs")
        if not (post.slot & pre.slot):
            reasons.append(f"alignment in slot doesn't match")
        if not (post.leader_weight & pre.leader_weight):
            reasons.append(f"leader's weight is on the wrong foot")
        if not (post.follower_weight & pre.follower_weight):
            reasons.append(f"follower's weight is on the wrong foot")
            
        if not reasons:
            return "Unknown reason"
        return f"because " + " and ".join(reasons)


@dataclass
class Figure:
    """
    A sequence of elements forming a complete move or combination.
    """
    id: str
    name: str
    description: str
    level: int
    sequence: List[str]   # Element IDs
    total_counts: int
    tags: List[str]
    videos: List[Dict[str, str]] = field(default_factory=list)
    notes: str = ""
    # Populated after loading:
    elements: List[Element] = field(default_factory=list)
    valid: bool = True
    validation_errors: List[str] = field(default_factory=list)

    def is_executable_with(self, known_ids: Set[str]) -> bool:
        """Returns True if all elements in the sequence are in the known repertoire."""
        return all(eid in known_ids for eid in self.sequence)

    def missing_elements(self, known_ids: Set[str]) -> List[str]:
        """Returns a list of element IDs that are not yet in the known repertoire."""
        return [eid for eid in self.sequence if eid not in known_ids]

    def is_almost_executable(self, known_ids: Set[str]) -> bool:
        """Returns True if exactly one element is missing from the known repertoire."""
        missing = self.missing_elements(known_ids)
        return len(missing) == 1


# ---------------------------------------------------------------------------
# Loading & Validation
# ---------------------------------------------------------------------------

def _parse_state(raw: dict, key: str = None) -> SalsaState:
    """
    Internal helper to convert a YAML state dictionary into a SalsaState object.
    Handles single values, lists, and None (converting to {'any'}).
    """
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
        connection=as_set(raw.get("connection", ["neutral"])),
    )


def _parse_actions(raw_list: list) -> List[LeaderAction]:
    """Parses a list of leader action dictionaries into LeaderAction objects."""
    if not raw_list:
        return []
    result = []
    for item in raw_list:
        result.append(LeaderAction(
            beat=str(item.get("beat", "?")),
            foot=item.get("foot"),
            direction=item.get("direction"),
            turn_type=item.get("turn_type"),
            action=item.get("action"),
            hand=item.get("hand"),
            description=item.get("description", ""),
        ))
    return result


def _parse_follower_actions(raw_list: list) -> List[FollowerAction]:
    """Parses a list of follower action dictionaries into FollowerAction objects."""
    if not raw_list:
        return []
    result = []
    for item in raw_list:
        result.append(FollowerAction(
            beat=str(item.get("beat", "?")),
            foot=item.get("foot"),
            direction=item.get("direction"),
            turn_type=item.get("turn_type"),
            action=item.get("action"),
            description=item.get("description", ""),
        ))
    return result


def _parse_signals(raw_list: list) -> List[Signal]:
    """Parses a list of signal dictionaries into Signal objects."""
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
    """
    Loads elements from a YAML file.
    Resolves 'same' post-conditions based on pre-conditions.
    """
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data or "elements" not in data:
        return {}

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
            videos=raw.get("videos", []),
            notes=raw.get("notes", "").strip(),
        )
        elements[elem.id] = elem

    return elements


def load_figures(path: Path, elements: Dict[str, Element]) -> Dict[str, Figure]:
    """
    Loads figures from a YAML file and validates them against the provided elements.
    Checks for state compatibility between elements in a sequence.
    """
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
            videos=raw.get("videos", []),
            notes=raw.get("notes", "").strip(),
        )

        # Resolve elements and check compatibility
        errors = []
        elem_list = []
        for eid in fig.sequence:
            if eid not in elements:
                errors.append(f"Element '{eid}' not found")
            else:
                elem_list.append(elements[eid])

        if not errors:
            for i in range(len(elem_list) - 1):
                a, b = elem_list[i], elem_list[i + 1]
                if not b.can_follow(a):
                    errors.append(
                        f"State conflict: '{a.id}' → '{b.id}' "
                        f"(post={a.post} / pre={b.pre})"
                    )

        fig.elements = elem_list
        fig.valid = len(errors) == 0
        fig.validation_errors = errors

        # Calculate total_counts if not provided
        if fig.total_counts == 0 and elem_list:
            fig.total_counts = sum(e.counts for e in elem_list)

        figures[fig.id] = fig

    return figures


# ---------------------------------------------------------------------------
# Recommendation Logic
# ---------------------------------------------------------------------------

def get_executable_figures(
    known_ids: Set[str],
    figures: Dict[str, Figure],
    only_valid: bool = True,
) -> List[Figure]:
    """
    Returns a list of figures that can be performed given the set of known element IDs.
    
    Args:
        known_ids: Set of element IDs the user already knows.
        figures: Dictionary of all available figures.
        only_valid: If True, only return figures that passed state validation.
        
    Returns:
        Sorted list of executable figures (by level).
    """
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
) -> Dict[str, Any]:
    """
    Calculates a learning score for an element based on how many new figures it unlocks.
    
    Args:
        candidate_id: ID of the element to evaluate.
        known_ids: Set of IDs already known.
        figures: Dictionary of all figures.
        elements: Dictionary of all elements.
        
    Returns:
        Dictionary containing score, element object, and lists of unlocked/almost unlocked figures.
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

    # Figures missing exactly 1 element (almost done)
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
) -> List[Dict[str, Any]]:
    """
    Recommends the next elements to learn based on the current level and unlocked figures.
    
    Args:
        known_ids: Set of IDs already known.
        figures: Dictionary of all figures.
        elements: Dictionary of all elements.
        current_level: Current learning level.
        top_n: Maximum number of recommendations to return.
        
    Returns:
        List of dictionaries with recommendation details, sorted by score descending.
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
