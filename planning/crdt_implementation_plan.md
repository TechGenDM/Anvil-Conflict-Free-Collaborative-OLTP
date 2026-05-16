# CRDT OLTP Implementation Plan

This is a structured implementation plan divided into phases. Each phase represents a logical chunk of work that can be implemented and validated before moving on to the next.

## Phase 0: Setup and Baseline
* **File:** Terminal
* **Goal:** Repo clone + dummy test
* **Instructions:**
  ```bash
  git clone https://github.com/Sauhard74/Anvil-P-E
  cd Anvil-P-E/bench-p01-crdt
  pip install sqlglot
  python self_check.py --adapter adapters.dummy:DummyAdapter --fk-policy tombstone
  ```
  Note the failures — these are what we aim to fix.

---

## Phase 1: Foundational Data Structures
We begin by defining the core data types and low-level CRDT components.

### Step 1: Shared Dataclasses (`engine/interfaces.py`)
* **Goal:** Define `VectorClockData`, `CRDTCellData`, `CRDTRowData`, and `EscrowClaim`.
* **Important:** No logic here, only structure.
* **Prompt/Task:** Write Python dataclasses with type hints.

### Step 2: VectorClock (`engine/vector_clock.py`)
* **Goal:** Implement the heart of the CRDT — `VectorClock`.
* **Important:** Clock grows per WRITER, not per write. Unbounded growth is auto-disqualify.
* **Methods:** `increment`, `merge`, `dominates`, `concurrent`, `to_dict`, `from_dict`, `prune`.
* **Testing:** 5 unit tests at the bottom.

### Step 3: CRDTCell (`engine/crdt_cell.py`)
* **Goal:** Represent one column's value (Multi-Value Register).
* **Methods:** `merge`, `winner_value` (deterministic sorting), `all_values`.
* **Testing:** 4 unit tests (self-wins, other-wins, concurrent merge, determinism).

### Step 4: CRDTRow (`engine/crdt_row.py`)
* **Goal:** Represent a full row combining cells, tombstone flags, and statuses.
* **Important:** Tombstone is monotonic (once tombstoned, always tombstoned).
* **Methods:** `merge`, `is_visible`, `snapshot`.
* **Testing:** 3 unit tests.

> **Phase 1 Checkpoint:** Review the structures and unit tests. Ensure no logic leaks between layers and vector clocks are behaving correctly.

---

## Phase 2: State Management and Parsing
Handling the storage of rows and parsing incoming commands.

### Step 5: CRDTStore (`engine/crdt_store.py`)
* **Goal:** The in-memory database for one peer.
* **Methods:** `tick`, `register_schema`, `upsert_row`, `tombstone_row`, `merge_row`, `snapshot_state`, `snapshot_hash`, `get_all_rows`.

### Step 6: SQL Parser (`engine/sql_parser.py`)
* **Goal:** Convert SQL strings into structured dicts using `sqlglot`.
* **Important:** Only handle `CREATE TABLE`, `CREATE INDEX`, `INSERT`, `UPDATE`, `DELETE`. Ensure `?` placeholder substitution.

> **Phase 2 Checkpoint:** You should be able to create a store, parse some basic SQL queries into dicts, and manually call upsert/tombstone methods on the store.

---

## Phase 3: Execution and Policies
Executing the parsed commands and enforcing database constraints.

### Step 7: SQL Executor (`engine/sql_executor.py`)
* **Goal:** Map Parser output to Store actions.
* **Important:** `UPDATE` must ONLY touch named cells (do not replace the whole row).
* **Methods:** `execute` handling each operation.

### Step 8: EscrowLog (`engine/uniqueness.py`)
* **Goal:** Implement uniqueness constraints via the escrow/reservation protocol.
* **Important:** Smallest `peer_id` wins concurrent claims. Losers are invisible, not rejected.
* **Testing:** 2 unit tests for single claimant and conflict resolution.

### Step 9: FK Enforcer (`engine/fk_enforcer.py`)
* **Goal:** Implement the Tombstone policy for Foreign Keys.
* **Important:** Child survives when parent is deleted (`fk_status = "orphaned"`). Orphaned rows ARE visible in the snapshot.

> **Phase 3 Checkpoint:** At this point, a single peer can process SQL statements, manage state, enforce uniqueness (locally), and handle FK cascades.

---

## Phase 4: Network and Synchronization
Bringing peers together to achieve eventual consistency.

### Step 10: Sync (`engine/sync.py`)
* **Goal:** Bidirectional, idempotent synchronization between two peers.
* **Important:** Must snapshot before merging, resolve escrow, recheck FKs, and explicitly prune vector clocks (GC).
* **Testing:** 1 test ensuring bidirectional convergence.

### Step 11: Peer (`engine/peer.py`)
* **Goal:** A thin wrapper integrating Store, Executor, Sync, FKEnforcer, and EscrowLog.
* **Methods:** `execute`, `sync_with`, `snapshot_hash`, `dump_tables`, `shutdown`.

### Step 12: Adapter (`adapters/ourteam.py`)
* **Goal:** The benchmark interface (`Engine` class).
* **Important:** Keep it exactly to the benchmark's API, no extra logic here.

> **Phase 4 Checkpoint:** The entire engine is wired up. Peers can sync with each other and output deterministic snapshots.

---

## Phase 5: Benchmark and Validation
The final testing phase.

### Step 13: Test Execution
* **Goal:** Run the benchmark suite to validate the implementation.
* **Commands:**
  ```bash
  # Quick check
  python self_check.py --adapter adapters.ourteam:Engine --fk-policy tombstone --quick

  # Full check
  python self_check.py --adapter adapters.ourteam:Engine --fk-policy tombstone

  # Randomized seeds check
  python run.py --adapter adapters.ourteam:Engine --fk-policy tombstone --randomized-seeds 9999 31415 27182
  ```
* **Troubleshooting:**
  * Hash mismatch: check `sort_keys=True` in JSON dump.
  * U3 visible: check escrow `resolve_all`.
  * O1 not visible: check FK enforcer tombstone policy.
  * Convergence fails: check `snapshot-before-merge` pattern in sync.
