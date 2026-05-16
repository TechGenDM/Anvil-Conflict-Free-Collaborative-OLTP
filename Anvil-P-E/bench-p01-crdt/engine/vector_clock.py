from __future__ import annotations

class VectorClock:
    def __init__(self, clock: dict[str, int] | None = None):
        """Initialize with a copy of the provided clock dict, or an empty dict."""
        self.clock = dict(clock) if clock is not None else {}

    def increment(self, peer_id: str) -> None:
        """Bump the counter for the given peer by 1."""
        self.clock[peer_id] = self.clock.get(peer_id, 0) + 1

    def merge(self, other: 'VectorClock') -> 'VectorClock':
        """Return a new VectorClock with the component-wise maximum of both clocks."""
        merged_clock = {}
        all_peers = set(self.clock.keys()).union(set(other.clock.keys()))
        for peer in all_peers:
            merged_clock[peer] = max(self.clock.get(peer, 0), other.clock.get(peer, 0))
        return VectorClock(merged_clock)

    def dominates(self, other: 'VectorClock') -> bool:
        """
        Return True if self >= other everywhere AND strictly greater somewhere.
        Missing peers are treated as having a counter of 0.
        """
        is_strictly_greater = False
        all_peers = set(self.clock.keys()).union(set(other.clock.keys()))
        
        for peer in all_peers:
            self_count = self.clock.get(peer, 0)
            other_count = other.clock.get(peer, 0)
            
            if self_count < other_count:
                return False
            if self_count > other_count:
                is_strictly_greater = True
                
        return is_strictly_greater

    def concurrent(self, other: 'VectorClock') -> bool:
        """Return True if neither dominates the other and they are not equal."""
        return not self.dominates(other) and not other.dominates(self) and self != other

    def to_dict(self) -> dict[str, int]:
        """Return a copy of the internal clock dictionary."""
        return dict(self.clock)

    @classmethod
    def from_dict(cls, d: dict[str, int]) -> 'VectorClock':
        """Create a VectorClock from a dictionary."""
        return cls(d)

    def prune(self, active_peers: set[str]) -> None:
        """Remove entries for peers NOT in active_peers to prevent unbounded growth."""
        peers_to_remove = [p for p in self.clock if p not in active_peers]
        for p in peers_to_remove:
            del self.clock[p]

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, VectorClock):
            return False
        # Treat missing as 0 for equality as well, though usually we don't store 0s
        all_peers = set(self.clock.keys()).union(set(other.clock.keys()))
        return all(self.clock.get(p, 0) == other.clock.get(p, 0) for p in all_peers)

    def __repr__(self) -> str:
        return f"VectorClock({self.clock})"


if __name__ == '__main__':
    # Unit Tests
    
    # 1. Test increment
    vc1 = VectorClock()
    vc1.increment('A')
    vc1.increment('A')
    assert vc1.to_dict() == {'A': 2}, "Increment test failed"
    
    # 2. Test merge
    vc2 = VectorClock({'A': 1, 'B': 3})
    vc3 = VectorClock({'A': 2, 'C': 1})
    merged = vc2.merge(vc3)
    assert merged.to_dict() == {'A': 2, 'B': 3, 'C': 1}, "Merge test failed"
    
    # 3. Test dominates
    vc4 = VectorClock({'A': 2, 'B': 1})
    vc5 = VectorClock({'A': 1, 'B': 1})
    assert vc4.dominates(vc5) is True, "Dominates test failed (strictly greater)"
    assert vc5.dominates(vc4) is False, "Dominates test failed (less than)"
    assert vc4.dominates(vc4) is False, "Dominates test failed (equal is not strictly greater)"
    
    # 4. Test concurrent
    vc6 = VectorClock({'A': 1, 'B': 2})
    vc7 = VectorClock({'A': 2, 'B': 1})
    assert vc6.concurrent(vc7) is True, "Concurrent test failed"
    assert vc6.concurrent(vc6) is False, "Concurrent test failed (equal is not concurrent)"
    
    # 5. Test prune
    vc8 = VectorClock({'A': 5, 'B': 2, 'C': 1})
    vc8.prune({'A', 'B'})
    assert vc8.to_dict() == {'A': 5, 'B': 2}, "Prune test failed"

    print("All VectorClock unit tests passed!")
