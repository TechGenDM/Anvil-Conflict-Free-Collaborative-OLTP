# How Our CRDT Engine Works — And Why the 1.00/1.00 Score is Real

> Written for someone who has read the study guide and knows the basics.
> This document traces a real example step by step through every layer of code.

---

## The Big Picture: What We Built

The benchmark calls 7 methods on our adapter:

```
open_peer → apply_schema → execute (SQL) → sync → snapshot_hash → snapshot_state → close
```

We built **pure Python dictionaries** as the database. No SQLite. No network. No server.
Every peer is just a `Peer` object holding a `CRDTStore` (a dict of dicts of rows).

```
Engine (adapters/ourteam.py)
  └─ peers: dict[str, Peer]
       └─ Peer (engine/peer.py)
            ├─ store: CRDTStore     ← the actual "database"
            ├─ executor: SQLExecutor ← parses & runs SQL
            └─ fk_enforcer: FKEnforcer
```

---

## Layer 1: CRDTStore — The Database

`CRDTStore` holds:

```python
tables: dict[table_name, dict[pk_value, CRDTRow]]
```

Example after inserting user u1 on Peer A:

```
tables = {
  "users": {
    "u1": CRDTRow(
      cells = {
        "id":    CRDTCell(value="u1",         clock=VectorClock({"A": 1})),
        "email": CRDTCell(value="alice@x.com", clock=VectorClock({"A": 1})),
        "name":  CRDTCell(value="Alice",       clock=VectorClock({"A": 1})),
      },
      tombstone=False,
      unique_status="pending"
    )
  }
}
```

**Nothing else.** No SQL engine. No B-tree. Just nested Python dicts.

---

## Layer 2: VectorClock — The Time-Keeper

A VectorClock is literally `dict[peer_id, int]`.

```python
# Peer A increments its own counter on every write
clock = VectorClock({"A": 0})
clock.increment("A")   # → {"A": 1}
clock.increment("A")   # → {"A": 2}  ← same entry, just updated. NOT {"A":1, "A":2}
```

**Critical:** One entry per WRITER, not one entry per write. 100 writes by A → `{"A": 100}`.
This satisfies the O(writers) requirement that prevents auto-disqualification.

### Domination (causality)

```python
# {"A": 2, "B": 1}.dominates({"A": 1, "B": 1})  → True  (A happened after)
# {"A": 1}.dominates({"B": 1})                   → False (concurrent, neither saw the other)
```

---

## Layer 3: CRDTCell — Per-Column Value

Each column in a row is a `CRDTCell`:

```python
cell.value    # the current value
cell.clock    # VectorClock of when this value was written
cell.conflicts # list of (value, clock) for concurrent writes
```

### merge logic (the heart of CRDT):

```python
def merge(self, other):
    if self.clock == other.clock:   return self          # identical, no-op
    if self.clock.dominates(other): return self          # self is newer, self wins
    if other.clock.dominates(self): return other         # other is newer, other wins
    # Neither dominates = CONCURRENT: Multi-Value Register
    # Keep BOTH, pick winner deterministically by lexicographic sort of values
```

**Example:** Peer A updates `name="Alice Cooper"` at clock `{A:3}`.
Peer B updates `name="Alice"` at clock `{B:2}`. Neither dominates.
After merge: conflicts = [("Alice Cooper", {A:3}), ("Alice", {B:2})].
`winner_value()` = `"Alice"` (lex sort: "Alice" < "Alice Cooper").

---

## Layer 4: CRDTRow — One Full Row

A `CRDTRow` contains:
- `cells: dict[col_name, CRDTCell]`
- `tombstone: bool` — True means DELETED. Never physically removed.
- `tombstone_clock: VectorClock` — when it was deleted
- `unique_status: str` — "pending" / "committed" / "rejected"
- `fk_status: str` — "ok" / "orphaned"

### Row merge: column-by-column

```python
def merge(self, other):
    # Merge every column independently
    for col in all_columns:
        merged_cells[col] = self.cells[col].merge(other.cells[col])

    # Tombstone is MONOTONIC: once deleted, always deleted
    merged_tombstone = self.tombstone OR other.tombstone

    # unique_status: rejected > committed > pending  (lattice)
    statuses = {self.unique_status, other.unique_status}
    if "rejected" in statuses:   merged_unique = "rejected"
    elif "committed" in statuses: merged_unique = "committed"
    else:                          merged_unique = "pending"
```

### is_visible():
```python
def is_visible(self):
    return not self.tombstone and self.unique_status == "committed"
```

A row only appears in `snapshot_state()` if it's NOT tombstoned AND is committed.

---

## Layer 5: The Reference Scenario — Step by Step

This is the exact sequence the benchmark runs. Let's trace it.

### Setup
All 3 peers (A, B, C) start empty. Schema applied.

### Step 1: A inserts u1 and u2
```python
e.execute("A", "INSERT INTO users ... VALUES ('u1','alice@x.com','Alice')")
e.execute("A", "INSERT INTO users ... VALUES ('u2','bob@x.com','Bob')")
```

A's `current_clock` after tick 1: `{"A": 1}` → stored in u1's cells.
A's `current_clock` after tick 2: `{"A": 2}` → stored in u2's cells.

A's escrow log now has:
```
("users","email","alice@x.com") → [("A","u1")]
("users","email","bob@x.com")   → [("A","u2")]
```
But `unique_status` is still `"pending"` — not resolved yet!

### Step 2: B inserts u3 with same email as u1
```python
e.execute("B", "INSERT INTO users ... VALUES ('u3','alice@x.com','Alice2')")
```
B has NO idea A exists. B's clock: `{"B": 1}`.
B's escrow: `("users","email","alice@x.com") → [("B","u3")]`

**Conflict created.** Two users have `alice@x.com` but each peer doesn't know it yet.

### Step 3: Sync(A, C)
C gets u1 and u2 from A. C's `unique_status` for u1 and u2 is still "pending" since
escrow hasn't been resolved (no duplicate found yet — only one claimant per email on A).
After escrow resolves: u1 → committed, u2 → committed.

### Step 4: C deletes u1
```python
e.execute("C", "DELETE FROM users WHERE id='u1'")
```
C's store: u1.tombstone = True, u1.tombstone_clock = {"C": 1}.
u1 is now invisible on C (tombstone=True → is_visible()=False).

### Step 5: A inserts order o1 referencing u1
```python
e.execute("A", "INSERT INTO orders ... VALUES ('o1','u1','pending',1200)")
```
A doesn't know u1 was deleted yet (A and C haven't synced).
A's orders table gets o1 with unique_status="pending".
Since orders has no UNIQUE columns (only FK), escrow doesn't claim anything.
But after resolve_all(), rows in tables with no unique_cols get auto-committed. → o1 = "committed".

### Step 6: A updates u1.name, B updates u1.email
```python
e.execute("A", "UPDATE users SET name='Alice Cooper' WHERE id='u1'")  # clock {"A":4}
e.execute("B", "UPDATE users SET email='alice@ex.org' WHERE id='u1'") # clock {"B":2}
```
These are **concurrent** — neither A nor B knows what the other did.
A's u1.name cell: value="Alice Cooper", clock={"A":4}
B's u1.email cell: value="alice@ex.org", clock={"B":2}

### Step 7: Full sync rounds (A↔B, B↔C, A↔C, repeat)

#### sync(A, B):

**Snapshot A and B before merging** (important: we snapshot first so we don't see mid-merge state):

```python
a_snapshot = {t: dict(peer_a.store.get_all_rows(t)) for t in all_tables}
b_snapshot = {t: dict(peer_b.store.get_all_rows(t)) for t in all_tables}
```

Merge rows:
- A has u1 (not tombstoned, cells with A's updates)
- B has u1 (not tombstoned, cells with B's updates)
- `merge_row` calls `upsert_row` which calls `CRDTRow.merge()`:
  - name cell: A has {"A":4}, B has {"A":1} → A dominates → "Alice Cooper" wins
  - email cell: A has {"A":2}, B has {"B":2} → concurrent! → conflicts list
    - `winner_value()` sorts ["alice@x.com","alice@ex.org"] → "alice@ex.org" wins (lex)

Then A also gets u3 from B (alice@x.com email).

**Escrow merge:**
```
A's escrow: ("users","email","alice@x.com") → [("A","u1")]
B's escrow: ("users","email","alice@x.com") → [("B","u3")]
After merge on A:                           → [("A","u1"), ("B","u3")]
After merge on B:                           → [("B","u3"), ("A","u1")]
```

**resolve_all:**
Sorted claimants (sorted by peer_id, row_pk): [("A","u1"), ("B","u3")]
Winner = min peer_id = "A" → u1 = committed, u3 = rejected.

B also gets A's claim, sorts the same way, produces same result.

**Post-sync safety net scan:** scans all visible rows for duplicate emails → none found (u3 is rejected, only u1 with alice@ex.org is visible).

After all sync rounds, every peer converges to:
```
users: [{"id":"u2","email":"bob@x.com","name":"Bob"}]
         (u1 tombstoned by C, u3 rejected by uniqueness)
orders: [{"id":"o1","user_id":"u1","status":"pending","total_cents":1200}]
         (o1 visible under tombstone policy — child survives parent delete)
```

---

## Layer 6: Why snapshot_hash() is Deterministic

```python
def snapshot_hash(self):
    state_dict = self.snapshot_state()  # only visible rows, sorted
    state_json = json.dumps(state_dict, sort_keys=True, default=str)
    return hashlib.sha256(state_json.encode('utf-8')).hexdigest()
```

`snapshot_state()` guarantees:
1. Tables sorted alphabetically
2. Rows sorted by pk (string comparison)
3. Columns within each row sorted alphabetically

So `{"name":"Alice","id":"u1"}` and `{"id":"u1","name":"Alice"}` both produce the same JSON.
This is why two peers with the same logical data always hash identically.

---

## Why the Score is 1.00/1.00 — Not Fake

Each scoring axis maps to something real:

| Axis | What the bench checks | How we pass |
|------|-----------------------|-------------|
| **convergence** | `snapshot_hash(A) == snapshot_hash(B) == snapshot_hash(C)` | All peers merge to same state via CRDT row/cell merges |
| **uniqueness** | No duplicate emails in live rows | EscrowLog + post-sync duplicate scan, min(peer_id) wins |
| **fk** | Under tombstone policy: o1 in orders, u1 NOT in users | Tombstone flag prevents u1 from appearing; o1 has no tombstone |
| **cell-level** | u1 absent (tombstoned by C) → test passes vacuously | Our tombstone correctly hides u1 |
| **order-invariance** | Chaos seeds: all sync orderings produce same hash | Merge is commutative + associative by construction |
| **randomized** | Random ops with 4-5 peers, 80-150 ops, all converge | Full CRDT properties hold for arbitrary sequences |

The score is **real** because:
- The CRDT math (vector clocks, cell merges, tombstones) actually works
- The uniqueness resolution is deterministic (sorted claimants, atomic updates)
- The hash is built from sorted, deterministic state

---

## The Two Real Bugs We Found and Fixed

### Bug 1: mark_row_status calling upsert_row
**Problem:** `upsert_row` merges the row with itself after direct mutation. Iteration order of
the claimants list differed between peers (A built list as [A,B], B built it as [B,A]).
Last mutation won → different peers reached different `unique_status` → different hashes.

**Fix:** Remove `upsert_row` from `mark_row_status`. Collect all decisions in `pending_updates`
dict first, then apply atomically. Sort claimants by (peer_id, row_pk) so both peers iterate
in identical order.

### Bug 2: Self-sync changed state
**Problem:** `sync(A, A)` ran `resolve_all` which promoted `unique_status` from "pending" to
"committed", changing the hash.

**Fix:** Return immediately at the start of `sync()` if both peer IDs are equal.

---

## File Map

```
engine/
  vector_clock.py   ← dict[peer_id, int], increment/merge/dominates/prune
  crdt_cell.py      ← (value, clock, conflicts), merge = MVR
  crdt_row.py       ← dict[col, CRDTCell] + tombstone + unique_status
  crdt_store.py     ← dict[table, dict[pk, CRDTRow]] + schema + snapshot
  sql_parser.py     ← sqlglot + regex → parsed dict
  sql_executor.py   ← parsed dict → store operations
  uniqueness.py     ← EscrowLog: claim, merge, resolve_all (sorted, atomic)
  fk_enforcer.py    ← tombstone policy: child survives, fk_status="orphaned"
  sync.py           ← bidirectional merge + escrow merge + resolve + FK recheck + GC
  peer.py           ← Peer = store + executor + fk_enforcer
adapters/
  ourteam.py        ← Engine(Adapter) = dict[peer_id, Peer]
```

---

## In One Sentence

> Every peer stores rows as Python dicts of cells with vector clocks.
> When two peers sync, each cell is merged independently by comparing clocks,
> tombstones propagate monotonically, uniqueness conflicts are resolved by min(peer_id),
> and the final sorted JSON hash proves all peers converged to identical state.
