"""Deterministic finite audit of the full-abstraction witness constructor.

This is a bounded executable check, not the general proof.  It enumerates a small
state universe, checks every ordered pair, and verifies all generated separating
contexts by direct execution.  Equivalent pairs are also checked against a finite
observation basis (empty context, scalar emission, and every one-cell byte probe).
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Iterable

from contextual import (
    ObjectState,
    State,
    allocation_equivalent,
    distinguishing_continuation,
    run_basis_continuation,
)


def states() -> list[State]:
    result: list[State] = []
    # Logical two-byte states over {0,1}; payloads of uninitialized cells use 0.
    for flags in itertools.product((False, True), repeat=2):
        initialized_positions = [index for index, flag in enumerate(flags) if flag]
        for values in itertools.product((0, 1), repeat=len(initialized_positions)):
            payload = [0, 0]
            for index, value in zip(initialized_positions, values):
                payload[index] = value
            obj = ObjectState(tuple(payload), tuple(flags))
            for scalar in (0, 1):
                for emitted in ((), (0,)):
                    result.append(State({"b": obj}, {"r": scalar}, emitted, {}, "bytes"))
    return result


def basis() -> Iterable[list[dict]]:
    yield []
    yield [{"op": "emit", "value": "$r"}]
    for offset in range(2):
        for constant in (0, 1):
            yield [
                {
                    "op": "byte_eq",
                    "left": {"read": ["b", offset]},
                    "right": constant,
                    "out": "z",
                },
                {"op": "emit", "value": "$z"},
            ]


def run() -> dict:
    universe = states()
    pairs = 0
    equivalent_pairs = 0
    differing_pairs = 0
    empty_witnesses = 0
    one_command_witnesses = 0
    two_command_witnesses = 0
    basis_executions = 0
    for left in universe:
        for right in universe:
            pairs += 1
            equivalent = allocation_equivalent(left, right)
            witness = distinguishing_continuation(left, right)
            if equivalent:
                equivalent_pairs += 1
                if witness is not None:
                    raise AssertionError("equivalent pair received a witness")
                for continuation in basis():
                    basis_executions += 1
                    if run_basis_continuation(left, continuation) != run_basis_continuation(right, continuation):
                        raise AssertionError("finite basis distinguishes related states")
            else:
                differing_pairs += 1
                if witness is None:
                    raise AssertionError("unrelated pair has no witness")
                if len(witness) == 0:
                    empty_witnesses += 1
                elif len(witness) == 1:
                    one_command_witnesses += 1
                elif len(witness) == 2:
                    two_command_witnesses += 1
                else:
                    raise AssertionError("witness length bound")
                if run_basis_continuation(left, witness) == run_basis_continuation(right, witness):
                    raise AssertionError("generated continuation does not distinguish")
    # Explicitly exercise capacity and initialization mismatches, absent from the
    # fixed-capacity universe, plus the components deliberately quotiented by the
    # relation: view, valid cache representation, and uninitialized payload.
    extra = []
    base = State({"b": ObjectState((0,), (True,))}, {"r": 0})
    extra.append((base, State({"b": ObjectState((0, 0), (True, True))}, {"r": 0})))
    extra.append((base, State({"b": ObjectState((0,), (False,))}, {"r": 0})))
    for left, right in extra:
        pairs += 1
        differing_pairs += 1
        witness = distinguishing_continuation(left, right)
        if witness is None or len(witness) > 2:
            raise AssertionError("missing explicit structural witness")
        if run_basis_continuation(left, witness) == run_basis_continuation(right, witness):
            raise AssertionError("structural witness does not distinguish")
        two_command_witnesses += 1
    related_extras = [
        (
            State({"b": ObjectState((0, 9), (True, False))}, {"r": 0}, (), {("b", 0): 0}, "bytes"),
            State({"b": ObjectState((0, 200), (True, False))}, {"r": 0}, (), {}, "string"),
        )
    ]
    for left, right in related_extras:
        pairs += 1
        equivalent_pairs += 1
        if not allocation_equivalent(left, right) or distinguishing_continuation(left, right) is not None:
            raise AssertionError("quotiented representation component became observable")
        for continuation in basis():
            basis_executions += 1
            if run_basis_continuation(left, continuation) != run_basis_continuation(right, continuation):
                raise AssertionError("basis distinguishes a quotiented component")
    return {
        "status": "pass",
        "state_count": len(universe),
        "pair_obligations": pairs,
        "equivalent_pairs": equivalent_pairs,
        "differing_pairs": differing_pairs,
        "finite_basis_executions": basis_executions,
        "witness_lengths": {
            "zero": empty_witnesses,
            "one": one_command_witnesses,
            "two": two_command_witnesses,
            "maximum": 2,
        },
        "scope": "bounded executable audit; general theorem is proved on paper",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = run()
    text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
