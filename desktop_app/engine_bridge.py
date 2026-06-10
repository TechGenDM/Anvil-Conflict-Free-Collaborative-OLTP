"""
Anvil CRDT Desktop App — Engine Bridge
Thin wrapper around the existing bench-p01-crdt engine.
Provides a clean, UI-friendly API without modifying any engine code.
"""

import sys
import os
import json
from datetime import datetime

# Add engine path so we can import it
_ENGINE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "Anvil-P-E", "bench-p01-crdt"
)
if _ENGINE_DIR not in sys.path:
    sys.path.insert(0, _ENGINE_DIR)

from engine.peer import Peer
from engine.sync import sync


class EngineBridge:
    """UI-friendly wrapper around the CRDT engine."""

    def __init__(self, fk_policy: str = "cascade"):
        self.fk_policy = fk_policy
        self.peers: dict[str, Peer] = {}
        self.event_log: list[dict] = []
        self.schema_stmts: list[str] = []

    def _log(self, action: str, detail: str, peer_id: str = None):
        """Add an event to the log."""
        entry = {
            "time": datetime.now().strftime("%H:%M:%S"),
            "action": action,
            "detail": detail,
            "peer_id": peer_id,
        }
        self.event_log.append(entry)
        return entry

    # ── Peer Management ────────────────────────────────────────

    def create_peer(self, peer_id: str) -> None:
        """Create a new peer with empty state."""
        if peer_id in self.peers:
            return
        self.peers[peer_id] = Peer(peer_id, fk_policy=self.fk_policy)
        self._log("CREATE_PEER", f"Peer {peer_id} created", peer_id)

        # Apply existing schema to new peer
        for stmt in self.schema_stmts:
            self.peers[peer_id].execute(stmt)

    def get_peer_ids(self) -> list[str]:
        """Get sorted list of all peer IDs."""
        return sorted(self.peers.keys())

    # ── SQL Execution ──────────────────────────────────────────

    def execute_sql(self, peer_id: str, sql: str, params: tuple = ()) -> dict:
        """Execute SQL on a specific peer. Returns result info."""
        if peer_id not in self.peers:
            raise ValueError(f"Unknown peer: {peer_id}")

        try:
            peer = self.peers[peer_id]
            peer.execute(sql, params)

            # Track schema for new peers
            sql_upper = sql.strip().upper()
            if sql_upper.startswith("CREATE TABLE") or sql_upper.startswith("CREATE INDEX"):
                if sql not in self.schema_stmts:
                    self.schema_stmts.append(sql)

            self._log("EXECUTE", f"{sql}", peer_id)
            return {
                "success": True,
                "peer_id": peer_id,
                "sql": sql,
                "state": self.get_peer_state(peer_id),
                "hash": self.get_peer_hash(peer_id),
            }
        except Exception as e:
            self._log("ERROR", f"Failed: {sql} — {e}", peer_id)
            return {"success": False, "error": str(e)}

    # ── Sync ───────────────────────────────────────────────────

    def sync_peers(self, peer_a_id: str, peer_b_id: str) -> dict:
        """Bidirectional sync between two peers."""
        if peer_a_id not in self.peers or peer_b_id not in self.peers:
            raise ValueError(f"Unknown peer(s): {peer_a_id}, {peer_b_id}")

        peer_a = self.peers[peer_a_id]
        peer_b = self.peers[peer_b_id]

        hash_a_before = peer_a.snapshot_hash()
        hash_b_before = peer_b.snapshot_hash()

        peer_a.sync_with(peer_b)

        hash_a_after = peer_a.snapshot_hash()
        hash_b_after = peer_b.snapshot_hash()

        match = hash_a_after == hash_b_after
        self._log(
            "SYNC",
            f"Sync {peer_a_id} ↔ {peer_b_id} — {'✅ MATCH' if match else '❌ MISMATCH'}",
        )

        return {
            "peer_a": peer_a_id,
            "peer_b": peer_b_id,
            "hash_match": match,
            "hash_a": hash_a_after,
            "hash_b": hash_b_after,
            "changed_a": hash_a_before != hash_a_after,
            "changed_b": hash_b_before != hash_b_after,
        }

    def sync_all(self) -> dict:
        """Sync all peers pairwise until convergence."""
        peer_ids = self.get_peer_ids()
        results = []

        # Do rounds of pairwise sync until all hashes match
        for _ in range(3):  # Max 3 rounds (sufficient for 3-level FK chains)
            for i in range(len(peer_ids)):
                for j in range(i + 1, len(peer_ids)):
                    result = self.sync_peers(peer_ids[i], peer_ids[j])
                    results.append(result)

            if self.are_all_synced():
                break

        return {
            "synced": self.are_all_synced(),
            "rounds": results,
            "hashes": self.get_all_hashes(),
        }

    # ── State Queries ──────────────────────────────────────────

    def get_peer_state(self, peer_id: str) -> dict:
        """Get a peer's visible snapshot state."""
        if peer_id not in self.peers:
            return {}
        return self.peers[peer_id].dump_tables()

    def get_peer_hash(self, peer_id: str) -> str:
        """Get a peer's state hash."""
        if peer_id not in self.peers:
            return ""
        return self.peers[peer_id].snapshot_hash()

    def get_all_hashes(self) -> dict[str, str]:
        """Get hashes for all peers."""
        return {pid: self.get_peer_hash(pid) for pid in self.get_peer_ids()}

    def are_all_synced(self) -> bool:
        """Check if all peers have identical state."""
        hashes = list(self.get_all_hashes().values())
        if len(hashes) <= 1:
            return True
        return all(h == hashes[0] for h in hashes)

    def get_peer_detail(self, peer_id: str) -> dict:
        """Get detailed peer info including internal CRDT state."""
        if peer_id not in self.peers:
            return {}

        peer = self.peers[peer_id]
        store = peer.store

        # Build detailed row info with status
        tables_detail = {}
        for table_name in sorted(store.tables.keys()):
            rows = store.tables[table_name]
            schema_info = store.schema.get(table_name, {})
            unique_cols = set(schema_info.get("unique_cols", []))
            fk_cols = list(schema_info.get("fk_cols", {}).keys())

            table_rows = []
            for pk in sorted(rows.keys(), key=str):
                row = rows[pk]
                row_data = {
                    "pk": pk,
                    "tombstone": row.tombstone,
                    "fk_status": row.fk_status,
                    "unique_status": row.unique_status,
                    "visible": row.is_visible(self.fk_policy),
                    "cells": {},
                }
                for col, cell in row.cells.items():
                    row_data["cells"][col] = {
                        "value": cell.winner_value(),
                        "clock": cell.clock.to_dict(),
                        "conflicts": len(cell.conflicts),
                        "all_values": cell.all_values() if cell.conflicts else None,
                    }
                table_rows.append(row_data)
            tables_detail[table_name] = {
                "schema": schema_info,
                "rows": table_rows,
            }

        return {
            "peer_id": peer_id,
            "hash": self.get_peer_hash(peer_id),
            "known_peers": sorted(store.known_peers),
            "clock": store.current_clock.to_dict(),
            "tables": tables_detail,
        }

    # ── Preset Scenarios ───────────────────────────────────────

    def get_preset_scenarios(self) -> dict[str, list[dict]]:
        """Return preset scenarios as step lists."""
        return {
            "Reference Scenario": self._reference_scenario(),
            "Cell-Level Conflict": self._cell_level_scenario(),
            "Uniqueness Conflict": self._uniqueness_scenario(),
            "FK Cascade": self._fk_cascade_scenario(),
        }

    def _reference_scenario(self) -> list[dict]:
        """The classic 3-peer reference scenario from the problem statement."""
        return [
            {"type": "schema", "sql": "CREATE TABLE orgs (id VARCHAR PRIMARY KEY, name VARCHAR)"},
            {"type": "schema", "sql": "CREATE TABLE users (id VARCHAR PRIMARY KEY, email VARCHAR UNIQUE, name VARCHAR, org_id VARCHAR REFERENCES orgs)"},
            {"type": "schema", "sql": "CREATE TABLE orders (id VARCHAR PRIMARY KEY, user_id VARCHAR REFERENCES users, status VARCHAR, total_cents VARCHAR)"},
            {"type": "schema", "sql": "CREATE INDEX idx_email ON users (email)"},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO orgs (id, name) VALUES (?, ?)", "params": ("org1", "Acme Corp")},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO users (id, email, name, org_id) VALUES (?, ?, ?, ?)", "params": ("u1", "alice@x.com", "Alice", "org1")},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO users (id, email, name, org_id) VALUES (?, ?, ?, ?)", "params": ("u2", "bob@x.com", "Bob", "org1")},
            {"type": "execute", "peer": "B", "sql": "INSERT INTO users (id, email, name, org_id) VALUES (?, ?, ?, ?)", "params": ("u3", "alice@x.com", "Alice'", "org1"), "note": "⚠️ Uniqueness conflict on email!"},
            {"type": "sync", "peers": ["A", "C"], "note": "C gets u1, u2 from A"},
            {"type": "execute", "peer": "C", "sql": "DELETE FROM users WHERE id = ?", "params": ("u1",), "note": "🗑️ Parent delete under partition"},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO orders (id, user_id, status, total_cents) VALUES (?, ?, ?, ?)", "params": ("o1", "u1", "pending", "1200"), "note": "📦 Child insert vs deleted parent"},
            {"type": "execute", "peer": "A", "sql": "UPDATE users SET name = ? WHERE id = ?", "params": ("Alice Cooper", "u1")},
            {"type": "execute", "peer": "B", "sql": "UPDATE users SET email = ? WHERE id = ?", "params": ("alice@ex.org", "u1"), "note": "🔀 Cell-level conflict with A's name update"},
            {"type": "sync_all", "note": "🔄 Full pairwise sync → all peers converge"},
        ]

    def _cell_level_scenario(self) -> list[dict]:
        """Demonstrates cell-level (not row-level) conflict resolution."""
        return [
            {"type": "schema", "sql": "CREATE TABLE users (id VARCHAR PRIMARY KEY, email VARCHAR UNIQUE, name VARCHAR)"},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO users (id, email, name) VALUES (?, ?, ?)", "params": ("u1", "alice@x.com", "Alice")},
            {"type": "sync", "peers": ["A", "B"], "note": "B gets u1 from A"},
            {"type": "execute", "peer": "A", "sql": "UPDATE users SET name = ? WHERE id = ?", "params": ("Alice Cooper", "u1"), "note": "A updates NAME column"},
            {"type": "execute", "peer": "B", "sql": "UPDATE users SET email = ? WHERE id = ?", "params": ("alice@new.com", "u1"), "note": "B updates EMAIL column (different column!)"},
            {"type": "sync", "peers": ["A", "B"], "note": "🔀 Both updates survive — cell-level merge!"},
        ]

    def _uniqueness_scenario(self) -> list[dict]:
        """Shows the Escrow-First uniqueness protocol."""
        return [
            {"type": "schema", "sql": "CREATE TABLE users (id VARCHAR PRIMARY KEY, email VARCHAR UNIQUE, name VARCHAR)"},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO users (id, email, name) VALUES (?, ?, ?)", "params": ("u1", "alice@x.com", "Alice from A"), "note": "A claims alice@x.com"},
            {"type": "execute", "peer": "B", "sql": "INSERT INTO users (id, email, name) VALUES (?, ?, ?)", "params": ("u2", "alice@x.com", "Alice from B"), "note": "B also claims alice@x.com!"},
            {"type": "sync", "peers": ["A", "B"], "note": "⚖️ Escrow resolves: min(peer_id, row_pk) wins"},
        ]

    def _fk_cascade_scenario(self) -> list[dict]:
        """Shows foreign key cascade under partition."""
        return [
            {"type": "schema", "sql": "CREATE TABLE orgs (id VARCHAR PRIMARY KEY, name VARCHAR)"},
            {"type": "schema", "sql": "CREATE TABLE users (id VARCHAR PRIMARY KEY, name VARCHAR, org_id VARCHAR REFERENCES orgs)"},
            {"type": "schema", "sql": "CREATE TABLE orders (id VARCHAR PRIMARY KEY, user_id VARCHAR REFERENCES users, item VARCHAR)"},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO orgs (id, name) VALUES (?, ?)", "params": ("org1", "Acme Corp")},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO users (id, name, org_id) VALUES (?, ?, ?)", "params": ("u1", "Alice", "org1")},
            {"type": "execute", "peer": "A", "sql": "INSERT INTO orders (id, user_id, item) VALUES (?, ?, ?)", "params": ("o1", "u1", "Widget")},
            {"type": "sync", "peers": ["A", "B"], "note": "B gets everything from A"},
            {"type": "execute", "peer": "B", "sql": "DELETE FROM orgs WHERE id = ?", "params": ("org1",), "note": "🗑️ B deletes the root org!"},
            {"type": "sync", "peers": ["A", "B"], "note": "⛓️ Cascade: org1 deleted → u1 orphaned → o1 orphaned"},
        ]

    # ── Benchmark Report ───────────────────────────────────────

    @staticmethod
    def load_benchmark_report(path: str) -> dict | None:
        """Load and parse a benchmark report JSON file."""
        try:
            with open(path, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return None

    @staticmethod
    def find_benchmark_reports() -> list[str]:
        """Find all benchmark report JSON files in the bench directory."""
        bench_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "Anvil-P-E", "bench-p01-crdt"
        )
        reports = []
        for f in os.listdir(bench_dir):
            if f.endswith(".json") and ("report" in f or "l3" in f.lower()):
                reports.append(os.path.join(bench_dir, f))
        return sorted(reports)

    # ── Reset ──────────────────────────────────────────────────

    def reset(self):
        """Reset all state."""
        self.peers.clear()
        self.event_log.clear()
        self.schema_stmts.clear()


if __name__ == "__main__":
    # Self-test
    bridge = EngineBridge(fk_policy="cascade")
    bridge.create_peer("A")
    bridge.create_peer("B")

    bridge.execute_sql("A", "CREATE TABLE users (id VARCHAR PRIMARY KEY, email VARCHAR UNIQUE, name VARCHAR)")
    bridge.execute_sql("A", "INSERT INTO users (id, email, name) VALUES (?, ?, ?)", ("u1", "alice@x.com", "Alice"))

    bridge.sync_peers("A", "B")
    assert bridge.are_all_synced(), "Peers should be synced"
    assert bridge.get_peer_hash("A") == bridge.get_peer_hash("B"), "Hashes should match"

    print("✅ EngineBridge self-test passed!")
