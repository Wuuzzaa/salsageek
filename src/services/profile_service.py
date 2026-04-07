import os
import yaml
import re
from pathlib import Path
from typing import List, Set, Optional, Dict

class ProfileService:
    def __init__(self, profiles_dir: str = "profiles"):
        self.profiles_dir = Path(profiles_dir)
        self.profiles_dir.mkdir(exist_ok=True)

    def slugify(self, name: str) -> str:
        """Normalizes the profile name for use as a filename."""
        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9_\-]", "_", name)
        return name if name else "unnamed"

    def get_profile_path(self, profile_name: str) -> Path:
        return self.profiles_dir / f"{self.slugify(profile_name)}.yaml"

    def list_profiles(self) -> List[str]:
        """Lists all available profile names (based on filenames)."""
        profiles = []
        for f in self.profiles_dir.glob("*.yaml"):
            profiles.append(f.stem)
        return sorted(profiles)

    def load_profile(self, profile_name: str) -> Dict:
        """Loads profile data (known elements)."""
        path = self.get_profile_path(profile_name)
        if not path.exists():
            return {"known_elements": []}
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "known_elements" not in data:
                    data["known_elements"] = []
                return data
        except Exception:
            return {"known_elements": []}

    def save_profile(self, profile_name: str, known_ids: Set[str]):
        """Saves profile data."""
        path = self.get_profile_path(profile_name)
        
        data = {
            "known_elements": sorted(list(known_ids))
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def delete_profile(self, profile_name: str):
        path = self.get_profile_path(profile_name)
        if path.exists():
            path.unlink()
