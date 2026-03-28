import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

class ElementEditorService:
    def __init__(self, custom_elements_path: Path, schema: Optional[Dict] = None):
        self.path = custom_elements_path
        self.schema = schema or {}

    def to_dict(self, obj):
        """Converts complex types (Sets, Dataclasses) into simple dicts/lists for Jinja2."""
        if isinstance(obj, set):
            return sorted(list(obj))
        if isinstance(obj, (list, tuple)):
            return [self.to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {k: self.to_dict(v) for k, v in obj.items()}
        if hasattr(obj, "__dict__"):
            return {k: self.to_dict(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        return obj

    def fill_missing_steps(self, actions: List[Dict], target_counts: int) -> List[Dict]:
        """Ensures the actions list has exactly target_counts entries."""
        current_actions = {str(a.get("beat")): a for a in actions if "beat" in a}
        new_actions = []
        for i in range(1, target_counts + 1):
            beat_str = str(i)
            if beat_str in current_actions:
                new_actions.append(current_actions[beat_str])
            else:
                new_actions.append({
                    "beat": beat_str,
                    "foot": "-",
                    "direction": "pause",
                    "turn_type": "",
                    "description": ""
                })
        return sorted(new_actions, key=lambda x: int(x["beat"]) if x["beat"].isdigit() else 999)

    def validate_element(self, data: Dict) -> Tuple[bool, List[str]]:
        """Checks an element against the schema."""
        if not self.schema:
            return True, []
        
        errors = []
        # Hand hold
        valid_hands = {h["id"] for h in self.schema.get("hand_holds", [])}
        valid_hands.add("same")
        valid_hands.add("any")
        
        pre_hands = data.get("pre", {}).get("hand_hold", [])
        for h in pre_hands:
            if h not in valid_hands:
                errors.append(f"Invalid pre-hand hold: {h}")
        
        post_hands = data.get("post", {}).get("hand_hold", [])
        if isinstance(post_hands, str): post_hands = [post_hands]
        for h in post_hands:
            if h not in valid_hands:
                errors.append(f"Invalid post-hand hold: {h}")

        # Connection
        valid_conn = {c["id"] for c in self.schema.get("connections", [])}
        valid_conn.add("same")
        valid_conn.add("any")
        for c in data.get("pre", {}).get("connection", []):
            if c not in valid_conn:
                errors.append(f"Invalid pre-connection: {c}")
        post_conn = data.get("post", {}).get("connection", [])
        if isinstance(post_conn, str): post_conn = [post_conn]
        for c in post_conn:
            if c not in valid_conn:
                errors.append(f"Invalid post-connection: {c}")

        # Position
        valid_pos = {p["id"] for p in self.schema.get("positions", [])}
        valid_pos.add("any")
        for p in data.get("pre", {}).get("position", []):
            if p not in valid_pos:
                errors.append(f"Invalid pre-position: {p}")
        post_pos = data.get("post", {}).get("position", [])
        if isinstance(post_pos, str): post_pos = [post_pos]
        for p in post_pos:
            if p not in valid_pos:
                errors.append(f"Invalid post-position: {p}")

        # Actions
        valid_dirs = {d["id"] for d in self.schema.get("directions", [])}
        valid_turns = {t["id"] for t in self.schema.get("turn_types", [])}
        for action in data.get("leader_actions", []) + data.get("follower_actions", []):
            d = action.get("direction")
            if d and d not in valid_dirs:
                errors.append(f"Invalid direction in actions: {d}")
            t = action.get("turn_type")
            if t and t not in valid_turns:
                errors.append(f"Invalid turn_type in actions: {t}")

        return len(errors) == 0, errors

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9_\-]", "_", text)
        return text if text else "element"

    def add_custom_element(self, name: str, level: int, counts: int, pre: Dict, post: Dict, 
                           description: str = "", tags: List[str] = None, 
                           leader_actions: List[Dict] = None, follower_actions: List[Dict] = None,
                           signals: List[Dict] = None, notes: str = "",
                           custom_id: str = None) -> Tuple[Optional[str], List[str]]:
        # Generate ID if not provided
        if not custom_id:
            import time
            elem_id = f"custom_{self._slugify(name)}_{int(time.time())}"
        else:
            elem_id = custom_id
        
        new_element = {
            "id": elem_id,
            "name": name,
            "description": description or f"Newly created element: {name}",
            "counts": counts,
            "level": int(level),
            "tags": tags or ["Custom"],
            "pre": pre,
            "post": post,
            "leader_actions": leader_actions or [],
            "follower_actions": follower_actions or [],
            "signals": signals or [],
            "notes": notes or ""
        }

        # Validation
        is_valid, errors = self.validate_element(new_element)
        if not is_valid:
            return None, errors

        # Load
        data = {"elements": []}
        if self.path.exists():
            with open(self.path, "r", encoding="utf-8") as f:
                existing = yaml.safe_load(f)
                if existing and "elements" in existing:
                    data = existing
        
        # If updating, replace existing element with same ID
        if custom_id:
            data["elements"] = [e for e in data["elements"] if e["id"] != custom_id]
            
        data["elements"].append(new_element)

        # Save
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            
        return elem_id, []
