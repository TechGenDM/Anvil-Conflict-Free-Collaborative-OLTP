# Anvil P-01: Demo Video Script
**Target Duration:** 5 Minutes
**Objective:** Visually prove that the engine achieves eventual consistency under high-concurrency (5 peers, 150 operations) and mathematically handles uniqueness resolution dynamically without central locking.

---

### Segment 1: The Setup (0:00 - 1:00)
- **Visual:** Terminal window, `bench-p01-crdt` folder. Split screen with code showing `uniqueness.py` or `crdt_store.py`.
- **Script:** "Hi, we are Team TechGenDM. We chose the P-01 Conflict-Free Collaborative OLTP challenge. Our engine is a pure Python, in-memory CRDT database that achieves strict eventual consistency with zero external dependencies. There is no SQLite and no central server."
- **Action:** Open `uniqueness.py` and briefly highlight the `EscrowLog` class.
- **Script:** "To handle uniqueness constraints across decentralized nodes, we built an Escrow Log system. Inserts are marked as 'pending' and are deterministically resolved via chronological and lexicographical sorting during synchronization, ensuring all peers independently agree on the exact same winner."

### Segment 2: Running the Adversarial Tests (1:00 - 2:00)
- **Visual:** Terminal executing `python adversarial_tests.py`
- **Script:** "We built a 67-assertion adversarial test suite to cover extreme edge cases. Watch as we run it."
- **Action:** Press enter, show all 67 tests passing in green.
- **Script:** "This test suite covers concurrent deletes, multi-node uniqueness collisions, associative and commutative merge rules, and the 'orphan' FK tombstone policy. We explicitly prove that cell-level Last-Writer-Wins is implemented correctly (Anti-Pattern 2) by showing that if Peer A updates a user's name and Peer B updates their email, both survive."

### Segment 3: The Multi-Seed L2 Benchmark (2:00 - 4:00)
- **Visual:** Terminal executing the stress test command.
- **Script:** "Now for the real proof: the L2 Property-Based Evaluator. We aren't hardcoding hashes because the harness generates new, random operations dynamically per seed."
- **Action:** Execute the exact command: `python run.py --adapter adapters.ourteam:Engine --fk-policy tombstone --randomized-seeds 9999 31415 27182 16180 11235 --rand-peers 5 --rand-ops 150`
- **Script:** "We are running 5 completely random seeds with 5 peers generating 150 chaotic operations each. As you can see, every single seed evaluates to a perfect 1.00/1.00. The engine achieves perfect convergence, the vectors clocks remain bounded to O(writers) proving Anti-Pattern 3 is handled, and order-invariance is maintained."

### Segment 4: Conclusion (4:00 - 5:00)
- **Visual:** Show the `benchmark_results.md` or a quick slide summarizing compliance.
- **Script:** "In summary, we passed the 3-peer canonical trace, our 67 adversarial assertions, and the L2 multi-seed stress test flawlessly. We are fully compliant with all 4 Anti-Patterns and ready for the L3 held-out evaluation. Thank you!"
