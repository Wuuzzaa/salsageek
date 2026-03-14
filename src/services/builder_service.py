from typing import List, Dict, Optional, Tuple, Set
from src.salsa_notation import Element

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
            return {"valid": False, "error": f"Unbekannte Elemente: {', '.join(unknown)}"}

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
        return {
            "valid": True,
            "elem_list": elem_list,
            "total_counts": total_counts,
            "phrase_count": total_counts / 8,
            "start_state": self._state_str(elem_list[0].pre),
            "end_state": self._state_str(elem_list[-1].post),
        }

    def get_recommendations(self, sequence: List[str]) -> List[Element]:
        if not sequence:
            # Wenn leer, alle Level 1 Elemente vorschlagen? Oder einfach leer lassen.
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
        """Kopie der Hilfsfunktion aus app.py (oder in utils auslagern)"""
        hh = ", ".join(sorted(state.hand_hold))
        pos = ", ".join(sorted(state.position))
        sl = ", ".join(sorted(state.slot))
        lw = ", ".join(sorted(state.leader_weight))
        fw = ", ".join(sorted(state.follower_weight))
        return f"Hände: {hh} | Pos: {pos} | Slot: {sl} | Gewicht: L:{lw}/F:{fw}"

    def _explain_compatibility_error(self, first: Element, second: Element) -> str:
        """Kopie der Hilfsfunktion aus app.py (oder in utils auslagern)"""
        reasons = []
        if not (first.post.hand_hold & second.pre.hand_hold):
            reasons.append(f"Haltung passt nicht: {first.post.hand_hold} vs {second.pre.hand_hold}")
        if not (first.post.position & second.pre.position):
            reasons.append(f"Position passt nicht: {first.post.position} vs {second.pre.position}")
        if not (first.post.slot & second.pre.slot):
            reasons.append(f"Slot/Ausrichtung passt nicht: {first.post.slot} vs {second.pre.slot}")
        if not (first.post.leader_weight & second.pre.leader_weight):
            reasons.append(f"Gewicht Leader passt nicht: {first.post.leader_weight} vs {second.pre.leader_weight}")
        if not (first.post.follower_weight & second.pre.follower_weight):
            reasons.append(f"Gewicht Follower passt nicht: {first.post.follower_weight} vs {second.pre.follower_weight}")
        return " / ".join(reasons)
