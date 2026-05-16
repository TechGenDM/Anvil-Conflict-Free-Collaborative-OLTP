from engine.uniqueness import EscrowLog, mark_row_status
from engine.fk_enforcer import FKEnforcer

def sync(peer_a, peer_b) -> None:
    # Guard: self-sync is a no-op
    if peer_a.store.peer_id == peer_b.store.peer_id:
        return

    # 1. Merge known_peers
    combined = peer_a.store.known_peers | peer_b.store.known_peers | {peer_a.store.peer_id, peer_b.store.peer_id}
    peer_a.store.known_peers = combined.copy()
    peer_b.store.known_peers = combined.copy()

    # 2. Exchange ALL rows bidirectionally
    all_tables = set(peer_a.store.all_tables()) | set(peer_b.store.all_tables())
    
    # Snapshot before merging to avoid seeing merged state mid-sync
    a_snapshot = {t: dict(peer_a.store.get_all_rows(t)) for t in all_tables}
    b_snapshot = {t: dict(peer_b.store.get_all_rows(t)) for t in all_tables}
    
    for table in all_tables:
        for pk, row in a_snapshot.get(table, {}).items():
            peer_b.store.merge_row(table, pk, row)
            
        for pk, row in b_snapshot.get(table, {}).items():
            peer_a.store.merge_row(table, pk, row)

    # 3. Merge escrow logs (bidirectional, idempotent union)
    if peer_a.store.escrow is not None and peer_b.store.escrow is not None:
        peer_a.store.escrow.merge(peer_b.store.escrow)
        peer_b.store.escrow.merge(peer_a.store.escrow)

    # 4. Resolve uniqueness on both
    if peer_a.store.escrow:
        peer_a.store.escrow.resolve_all(peer_a.store)
    if peer_b.store.escrow:
        peer_b.store.escrow.resolve_all(peer_b.store)

    # 4b. Safety-net: full post-sync duplicate scan for unique columns.
    # Catches UPDATE-driven collisions the escrow log may miss.
    for store in (peer_a.store, peer_b.store):
        _resolve_unique_duplicates(store)

    # 5. Recheck FK on both
    fk = FKEnforcer()
    fk.recheck_all(peer_a.store)
    fk.recheck_all(peer_b.store)

    # 6. GC — prune vector clocks
    active_peers = peer_a.store.known_peers
    for store in (peer_a.store, peer_b.store):
        for table, rows in store.tables.items():
            for row in rows.values():
                for cell in row.cells.values():
                    cell.clock.prune(active_peers)
                if row.tombstone_clock:
                    row.tombstone_clock.prune(active_peers)


def _resolve_unique_duplicates(store) -> None:
    """Post-sync full-table scan: for each unique column, detect duplicate
    values among visible rows and mark the loser(s) as 'rejected'.
    Winner selection: min(row_pk) lexicographically — deterministic."""
    for table, schema_info in store.schema.items():
        unique_cols = schema_info.get("unique_cols", [])
        if not unique_cols:
            continue
        rows = store.tables.get(table, {})
        for unique_col in unique_cols:
            # Build val -> [pk] map for visible rows only
            val_to_pks: dict = {}
            for pk, row in rows.items():
                if row.tombstone or row.unique_status == "rejected":
                    continue
                if unique_col not in row.cells:
                    continue
                val = row.cells[unique_col].winner_value()
                if val is None:
                    continue
                val_to_pks.setdefault(val, []).append(pk)

            for val, pks in val_to_pks.items():
                if len(pks) <= 1:
                    continue
                # Multiple rows claim same unique value — pick winner
                winner_pk = min(pks, key=lambda pk: str(pk))
                for pk in pks:
                    status = "committed" if pk == winner_pk else "rejected"
                    mark_row_status(store, table, pk, status)


if __name__ == '__main__':
    from engine.crdt_store import CRDTStore
    from engine.crdt_row import CRDTRow
    from engine.crdt_cell import CRDTCell
    from engine.vector_clock import VectorClock

    class DummyPeer:
        def __init__(self, peer_id):
            self.store = CRDTStore(peer_id)
            self.store.escrow = EscrowLog()
            
    peer_a = DummyPeer("A")
    peer_b = DummyPeer("B")
    
    # A writes row
    clock_a = VectorClock({"A": 1})
    row_a = CRDTRow(cells={"id": CRDTCell("u1", clock_a), "name": CRDTCell("Alice", clock_a)})
    peer_a.store.upsert_row("users", "u1", row_a)
    
    # B writes different row
    clock_b = VectorClock({"B": 1})
    row_b = CRDTRow(cells={"id": CRDTCell("u2", clock_b), "name": CRDTCell("Bob", clock_b)})
    peer_b.store.upsert_row("users", "u2", row_b)
    
    # Sync
    sync(peer_a, peer_b)
    
    # Both should have both rows
    assert "u1" in peer_a.store.tables["users"]
    assert "u2" in peer_a.store.tables["users"]
    assert "u1" in peer_b.store.tables["users"]
    assert "u2" in peer_b.store.tables["users"]
    
    # Hashes should match
    assert peer_a.store.snapshot_hash() == peer_b.store.snapshot_hash()
    
    print("All sync unit tests passed!")
