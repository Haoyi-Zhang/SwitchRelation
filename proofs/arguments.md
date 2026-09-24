# Mathematical arguments and certificate metatheory

This file collects the proof obligations used by the paper.  Section 1 points to
the exact universal-switch theorem.  Sections 2--6 justify the finite region
certificate for one fixed continuation.  Section 7 states the limits of the
argument.  These are human-readable proofs, supported by executable finite
checks; no claim of proof-assistant mechanization is made.

## 1. Universal switches

The exact universal relation and its constructive converse are proved in
`full_abstraction.md`:

* allocation equivalence retains capacity, initialization, every initialized
  byte, scalar registers, and previous emissions, while quotienting valid cache
  representation, uninitialized payload, and the view marker;
* allocation equivalence is preserved by every correct primitive;
* it is exactly contextual equivalence for all continuations in the declared
  language; and
* any relation failure has a distinguishing continuation of at most two commands.

The `[0,x,0]` example shows why the initialized tail after the first NUL cannot be
discarded by a universal switch.

## 2. Finite regions for one continuation

Fix input variables `V={v1,...,vm}` ranging over `B={0,...,255}`.  A regional
fact is either

```
cmp(a,r,b)       where r is one of <, =, >
unary(a,M,E,t)   where t is 0 or 1 and denotes ((a & M) == E) == t
```

and `a,b` are input origins or byte literals.  Literals are singleton domains.
For each equality class of origins, a region stores an allowed byte set and a
lower/upper interval induced by order constraints.  Equalities contract
vertices; strict comparisons produce directed edges.

**Lemma 1 (origin support).**  Every byte read during execution is either a byte
literal in the program or the value of one declared input origin.

**Proof.**  Initially the claim holds by the case grammar.  The only byte writes
copy a previously read origin or write a literal.  String copy, concatenation,
and snapshot move only copy bytes.  No scalar-to-byte cast exists.  Induction on
commands proves the claim.  QED.

**Lemma 2 (regional satisfiability).**  After equality contraction, a fact set is
satisfiable exactly when (i) each class has a nonempty allowed set, (ii) no strict
edge lies within a class, and (iii) the strict-order graph is acyclic and admits
values from the classes' allowed sets that increase along every edge.

**Proof.**  Necessity is immediate.  For sufficiency, process the acyclic graph
in a topological order.  The least feasible value of a vertex is the least
allowed value strictly above the maximum assigned predecessor.  If this greedy
choice fails, any other assignment must choose a value at least as large at the
first failing vertex and also fails.  If it succeeds, all equalities, unary
membership restrictions, and strict edges are satisfied.  QED.

`src/order_domain.py` and `src/branch_replay.py` deliberately implement this
reasoning differently: the producer propagates interval/allowed-set bounds over
contracted components, while the replayer reconstructs its own region and greedy
minimum.  Their shared mathematical specification does not make either Python
implementation formally verified.

**Lemma 3 (least regional assignment).**  For every satisfiable region, the
greedy topological construction returns the coordinatewise least assignment in
declared input order among assignments satisfying that region.

**Proof.**  Equality contraction fixes equal variables together.  Consider the
first component, in the replayer's deterministic topological/tie order, where a
satisfying assignment is smaller than the greedy result.  All predecessor values
are at least their greedy values by minimality of the first difference.  The
supposed smaller value is therefore either outside the component's allowed set or
not strictly above a predecessor, contradicting satisfaction.  Expanding equal
components and reading variables in declared order yields the least input tuple.
QED.

The coordinatewise statement is stronger than needed for a lexicographic
minimum.  Deterministic variable order handles incomparable components.

## 3. Region-uniform execution

Execution carries origins instead of selecting concrete byte values.  When a
command needs an unresolved fact, the producer creates a split node: three
children for comparison (`<,=,>`) or two for a unary predicate (`false,true`).
Infeasible choices are represented by a null child.  A leaf is reached only when
both programs execute without asking an unresolved byte question.

**Lemma 4 (partition).**  The feasible children of a split are pairwise disjoint
and their union is the parent region.

**Proof.**  Trichotomy partitions every pair of bytes into exactly one of `<,=,>`.
A Boolean unary test has exactly one truth value.  Conjoining the corresponding
fact therefore makes children disjoint and covers every parent assignment.
Removing unsatisfiable children removes no concrete assignment.  QED.

**Lemma 5 (uniform leaf).**  At a completed leaf, every concrete input satisfying
the leaf facts gives the exact left and right outcomes recorded at that leaf.

**Proof.**  Induct over each interpreter step.  Lemma 1 ensures every byte is an
origin or literal.  A branch-dependent byte comparison or unary test would have
raised an unresolved question unless the current region entailed its answer.
All scalar operations, offsets, scan orders, faults, writes, and emissions are
then deterministic functions of already fixed answers.  Thus all inputs in the
region follow the same operational trace and outcome.  QED.

The lemma is about exact outcomes, including fault tags and prior emissions.  It
therefore also supports the weaker accepting-input and satisfiability summaries,
but those summaries are not interchangeable with whole-outcome equivalence.

## 4. Certificate replay

A branch certificate contains the complete source statement, a node array, the
overall whole-outcome verdict and least disagreement input, node/leaf/closed
counts, maximum facts on a branch, and a separate feasibility summary.  A leaf
stores the exact two operational outcomes and the least input of its region.  A
split stores the unresolved query, its ordered choices, and one child reference
or null for each choice.

The replayer validates strict JSON types and duplicate-key/nonfinite-number
rejection before checking the certificate.  It validates source binding, budgets,
node references, acyclicity-by-single-visit, reachability of every node, each split
query and feasible partition, each leaf execution, each leaf minimum, aggregate
counts, whole-outcome verdict, acceptance-set verdict, and each least witness.

**Theorem 6 (accepted-certificate soundness).**  If the replayer accepts a
certificate with verdict `equivalent`, then the two programs have equal exact
outcomes for every one of the `256^m` input assignments.  If it accepts verdict
`different` with witness `w`, then `w` is the lexicographically least assignment
with unequal exact outcomes.

**Proof.**  Starting from the full root region, repeated application of Lemma 4
shows that accepted leaves are pairwise disjoint and cover the whole input
domain.  The single-visit and reachability checks prevent cycles, sharing, or
unexamined nodes.  Lemma 5 makes each recorded leaf result valid for every input
in that leaf.  If no leaf differs, all inputs agree.  Otherwise Lemma 3 makes each
recorded leaf minimum the least input in that leaf; the lexicographic minimum of
all differing leaf minima is therefore the least element of the union of
all differing leaves.  The replayer recomputes that minimum and compares it with
the certificate.  QED.

**Corollary 7 (acceptance and SAT summaries).**  The separately replayed
feasibility field exactly reports whether each program has at least one accepting
input, whether their accepting-input sets are equal, and the least input on which
acceptance differs.

**Proof.**  By coverage and uniformity, a program accepts some input exactly when
an accepted leaf records `accept` for that side.  Acceptance sets differ exactly
when some leaf has different acceptance tags.  Apply Lemma 3 and the minimum-of-a
finite-union argument.  QED.

## 5. Termination and completeness without operational caps

The mathematical procedure chooses the first unresolved question in a
deterministic execution.  It creates only feasible strict subregions.  Operational
caps (6,000 nodes and 48 branch facts) are omitted in this section.

**Lemma 8 (strict progress).**  Every split has at least two nonempty feasible
children and each feasible child is a strict subset of its parent.

**Proof.**  A split is raised only when the current region does not entail one
answer.  If only one choice were feasible, that answer would be entailed and no
split would be raised.  Distinct comparison/truth choices are disjoint by Lemma 4,
so conjoining any one removes assignments belonging to the other feasible child.
QED.

**Theorem 9 (finite termination).**  For `m` byte variables, uncapped production
terminates after at most `256^m` leaves and at most `2*256^m-1` nodes.

**Proof.**  By Lemma 4, leaves are disjoint nonempty subsets of a root containing
`256^m` assignments, hence there are at most `256^m` leaves.  By Lemma 8 every
internal node has at least two children.  In any finite rooted tree with `L`
leaves and internal out-degree at least two, the number of internal nodes is at
most `L-1`, so total nodes are at most `2L-1`.  A path cannot split forever: each
split strictly decreases the finite number of assignments in its region.  QED.

**Theorem 10 (uncapped decision completeness).**  On every admitted finite case,
the uncapped producer returns a certificate, and an accepted replay decides exact
outcome equivalence, accepting-input equality, and satisfiability on the full
byte domain.

**Proof.**  Theorem 9 gives termination.  At every nonuniform region, deterministic
symbolic execution reaches a first unresolved byte question and Lemma 4 supplies
a complete split.  Regions on which no question remains are leaves by Lemma 5.
The resulting finite tree covers the root.  The producer serializes exactly that
tree, and Theorem 6 and Corollary 7 establish the three decisions after replay.
QED.

This is a completeness theorem for the declared finite language and the abstract
uncapped algorithm.  It is not a useful polynomial complexity bound: the upper
bound is exponential in the number of byte inputs.

## 6. Operational caps and final measurements

The delivered producer enforces at most 6,000 nodes and at most 48 regional facts
per branch.  Hitting either cap raises a rejection that the wrapper records as
`UNKNOWN`; no partial tree is replayed or reported as equivalence.

The final single-worker run retained certificates for C001--C166.  The replayer
accepted all 166, with 9,986 total nodes, 6,281 leaves, and 1,281 infeasible
children.  The expected labels matched for 150 equivalent and 16 different
cases.  Production used 11,267 regional-solver calls and replay used another
11,267.  Including top-level checks, the branch campaign counted 22,866 capped
obligations.

C167 is a 32-origin high-fanout negative control.  Under the formal 6,000-node and
48-fact caps, production stopped at the node budget after 6,055 regional-solver
calls and was recorded as `unknown_resource_exhaustion`.  It is not counted as
equivalent or different.

A separately written brute-force oracle over alphabet `{0,1,2,3}` checked 384
region instances, 11,292 concrete assignments, and 5,947 pairwise relation facts;
it found no disagreement with either regional solver.  A mutation suite performed
18 parser/certificate attacks, all rejected.  These are finite checks and do not
prove arbitrary Python execution.

The original completion campaign reached 91,087 solver/mutation/checker
obligations.  A budget-closing continuation audit added 8,608 obligations: it
rematerialized all cases, repeated the full-abstraction audit, checked 320 fresh
regions, freshly replayed C001--C165, and repeated all 18 mutations.  A final
predeclared clean-extract audit replayed C061, C062, C065, C162, and C163 using 299
regional calls and five top-level checks, adding 304 obligations.  The cumulative
count is therefore 99,999 of 100,000, leaving one.  Direct concrete assignment
checks are disclosed separately: 92,810 historical, 77,050 original-final, and
480,697 continuation checks, totaling 650,557.

C166 retains its original complete production and replay evidence.  A second full
replay was excluded because it would exceed the ceiling; instead, the continuation
audit concretely recomputed all 6,281 stored leaf minima through three execution
paths, including C166, and performed exhaustive one-byte and selected two-byte
checks.  This does not convert the continuation into a second complete regional
replay of C166.

Retained scientific runs used one worker.  Original final processes including
C167 used 21.192 process CPU seconds, the continuation audit used 12.685, and the
clean-extract replay used 0.310, for an aggregate of 34.187 seconds.  Peak RSS
across runs is 121,460 KiB.

## 7. Boundary of the proof

The completed argument does **not** prove:

1. a C/LLVM frontend-to-model correspondence;
2. a correspondence between SMT string/bitvector formulas and this model;
3. a proof-assistant theorem about the Python implementation;
4. completeness after either operational cap is hit;
5. solver-performance dominance or whole-program coverage;
6. a defect in any external library or symbolic executor; or
7. independent human review.

The scientific result is a bounded semantic theorem plus a finite, independently
structured producer/replayer artifact.  Any external submission would still need
human authors to verify the work, accept accountability, and satisfy the venue's
current authorship and AI-use policies.
