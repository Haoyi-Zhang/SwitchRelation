# Exact switching relation for the declared bounded language

This document states the central semantic result independently of the Python
implementation.  It is a paper proof over the operational model in
`semantics.md`; it is not a proof-assistant development and it does not establish
a correspondence from ISO C, LLVM, SMT-LIB strings, or any external executor.
The executable file `src/check_full_abstraction.py` checks the constructive
converse on a finite state family, but that finite check is supporting evidence,
not the proof of the general theorem below.

## 1. Valid states and observations

Fix a static interface consisting of a finite object-name set and a finite
scalar-register set.  Every object has a positive fixed capacity.  A state
contains, for every object and index, a payload byte and a separate initialized
bit; a scalar store; a sequence of integers already emitted; a partial
object/offset length cache; and a current representation marker (`bytes` or
`string`).  The physical payload of an uninitialized cell exists in the
mathematical record but cannot be read by any command.

A state is **valid** when every materialized cache entry is the length returned
by the declared terminator scan in that state.  A write invalidates every cache
entry whose base object is written.  The representation marker has no direct
operational effect.  Terminal observations are exact outcomes:

* `accept` together with the complete emitted sequence;
* `reject` together with the complete emitted sequence; or
* `fault(tag)` together with the complete emitted sequence, where `tag` is one
  of `bounds`, `uninitialized`, `unterminated`, or `overlap`.

Different fault tags are observable.  This makes the necessity direction
stronger and avoids equating two states merely because both executions fail.

For a well-typed finite continuation `K`, let `Obs(K, sigma)` be its exact
terminal observation when started in valid state `sigma`.  The language is
bounded and straight-line, so evaluation is deterministic and terminates.

## 2. Allocation equivalence

For valid states `sigma` and `tau` with the same object and scalar namespaces,
define **allocation equivalence**, written `sigma ~=A tau`, by all of the
following clauses.

1. Corresponding objects have equal capacities.
2. Corresponding cells have equal initialized bits.
3. Whenever a corresponding cell is initialized, its byte is equal in the two
   states.  Payloads of cells uninitialized in both states are ignored.
4. Corresponding scalar registers contain equal integers.
5. The already emitted integer sequences are equal.
6. The cache maps need not be equal, provided both caches are valid.
7. The representation markers need not be equal.

Thus `~=A` retains the complete observable allocation, including initialized
data after the first NUL.  It quotients only valid cache representation,
uninitialized payload, and the view marker.

Define contextual equivalence by

```
sigma ~=ctx tau  iff  for every well-typed continuation K,
                       Obs(K,sigma) = Obs(K,tau).
```

The quantified continuations may read or write any object allowed by the fixed
interface and may emit scalar values.  This is a universal switching guarantee,
not equivalence for one selected continuation.

## 3. Primitive preservation lemma

**Lemma 1 (expression agreement).**  If `sigma ~=A tau`, corresponding scalar
expressions evaluate to the same integer.  Corresponding readable byte
expressions either return the same byte or produce the same exact fault.

**Proof.**  Scalar constants and registers agree directly.  Scalar operators are
deterministic total functions of equal operands.  For a byte read, equal scalar
offsets and equal capacities give the same bounds result.  Equal initialized
bits give the same initialization result.  If the read succeeds, the cell is
initialized in both states and clause 3 gives the same byte.  Byte literals are
identical.  QED.

**Lemma 2 (scan agreement).**  If `sigma ~=A tau`, corresponding terminator
scans either return the same absolute index or produce the same exact fault.

**Proof.**  The starting offset agrees by Lemma 1.  Equal capacities give the
same bounds decision.  The scan then visits the same indices in the same order.
At each index, the initialized bits agree and, when initialized, the bytes agree.
Consequently the first zero is at the same index; otherwise the same first
uninitialized cell faults or both scans exhaust the object and report
`unterminated`.  QED.

**Lemma 3 (cache transparency).**  In valid states related by `~=A`, a cached
and an uncached length query return the same scalar or the same fault.  After any
ordinary write, the resulting caches remain valid and may still differ without
breaking `~=A`.

**Proof.**  Every materialized cache entry equals the logical scan length by the
valid-state invariant.  If one side hits and the other misses, Lemma 2 gives the
same logical length.  A write removes all entries on the written base object;
entries for other objects remain valid because distinct base objects do not
alias and those objects are unchanged.  QED.

**Lemma 4 (one-command simulation).**  Let `c` be any declared correct command.
If `sigma ~=A tau`, then executing `c` in both states gives the same terminal
observation, or gives successor states `sigma' ~=A tau'` and the same program
counter.

**Proof.**  Case analysis on `c`.

* Length, search, and comparison operations use the same scans, byte reads, and
  byte comparisons by Lemmas 1--3.  Normalized results therefore agree.
* A store evaluates its source first on both sides, obtains the same byte or the
  same fault, performs the same span check, writes equal bytes to equal indices,
  and invalidates the corresponding base-object caches.
* `memmove` validates the same spans, reads the same snapshot, and writes that
  snapshot to the same destination cells.  The snapshot rule handles overlap.
* `strcpy` and `strcat` find the same source and destination terminators, perform
  the same overlap and capacity decisions, and copy the same initialized bytes,
  including the source terminator.  If a precondition fails, the exact fault is
  equal because the prescribed access order is the same.
* `switch` changes only the representation marker, which `~=A` quotients.
* Byte predicates ask the same equality, unsigned-order, or fixed-mask question
  of equal bytes, so their Boolean results agree.  Scalar predicates and modular
  scalar operations are deterministic on equal scalar operands.
* `assume` takes the same decision.  `emit` appends the same integer to equal
  emitted sequences.

Every successful write preserves equal capacities, initialized maps, and bytes
at initialized cells; all untouched components remain related.  QED.

The intentionally faulty alternatives (`erase_tail`, stale cache, signed compare,
etc.) are not included in Lemma 4.  They are candidate transformations tested by
the certificate system, not operations whose correctness is assumed.

## 4. Sufficiency

**Theorem 5 (universal preservation).**  If `sigma ~=A tau`, then
`sigma ~=ctx tau`.

**Proof.**  Induct on the command sequence of an arbitrary well-typed
continuation.  The empty continuation observes equal pre-existing emissions and
accepts.  For a nonempty continuation, Lemma 4 gives either an equal terminal
observation or related successor states.  Apply the induction hypothesis to the
remaining commands.  Because the continuation was arbitrary, all observations
agree.  QED.

## 5. Constructive necessity

The converse is constructive.  Whenever `~=A` fails under a common static
interface, a continuation of at most two commands distinguishes the states.
The commands used are only `byte_eq` and `emit`; an empty continuation is also
allowed.  The construction is deterministic after choosing the first differing
component in object/register order.

**Lemma 6 (two-command witness basis).**  Let `sigma` and `tau` be valid states
with the same object and scalar namespaces.  If `sigma` is not allocation
-equivalent to `tau`, then there is a well-typed continuation `K` with at most
two commands such that `Obs(K,sigma) != Obs(K,tau)`.

**Proof.**  Exhaust the defining clauses of `~=A`.

1. If the already emitted sequences differ, choose the empty continuation.  Its
   accepting observations retain those different sequences.
2. Otherwise, if scalar register `r` differs, choose `emit r`.  The final emitted
   sequences differ.
3. Otherwise, some corresponding object capacities differ.  Let `i` be the
   smaller capacity and execute `b := (object[i] == 0); emit b`.  The smaller
   state faults `bounds`.  The larger state either reads and accepts or faults
   `uninitialized`; both observations differ from `bounds`.
4. Otherwise capacities agree but an initialized bit differs at index `i`.
   The same probe faults `uninitialized` on exactly one side and reaches `emit`
   on the other.
5. Otherwise initialized maps agree but initialized bytes differ at index `i`.
   Let the left byte be literal `v` and execute
   `b := (object[i] == v); emit b`.  The left emits 1 and the right emits 0.

The earlier cases have ruled out unequal scalars and emissions.  Cache maps and
view markers are not relation failures.  Payload differences at cells
uninitialized in both states are not relation failures either.  Therefore these
cases are exhaustive.  QED.

**Corollary 7 (full abstraction and exactness).**  For valid states with a
common static interface,

```
sigma ~=A tau  iff  sigma ~=ctx tau.
```

Moreover, every failure of `~=A` has a distinguishing continuation of length at
most two.

**Proof.**  The forward implication is Theorem 5.  The reverse implication is
the contrapositive of Lemma 6.  QED.

The theorem makes `~=A` both sufficient and necessary for switching safely when
the future continuation is unknown.  No strictly coarser state relation can be
a universal switch relation for this language, because every omitted component
has the witness above.

## 6. Why a NUL prefix is insufficient

Consider capacity-three states whose initialized allocation is `[0,x,0]`.
A representation that retains only the string prefix through the first NUL maps
every value of `x` to the same visible empty string.  Continue with

```
store object[0] := 1;
emit strlen(object,0);
```

For `x=0`, the result is 1.  For `x!=0`, the result is 2.  A transformation that
erases the tail after switching forces the result to 1 for every input.  Thus a
prefix relation is not preserved by arbitrary continuations.  This example does
not refute a continuation-specific abstraction whose selected continuation
provably never exposes the tail; it separates universal and fixed-continuation
contracts.

## 7. Executable audit and its scope

`src/contextual.py` implements `~=A` and the constructive witness function.
`src/check_full_abstraction.py` generated 36 valid small states and checked 1,299
ordered state-pair obligations.  It found 37 related pairs and 1,262 relation
failures; all failures were distinguished by the returned continuation, with
maximum length two.  The audit executed 222 finite basis continuations after
symmetry and early structural classification.

This finite audit checks the implementation of the witness construction on the
selected family.  It does not quantify over every state, every capacity up to 64,
or every continuation.  Those quantifiers are discharged only by the paper
argument above, whose trust base includes ordinary mathematical reasoning and the
accuracy of the declared operational model.
