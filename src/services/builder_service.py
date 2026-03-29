from typing import List, Dict, Optional, Tuple, Set
from src.salsa_notation import Element, Figure

class BuilderService:
    def __init__(self, elements: Dict[str, Element]):
        self.elements = elements

    def get_element(self, element_id: str) -> Optional[Element]:
        return self.elements.get(element_id)

    def sequence_from_raw(self, raw: str) -> List[str]:
        if not raw:
            return []
        return [item.strip() for item in raw.split(",") if item.strip()]

    def raw_from_sequence(self, sequence: List[str]) -> str:
        return ",".join(sequence)

    def add_element(self, sequence: List[str], element_id: str) -> List[str]:
        if element_id in self.elements:
            return sequence + [element_id]
        return sequence

    def remove_element(self, sequence: List[str], index: int) -> List[str]:
        if 0 <= index < len(sequence):
            new_seq = list(sequence)
            new_seq.pop(index)
            return new_seq
        return sequence

    def move_element(self, sequence: List[str], index: int, direction: int) -> List[str]:
        """direction: -1 for left/up, 1 for right/down"""
        if 0 <= index < len(sequence):
            new_index = index + direction
            if 0 <= new_index < len(sequence):
                new_seq = list(sequence)
                new_seq[index], new_seq[new_index] = new_seq[new_index], new_seq[index]
                return new_seq
        return sequence

    def validate_sequence(self, sequence: List[str]) -> Dict:
        if not sequence:
            return {"valid": True, "empty": True}

        unknown = [eid for eid in sequence if eid not in self.elements]
        if unknown:
            return {"valid": False, "error": f"Unknown elements: {', '.join(unknown)}"}

        elem_list = [self.elements[eid] for eid in sequence]
        errors = []

        for i in range(len(elem_list) - 1):
            first = elem_list[i]
            second = elem_list[i + 1]
            if not second.can_follow(first):
                errors.append({
                    "index": i,
                    "from_name": first.name,
                    "to_name": second.name,
                    "explanation": self._explain_compatibility_error(first, second),
                    "post_state": self._state_str(first.post),
                    "pre_state": self._state_str(second.pre),
                })

        if errors:
            return {"valid": False, "errors": errors, "elem_list": elem_list}

        total_counts = sum(elem.counts for elem in elem_list)
        sequence_names = [elem.name for elem in elem_list]
        return {
            "valid": True,
            "elem_list": elem_list,
            "sequence_names": sequence_names,
            "total_counts": total_counts,
            "phrase_count": total_counts / 8,
            "start_state": self._state_str(elem_list[0].pre),
            "end_state": self._state_str(elem_list[-1].post),
        }

    def get_recommendations(self, sequence: List[str]) -> List[Element]:
        if not sequence:
            # If empty, maybe suggest level 1 elements? Or just leave empty.
            return []
        
        last_id = sequence[-1]
        if last_id not in self.elements:
            return []
            
        last_elem = self.elements[last_id]
        recommendations = []
        for elem in self.elements.values():
            if elem.can_follow(last_elem):
                recommendations.append(elem)
        
        return sorted(recommendations, key=lambda e: (e.level, e.name))

    def _state_str(self, state) -> str:
        return state.state_str()

    def _explain_compatibility_error(self, first: Element, second: Element) -> str:
        return second.explain_compatibility_error(first)

    def create_custom_figure(self, validation_result: Dict) -> Optional[Figure]:
        if not validation_result.get("valid") or validation_result.get("empty"):
            return None

        elem_list = validation_result.get("elem_list", [])
        if not elem_list:
            return None

        # Determine max level
        max_level = max(e.level for e in elem_list) if elem_list else 1

        return Figure(
            id="custom_builder_figure",
            name="Custom Figure",
            description="Sequence assembled in the builder.",
            level=max_level,
            sequence=[e.id for e in elem_list],
            total_counts=validation_result.get("total_counts", 0),
            tags=["Builder", "Custom"],
            notes="",
            elements=elem_list,
            valid=True
        )
