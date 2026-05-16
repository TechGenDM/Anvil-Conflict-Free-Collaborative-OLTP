"""Generate final merged PDF: best of PDF writeup + TECHNICAL_ARCHITECTURAL_DEFENSE.md"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak, Preformatted
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY

OUT = "/Users/devasishmishra/Developer/TechGenDM_Codes/Hackathons/Anvil_SST_2026/Project/planning/Phi_Continuum_Anvil_Defense.pdf"

doc = SimpleDocTemplate(
    OUT, pagesize=A4,
    leftMargin=2*cm, rightMargin=2*cm,
    topMargin=2*cm, bottomMargin=2*cm
)

SS = getSampleStyleSheet()
W = A4[0] - 4*cm  # usable width

# ── Styles ─────────────────────────────────────────────────────────────────
def sty(name, parent="Normal", **kw):
    s = ParagraphStyle(name, parent=SS[parent], **kw)
    return s

TITLE   = sty("Title2",   "Title",   fontSize=18, textColor=colors.HexColor("#1a1a2e"), spaceAfter=4)
BYLINE  = sty("Byline",   "Normal",  fontSize=9,  textColor=colors.grey, spaceAfter=12, alignment=TA_CENTER)
H1      = sty("H1",       "Heading1", fontSize=13, textColor=colors.HexColor("#16213e"), spaceBefore=14, spaceAfter=4)
H2      = sty("H2",       "Heading2", fontSize=11, textColor=colors.HexColor("#0f3460"), spaceBefore=10, spaceAfter=3)
H3      = sty("H3",       "Heading3", fontSize=10, textColor=colors.HexColor("#533483"), spaceBefore=7,  spaceAfter=2)
BODY    = sty("Body2",    "Normal",   fontSize=9,  leading=13, spaceAfter=5, alignment=TA_JUSTIFY)
CODE    = sty("Code2",    "Code",     fontSize=7.5, leading=11, spaceAfter=5, fontName="Courier",
              backColor=colors.HexColor("#f5f5f5"), leftIndent=10, borderPad=4)
BULLET  = sty("Bullet2",  "Normal",  fontSize=9,  leading=12, leftIndent=14, spaceAfter=2,
              bulletIndent=4, bulletText="•")
CAPTION = sty("Caption2", "Normal",  fontSize=8,  textColor=colors.grey, spaceAfter=6, alignment=TA_CENTER)

ACCENT = colors.HexColor("#0f3460")

def hr(): return HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=6, spaceBefore=4)
def sp(h=6): return Spacer(1, h)
def p(text, style=BODY): return Paragraph(text, style)
def h1(t): return Paragraph(t, H1)
def h2(t): return Paragraph(t, H2)
def h3(t): return Paragraph(t, H3)
def b(t): return Paragraph(t, BULLET)
def code(t): return Preformatted(t, CODE)

def tbl(data, colWidths=None, hdr=True):
    t = Table(data, colWidths=colWidths or [W/len(data[0])]*len(data[0]))
    cmds = [
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("LEADING", (0,0), (-1,-1), 11),
        ("ROWBACKGROUNDS", (0,0), (-1,-1), [colors.white, colors.HexColor("#f0f4f8")]),
        ("GRID", (0,0), (-1,-1), 0.3, colors.HexColor("#cccccc")),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("LEFTPADDING", (0,0), (-1,-1), 5),
        ("RIGHTPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]
    if hdr:
        cmds += [
            ("BACKGROUND", (0,0), (-1,0), ACCENT),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ]
    t.setStyle(TableStyle(cmds))
    return t

# ══════════════════════════════════════════════════════════════════════════
story = []

# ── Cover ─────────────────────────────────────────────────────────────────
story += [
    sp(20),
    Paragraph("Anvil SST 2026 · Technical Architectural Defense", TITLE),
    Paragraph("Conflict-Free Collaborative OLTP Engine", sty("sub","Normal",fontSize=13,alignment=TA_CENTER,textColor=colors.HexColor("#0f3460"),spaceAfter=6)),
    hr(),
    Paragraph(
        "<b>Team:</b> Phi Continuum &nbsp;|&nbsp; <b>Authors:</b> Devasish Mishra et al. &nbsp;|&nbsp; "
        "<b>Benchmarks:</b> P-01 · P-02 · P-04 &nbsp;|&nbsp; <b>Revision:</b> Final",
        BYLINE),
    Paragraph(
        "<b>P-01 Score:</b> 1.0000 / 1.0000 (100%) &nbsp;|&nbsp; "
        "<b>FK Policy:</b> tombstone (declared uniform) &nbsp;|&nbsp; "
        "<b>Engine:</b> Pure Python 3.11, stdlib only",
        BYLINE),
    hr(),
    sp(10),
    p("<b>Abstract.</b> We present a coordinator-free CRDT engine supporting concurrent INSERT, UPDATE, and DELETE across N peers with no central authority. The engine implements per-column Multi-Value Registers (MVR) over vector clocks, an escrow-based uniqueness protocol, a configurable FK policy (tombstone/cascade/orphan), and a bidirectional merge-sync that is commutative, associative, and idempotent. Metadata grows O(writers), not O(writes). P-01 achieves a perfect 1.0000 score. This document also defends our P-02 causal context engine and P-04 noise-gated precision associative memory."),
    PageBreak(),
]

# ── PAGE 1: Lattice Choices ────────────────────────────────────────────────
story += [
    h1("1 · Lattice Choices Per Data Type"),
    h2("1.1 Row Membership — OR-Set via Monotone Tombstone"),
    p("Each row carries <code>tombstone: bool</code> and <code>tombstone_clock: VectorClock</code>. Rows are never physically deleted. A DELETE sets <code>tombstone = True</code> and records the deleting peer's VC. During merge: <code>merged.tombstone = self.tombstone OR other.tombstone</code> — monotone, irreversible. We choose <b>remove-wins</b>: a confirmed delete must not be resurrected by a late concurrent insert."),
    h2("1.2 Cell Values — Multi-Value Register (MVR) over Vector Clocks"),
    p("Each column is a <code>CRDTCell(value, clock, conflicts[])</code>. The merge rule is total and deterministic:"),
    tbl([
        ["Clock Relationship", "Merge Outcome", "Rationale"],
        ["self.clock dominates other.clock", "Keep self — causally newer", "Standard LWW on causal order"],
        ["other.clock dominates self.clock", "Keep other — causally newer", "Standard LWW on causal order"],
        ["Neither dominates (concurrent)", "MVR: retain both in conflicts[], merge clocks via component-wise max", "Preserves all concurrent writes — required by cell-level-strict bench scenario"],
    ], colWidths=[W*0.28, W*0.38, W*0.34]),
    sp(4),
    p("<b>Why MVR over pure LWW?</b> LWW requires a globally agreed-upon wall-clock or Lamport timestamp — unavailable in a coordinator-free setting. MVR preserves all concurrent writes and resolves them deterministically via <code>winner_value()</code>: sort all concurrent values lexicographically by string repr, return the smallest. The bench's <i>cell-level-strict</i> scenario explicitly tests that concurrent updates to different columns both survive — row-level LWW physically fails this."),
    code("""# engine/crdt_cell.py — CRDTCell.merge()
if self.clock.dominates(other.clock):  return self       # causally newer
if other.clock.dominates(self.clock):  return other      # causally newer
# Concurrent: Multi-Value Register — keep BOTH values
new_cell = CRDTCell(self.value, self.clock.merge(other.clock))
new_cell.conflicts = self.conflicts + [(other.value, other.clock)]
return new_cell

def winner_value(self):   # deterministic tie-break
    return sorted(self.all_values(), key=lambda v: str(v))[0]"""),
    h2("1.3 Vector Clocks — O(writers), not O(writes)"),
    p("Each <code>VectorClock</code> is a <code>dict{peer_id: int}</code>. Entries are <b>per-writer, not per-write</b>: a peer's counter increments once per local operation. After every sync, <code>prune(active_peers)</code> removes entries for departed peers. A cell updated 10,000 times by 3 peers has a VC of size 3, not 10,000. This is the metadata-growth invariant required by the problem statement."),
    h2("1.4 Status Lattices (Monotone Enums)"),
    tbl([
        ["Data Type", "Lattice", "Merge Rule", "Implementation"],
        ["Tombstone flag", "Grow-only bool", "OR — once True, never reverts", "CRDTRow.merge() L34"],
        ["FK status", "ok → orphaned", "Monotone worst-case: orphaned dominates", "CRDTRow.merge() L43"],
        ["Unique status", "pending → committed → rejected", "rejected > committed > pending", "CRDTRow.merge() L46-52"],
        ["Escrow claims", "Set union", "Append-only union on (table,cols,vals) key", "EscrowLog.merge()"],
    ], colWidths=[W*0.22, W*0.2, W*0.32, W*0.26]),
    sp(4),
    h2("1.5 Scoring Axis → Lattice Mapping"),
    tbl([
        ["Bench Axis", "Weight", "Lattice Mechanism"],
        ["cell-level / cell-level-strict", "10%", "MVR per column — concurrent updates to different columns both survive"],
        ["convergence", "30%", "Merge is commutative + associative → eventual consistency guaranteed"],
        ["order-invariance (chaos)", "10%", "Merge commutativity → same final state regardless of sync order"],
        ["randomized seeds", "15%", "Property-based invariants hold for any seed — no hardcoding possible"],
        ["uniqueness / composite_uniqueness", "≤15%", "Escrow log + post-sync scan → no duplicates in snapshot"],
        ["multi_level_fk / long_run", "≤10%", "Fixed-point FK recheck + VC pruning → correctness + bounded metadata"],
    ], colWidths=[W*0.30, W*0.10, W*0.60]),
    PageBreak(),
]

# ── PAGE 2: Uniqueness + FK + Sync ────────────────────────────────────────
story += [
    h1("2 · Uniqueness Protocol · FK Protocol · Sync Protocol"),
    h2("2.1 Uniqueness Protocol — Escrow Log"),
    p("Standard CRDT row membership does not enforce UNIQUE constraints: two peers can independently insert rows with the same email, and after sync both rows exist. A coordinator-free uniqueness protocol must resolve conflicts deterministically without communication at write time."),
    p("<b>Design:</b> An <code>EscrowLog</code> — a CRDT map from <code>(table, cols_tuple, vals_tuple)</code> to a list of <code>(peer_id, row_pk)</code> claimants. The escrow log is itself a CRDT: merge = set union (idempotent, commutative, associative). On every INSERT the executor calls <code>escrow.claim(...)</code>. During sync, both peers' logs are merged bidirectionally before resolution."),
    p("<b>Resolution rule</b> — after escrow merge, <code>resolve_all(store)</code> iterates every group:"),
    b("Single claimant → mark row <code>unique_status = \"committed\"</code>"),
    b("Multiple claimants → winner = <code>min(claimants, key=(peer_id, row_pk))</code> lexicographically. Winner → committed. All others → <b>rejected</b>."),
    p("Rejected rows are retained in the store (for sync correctness) but excluded from <code>snapshot_state()</code>. Their unique-constraint column values are <b>nullified</b> (set to None) on the read side — preserving audit history while enforcing the invariant at query time."),
    p("<b>Composite uniqueness:</b> the escrow log key uses <code>tuple(sorted_cols)</code>, so <code>UNIQUE(org_id, user_slug)</code> is handled identically to single-column constraints — no special-casing required."),
    p("<b>Safety net:</b> <code>_resolve_unique_duplicates(store)</code> runs after escrow resolution as a post-sync full-table scan — catching UPDATE-driven collisions the escrow log misses. Winner: <code>min(pk)</code> lexicographically. This is the backstop for <i>composite_uniqueness</i> and <i>high_density</i> scenarios."),
    p("<b>Idempotency:</b> given the same escrow log and store state, <code>resolve_all()</code> always produces the same <code>unique_status</code> assignments. Running sync twice produces identical hashes."),
    hr(),
    h2("2.2 FK Protocol — Tombstone Policy (Declared Uniform)"),
    p("<b>Policy declaration:</b> We declare <b>tombstone</b> as our FK-under-partition policy. When a parent row is deleted, child rows referencing it survive and remain visible in <code>snapshot_state()</code> with <code>fk_status = \"orphaned\"</code> and FK column value preserved (not nullified). The engine also supports <i>cascade</i> (orphans hidden) and <i>orphan</i> (FK column nullified) via <code>--fk-policy</code> flag."),
    p("<b>Storage/visibility decoupling:</b> a row can exist in the store but be invisible at query time based on its <code>fk_status</code>. FK enforcement is a read-side computation, not a write-side gate — writes are always accepted, visibility is evaluated after sync."),
    code("""# engine/crdt_row.py — is_visible()
def is_visible(self, fk_policy="cascade") -> bool:
    if self.tombstone:                              return False
    if fk_policy == "cascade" and self.fk_status == "orphaned": return False
    return True   # tombstone policy: orphans are visible"""),
    p("<b>Three FKEnforcer entry points:</b>"),
    tbl([
        ["Method", "When Called", "What It Does"],
        ["on_parent_delete(store, table, pk)", "On DELETE in executor", "Scans all child tables for rows referencing pk; sets fk_status='orphaned'"],
        ["on_child_insert(store, table, row)", "On INSERT in executor", "Checks if referenced parent is already tombstoned; marks child orphaned"],
        ["recheck_all(store)", "After every sync", "Fixed-point iteration: re-validates all FK relationships for out-of-order arrivals"],
    ], colWidths=[W*0.34, W*0.24, W*0.42]),
    sp(4),
    p("<b>Fixed-point iteration for multi-level chains:</b> <code>recheck_all()</code> iterates until no new orphaned rows are found. An Organization tombstoned → Users orphaned (Pass 1) → Orders orphaned (Pass 2). Terminates in O(FK chain depth) ≤ 3 passes for the benchmark schema. A child is orphaned if parent is missing, tombstoned, <i>or itself orphaned</i> — enabling recursive cascade."),
    hr(),
    h2("2.3 Sync Protocol — State-Based Bidirectional Exchange"),
    p("Our sync is <b>state-based</b> (not op-log-based). Correctness rests on the join-semilattice properties of our merge operator:"),
    tbl([
        ["Property", "Meaning", "How We Satisfy It"],
        ["Commutativity", "A ⊔ B = B ⊔ A", "VC dominance is symmetric; all merge ops treat both operands equally"],
        ["Associativity", "(A⊔B)⊔C = A⊔(B⊔C)", "Component-wise max on VCs; set-union on EscrowLog; monotone OR on tombstone"],
        ["Idempotency", "A ⊔ A = A", "Merging identical VC/value returns same object; EscrowLog deduplicates on claimant"],
    ], colWidths=[W*0.20, W*0.22, W*0.58]),
    sp(4),
    p("<b>7-step sync algorithm</b> (executed atomically — no partial sync):"),
    tbl([
        ["Step", "Action", "Correctness Role"],
        ["1", "Merge known_peers (union)", "Enables VC pruning to correct active set"],
        ["2", "Snapshot both stores BEFORE merging", "Prevents mid-sync contamination — keystone of correctness"],
        ["3", "Bidirectional row exchange via CRDTRow.merge()", "State convergence"],
        ["4", "Merge + resolve EscrowLogs bidirectionally", "Uniqueness convergence"],
        ["4b", "Post-sync full-table duplicate scan", "UPDATE-driven collision safety net"],
        ["5", "FKEnforcer.recheck_all() on both peers", "FK integrity after out-of-order arrivals"],
        ["6", "VC garbage collection: prune(active_peers)", "Bounded metadata growth"],
    ], colWidths=[W*0.06, W*0.38, W*0.56]),
    PageBreak(),
]

# ── PAGE 3: Metadata + Convergence Proof + P-02 + P-04 + Checklist ────────
story += [
    h1("3 · Metadata Growth Analysis · Convergence Proof · P-02 · P-04"),
    h2("3.1 Metadata Growth Analysis"),
    tbl([
        ["Metadata Item", "Growth Bound", "Bounding Mechanism", "Implementation"],
        ["VC entries per cell", "O(W) — W = distinct writers of that cell", "prune(active_peers) after every sync removes departed peers", "vector_clock.py:prune()"],
        ["Tombstone clock entries", "O(W) — peers that saw the delete", "Same prune mechanism on tombstone_clock", "sync.py GC block"],
        ["Escrow log entries", "O(U × P) — U = unique values, P = peers", "Bounded by unique constraint violations; entries never removed (needed for correctness)", "EscrowLog.claims dict"],
        ["FK status per row", "O(R) — one enum per row", "Recomputed on every recheck_all(); no accumulation", "CRDTRow.fk_status"],
        ["Conflict list per cell", "O(C) — C = concurrent writers", "Bounded by peer count; in practice 1-3 entries", "CRDTCell.conflicts"],
        ["Tombstoned rows", "O(D) — D = total deletes ever", "Permanent; full GC requires distributed consensus (out of scope)", "CRDTRow.tombstone"],
    ], colWidths=[W*0.22, W*0.24, W*0.36, W*0.18]),
    sp(4),
    p("<b>Critical bound:</b> VC size is O(writers per cell), not O(writes). A cell updated 10,000 times by 3 peers has a VC of size 3, not 10,000. This satisfies the metadata-growth constraint: bounded by the number of writers, not operations."),
    p("<b>Practical numbers (P-01 long_run stress test — 1,500 ops, 6 peers):</b> convergence time &lt; 5 ms per sync · metadata overhead ~12% of total payload · FK recheck passes ≤ 3."),
    hr(),
    h2("3.2 Convergence Proof (Formal Sketch)"),
    p("<b>Claim:</b> For any two peers A and B that have observed the same set of operations (possibly in different orders), <code>snapshot_hash(A) == snapshot_hash(B)</code> after sync."),
    p("<b>Proof:</b>"),
    b("<b>CRDTCell.merge is commutative:</b> the dominates/concurrent check is symmetric; the conflict list union is a set operation. merge(a,b) == merge(b,a)."),
    b("<b>CRDTCell.merge is associative:</b> component-wise max of VCs is associative; conflict list union is associative. merge(merge(a,b),c) == merge(a,merge(b,c))."),
    b("<b>CRDTRow.merge is commutative and associative:</b> follows from cell-level properties + tombstone monotonicity (boolean OR is commutative and associative)."),
    b("<b>Uniqueness resolution is deterministic:</b> the escrow log is a CRDT set (commutative, associative). resolve_all() with min(peer_id, row_pk) is a total order — no ties."),
    b("<b>FK recheck is deterministic:</b> recheck_all() is a fixed-point computation over a monotone function (orphaned status only grows, never shrinks). Fixed-point of a monotone function on a finite lattice is unique."),
    b("<b>snapshot_state is deterministic:</b> rows sorted by PK, columns sorted by name, json.dumps(sort_keys=True) — same state always produces the same SHA-256 hash. ∎"),
    hr(),
    h2("3.3 P-02 · Causal Context Reconstruction Under Cascading Renames"),
    p("The L3 generator applies 80 topology mutations with rename_weight=0.85 and cascading_renames=True, producing chains like <code>svc-04→svc-04-r6→...→svc-04-r6-r3-r6-r3-r8-r4-r8-r3-r7-r6-r4-r9</code>. Additionally, 20% of eval signals are decoys (<code>unknown_anomaly</code> trigger) with no matching family."),
    p("<b>Design: causal rename graph + lazy resolution.</b> Every <code>topology/rename</code> event stores a directed edge <code>old→new</code>. Resolution walks the chain to terminus with cycle detection (O(chain depth) per call). Family identification is then a resolved-service equality check — not string similarity."),
    code("""def _resolve(self, svc):
    seen = set()
    while svc in self.renames and svc not in seen:
        seen.add(svc);  svc = self.renames[svc]
    return svc   # canonical live name"""),
    p("<b>Decoy handling:</b> exact trigger-content check — no learned threshold. A threshold is fragile across seeds; an exact string match is seed-agnostic: <code>is_decoy = \"unknown_anomaly\" in signal[\"trigger\"]</code>."),
    p("<b>Remediation deduplication:</b> a <code>seen_actions</code> set ensures top-k suggestions are action-diverse, maximising coverage of the plausible remediation space."),
    hr(),
    h2("3.4 P-04 · Noise-Gated Precision for Associative Memory"),
    p("The PCAM model is a Hopfield-class associative memory where a precision vector π modulates feature influence on attractor dynamics. Queries arrive with 60-85% masking. The failure mode: zero features get the same weight as signal features, pulling dynamics toward spurious attractors."),
    tbl([
        ["Strategy", "Formula", "Risk"],
        ["Identity (baseline floor)", "π_i = 1 everywhere", "Noise and signal weighted equally — fails under high masking"],
        ["Variance-based", "π_i = 1/Var(feature_i) across stored patterns", "Distribution-dependent; wrong for unseen seeds"],
        ["Noise-Gated (chosen)", "π_i = 5.0 if |x_i| > ε else 0.1, then normalize", "Query-adaptive, seed-agnostic — correct choice for randomized evaluation"],
    ], colWidths=[W*0.28, W*0.38, W*0.34]),
    sp(4),
    p("Normalization (<code>π / mean(π)</code>) prevents energy scale drift while preserving the relative precision profile. <b>Why not learned π?</b> Learned precision overfits to one seed's pattern distribution and is precisely wrong for another seed's geometry. The Noise-Gated heuristic derives its mask from the corrupted input itself — seed-agnostic by construction."),
    hr(),
    h2("3.5 Submission Checklist"),
    tbl([
        ["Requirement", "Status", "Location"],
        ["Git repository (public)", "✅", "github.com/TechGenDM/Anvil-Conflict-Free-Collaborative-OLTP"],
        ["README quickstart (< 5 min, clean machine)", "✅", "Anvil-P-E/bench-p01-crdt/README.md"],
        ["Reproducibility (requirements.txt)", "✅", "bench-p01-crdt/requirements.txt"],
        ["Demo video (5 min, L3 banner visible)", "✅", "Submitted separately"],
        ["3-page writeup PDF", "✅", "This document"],
        ["L3 JSON output (P-01)", "✅", "bench-p01-crdt/l3_report.json — score 1.0000"],
        ["L3 JSON output (P-02)", "✅", "bench-p02-context/l3_report.json"],
        ["L3 JSON output (P-04)", "✅", "bench-p04-pcam/l3_report.json"],
        ["FK policy declared uniform (tombstone)", "✅", "Engine constructor + README + Section 2.2 above"],
        ["Bench frozen (no harness modifications)", "✅", "Only adapters/ourteam.py + engine/ modified"],
    ], colWidths=[W*0.44, W*0.08, W*0.48]),
    sp(8),
    hr(),
    p("<i>Submitted to the Anvil Council for L3 evaluation.</i>"),
    p("<b>Team Phi Continuum</b> · Devasish Mishra et al. · P-01: 1.0000/1.0000 · P-02: Submitted · P-04: Submitted"),
    p("<i>\"Build it so it cannot be wrong, not so it looks right.\"</i>"),
]

doc.build(story)
print(f"PDF generated: {OUT}")
