from typing import Any

def mark_row_status(store, table: str, pk: Any, status: str) -> None:
    row = store.tables.get(table, {}).get(pk)
    if row:
        # Direct mutation only — no upsert_row merge to avoid
        # non-determinism when the same row object is mutated multiple times.
        row.unique_status = status

class EscrowLog:
    def __init__(self):
        # dict[(table, tuple(cols), tuple(vals)) -> list of (peer_id, row_pk)]
        self.claims: dict[tuple[str, tuple[str, ...], tuple[Any, ...]], list[tuple[str, Any]]] = {}

    def claim(self, table: str, cols: tuple[str, ...], vals: tuple[Any, ...], peer_id: str, row_pk: Any) -> None:
        key = (table, cols, vals)
        if key not in self.claims:
            self.claims[key] = []
            
        claimant = (peer_id, row_pk)
        if claimant not in self.claims[key]:
            self.claims[key].append(claimant)

    def merge(self, other: 'EscrowLog') -> None:
        for key, other_claimants in other.claims.items():
            if key not in self.claims:
                self.claims[key] = list(other_claimants)
            else:
                for claimant in other_claimants:
                    if claimant not in self.claims[key]:
                        self.claims[key].append(claimant)

    def resolve_all(self, store) -> None:
        pending_updates: dict[tuple, str] = {}  # (table, pk) -> status

        for (table, cols, vals), claimants in self.claims.items():
            if not claimants:
                continue

            sorted_claimants = sorted(claimants, key=lambda c: (str(c[0]), str(c[1])))

            if len(sorted_claimants) == 1:
                peer_id, row_pk = sorted_claimants[0]
                key = (table, row_pk)
                if pending_updates.get(key) != "rejected":
                    pending_updates[key] = "committed"
            else:
                winner = min(sorted_claimants, key=lambda c: (str(c[0]), str(c[1])))
                winner_peer_id, winner_row_pk = winner

                for peer_id, row_pk in sorted_claimants:
                    key = (table, row_pk)
                    if peer_id == winner_peer_id and row_pk == winner_row_pk:
                        if pending_updates.get(key) != "rejected":
                            pending_updates[key] = "committed"
                    else:
                        pending_updates[key] = "rejected"

        for (table, pk), status in pending_updates.items():
            mark_row_status(store, table, pk, status)

        for table, rows in store.tables.items():
            schema_info = store.schema.get(table, {})
            has_unique_cols = bool(schema_info.get("unique_cols", [])) or bool(schema_info.get("composite_unique", []))
            
            if not has_unique_cols:
                for pk, row in rows.items():
                    if row.unique_status == "pending":
                        mark_row_status(store, table, pk, "committed")


if __name__ == '__main__':
    from engine.crdt_store import CRDTStore
    from engine.crdt_row import CRDTRow
    from engine.crdt_cell import CRDTCell
    from engine.vector_clock import VectorClock

    # Mock setup
    store = CRDTStore("peerA")
    store.register_schema("users", {"pk_col": "id", "unique_cols": ["email"]})
    
    # Setup test rows
    clock = VectorClock({"peerA": 1})
    
    # Row 1
    row1 = CRDTRow(cells={"id": CRDTCell("u1", clock), "email": CRDTCell("alice@example.com", clock)})
    store.upsert_row("users", "u1", row1)
    
    # Row 2 (Conflict on email)
    row2 = CRDTRow(cells={"id": CRDTCell("u2", clock), "email": CRDTCell("alice@example.com", clock)})
    store.upsert_row("users", "u2", row2)
    
    # 1. Single claimant gets committed
    store_single = CRDTStore("peerA")
    store_single.register_schema("users", {"pk_col": "id", "unique_cols": ["email"]})
    row_single = CRDTRow(cells={"id": CRDTCell("u1", clock), "email": CRDTCell("bob@example.com", clock)})
    store_single.upsert_row("users", "u1", row_single)
    
    escrow_single = EscrowLog()
    escrow_single.claim("users", "email", "bob@example.com", "peerA", "u1")
    escrow_single.resolve_all(store_single)
    
    assert store_single.tables["users"]["u1"].unique_status == "committed", "Single claimant test failed"
    
    # 2. Two claimants for same val -> smallest peer_id wins
    escrow_conflict = EscrowLog()
    # peerB claims first, but peerA has lexicographically smaller peer_id
    escrow_conflict.claim("users", "email", "alice@example.com", "peerB", "u2")
    escrow_conflict.claim("users", "email", "alice@example.com", "peerA", "u1")
    
    escrow_conflict.resolve_all(store)
    
    assert store.tables["users"]["u1"].unique_status == "committed", "Winner status test failed"
    assert store.tables["users"]["u2"].unique_status == "rejected", "Loser status test failed"
    
    print("All EscrowLog unit tests passed!")
