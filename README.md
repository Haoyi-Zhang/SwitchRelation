# Proof-carrying hybrid string

This standalone repository contains a bounded operational model, an exact
universal switching theorem, a continuation-specific certificate producer and
separately structured replayer, 167 owned synthetic cases, 166 retained branch
certificates, finite cross-checks, mutation tests, and the final resource ledger.
It is an internal research artifact, not a C/LLVM frontend, SMT proof checker,
external vulnerability reproduction, or publication claim.

## Established results

For valid states in the declared language, the **full-allocation relation** keeps
object capacities, initialization bits, every initialized byte, scalar registers,
and previous emissions, while ignoring valid-cache representation,
uninitialized payload, and the bytes/string view marker.  The paper proof in
`proofs/full_abstraction.md` establishes that this relation is exactly contextual
equivalence for every well-typed continuation.  Every relation failure has a
constructively generated distinguishing continuation of at most two commands.

For a fixed pair of bounded continuations, the branch producer partitions the
finite byte domain only when execution asks an unresolved equality, unsigned
order, or fixed-mask question.  A certificate binds the complete statement,
records every feasible child, exact leaf outcomes, and regional minima.  The
separately written replayer reconstructs regions and execution, rejects omitted
or malformed structure, and recomputes exact-outcome, accepting-input, SAT, and
least-witness summaries.  Without operational caps, the mathematical procedure
terminates and is complete on the finite domain; with the delivered 6,000-node or
48-fact caps, exhaustion is `UNKNOWN`.

These are human-readable theorems plus executable finite checks.  They are not a
proof-assistant verification of Python and do not establish a correspondence from
ISO C, LLVM, or SMT-LIB string/bitvector encodings.

## Final retained evidence

The final single-worker run produced and retained certificates C001--C166 and
replayed all of them successfully:

| Quantity | Result |
|---|---:|
| Retained/replayed certificates | 166 |
| Expected labels matched | 166 |
| Equivalent / different cases | 150 / 16 |
| Nodes / leaves / infeasible children | 9,986 / 6,281 / 1,281 |
| Producer / replayer regional calls | 11,267 / 11,267 |
| Certificate bytes | 1,243,986 |

C167 was run under the formal 6,000-node and 48-fact caps.  Production stopped at
the node budget after 6,055 regional calls, so its recorded result is
`unknown_resource_exhaustion`, not equivalence or difference.

Supporting checks include:

* a two-byte primitive oracle over all 65,536 assignments, with 20 canonical
  order patterns and zero observed semantic/transport mismatches;
* a finite full-abstraction witness audit over 36 states and 1,299 ordered pairs,
  repeated in the budget-closing audit;
* 384 original and 320 fresh-seed regional instances cross-checked against brute
  force on alphabet `{0,1,2,3}`;
* two executions of the 18 parser/certificate mutations, all rejected; and
* a continuation audit that freshly replayed C001--C165, recomputed all 6,281
  stored leaf minima through three concrete execution paths, exhausted all
  one-byte cases and all seven differing two-byte cases, and sampled every case;
  and
* a final clean-extract stratified replay of C061, C062, C065, C162, and C163,
  accepting all five with 299 regional calls and five top-level checks.

The cumulative campaign counted **99,999 / 100,000** solver, mutation, and checker
obligations under the frozen rule, leaving one.  The final clean-extract replay
accounts for 304 of those obligations and 0.310 process CPU seconds. Direct
concrete assignment checks are separately disclosed: 92,810 historical, 77,050
original-final, and 480,697 continuation checks, totaling 650,557.  Original final
processes used 21.192 process CPU seconds and the continuation audit 12.685
seconds; the retained aggregate including the clean-extract replay is 34.187
seconds.  Peak RSS across the runs is 121,460 KiB.

C166 was completely generated and replayed in the original campaign.  It was not
fully replayed a second time because that would exceed the cumulative ceiling.
The continuation audit instead retained the original complete evidence and
concretely recomputed all stored leaf minima, including C166.  This distinction is
recorded in `results/final_continuation_audit.json` rather than hidden.

Machine-readable summaries are in `results/`.  The claim ledger distinguishes
proved, finite-checked, measured, and open claims; `results/reference_audit.csv`
records all 48 cited references, persistent identifiers, verification scope, and
role in the paper.

## Reproduction commands

The scientific run has already been completed for this campaign.  Re-running it
consumes new obligations and must be accounted for rather than silently resetting
the 100,000 ceiling.  With a separately authorized fresh campaign, from this
repository root run:

```sh
python reproduce.py --region-instances 384
python run_fanout_control.py
python src/final_audit.py --output results/final_continuation_audit.json
```

`reproduce.py` uses only the Python standard library.  It binds execution to one
CPU, requests a 2.5 GiB address-space limit, installs 110/115-second soft/hard CPU
limits and a 118-second wall alarm, regenerates the 167 case schemas, writes the
166 completed certificates atomically, replays them, runs the finite oracles and
mutation suite, and refuses a campaign whose precomputed worst-case reservation
would exceed the cumulative ceiling.  `run_fanout_control.py` performs the
separately guarded C167 cap test.  `src/final_audit.py` implements the retained
8,608-obligation continuation audit. `src/final_clean_extract_audit.py` documents
the already executed 304-obligation clean-extract replay and must not be rerun
under this ledger. These scientific commands exceed the single obligation left in
the closed campaign and therefore belong to a separately accounted future run,
not to packaging verification.

For packaging-only inspection, which does not execute research modules:

```sh
python inspect_packet.py
```

It parses every source file, validates all case identifiers, checks C001--C166
certificate presence and certificate/result consistency, parses all result JSON,
checks the claim/resource ledgers, and reports the retained campaign totals.  A
successful packet inspection is not itself a semantic proof.

To replay one retained certificate without producing a new one:

```sh
python src/branch_replay.py cases/C135.json certificates/branch/C135.json
```

This is a checker execution and should be counted as a new checker obligation in
any renewed campaign.

## Repository map

* `src/contextual.py` and `src/check_full_abstraction.py`: exact state relation,
  constructive witnesses, and finite witness audit.
* `src/order_domain.py` and `src/branch_producer.py`: producer-side region solver
  and complete branch-tree construction.
* `src/branch_replay.py`: separately structured region reconstruction,
  interpreter, and fail-closed certificate checker.
* `src/check_regions.py`: deterministic brute-force regional cross-check.
* `src/check_mutations.py`: parser and structural certificate attacks.
* `src/final_audit.py`: budget-aware fresh replay, regional cross-check, direct
  concrete audit, and repeated mutation suite.
* `src/final_clean_extract_audit.py`: predeclared five-certificate clean-extract
  stratified replay retained as the final 304 counted obligations.
* `src/primitive_oracle.py`: direct two-byte exhaustive pilot.
* `cases/`: deterministic owned schemas C001--C167.
* `certificates/branch/`: retained certificates C001--C166.
* `proofs/`: normative semantics and paper proofs.
* `results/`: final summaries, resource accounting, continuation and clean-extract
  audits, and 48-entry reference metadata/integrity audits.
* `claim_evidence_ledger.csv`: material claims and maturity.
* `external_resources.csv`: cited external resources, licenses, and integration.

## Trust boundary and non-claims

The producer and replayer use different region-solving and interpreter code, but
both run on the same ordinary Python implementation and were not independently
implemented by different research groups.  Source validation, exact JSON parsing,
and mutation rejection reduce accidental trust; they do not make the checker
formally verified or hardened as an untrusted-input service.

All cases are synthetic and owned.  No SymCC, KLEE, cvc5, Ethos, external solver,
real service, or target application was executed.  The artifact does not claim
solver-performance superiority, unbounded completeness, whole-program coverage,
security of deployed code, or a defect in an external tool.

AI assistance was substantive in research design, semantics, proofs, code,
experiments, analysis, validation, and writing.  Any external use requires the
human authors to inspect the full evidence, make demonstrable intellectual
contributions, accept responsibility for the claims, and comply with the current
venue and ACM authorship/AI-use policies.  No faculty participation, independent
review, publication, or acceptance is asserted.


## Reviewer-facing audit surfaces

- `REVIEWER-AUDIT.md`: closed issues and irreducible external risks.
- `TRUSTED-COMPUTING-BASE.md`: what accepted replay trusts and excludes.
- `ASSUMPTION-DEPENDENCY.md`: theorem/assumption matrix.
- `SPEC-CODE-MAP.csv`: formal-object to source-symbol traceability.
- `SUBMISSION-CHECKLIST.md`: technical closure versus human venue actions.
- `src/structural_audit.py`: fail-closed static audit and strict certificate preflight.
- `tests/test_strict_json.py`: hostile-JSON regression tests.
