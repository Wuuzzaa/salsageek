from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Set, Optional
import yaml
from src.salsa_notation import (
    Element,
    Figure,
    load_elements,
    load_figures,
    recommend_elements_to_learn
)
from src.services.profile_service import ProfileService

class SalsaService:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.profile_service = ProfileService()
        self.elements = self._load_all_elements()
        self.figures = self._load_all_figures()
        self.schema = self._load_schema()
        
        self.level_label = {
            0: "TBD", 1: "Novice", 2: "Beginner", 3: "Intermediate", 4: "Advanced", 5: "Expert"
        }
        self.level_badge = {
            1: "success", 2: "info", 3: "warning", 4: "danger", 5: "dark"
        }

    def _load_all_elements(self) -> Dict[str, Element]:
        all_elems = {}
        elem_dir = self.data_dir / "elements"
        if elem_dir.exists() and elem_dir.is_dir():
            for yaml_file in elem_dir.glob("*.yaml"):
                all_elems.update(load_elements(yaml_file))
        return all_elems

    def _load_all_figures(self) -> Dict[str, Figure]:
        all_figs = {}
        fig_dir = self.data_dir / "figures"
        if fig_dir.exists() and fig_dir.is_dir():
            for yaml_file in fig_dir.glob("*.yaml"):
                try:
                    all_figs.update(load_figures(yaml_file, self.elements))
                except Exception as e:
                    print(f"Error loading figure from {yaml_file}: {e}")
        return all_figs

    def _load_schema(self) -> Dict:
        schema_path = self.data_dir / "schema.yaml"
        if schema_path.exists():
            with open(schema_path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        return {}

    def reload_elements(self):
        self.elements = self._load_all_elements()
        self.figures = self._load_all_figures() # Also reload figures as they depend on elements

    def reload_figures(self):
        self.figures = self._load_all_figures()

    def get_element(self, element_id: str) -> Optional[Element]:
        return self.elements.get(element_id)

    def get_all_figures(self) -> Dict[str, Figure]:
        return self.figures

    def get_known_elements(self, profile_name: str) -> Set[str]:
        profile_data = self.profile_service.load_profile(profile_name)
        return set(profile_data.get("known_elements", []))

    def get_current_level(self, known_ids: Set[str]) -> int:
        if not known_ids: return 1
        known_levels = [self.elements[eid].level for eid in known_ids if eid in self.elements]
        return max(known_levels) if known_levels else 1

    def group_elements_by_level(self) -> Dict[int, List[Element]]:
        grouped = {}
        for elem in self.elements.values():
            level = elem.level
            if level not in grouped: grouped[level] = []
            grouped[level].append(elem)
        
        for level in grouped:
            grouped[level].sort(key=lambda e: e.name)
        return dict(sorted(grouped.items()))

    def find_figures_using_element(self, element_id: str, all_figures: Dict[str, Figure]) -> List[Figure]:
        return [f for f in all_figures.values() if element_id in f.sequence]

    def get_almost_executable_figures(self, known_ids: Set[str], all_figures: Dict[str, Figure]) -> List[Figure]:
        almost = []
        for fig in all_figures.values():
            if not fig.is_executable_with(known_ids) and fig.is_almost_executable(known_ids):
                almost.append(fig)
        return almost

    def get_recommendations(self, known_ids: Set[str], all_figures: Dict[str, Figure], current_level: int) -> List[Dict]:
        recs = recommend_elements_to_learn(
            known_ids, all_figures, self.elements, current_level
        )
        # Add labels etc if needed, but for now just the list
        return recs
