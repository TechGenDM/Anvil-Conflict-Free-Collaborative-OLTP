from typing import Any
import hashlib
import json
from engine.vector_clock import VectorClock
from engine.crdt_row import CRDTRow

class CRDTStore:
    def __init__(self, peer_id: str):
        self.peer_id = peer_id
        self.tables: dict[str, dict[Any, CRDTRow]] = {}
        self.current_clock = VectorClock()
        self.schema: dict[str, dict] = {}
        self.known_peers: set[str] = {peer_id}
        self.escrow = None

    def tick(self) -> None:
        self.current_clock.increment(self.peer_id)

    def register_schema(self, table: str, schema_dict: dict) -> None:
        self.schema[table] = schema_dict
        if table not in self.tables:
            self.tables[table] = {}

    def upsert_row(self, table: str, pk: Any, row: CRDTRow) -> None:
        if table not in self.tables:
            self.tables[table] = {}
            
        if pk in self.tables[table]:
            # Merge existing with incoming, store result
            merged = self.tables[table][pk].merge(row)
            self.tables[table][pk] = merged
        else:
            # Store directly
            self.tables[table][pk] = row

    def tombstone_row(self, table: str, pk: Any) -> None:
        if table not in self.tables:
            self.tables[table] = {}
            
        if pk in self.tables[table]:
            # Fetch existing row and update tombstone
            row = self.tables[table][pk]
            row.tombstone = True
            row.tombstone_clock = VectorClock(self.current_clock.to_dict())
        else:
            # Create new row
            row = CRDTRow(
                cells={},
                tombstone=True,
                tombstone_clock=VectorClock(self.current_clock.to_dict())
            )
            self.tables[table][pk] = row

    def merge_row(self, table: str, pk: Any, incoming_row: CRDTRow) -> None:
        # Same as upsert_row but called during sync
        self.upsert_row(table, pk, incoming_row)

    def snapshot_state(self) -> dict:
        state = {}
        # Sort table names for determinism
        for table in sorted(self.tables.keys()):
            table_rows = self.tables[table]
            # Sort by pk (converted to string) for determinism
            sorted_pks = sorted(table_rows.keys(), key=lambda k: str(k))
            
            table_state = []
            for pk in sorted_pks:
                row = table_rows[pk]
                if row.is_visible():
                    # Sort columns within each row for determinism
                    row_dict = row.snapshot()
                    table_state.append(dict(sorted(row_dict.items())))
                    
            state[table] = table_state
        return state

    def snapshot_hash(self) -> str:
        state_dict = self.snapshot_state()
        state_json = json.dumps(state_dict, sort_keys=True, default=str)
        return hashlib.sha256(state_json.encode('utf-8')).hexdigest()

    def get_all_rows(self, table: str) -> dict:
        # Return all rows including tombstoned (for sync)
        return dict(self.tables.get(table, {}))

    def all_tables(self) -> list[str]:
        return list(self.tables.keys())
