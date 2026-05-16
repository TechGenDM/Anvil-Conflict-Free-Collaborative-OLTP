"""
Adversarial test suite — designed to BREAK the CRDT engine.
Run: PYTHONPATH=. python adversarial_tests.py
"""
from adapters.ourteam import Engine

SCHEMA = [
    """CREATE TABLE users (
         id    TEXT PRIMARY KEY,
         email TEXT NOT NULL UNIQUE,
         name  TEXT
       )""",
    """CREATE TABLE orders (
         id          TEXT PRIMARY KEY,
         user_id     TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
         status      TEXT NOT NULL,
         total_cents INTEGER NOT NULL DEFAULT 0
       )""",
    "CREATE INDEX orders_by_user ON orders(user_id, status)",
]

def fresh_engine(*peer_ids):
    e = Engine()
    for p in peer_ids:
        e.open_peer(p)
        e.apply_schema(p, SCHEMA)
    return e

PASSED = []
FAILED = []

def check(name, condition, detail=""):
    if condition:
        PASSED.append(name)
        print(f"  ✅ {name}")
    else:
        FAILED.append(name)
        print(f"  ❌ FAIL: {name} — {detail}")

# ─────────────────────────────────────────────────────────────────
# T01: Same email inserted on 3 peers concurrently → exactly 1 winner
# ─────────────────────────────────────────────────────────────────
print("\n[T01] Triple concurrent email conflict")
e = fresh_engine("A","B","C")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","x@x.com","Alice"))
e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","x@x.com","Bob"))
e.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","x@x.com","Carol"))
e.sync("A","B"); e.sync("B","C"); e.sync("A","C")
e.sync("A","B"); e.sync("B","C"); e.sync("A","C")
for p in ("A","B","C"):
    s = e.snapshot_state(p)
    emails = [u["email"] for u in s.get("users",[]) if u.get("email")=="x@x.com"]
    check(f"T01-unique-{p}", len(emails)==1, f"got {len(emails)} rows with same email")
hashes = {p: e.snapshot_hash(p) for p in ("A","B","C")}
check("T01-converge", len(set(hashes.values()))==1, str(hashes))

# ─────────────────────────────────────────────────────────────────
# T02: UPDATE both rows to same email concurrently → only 1 visible
# ─────────────────────────────────────────────────────────────────
print("\n[T02] Concurrent UPDATE collision on unique column")
e = fresh_engine("A","B")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
e.sync("A","B")
# Both peers update different users to the same email
e.execute("A", "UPDATE users SET email=? WHERE id=?", ("clash@x.com","u1"))
e.execute("B", "UPDATE users SET email=? WHERE id=?", ("clash@x.com","u2"))
e.sync("A","B"); e.sync("B","A")
for p in ("A","B"):
    s = e.snapshot_state(p)
    clash = [u for u in s.get("users",[]) if u.get("email")=="clash@x.com"]
    check(f"T02-unique-{p}", len(clash)==1, f"got {len(clash)} rows with clash@x.com")
check("T02-converge", e.snapshot_hash("A")==e.snapshot_hash("B"))

# ─────────────────────────────────────────────────────────────────
# T03: Delete parent AFTER child is inserted — out-of-order arrival
# ─────────────────────────────────────────────────────────────────
print("\n[T03] Out-of-order: child inserted before parent delete arrives")
e = fresh_engine("A","B","C")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e.sync("A","C")
e.execute("C", "DELETE FROM users WHERE id=?", ("u1",))
e.execute("A", "INSERT INTO orders (id,user_id,status,total_cents) VALUES (?,?,?,?)", ("o1","u1","pending",500))
e.sync("A","B"); e.sync("B","C"); e.sync("A","C")
e.sync("A","B"); e.sync("B","C"); e.sync("A","C")
for p in ("A","B","C"):
    s = e.snapshot_state(p)
    users = [u["id"] for u in s.get("users",[])]
    orders = [o["id"] for o in s.get("orders",[])]
    # Tombstone policy: u1 NOT visible, o1 IS visible
    check(f"T03-u1-tombstoned-{p}", "u1" not in users, f"u1 still visible: {users}")
    check(f"T03-o1-alive-{p}", "o1" in orders, f"o1 missing: {orders}")
check("T03-converge", len(set(e.snapshot_hash(p) for p in ("A","B","C")))==1)

# ─────────────────────────────────────────────────────────────────
# T04: Re-insert after delete — tombstone must win (delete-wins)
# ─────────────────────────────────────────────────────────────────
print("\n[T04] Re-insert same PK after it was deleted")
e = fresh_engine("A","B")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e.sync("A","B")
e.execute("A", "DELETE FROM users WHERE id=?", ("u1",))
e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a2@x.com","Alice2"))
e.sync("A","B"); e.sync("B","A")
# Tombstone must win — u1 must NOT be visible
for p in ("A","B"):
    s = e.snapshot_state(p)
    ids = [u["id"] for u in s.get("users",[])]
    check(f"T04-tombstone-wins-{p}", "u1" not in ids, f"u1 resurrected: {ids}")
check("T04-converge", e.snapshot_hash("A")==e.snapshot_hash("B"))

# ─────────────────────────────────────────────────────────────────
# T05: Cell-level merge — 4 peers update 4 different columns of same row
# ─────────────────────────────────────────────────────────────────
print("\n[T05] Cell-level merge 4 peers × different columns")
e = fresh_engine("A","B","C","D")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","orig@x.com","Orig"))
e.sync("A","B"); e.sync("A","C"); e.sync("A","D")
# All 4 update different columns concurrently
e.execute("A", "UPDATE users SET name=? WHERE id=?", ("NameFromA","u1"))
e.execute("B", "UPDATE users SET email=? WHERE id=?", ("emailFromB@x.com","u1"))
# C and D do nothing extra — just A and B updates matter for cell-level
e.sync("A","B"); e.sync("B","C"); e.sync("C","D"); e.sync("A","D")
e.sync("A","B"); e.sync("B","C"); e.sync("C","D"); e.sync("A","D")
for p in ("A","B","C","D"):
    s = e.snapshot_state(p)
    u1 = next((u for u in s.get("users",[]) if u.get("id")=="u1"), None)
    check(f"T05-name-{p}", u1 and u1.get("name")=="NameFromA", f"u1={u1}")
    check(f"T05-email-{p}", u1 and u1.get("email")=="emailFromB@x.com", f"u1={u1}")
check("T05-converge", len(set(e.snapshot_hash(p) for p in ("A","B","C","D")))==1)

# ─────────────────────────────────────────────────────────────────
# T06: Idempotency — syncing same pair 10 times must not change state
# ─────────────────────────────────────────────────────────────────
print("\n[T06] Idempotency — 10 extra syncs must not change hash")
e = fresh_engine("A","B")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
e.sync("A","B")
h_before = (e.snapshot_hash("A"), e.snapshot_hash("B"))
for _ in range(10):
    e.sync("A","B")
h_after = (e.snapshot_hash("A"), e.snapshot_hash("B"))
check("T06-idempotent", h_before == h_after, f"before={h_before} after={h_after}")

# ─────────────────────────────────────────────────────────────────
# T07: Commutativity — sync(A,B) then sync(B,C) == sync(B,C) then sync(A,B) result
# ─────────────────────────────────────────────────────────────────
print("\n[T07] Commutativity of sync order")
def scenario1():
    e = fresh_engine("A","B","C")
    e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
    e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
    e.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","c@x.com","Carol"))
    e.sync("A","B"); e.sync("B","C"); e.sync("A","C")
    return e.snapshot_hash("A")

def scenario2():
    e = fresh_engine("A","B","C")
    e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
    e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
    e.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","c@x.com","Carol"))
    e.sync("C","B"); e.sync("B","A"); e.sync("C","A")
    return e.snapshot_hash("A")

check("T07-commutative", scenario1()==scenario2(), f"s1={scenario1()} s2={scenario2()}")

# ─────────────────────────────────────────────────────────────────
# T08: Mass insert + delete — no ghost rows visible
# ─────────────────────────────────────────────────────────────────
print("\n[T08] Mass insert 50 users then delete all — none should be visible")
e = fresh_engine("A","B")
for i in range(50):
    e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", (f"u{i}", f"u{i}@x.com", f"User{i}"))
e.sync("A","B")
for i in range(50):
    e.execute("A", "DELETE FROM users WHERE id=?", (f"u{i}",))
e.sync("A","B")
for p in ("A","B"):
    s = e.snapshot_state(p)
    count = len(s.get("users",[]))
    check(f"T08-all-deleted-{p}", count==0, f"{count} users still visible")
check("T08-converge", e.snapshot_hash("A")==e.snapshot_hash("B"))

# ─────────────────────────────────────────────────────────────────
# T09: 5-peer star topology — A syncs with all, then all converge
# ─────────────────────────────────────────────────────────────────
print("\n[T09] 5-peer star topology convergence")
peers = ["P0","P1","P2","P3","P4"]
e = fresh_engine(*peers)
for i, p in enumerate(peers):
    e.execute(p, "INSERT INTO users (id,email,name) VALUES (?,?,?)", (f"u{i}", f"u{i}@x.com", f"User{i}"))
# Star: P0 syncs with all
for p in peers[1:]:
    e.sync("P0", p)
# Then full mesh
for i in range(len(peers)):
    for j in range(i+1, len(peers)):
        e.sync(peers[i], peers[j])
hashes = {p: e.snapshot_hash(p) for p in peers}
check("T09-converge", len(set(hashes.values()))==1, str(set(hashes.values())))
# All 5 users should be visible
s = e.snapshot_state("P0")
check("T09-all-rows", len(s.get("users",[]))==5, f"got {len(s.get('users',[]))} rows")

# ─────────────────────────────────────────────────────────────────
# T10: Vector clock growth — writing 100 times must not grow clock beyond 1 entry
# ─────────────────────────────────────────────────────────────────
print("\n[T10] Vector clock bounded by O(writers), not O(writes)")
e = fresh_engine("A","B")
e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
for _ in range(99):
    e.execute("A", "UPDATE users SET name=? WHERE id=?", ("Alice","u1"))
e.sync("A","B")
from engine.crdt_store import CRDTStore
store_a = e.peers["A"].store
row = store_a.tables["users"]["u1"]
for col, cell in row.cells.items():
    clock_size = len(cell.clock.to_dict())
    check(f"T10-clock-bounded-{col}", clock_size <= 2, f"clock has {clock_size} entries: {cell.clock.to_dict()}")


# ═══════════════════════════════════════════════════════════════════
# WAVE 2: EVEN HARDER EDGE CASES
# ═══════════════════════════════════════════════════════════════════

# T11: Hash determinism — same state, different insert orders
print("\n[T11] Hash determinism: different insert orders → same hash")
e2 = fresh_engine("A","B")
e2.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e2.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
e2.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","Bob"))
e2.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e2.sync("A","B")
check("T11-hash-determinism", e2.snapshot_hash("A")==e2.snapshot_hash("B"),
      f"A={e2.snapshot_hash('A')[:16]} B={e2.snapshot_hash('B')[:16]}")

# T12: Delete → re-insert conflict → delete again — tombstone must still win
print("\n[T12] Delete → concurrent re-insert → delete again")
e12 = fresh_engine("A","B")
e12.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e12.sync("A","B")
e12.execute("A", "DELETE FROM users WHERE id=?", ("u1",))
e12.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a2@x.com","Alice2"))
e12.sync("A","B")
e12.execute("A", "DELETE FROM users WHERE id=?", ("u1",))
e12.sync("A","B")
for p in ("A","B"):
    ids = [u["id"] for u in e12.snapshot_state(p).get("users",[])]
    check(f"T12-still-dead-{p}", "u1" not in ids, f"u1 visible: {ids}")
check("T12-converge", e12.snapshot_hash("A")==e12.snapshot_hash("B"))

# T13: Uniqueness winner deleted — loser must NOT auto-promote
print("\n[T13] Uniqueness: winner deleted — loser stays rejected")
e13 = fresh_engine("A","B")
e13.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","clash@x.com","Alice"))
e13.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","clash@x.com","Bob"))
e13.sync("A","B"); e13.sync("B","A")
live = [u for u in e13.snapshot_state("A").get("users",[]) if u.get("email")=="clash@x.com"]
check("T13-setup", len(live)==1, f"setup: {len(live)} live")
winner_id = live[0]["id"]
e13.execute("A", "DELETE FROM users WHERE id=?", (winner_id,))
e13.sync("A","B"); e13.sync("B","A")
for p in ("A","B"):
    clash_live = [u for u in e13.snapshot_state(p).get("users",[]) if u.get("email")=="clash@x.com"]
    check(f"T13-loser-stays-rejected-{p}", len(clash_live)==0, f"loser promoted: {clash_live}")
check("T13-converge", e13.snapshot_hash("A")==e13.snapshot_hash("B"))

# T14: 3 peers all delete same row concurrently
print("\n[T14] Three peers delete same row concurrently")
e14 = fresh_engine("A","B","C")
e14.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e14.sync("A","B"); e14.sync("A","C")
e14.execute("A", "DELETE FROM users WHERE id=?", ("u1",))
e14.execute("B", "DELETE FROM users WHERE id=?", ("u1",))
e14.execute("C", "DELETE FROM users WHERE id=?", ("u1",))
e14.sync("A","B"); e14.sync("B","C"); e14.sync("A","C")
for p in ("A","B","C"):
    ids = [u["id"] for u in e14.snapshot_state(p).get("users",[])]
    check(f"T14-dead-{p}", "u1" not in ids, f"u1 visible: {ids}")
check("T14-converge", len(set(e14.snapshot_hash(p) for p in ("A","B","C")))==1)

# T15: Orders visible under tombstone — reference must be preserved
print("\n[T15] Orders FK tombstone: order visible, user not, reference intact")
e15 = fresh_engine("A","B","C")
e15.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e15.execute("A", "INSERT INTO orders (id,user_id,status,total_cents) VALUES (?,?,?,?)", ("o1","u1","pending",999))
e15.sync("A","C")
e15.execute("C", "DELETE FROM users WHERE id=?", ("u1",))
for _ in range(2):
    e15.sync("A","B"); e15.sync("B","C"); e15.sync("A","C")
for p in ("A","B","C"):
    s = e15.snapshot_state(p)
    user_ids = {u["id"] for u in s.get("users",[])}
    o1 = next((o for o in s.get("orders",[]) if o.get("id")=="o1"), None)
    check(f"T15-u1-gone-{p}", "u1" not in user_ids)
    check(f"T15-o1-alive-{p}", o1 is not None, f"o1 missing")
    check(f"T15-o1-refs-u1-{p}", o1 and o1.get("user_id")=="u1", f"o1={o1}")
check("T15-converge", len(set(e15.snapshot_hash(p) for p in ("A","B","C")))==1)

# T16: Empty peer synced with full peer
print("\n[T16] Empty peer synced with full peer")
e16 = fresh_engine("A","B")
for i in range(10):
    e16.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)",
                (f"u{i}", f"u{i}@x.com", f"User{i}"))
e16.sync("A","B")
check("T16-full-transfer", len(e16.snapshot_state("B").get("users",[]))==10)
check("T16-converge", e16.snapshot_hash("A")==e16.snapshot_hash("B"))

# T17: Associativity — (A+B)+C == A+(B+C)
print("\n[T17] Associativity: sync order grouping doesn't matter")
def build_left():
    e = fresh_engine("A","B","C")
    e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","A"))
    e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","B"))
    e.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","c@x.com","C"))
    e.sync("A","B"); e.sync("A","C"); e.sync("B","C")
    return e.snapshot_hash("A")
def build_right():
    e = fresh_engine("A","B","C")
    e.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","A"))
    e.execute("B", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u2","b@x.com","B"))
    e.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","c@x.com","C"))
    e.sync("B","C"); e.sync("A","C"); e.sync("A","B")
    return e.snapshot_hash("A")
check("T17-associative", build_left()==build_right(), f"left={build_left()[:12]} right={build_right()[:12]}")

# T18: Chain A→B→C — A's data reaches C only via B
print("\n[T18] Chain topology A→B→C (no direct A↔C sync)")
e18 = fresh_engine("A","B","C")
e18.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
e18.execute("C", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u3","c@x.com","Carol"))
e18.sync("A","B"); e18.sync("B","C"); e18.sync("A","B"); e18.sync("B","C")
ids_c = {u["id"] for u in e18.snapshot_state("C").get("users",[])}
check("T18-a-reached-c", "u1" in ids_c, f"C missing u1: {ids_c}")
check("T18-c-has-own", "u3" in ids_c)
check("T18-converge", e18.snapshot_hash("A")==e18.snapshot_hash("B")==e18.snapshot_hash("C"))

# T19: UPDATE non-existent row — must be silent no-op
print("\n[T19] UPDATE non-existent row — silent no-op")
e19 = fresh_engine("A")
try:
    e19.execute("A", "UPDATE users SET name=? WHERE id=?", ("Ghost","ghost_id"))
    ids = [u["id"] for u in e19.snapshot_state("A").get("users",[])]
    check("T19-no-ghost-row", "ghost_id" not in ids, f"ghost row created: {ids}")
    check("T19-no-crash", True)
except Exception as ex:
    check("T19-no-crash", False, f"crashed: {ex}")

# T20: Self-sync — sync(A,A) must be a perfect no-op
print("\n[T20] Self-sync is a no-op")
e20 = fresh_engine("A")
e20.execute("A", "INSERT INTO users (id,email,name) VALUES (?,?,?)", ("u1","a@x.com","Alice"))
h_before = e20.snapshot_hash("A")
try:
    e20.sync("A","A")
    check("T20-self-sync-no-op", e20.snapshot_hash("A")==h_before, "hash changed after self-sync")
except Exception as ex:
    check("T20-self-sync-no-op", False, f"crashed: {ex}")

# ─────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"RESULTS: {len(PASSED)} passed, {len(FAILED)} failed")
if FAILED:
    print(f"\nFAILED TESTS:")
    for f in FAILED:
        print(f"  ❌ {f}")
else:
    print("🎉 ALL ADVERSARIAL TESTS PASSED!")
print("="*60)
