# Anvil SST 2026 - Final Benchmark Results Summary

This document summarizes the performance of our custom Anvil engine across the core benchmark suites (P-01, P-02, P-04) using both the **Condensed Battery** (quick validation) and the **Full Battery** (final stress test).

## 1. Summary of Benchmark Updates
The benchmark repository was recently updated to include stricter L3 "Stretch" scenarios:
- **P-01 (CRDT):** Added `composite_uniqueness` (multi-column keys) and `multi_level_fk` (recursive cascading deletions through 3 levels).
- **P-02 (Context):** Introduced a 20% **decoy rate** (signals with no history) and **topology mutations** (renames/moves during an incident window).
- **P-04 (PCAM):** Shifted to **clustered pattern distributions**, making identity precision ($\Pi=I$) more prone to retrieval errors and high anisotropy.

---

## 2. Benchmark Results

### P-01: CRDT-Native OLTP
| Battery | Score | Invariants Passed | Notes |
| :--- | :--- | :--- | :--- |
| **Condensed** | 1.0000 / 1.0000 | 100% | Verified Reference + Chaos (1 seed) + Randomized (1 seed). |
| **Full** | **1.0000 / 1.0000** | **100%** | **Perfect score on all 8 Randomized seeds + Long-Run Stress.** |

**Key Features:**
- Recursive Fixed-Point FK Enforcement.
- Composite Unique Index Support.
- Deterministic Row/Cell resolution.

### P-02: Predictive Context Reconstruction
| Battery | Score | Recall@5 | Precision@5 |
| :--- | :--- | :--- | :--- |
| **Condensed** | 0.7952 / 0.8000 | 1.000 | 0.952 |
| **Full** | **0.7616 / 0.8000** | **0.992** | **0.888** |

**Key Features:**
- Decoy Suppression (Unknown Anomaly rejection).
- Path-resolved topology rename tracking.
- Similarity-based past incident ranking.

### P-04: PCAM Anisotropy Control
| Battery | Score | Mean Delta | Notes |
| :--- | :--- | :--- | :--- |
| **Condensed** | 7.00 / 90.00 | +0.008 | Bebeats baseline on Seed 42. |
| **Full** | **7.58 / 90.00** | **+0.017** | **Consistent retrieval gain across clustered patterns.** |

**Key Features:**
- Stable Variance Heuristic for feature-wise precision.
- Jacobi-style diagonal preconditioning.

---

## 3. Implementation Integrity
All engines are implemented using **pure Python + NumPy** with zero external dependencies, meeting the strict Council submission criteria. The `adapters.ourteam:Engine` class consistently demonstrates bit-identical state convergence across all chaotic synchronization scenarios.

**Timestamp:** 2026-05-16 07:50:00
**L3 Version:** anvil-2026-final-release
