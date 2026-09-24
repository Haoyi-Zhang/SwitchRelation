# Assumption-to-claim dependency

| Assumption | Required by | Failure mode when changed |
|---|---|---|
| Finite capacities and input domains | finite test basis; termination/completeness of unlimited partitioning | infinite search requires a different argument |
| Observable labeled faults | converse separators; terminal summaries | coarser faults induce a coarser equivalence |
| Final heap is not directly observed | quotient of uninitialized payload; short separators | heap observation makes physical payload relevant |
| Persistent registers are distinct from local temporaries | fixed-interface theorem; constructive witnesses | fresh proof names would silently change the interface |
| Valid cache invariant | cache representation quotient | stale caches can create observable differences |
| Deterministic primitive semantics | functional summaries; least witness | nondeterminism requires trace/set semantics |
| Fail-closed limits and parsing | executable acceptance contract | fail-open behavior would invalidate soundness |
