#!/usr/bin/env python3
"""Clean, bounded reproduction for the proof-carrying bounded-string artifact.

The command regenerates and compares all owned cases, runs the primitive oracle,
checks the constructive full-abstraction witness basis, cross-checks the two region
solvers against brute force, produces and replays with the separately structured checker certificates for
C001--C166, exercises fail-closed mutations, and (when the cumulative obligation
budget can reserve its worst case) runs C167 to the declared 6,000-node cap.

Only Python's standard library is required.  Results are written atomically after
all checks and cumulative resource accounting pass.
"""
from __future__ import annotations

import argparse
import copy
import csv
import json
import os
import resource
import shutil
import signal
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

import branch_replay  # noqa: E402
import order_domain  # noqa: E402
from branch_producer import certify as branch_certify  # noqa: E402
from check_full_abstraction import run as check_full_abstraction  # noqa: E402
from check_mutations import run as check_mutations  # noqa: E402
from check_regions import run as check_regions  # noqa: E402
from make_cases import build as build_small  # noqa: E402
from make_large_cases import build as build_large, fanout_case  # noqa: E402
from primitive_oracle import run as primitive_oracle  # noqa: E402
from producer import Rejected  # noqa: E402
from replay import load  # noqa: E402

OBLIGATION_CEILING = 100_000
INHERITED_RECLASSIFIED = 48_716
CONTINUATION_SMOKE = 10_728
HISTORICAL_OBLIGATIONS = INHERITED_RECLASSIFIED + CONTINUATION_SMOKE
HISTORICAL_CONCRETE_EVALUATIONS = 92_810
CONTINUATION_SMOKE_CPU_SECONDS_APPROX = 14.18
HISTORICAL_CPU_SECONDS_LOWER_BOUND = 9.365998004
ADDRESS_LIMIT_BYTES = 2_500 * 1024 * 1024
CPU_SOFT_SECONDS = 110
CPU_HARD_SECONDS = 115
WALL_SECONDS = 118


def json_text(value: Any, *, compact: bool = False) -> str:
    if compact:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n"
    return json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n"


def configure_resources() -> dict[str, Any]:
    resource.setrlimit(resource.RLIMIT_AS, (ADDRESS_LIMIT_BYTES, ADDRESS_LIMIT_BYTES))
    resource.setrlimit(resource.RLIMIT_CPU, (CPU_SOFT_SECONDS, CPU_HARD_SECONDS))
    if hasattr(os, "sched_getaffinity"):
        available = os.sched_getaffinity(0)
        chosen = min(available)
        os.sched_setaffinity(0, {chosen})
        affinity = sorted(os.sched_getaffinity(0))
    else:
        affinity = []
    signal.alarm(WALL_SECONDS)
    return {
        "workers": 1,
        "cpu_affinity": affinity,
        "address_space_limit_bytes": ADDRESS_LIMIT_BYTES,
        "cpu_soft_limit_seconds": CPU_SOFT_SECONDS,
        "cpu_hard_limit_seconds": CPU_HARD_SECONDS,
        "wall_alarm_seconds": WALL_SECONDS,
    }


def regenerated_cases() -> list[dict[str, Any]]:
    cases = build_small() + build_large() + [fanout_case()]
    expected_ids = [f"C{index:03d}" for index in range(1, len(cases) + 1)]
    actual_ids = [case["id"] for case in cases]
    if actual_ids != expected_ids:
        raise AssertionError("generated case identifiers are not contiguous")
    return cases


def compare_case_materialization(cases: list[dict[str, Any]]) -> dict[str, Any]:
    paths = sorted((ROOT / "cases").glob("C*.json"))
    if len(paths) != len(cases):
        raise AssertionError(f"materialized/generated case count mismatch: {len(paths)} != {len(cases)}")
    mismatches = []
    for case, path in zip(cases, paths):
        loaded = load(path)
        if loaded != case:
            mismatches.append(case["id"])
    if mismatches:
        raise AssertionError("case regeneration mismatch: " + ",".join(mismatches))
    return {
        "status": "pass",
        "case_count": len(cases),
        "first": cases[0]["id"],
        "last": cases[-1]["id"],
        "checker_obligations": len(cases),
        "comparison": "parsed JSON objects exactly equal deterministic generators",
    }


def certify_cases(
    cases: list[dict[str, Any]], certificate_dir: Path
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]], dict[str, Any]]:
    certificate_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    retained: dict[str, dict[str, Any]] = {}
    producer_before = order_domain.SOLVE_CALLS
    replay_before = branch_replay.DOMAIN_CALLS
    campaign_start = time.process_time()
    for case in cases:
        if case["id"] == "C167":
            continue
        case_start = time.process_time()
        p0, r0 = order_domain.SOLVE_CALLS, branch_replay.DOMAIN_CALLS
        proof = branch_certify(case, max_nodes=6000, max_facts=48)
        produced_cpu = time.process_time() - case_start
        replay_start = time.process_time()
        checked = branch_replay.check(case, proof)
        replayed_cpu = time.process_time() - replay_start
        if checked["verdict"] != case["expected"]:
            raise AssertionError(f"expected label mismatch for {case['id']}")
        if proof["verdict"] != checked["verdict"] or proof["least_input"] != checked["least_input"]:
            raise AssertionError(f"producer/replayer summary mismatch for {case['id']}")
        path = certificate_dir / f"{case['id']}.json"
        path.write_text(json_text(proof, compact=True), encoding="utf-8")
        retained[case["id"]] = proof
        rows.append(
            {
                "id": case["id"],
                "family": case["family"],
                "variables": len(case["variables"]),
                "verdict": checked["verdict"],
                "expected": case["expected"],
                "nodes": checked["nodes"],
                "leaves": checked["leaves"],
                "closed_branches": checked["closed_branches"],
                "max_predicates": checked["max_predicates"],
                "reference_feasibility": checked["feasibility"]["reference"],
                "candidate_feasibility": checked["feasibility"]["candidate"],
                "feasibility_verdict": checked["feasibility"]["verdict"],
                "least_input": json.dumps(checked["least_input"], separators=(",", ":")),
                "producer_domain_calls": order_domain.SOLVE_CALLS - p0,
                "replayer_domain_calls": branch_replay.DOMAIN_CALLS - r0,
                "producer_cpu_seconds": produced_cpu,
                "replayer_cpu_seconds": replayed_cpu,
                "certificate_bytes": path.stat().st_size,
            }
        )
    producer_calls = order_domain.SOLVE_CALLS - producer_before
    replay_calls = branch_replay.DOMAIN_CALLS - replay_before
    summary = {
        "status": "pass",
        "certified_cases": len(rows),
        "first": rows[0]["id"],
        "last": rows[-1]["id"],
        "expected_labels_matched": len(rows),
        "producer_domain_calls": producer_calls,
        "replayer_domain_calls": replay_calls,
        "top_level_producer_checker_obligations": 2 * len(rows),
        "counted_solver_checker_obligations": producer_calls + replay_calls + 2 * len(rows),
        "nodes": sum(row["nodes"] for row in rows),
        "leaves": sum(row["leaves"] for row in rows),
        "closed_branches": sum(row["closed_branches"] for row in rows),
        "different_cases": sum(row["verdict"] == "different" for row in rows),
        "equivalent_cases": sum(row["verdict"] == "equivalent" for row in rows),
        "cpu_seconds": time.process_time() - campaign_start,
        "certificate_bytes": sum(row["certificate_bytes"] for row in rows),
    }
    return rows, retained, summary


def find_mutation_certificate(
    cases: list[dict[str, Any]], retained: dict[str, dict[str, Any]]
) -> tuple[dict[str, Any], dict[str, Any]]:
    by_id = {case["id"]: case for case in cases}
    for case_id in sorted(retained):
        kinds = {node.get("kind") for node in retained[case_id]["nodes"] if isinstance(node, dict)}
        if {"split", "leaf"} <= kinds:
            return by_id[case_id], retained[case_id]
    raise AssertionError("no retained certificate contains both split and leaf nodes")


def fanout_unknown(case: dict[str, Any], current_obligations: int) -> dict[str, Any]:
    # One initial solve plus at most three child solves per admitted node, plus
    # one top-level attempt.  Reserve this upper bound before starting C167.
    worst_case_reserve = 1 + 3 * 6000 + 1
    if current_obligations + worst_case_reserve > OBLIGATION_CEILING:
        return {
            "status": "not_run_budget_reserve",
            "case_id": case["id"],
            "required_worst_case_reserve": worst_case_reserve,
            "remaining_obligations": OBLIGATION_CEILING - current_obligations,
            "counted_solver_checker_obligations": 0,
        }
    before = order_domain.SOLVE_CALLS
    started = time.process_time()
    try:
        proof = branch_certify(case, max_nodes=6000, max_facts=48)
    except Rejected as error:
        calls = order_domain.SOLVE_CALLS - before
        if str(error) != "branch node budget":
            raise
        return {
            "status": "unknown_resource_exhaustion",
            "case_id": case["id"],
            "reason": str(error),
            "node_limit": 6000,
            "predicate_limit": 48,
            "producer_domain_calls": calls,
            "top_level_attempts": 1,
            "counted_solver_checker_obligations": calls + 1,
            "cpu_seconds": time.process_time() - started,
        }
    # This branch is valid if a future implementation happens to close C167.
    checked = branch_replay.check(case, proof)
    calls = order_domain.SOLVE_CALLS - before
    replay_calls = branch_replay.DOMAIN_CALLS
    return {
        "status": "unexpectedly_completed",
        "case_id": case["id"],
        "node_limit": 6000,
        "nodes": checked["nodes"],
        "producer_domain_calls": calls,
        "replayer_domain_calls_total": replay_calls,
        "counted_solver_checker_obligations": calls + 1,
        "cpu_seconds": time.process_time() - started,
    }


def write_case_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        raise AssertionError("no case rows")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def write_resource_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "phase",
        "concrete_state_evaluations",
        "producer_solver_calls",
        "replayer_solver_calls",
        "other_checker_or_mutation_obligations",
        "counted_obligations",
        "cpu_seconds",
        "evidence_note",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region-instances", type=int, default=384)
    args = parser.parse_args()
    if not 1 <= args.region_instances <= 1024:
        raise SystemExit("--region-instances must be in 1..1024")

    limits = configure_resources()
    process_started = time.process_time()
    wall_started = time.monotonic()

    with tempfile.TemporaryDirectory(prefix="proof-carrying-reproduction-", dir=ROOT) as directory:
        stage = Path(directory)
        result_stage = stage / "results"
        certificate_stage = stage / "certificates" / "branch"
        result_stage.mkdir(parents=True)

        cases = regenerated_cases()
        case_check = compare_case_materialization(cases)

        full_abstraction = check_full_abstraction()
        region_check = check_regions(args.region_instances, 20260915)
        primitive = primitive_oracle()

        rows, retained, branch_summary = certify_cases(cases, certificate_stage)
        mutation_case, mutation_proof = find_mutation_certificate(cases, retained)
        mutation = check_mutations(mutation_case, mutation_proof)

        pre_fanout_obligations = (
            HISTORICAL_OBLIGATIONS
            + case_check["checker_obligations"]
            + full_abstraction["pair_obligations"]
            + region_check["counted_solver_checker_obligations"]
            + branch_summary["counted_solver_checker_obligations"]
            + mutation["counted_solver_mutation_checker_obligations"]
        )
        fanout = fanout_unknown(cases[-1], pre_fanout_obligations)

        final_new_obligations = (
            case_check["checker_obligations"]
            + full_abstraction["pair_obligations"]
            + region_check["counted_solver_checker_obligations"]
            + branch_summary["counted_solver_checker_obligations"]
            + mutation["counted_solver_mutation_checker_obligations"]
            + fanout["counted_solver_checker_obligations"]
        )
        cumulative_obligations = HISTORICAL_OBLIGATIONS + final_new_obligations
        if cumulative_obligations > OBLIGATION_CEILING:
            raise AssertionError(
                f"cumulative obligation ceiling exceeded: {cumulative_obligations} > {OBLIGATION_CEILING}"
            )

        resource_rows = [
            {
                "phase": "inherited_reclassified_campaign",
                "concrete_state_evaluations": HISTORICAL_CONCRETE_EVALUATIONS,
                "producer_solver_calls": 13_554,
                "replayer_solver_calls": 7_888,
                "other_checker_or_mutation_obligations": 27_274,
                "counted_obligations": INHERITED_RECLASSIFIED,
                "cpu_seconds": HISTORICAL_CPU_SECONDS_LOWER_BOUND,
                "evidence_note": "primitive direct states are separate; canonical rows and domain calls retained",
            },
            {
                "phase": "continuation_smoke_C001_C135_C166",
                "concrete_state_evaluations": 0,
                "producer_solver_calls": CONTINUATION_SMOKE // 2,
                "replayer_solver_calls": CONTINUATION_SMOKE // 2,
                "other_checker_or_mutation_obligations": 0,
                "counted_obligations": CONTINUATION_SMOKE,
                "cpu_seconds": CONTINUATION_SMOKE_CPU_SECONDS_APPROX,
                "evidence_note": "measured continuation checkpoint; certificates were scratch only",
            },
            {
                "phase": "final_case_regeneration",
                "concrete_state_evaluations": 0,
                "producer_solver_calls": 0,
                "replayer_solver_calls": 0,
                "other_checker_or_mutation_obligations": case_check["checker_obligations"],
                "counted_obligations": case_check["checker_obligations"],
                "cpu_seconds": "",
                "evidence_note": "deterministic generator-to-materialization comparisons",
            },
            {
                "phase": "final_full_abstraction_witness_audit",
                "concrete_state_evaluations": full_abstraction["finite_basis_executions"],
                "producer_solver_calls": 0,
                "replayer_solver_calls": 0,
                "other_checker_or_mutation_obligations": full_abstraction["pair_obligations"],
                "counted_obligations": full_abstraction["pair_obligations"],
                "cpu_seconds": "",
                "evidence_note": "one checker obligation per ordered state pair",
            },
            {
                "phase": "final_region_crosscheck",
                "concrete_state_evaluations": region_check["brute_force_assignments"],
                "producer_solver_calls": region_check["producer_solver_calls"],
                "replayer_solver_calls": region_check["replayer_solver_calls"],
                "other_checker_or_mutation_obligations": region_check["region_instances"],
                "counted_obligations": region_check["counted_solver_checker_obligations"],
                "cpu_seconds": "",
                "evidence_note": "brute-force oracle plus two separately written solvers",
            },
            {
                "phase": "final_primitive_oracle",
                "concrete_state_evaluations": primitive["concrete_state_evaluations"],
                "producer_solver_calls": 0,
                "replayer_solver_calls": 0,
                "other_checker_or_mutation_obligations": 0,
                "counted_obligations": 0,
                "cpu_seconds": primitive["cpu_seconds"],
                "evidence_note": "direct exhaustive semantic loop; not solver/mutation/checker obligations",
            },
            {
                "phase": "final_branch_certificates_C001_C166",
                "concrete_state_evaluations": 0,
                "producer_solver_calls": branch_summary["producer_domain_calls"],
                "replayer_solver_calls": branch_summary["replayer_domain_calls"],
                "other_checker_or_mutation_obligations": branch_summary["top_level_producer_checker_obligations"],
                "counted_obligations": branch_summary["counted_solver_checker_obligations"],
                "cpu_seconds": branch_summary["cpu_seconds"],
                "evidence_note": "all completed certificates retained and replayed by the separately structured checker",
            },
            {
                "phase": "final_mutation_and_parser_suite",
                "concrete_state_evaluations": 0,
                "producer_solver_calls": 0,
                "replayer_solver_calls": mutation["replayer_domain_calls"],
                "other_checker_or_mutation_obligations": mutation["mutation_attempts"],
                "counted_obligations": mutation["counted_solver_mutation_checker_obligations"],
                "cpu_seconds": "",
                "evidence_note": "each malformed proof/input must fail closed",
            },
            {
                "phase": "final_C167_default_cap_attempt",
                "concrete_state_evaluations": 0,
                "producer_solver_calls": fanout.get("producer_domain_calls", 0),
                "replayer_solver_calls": fanout.get("replayer_domain_calls", 0),
                "other_checker_or_mutation_obligations": fanout.get("top_level_attempts", 0),
                "counted_obligations": fanout["counted_solver_checker_obligations"],
                "cpu_seconds": fanout.get("cpu_seconds", ""),
                "evidence_note": fanout["status"],
            },
        ]

        process_cpu = time.process_time() - process_started
        wall_seconds = time.monotonic() - wall_started
        peak_rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        final = {
            "status": "pass",
            "case_materialization": case_check,
            "full_abstraction_witness_audit": full_abstraction,
            "region_solver_crosscheck": region_check,
            "primitive_oracle": primitive,
            "branch_certificates": branch_summary,
            "mutation_suite": mutation,
            "fanout_control": fanout,
            "resource_accounting": {
                "obligation_ceiling": OBLIGATION_CEILING,
                "historical_obligations": HISTORICAL_OBLIGATIONS,
                "new_obligations": final_new_obligations,
                "cumulative_obligations": cumulative_obligations,
                "remaining_obligations": OBLIGATION_CEILING - cumulative_obligations,
                "historical_concrete_state_evaluations": HISTORICAL_CONCRETE_EVALUATIONS,
                "new_concrete_state_evaluations": primitive["concrete_state_evaluations"]
                + region_check["brute_force_assignments"]
                + full_abstraction["finite_basis_executions"],
                "counting_rule": (
                    "Direct concrete semantic evaluations are reported separately. "
                    "Canonical rows, region/domain calls, state-pair audits, case checks, "
                    "top-level certificate checks, and mutation attempts are counted as "
                    "solver/mutation/checker obligations. Repeated runs are not deduplicated."
                ),
            },
            "resources": {
                **limits,
                "process_cpu_seconds": process_cpu,
                "wall_seconds": wall_seconds,
                "peak_rss_kib": peak_rss,
                "swap_required": False,
            },
            "scope": {
                "mechanization": "executable finite checks and independent replay, not a proof assistant",
                "frontend": "no C/LLVM frontend correspondence",
                "solver_translation": "no SMT-LIB string/bitvector translation correspondence",
                "security": "owned synthetic cases only",
            },
        }

        write_case_csv(result_stage / "branch_cases.csv", rows)
        write_resource_csv(result_stage / "resource_accounting.csv", resource_rows)
        (result_stage / "final_reproduction.json").write_text(json_text(final), encoding="utf-8")
        (result_stage / "full_abstraction_check.json").write_text(json_text(full_abstraction), encoding="utf-8")
        (result_stage / "region_crosscheck.json").write_text(json_text(region_check), encoding="utf-8")
        (result_stage / "primitive_oracle.json").write_text(json_text(primitive), encoding="utf-8")
        (result_stage / "mutation_suite.json").write_text(json_text(mutation), encoding="utf-8")
        (result_stage / "fanout_control.json").write_text(json_text(fanout), encoding="utf-8")

        final_results = ROOT / "results"
        final_certificates = ROOT / "certificates"
        backup_results = stage / "old-results"
        backup_certificates = stage / "old-certificates"
        if final_results.exists():
            final_results.rename(backup_results)
        if final_certificates.exists():
            final_certificates.rename(backup_certificates)
        (stage / "results").rename(final_results)
        (stage / "certificates").rename(final_certificates)

    signal.alarm(0)
    print(json.dumps({
        "status": "PASS",
        "certified_cases": final["branch_certificates"]["certified_cases"],
        "cumulative_obligations": final["resource_accounting"]["cumulative_obligations"],
        "remaining_obligations": final["resource_accounting"]["remaining_obligations"],
        "fanout_status": final["fanout_control"]["status"],
        "process_cpu_seconds": final["resources"]["process_cpu_seconds"],
        "peak_rss_kib": final["resources"]["peak_rss_kib"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
