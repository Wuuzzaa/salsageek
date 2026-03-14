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
        """Normalisiert den Profilnamen für die Verwendung als Dateiname."""
        name = name.lower().strip()
        name = re.sub(r"[^a-z0-9_\-]", "_", name)
        return name if name else "unnamed"

    def get_profile_path(self, profile_name: str) -> Path:
        return self.profiles_dir / f"{self.slugify(profile_name)}.yaml"

    def list_profiles(self) -> List[str]:
        """Listet alle verfügbaren Profilnamen auf (basierend auf Dateinamen)."""
        profiles = []
        for f in self.profiles_dir.glob("*.yaml"):
            profiles.append(f.stem)
        return sorted(profiles)

    def load_profile(self, profile_name: str) -> Dict:
        """Lädt die Profildaten (bekannte Elemente und eigene Figuren)."""
        path = self.get_profile_path(profile_name)
        if not path.exists():
            return {"known_elements": [], "custom_figures": []}
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
                if "known_elements" not in data:
                    data["known_elements"] = []
                if "custom_figures" not in data:
                    data["custom_figures"] = []
                return data
        except Exception:
            return {"known_elements": [], "custom_figures": []}

    def save_profile(self, profile_name: str, known_ids: Set[str], custom_figures: List[Dict] = None):
        """Speichert die Profildaten."""
        path = self.get_profile_path(profile_name)
        
        # Falls wir nur known_ids aktualisieren, laden wir den Rest
        if custom_figures is None:
            existing = self.load_profile(profile_name)
            custom_figures = existing.get("custom_figures", [])

        data = {
            "known_elements": sorted(list(known_ids)),
            "custom_figures": custom_figures
        }
        with open(path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def delete_profile(self, profile_name: str):
        path = self.get_profile_path(profile_name)
        if path.exists():
            path.unlink()
