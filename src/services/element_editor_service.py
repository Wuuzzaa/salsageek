import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re

class ElementEditorService:
    def __init__(self, custom_elements_path: Path, schema: Optional[Dict] = None):
        self.path = custom_elements_path
        self.schema = schema or {}

    def validate_element(self, data: Dict) -> Tuple[bool, List[str]]:
        """Checks an element against the schema."""
        if not self.schema:
            return True, []
        
        errors = []
        # Hand hold
        valid_hands = {h["id"] for h in self.schema.get("hand_holds", [])}
        valid_hands.add("same")
        
        pre_hands = data.get("pre", {}).get("hand_hold", [])
        for h in pre_hands:
            if h not in valid_hands:
                errors.append(f"Invalid pre-hand hold: {h}")
        
        post_hand = data.get("post", {}).get("hand_hold")
        if post_hand and post_hand not in valid_hands:
            errors.append(f"Invalid post-hand hold: {post_hand}")

        # Position
        valid_pos = {p["id"] for p in self.schema.get("positions", [])}
        for p in data.get("pre", {}).get("position", []):
            if p not in valid_pos:
                errors.append(f"Invalid pre-position: {p}")
        if data.get("post", {}).get("position") not in valid_pos:
            errors.append(f"Invalid post-position: {data.get('post', {}).get('position')}")

        # Actions
        valid_dirs = {d["id"] for d in self.schema.get("directions", [])}
        for action in data.get("leader_actions", []) + data.get("follower_actions", []):
            d = action.get("direction")
            if d and d not in valid_dirs:
                errors.append(f"Invalid direction in actions: {d}")

        return len(errors) == 0, errors

    def _slugify(self, text: str) -> str:
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9_\-]", "_", text)
        return text if text else "element"

    def add_custom_element(self, name: str, level: int, counts: int, pre: Dict, post: Dict, 
                           description: str = "", tags: List[str] = None, 
                           leader_actions: List[Dict] = None, follower_actions: List[Dict] = None,
                           signals: List[Dict] = None, notes: str = "") -> Tuple[Optional[str], List[str]]:
        # Generate ID
        import time
        elem_id = f"custom_{self._slugify(name)}_{int(time.time())}"
        
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
        
        data["elements"].append(new_element)

        # Save
        with open(self.path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            
        return elem_id, []
