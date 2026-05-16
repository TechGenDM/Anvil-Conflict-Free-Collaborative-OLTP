=# Final Implementation Plan — CRDT OLTP Engine

## Current Status: ✅ ALL TESTS PASSING (1.00 / 1.00)

```
  AXIS                          PASS    WEIGHT
  --------------------------------------------------
  convergence                     PASS    0.30
  uniqueness:users.email          PASS    0.20
  fk                              PASS    0.15
  cell-level:u1                   PASS    0.10
  order-invariance                PASS    0.10
  randomized                      PASS    0.15
  --------------------------------------------------
  WEIGHTED SCORE                1.00  / 1.00
```

All quick, full, and randomized seed tests pass including idempotent-sync checks.

---

## Part A: Gap Analysis (Guide vs Our Implementation)

### 1. ✅ OR-Set — No Issue
Guide says OR-Set is overcomplicated. We correctly used simple `tombstone: bool` flags on `CRDTRow`. No action needed.

### 2. ⚠️ Cell-Level Merge (MVR vs LWW)
- **Our approach:** Multi-Value Register with `conflicts` list + `winner_value()` picks lexicographically smallest.
- **Guide suggests:** Simple LWW per cell is sufficient.
- **Verdict:** Our MVR approach works and passes all tests. However, the `conflicts` list could theoretically grow across repeated concurrent merges. We already mitigated the worst case (same-clock infinite loop) with our `self.clock == other.clock` early-return. **Low risk — monitor but no change required.**

### 3. ⚠️ Uniqueness — Escrow vs Post-Sync Scan
- **Our approach:** `EscrowLog` with `claim()`, `merge()`, `resolve_all()`. Claims are only made on INSERT.
- **Guide says:** Just do a post-sync scan for duplicate emails. Simpler and catches UPDATE-driven duplicates too.
- **The gap:** When `UPDATE users SET email = ?` is executed, we do NOT add a new escrow claim for the new email value. If two peers concurrently update different rows to the same email, the escrow won't catch it.
- **Why it passes now:** Randomized test email updates use random values (`e{rand}@x.com`), making collisions statistically unlikely with tested seeds.
- **Risk for Layer 3 (adversarial tests):** **MEDIUM** — a hand-crafted scenario could exploit this.
- **Fix:** Add a post-sync duplicate-email scan as a safety net in `sync.py`.

### 4. ✅ snapshot_state Format
Guide warns `id` column must be in every row dict. Our `row.snapshot()` returns all cells including `id` since it's stored as a `CRDTCell`. Verified working against the bench assertions.

### 5. ✅ Idempotent Sync
Guide warns about the idempotent-sync axis in randomized tests. Our sync is fully idempotent — confirmed passing with all seeds.

### 6. ✅ Order Invariance (Chaos)
Our merge is commutative + associative. All chaos seeds produce identical hashes.

### 7. ⚠️ CRDTRow.merge() unique_status Is Not Commutative
```python
# Current logic:
merged_unique = self.unique_status
if other.unique_status in ("committed", "rejected"):
    merged_unique = other.unique_status
```
If self=`committed` and other=`rejected`, result is `rejected`. Swapped: result is `committed`. This is NOT commutative.
- **Why it doesn't break:** `resolve_all()` runs immediately after row merges in `sync()`, overwriting `unique_status` deterministically based on claims. The merge result is transient.
- **Risk:** **LOW** — but should be fixed for correctness.
- **Fix:** Use a deterministic merge rule (e.g., "rejected" always wins over "committed" since it's monotonic).

### 8. ✅ Schema Not Synced Between Peers
Schemas are not exchanged during `sync()`. Each peer has its own schema from `apply_schema()`.
- **Why it doesn't break:** The bench always calls `apply_schema()` on every peer before any operations.
- **Risk for adversarial tests:** **NONE** — the bench design guarantees this.

---

## Part B: Bug Fixes (Priority Order)

### Fix 1: Post-Sync Uniqueness Scan (HIGH PRIORITY)
**File:** `engine/sync.py`
**What:** After escrow resolution, add a scan of all live rows to detect duplicate unique column values. Mark losers as `rejected`.
**Why:** Catches UPDATE-driven email collisions that escrow misses.

### Fix 2: Escrow Claims on UPDATE (MEDIUM PRIORITY)
**File:** `engine/sql_executor.py`
**What:** When an UPDATE touches a unique column (e.g., `email`), add a new escrow claim for the new value.
**Why:** Makes the escrow log accurate even across updates.

### Fix 3: Commutative unique_status Merge (LOW PRIORITY)
**File:** `engine/crdt_row.py`
**What:** Change merge logic to: `"rejected"` wins over `"committed"` wins over `"pending"` (monotonic lattice).
**Why:** Ensures commutativity even though `resolve_all` overwrites this.

---

## Part C: Stress Testing

### Test 1: Higher Parameters
```bash
python run.py --adapter adapters.ourteam:Engine --fk-policy tombstone \
  --randomized-seeds 9999 31415 27182 16180 11235 \
  --rand-peers 5 --rand-ops 150 --out report.json
```

### Test 2: Many More Seeds
```bash
python run.py --adapter adapters.ourteam:Engine --fk-policy tombstone \
  --randomized-seeds 1 2 3 4 5 6 7 8 9 10 42 100 999 1234 5678 \
  --rand-peers 5 --rand-ops 150 --out report_stress.json
```

### Test 3: Edge Case Manual Test
Create a manual test that specifically triggers:
- Two peers concurrently UPDATE different rows to the same email
- DELETE parent then INSERT child on same peer within same tick
- Three-way concurrent writes to same cell

---

## Part D: Deliverables Remaining

### 1. 3-Page Writeup PDF (25 judging points!)

**This is 25% of the total score. This is non-negotiable.**

**Section 1: Lattice Choices Per Type**
- Row existence: Simple tombstone flag (monotonic: once `True`, always `True`)
- Cell values: Multi-Value Register with deterministic `winner_value()`
- Vector clocks: Component-wise max merge (standard join-semilattice)

**Section 2: Uniqueness Protocol**
- Escrow-based claim tracking + post-sync duplicate scan
- Deterministic winner: `min(peer_id)` lexicographically
- Trade-off: "eventually unique" — temporary violation offline, restored on sync

**Section 3: FK Protocol**
- Tombstone policy: parent becomes tombstone, child survives
- Orphaned rows are visible in snapshots
- Defended over cascade (data loss) and orphan (loses traceability)

**Section 4: Sync Protocol**
- Bidirectional, snapshot-before-merge pattern
- Commutative + associative + idempotent merge
- Convergence argument: standard CRDT theorem

**Section 5: Metadata Growth**
- Vector clocks: O(writers) per cell — one entry per unique peer
- `prune()` removes inactive peers after sync (GC)
- Tombstones: kept permanently for simplicity, GC strategy documented

### 2. 5-Minute Demo Recording
- Show the reference scenario running
- Show hash matching across peers A, B, C
- Brief architecture walkthrough (engine layers)
- Show randomized test passing

### 3. GitHub Push
- Clean up test code from `if __name__ == '__main__'` blocks (optional)
- Ensure README exists
- Push final code

---

## Part E: Execution Order

| Step | Task | Time Est. | Priority |
|------|------|-----------|----------|
| 1 | Fix 1: Post-sync uniqueness scan | 15 min | HIGH |
| 2 | Fix 2: Escrow claims on UPDATE | 10 min | MEDIUM |
| 3 | Fix 3: Commutative unique_status | 5 min | LOW |
| 4 | Stress test with many seeds | 10 min | HIGH |
| 5 | Write 3-page PDF writeup | 60-90 min | CRITICAL |
| 6 | Record 5-min demo | 15 min | HIGH |
| 7 | Push to GitHub | 5 min | HIGH |
