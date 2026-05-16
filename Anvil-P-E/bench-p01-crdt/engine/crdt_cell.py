from __future__ import annotations
from typing import Any
from engine.vector_clock import VectorClock

class CRDTCell:
    def __init__(self, value: Any, clock: VectorClock):
        self.value = value
        self.clock = clock
        self.conflicts: list[tuple[Any, VectorClock]] = []

    def merge(self, other: 'CRDTCell') -> 'CRDTCell':
        if self.clock == other.clock:
            return self
        if self.clock.dominates(other.clock):
            return self
        if other.clock.dominates(self.clock):
            return other
            
        # Concurrent: Multi-Value Register
        merged_clock = self.clock.merge(other.clock)
        new_cell = CRDTCell(self.value, merged_clock)
        
        # Combine conflicts
        new_conflicts = list(self.conflicts)
        new_conflicts.append((other.value, other.clock))
        new_conflicts.extend(other.conflicts)
        
        new_cell.conflicts = new_conflicts
        return new_cell

    def winner_value(self) -> Any:
        if not self.conflicts:
            return self.value
            
        all_vals = self.all_values()
        # Sort as strings deterministically, return lexicographically smallest
        return sorted(all_vals, key=lambda v: str(v))[0]

    def all_values(self) -> list[Any]:
        return [self.value] + [c[0] for c in self.conflicts]


if __name__ == '__main__':
    # Unit Tests
    
    vc1 = VectorClock({'A': 1})
    vc2 = VectorClock({'A': 1, 'B': 1})
    vc3 = VectorClock({'C': 1})
    
    # 1. Test self-wins
    cell1 = CRDTCell("apple", vc2)
    cell2 = CRDTCell("banana", vc1)
    merged_self = cell1.merge(cell2)
    assert merged_self is cell1, "Self-wins test failed"
    assert merged_self.winner_value() == "apple", "Self-wins winner failed"
    
    # 2. Test other-wins
    merged_other = cell2.merge(cell1)
    assert merged_other is cell1, "Other-wins test failed"
    
    # 3. Test concurrent merge
    cell3 = CRDTCell("orange", vc3)
    merged_concurrent = cell1.merge(cell3)
    assert merged_concurrent is not cell1 and merged_concurrent is not cell3, "Concurrent merge should return new cell"
    assert set(merged_concurrent.all_values()) == {"apple", "orange"}, "Concurrent merge all_values failed"
    assert merged_concurrent.clock.to_dict() == {'A': 1, 'B': 1, 'C': 1}, "Concurrent merge clock failed"
    
    # 4. Test winner_value determinism
    # "apple" vs "orange", "apple" is lexicographically smaller
    assert merged_concurrent.winner_value() == "apple", "Winner value determinism failed"
    
    # Test winner determinism reverse
    cell_a = CRDTCell("zebra", VectorClock({'A': 1}))
    cell_b = CRDTCell("alpaca", VectorClock({'B': 1}))
    merged_ab = cell_a.merge(cell_b)
    assert merged_ab.winner_value() == "alpaca", "Winner value determinism (reverse) failed"

    print("All CRDTCell unit tests passed!")
