"""Executable witness basis for the full-allocation state relation.

The paper proves a theorem about all well-typed continuations in the declared
language.  This module does not replace that proof.  It implements the theorem's
state relation and its constructive *necessity* direction: whenever two valid
states with the same static interface violate the relation, it returns a common
continuation of at most two commands whose observable outcomes differ.

A state keeps physical payload bytes even for uninitialized cells.  The relation
intentionally ignores those payloads, cache representation, and the current view.
Those components are not observable in the declared semantics when cache entries
are valid.  Fault kinds and the emitted integer sequence are observable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


class StateError(ValueError):
    """The supplied state is outside the theorem's valid-state precondition."""


@dataclass(frozen=True)
class ObjectState:
    payload: tuple[int, ...]
    initialized: tuple[bool, ...]

    def __post_init__(self) -> None:
        if not self.payload or len(self.payload) > 64:
            raise StateError("object capacity")
        if len(self.payload) != len(self.initialized):
            raise StateError("payload/initialization length")
        if any(type(value) is not int or not 0 <= value < 256 for value in self.payload):
            raise StateError("byte payload")
        if any(type(flag) is not bool for flag in self.initialized):
            raise StateError("initialization flag")


@dataclass(frozen=True)
class State:
    objects: Mapping[str, ObjectState]
    scalars: Mapping[str, int]
    emitted: tuple[int, ...] = ()
    cache: Mapping[tuple[str, int], int] | None = None
    view: str = "bytes"

    def __post_init__(self) -> None:
        if not self.objects or len(self.objects) > 4:
            raise StateError("object count")
        if any(not isinstance(name, str) or not name.isidentifier() for name in self.objects):
            raise StateError("object name")
        if any(not isinstance(name, str) or not name.isidentifier() for name in self.scalars):
            raise StateError("scalar name")
        if any(type(value) is not int for value in self.scalars.values()):
            raise StateError("scalar value")
        if any(type(value) is not int for value in self.emitted):
            raise StateError("emitted value")
        if self.view not in {"bytes", "string"}:
            raise StateError("view")
        if not valid_cache(self):
            raise StateError("invalid cache")


def logical_strlen(state: State, name: str, offset: int) -> int:
    """Return the declared length or raise StateError for a faulting scan."""
    if name not in state.objects:
        raise StateError("unknown object")
    obj = state.objects[name]
    if type(offset) is not int or not 0 <= offset < len(obj.payload):
        raise StateError("bounds")
    for index in range(offset, len(obj.payload)):
        if not obj.initialized[index]:
            raise StateError("uninitialized")
        if obj.payload[index] == 0:
            return index - offset
    raise StateError("unterminated")


def valid_cache(state: State) -> bool:
    """Every materialized cache entry denotes the logical length in that state."""
    cache = {} if state.cache is None else state.cache
    if not isinstance(cache, Mapping):
        return False
    for key, value in cache.items():
        if (
            not isinstance(key, tuple)
            or len(key) != 2
            or not isinstance(key[0], str)
            or type(key[1]) is not int
            or type(value) is not int
        ):
            return False
        try:
            if logical_strlen_unchecked(state.objects, key[0], key[1]) != value:
                return False
        except StateError:
            return False
    return True


def logical_strlen_unchecked(objects: Mapping[str, ObjectState], name: str, offset: int) -> int:
    if name not in objects:
        raise StateError("unknown object")
    obj = objects[name]
    if not 0 <= offset < len(obj.payload):
        raise StateError("bounds")
    for index in range(offset, len(obj.payload)):
        if not obj.initialized[index]:
            raise StateError("uninitialized")
        if obj.payload[index] == 0:
            return index - offset
    raise StateError("unterminated")


def same_interface(left: State, right: State) -> bool:
    """The full-abstraction theorem fixes object and scalar namespaces."""
    return set(left.objects) == set(right.objects) and set(left.scalars) == set(right.scalars)


def allocation_equivalent(left: State, right: State) -> bool:
    """Exact universal switch relation from the paper.

    The relation compares the complete allocation interface, initialization map,
    all initialized bytes, scalar store, and already emitted observations.  It
    deliberately quotients valid cache contents, uninitialized payloads, and view.
    """
    if not same_interface(left, right):
        return False
    if left.scalars != right.scalars or left.emitted != right.emitted:
        return False
    for name in sorted(left.objects):
        a, b = left.objects[name], right.objects[name]
        if len(a.payload) != len(b.payload) or a.initialized != b.initialized:
            return False
        for index, initialized in enumerate(a.initialized):
            if initialized and a.payload[index] != b.payload[index]:
                return False
    return True


def distinguishing_continuation(left: State, right: State) -> list[dict[str, Any]] | None:
    """Construct a <=2-command distinguishing continuation, or ``None``.

    Both states must satisfy the valid-cache invariant and use the same object and
    scalar namespaces.  If the relation fails, the returned program distinguishes
    exact terminal outcomes under :func:`run_basis_continuation`.
    """
    if not same_interface(left, right):
        raise StateError("static interface mismatch")
    if allocation_equivalent(left, right):
        return None
    if left.emitted != right.emitted:
        return []
    for name in sorted(left.scalars):
        if left.scalars[name] != right.scalars[name]:
            return [{"op": "emit", "value": f"${name}"}]
    for name in sorted(left.objects):
        a, b = left.objects[name], right.objects[name]
        if len(a.payload) != len(b.payload):
            offset = min(len(a.payload), len(b.payload))
            return _probe(name, offset, 0)
        for offset, (ia, ib) in enumerate(zip(a.initialized, b.initialized)):
            if ia != ib:
                return _probe(name, offset, 0)
        for offset, initialized in enumerate(a.initialized):
            if initialized and a.payload[offset] != b.payload[offset]:
                return _probe(name, offset, a.payload[offset])
    raise AssertionError("relation mismatch without a distinguishing component")


def _probe(name: str, offset: int, constant: int) -> list[dict[str, Any]]:
    return [
        {
            "op": "byte_eq",
            "left": {"read": [name, offset]},
            "right": constant,
            "out": "witness_bit",
        },
        {"op": "emit", "value": "$witness_bit"},
    ]


def run_basis_continuation(state: State, program: Sequence[Mapping[str, Any]]) -> list[Any]:
    """Execute the witness basis and return the paper's exact observable outcome.

    This tiny interpreter intentionally accepts only the commands needed by the
    constructive converse: ``byte_eq`` and ``emit``.  The sufficiency proof for the
    full language is in ``proofs/full_abstraction.md``.
    """
    registers = dict(state.scalars)
    emitted = list(state.emitted)

    def scalar(value: Any) -> int:
        if type(value) is int:
            return value
        if isinstance(value, str) and value.startswith("$") and value[1:] in registers:
            return registers[value[1:]]
        raise StateError("scalar expression")

    def byte(value: Any) -> int:
        if type(value) is int and 0 <= value < 256:
            return value
        if isinstance(value, Mapping) and set(value) == {"read"}:
            read = value["read"]
            if not isinstance(read, list) or len(read) != 2:
                raise StateError("read expression")
            name, offset_expr = read
            offset = scalar(offset_expr)
            if name not in state.objects:
                raise StateError("unknown object")
            obj = state.objects[name]
            if not 0 <= offset < len(obj.payload):
                raise RuntimeError("bounds")
            if not obj.initialized[offset]:
                raise RuntimeError("uninitialized")
            return obj.payload[offset]
        raise StateError("byte expression")

    try:
        for command in program:
            if not isinstance(command, Mapping) or "op" not in command:
                raise StateError("command")
            if command["op"] == "byte_eq":
                if set(command) != {"op", "left", "right", "out"}:
                    raise StateError("byte_eq fields")
                out = command["out"]
                if not isinstance(out, str) or not out.isidentifier():
                    raise StateError("output register")
                registers[out] = int(byte(command["left"]) == byte(command["right"]))
            elif command["op"] == "emit":
                if set(command) != {"op", "value"}:
                    raise StateError("emit fields")
                emitted.append(scalar(command["value"]))
            else:
                raise StateError("unsupported witness command")
        return ["accept", emitted]
    except RuntimeError as error:
        return ["fault", str(error), emitted]


def verify_constructive_converse(left: State, right: State) -> bool:
    """Check the executable necessity witness for one valid state pair."""
    witness = distinguishing_continuation(left, right)
    if witness is None:
        return allocation_equivalent(left, right)
    return run_basis_continuation(left, witness) != run_basis_continuation(right, witness)
