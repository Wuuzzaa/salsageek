import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import re
import time

class ElementEditorService:
    """
    Service for creating, updating and validating custom salsa elements.
    """
    def __init__(self, custom_elements_dir: Path, schema: Optional[Dict] = None):
        self.dir = custom_elements_dir
        self.dir.mkdir(parents=True, exist_ok=True)
        self.schema = schema or {}

    def to_dict(self, obj: Any) -> Any:
        """
        Converts complex types (Sets, Dataclasses, SalsaState) into simple dicts/lists for Jinja2.
        
        Args:
            obj: The object to convert.
            
        Returns:
            A JSON-serializable representation of the object.
        """
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, (list, tuple, set)):
            if isinstance(obj, set):
                return [self.to_dict(i) for i in sorted(list(obj), key=lambda x: str(x))]
            return [self.to_dict(i) for i in obj]
        if isinstance(obj, dict):
            return {str(k): self.to_dict(v) for k, v in obj.items()}
        
        # Dataclasses and other objects
        if hasattr(obj, "__dict__"):
            data = {}
            for k, v in vars(obj).items():
                if k.startswith("_"):
                    continue
                data[k] = self.to_dict(v)
            return data
        
        # Dataclasses (some might not have __dict__ or behave differently)
        try:
            from dataclasses import asdict, is_dataclass
            if is_dataclass(obj):
                return self.to_dict(asdict(obj))
        except ImportError:
            pass

        # SalsaState specialized handling if it's not caught by __dict__
        if obj.__class__.__name__ == 'SalsaState':
             return {
                 "hand_hold": self.to_dict(obj.hand_hold),
                 "position": self.to_dict(obj.position),
                 "slot": self.to_dict(obj.slot),
                 "leader_weight": self.to_dict(obj.leader_weight),
                 "follower_weight": self.to_dict(obj.follower_weight),
                 "connection": self.to_dict(obj.connection)
             }

        return str(obj)

    def fill_missing_steps(self, actions: List[Dict], target_counts: int) -> List[Dict]:
        """
        Ensures the actions list has exactly target_counts entries by filling gaps with pauses.
        
        Args:
            actions: List of action dictionaries.
            target_counts: The required number of beats.
            
        Returns:
            A complete list of actions for all beats.
        """
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

    def parse_actions_raw(self, raw_text: str) -> List[Dict[str, str]]:
        """
        Parses raw text into a list of action dictionaries.
        Format expected: "beat: foot direction [turn_type]"
        
        Args:
            raw_text: The multiline string from the form input.
            
        Returns:
            List of parsed action dicts.
        """
        actions = []
        if not raw_text:
            return actions
            
        for line in raw_text.splitlines():
            if ":" in line:
                parts = line.split(":", 1)
                beat = parts[0].strip()
                rest = parts[1].strip().split()
                
                # Special case: "-" or "pause" means no foot action
                foot = rest[0] if len(rest) > 0 else ""
                direction = rest[1] if len(rest) > 1 else ""
                turn_type = rest[2] if len(rest) > 2 else ""
                
                if foot in ["-", "pause"]:
                    foot = ""
                    if not direction: 
                        direction = "pause"
                
                actions.append({
                    "beat": beat,
                    "foot": foot,
                    "direction": direction,
                    "turn_type": turn_type,
                    "description": line.strip()
                })
        return actions

    def parse_actions_from_form(self, form_data: Any, counts: int, role: str) -> List[Dict[str, str]]:
        """
        Parses individual form fields (l_foot_1, l_dir_1, etc.) into actions.
        """
        prefix = 'l' if role == 'leader' else 'f'
        actions = []
        
        for i in range(1, counts + 1):
            foot = form_data.get(f"{prefix}_foot_{i}", "-")
            direction = form_data.get(f"{prefix}_dir_{i}", "pause")
            turn_type = form_data.get(f"{prefix}_turn_{i}", "")
            action_val = form_data.get(f"{prefix}_action_{i}", "").strip()
            hand_val = form_data.get(f"{prefix}_hand_{i}", "").strip()
            description = form_data.get(f"{prefix}_desc_{i}", "").strip()
            
            # Normalization
            if foot in ["-", "pause", "none", ""]:
                foot = ""
            
            if not direction or direction in ["-", "none", ""]:
                direction = "pause"
            
            # If no description is provided, generate a basic one
            if not description:
                description = f"{i}: {foot if foot else '-'} {direction} {turn_type}".strip()
            
            # If everything is empty/pause, we still keep it as a 'pause' step
            actions.append({
                "beat": str(i),
                "foot": foot,
                "direction": direction,
                "turn_type": turn_type if turn_type else "",
                "action": action_val if action_val else None,
                "hand": hand_val if hand_val else None,
                "description": description
            })
            
        return actions

    def validate_element(self, data: Dict) -> Tuple[bool, List[str]]:
        """
        Checks an element against the schema for valid values.
        
        Args:
            data: The element data to validate.
            
        Returns:
            Tuple of (is_valid, list_of_errors).
        """
        if not self.schema:
            return True, []
        
        errors = []
        
        # 1. Validate Pre/Post states
        self._validate_state_fields(data.get("pre", {}), "pre", errors)
        self._validate_state_fields(data.get("post", {}), "post", errors)

        # 2. Validate Actions
        self._validate_actions(data.get("leader_actions", []), "leader", errors)
        self._validate_actions(data.get("follower_actions", []), "follower", errors)

        return len(errors) == 0, errors

    def _validate_state_fields(self, state: Dict, prefix: str, errors: List[str]):
        """Internal helper to validate state fields against schema."""
        field_mapping = {
            "hand_hold": "hand_holds",
            "connection": "connections",
            "position": "positions",
            "slot": "slots",
            "leader_weight": "weights",
            "follower_weight": "weights"
        }
        
        for field, schema_key in field_mapping.items():
            valid_values = {v["id"] for v in self.schema.get(schema_key, [])}
            valid_values.update({"same", "any"})
            
            values = state.get(field, [])
            if isinstance(values, str):
                values = [values]
                
            for val in values:
                if val not in valid_values:
                    field_display = field.replace('_', ' ').capitalize()
                    errors.append(f"{prefix.upper()} {field_display}: Ungültiger Wert '{val}'")

    def _validate_actions(self, actions: List[Dict], person: str, errors: List[str]):
        """Internal helper to validate actions against schema."""
        valid_dirs = {d["id"] for d in self.schema.get("directions", [])}
        valid_turns = {t["id"] for t in self.schema.get("turn_types", [])}
        valid_turns.add("") # Allow empty turn
        
        for action in actions:
            beat = action.get("beat", "?")
            d = action.get("direction")
            if d and d not in valid_dirs:
                errors.append(f"Beat {beat}: Ungültige Richtung '{d}' ({person.capitalize()})")
            
            t = action.get("turn_type")
            if t and t not in valid_turns:
                errors.append(f"Beat {beat}: Ungültiger Turn-Typ '{t}' ({person.capitalize()})")

    def _slugify(self, text: str) -> str:
        """Converts a string to a URL-friendly slug."""
        text = text.lower().strip()
        text = re.sub(r"[^a-z0-9_\-]", "_", text)
        return text if text else "element"

    def add_custom_element(self, name: str, level: int, counts: int, pre: Dict, post: Dict, 
                           description: str = "", tags: List[str] = None, 
                           leader_actions: List[Dict] = None, follower_actions: List[Dict] = None,
                           signals: List[Dict] = None, videos: List[Dict[str, str]] = None,
                           notes: str = "", custom_id: str = None) -> Tuple[Optional[str], List[str], Optional[Dict]]:
        """
        Adds or updates a custom element in the YAML storage.
        
        Args:
            name: Human-readable name.
            level: Difficulty level (1-5).
            counts: Number of beats (usually 8).
            pre: Pre-conditions state.
            post: Post-conditions state.
            description: Short description.
            tags: List of tags.
            leader_actions: List of leader actions.
            follower_actions: List of follower actions.
            signals: List of hand signals.
            videos: List of associated video dicts (url, title, type).
            notes: Additional notes.
            custom_id: If provided, the element with this ID will be updated.
            
        Returns:
            Tuple of (element_id, list_of_errors, element_data).
        """
        # Generate ID if not provided
        if not custom_id:
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
            "videos": videos or [],
            "notes": notes or ""
        }

        # Validation
        is_valid, errors = self.validate_element(new_element)
        if not is_valid:
            return None, errors, None

        # Load existing custom elements from its own file
        self.dir.mkdir(parents=True, exist_ok=True)
        file_path = self.dir / f"{elem_id}.yaml"
        
        # Save to its own YAML file
        data = {"elements": [new_element]}
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            
        return elem_id, [], new_element
