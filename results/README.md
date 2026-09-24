# Final result inventory

The directory preserves the original completion campaign, the later
budget-closing continuation audit, and the final clean-extract stratified replay.
Repeated runs are never silently deduplicated.

* `final_reproduction.json`: authoritative aggregate containing the original
  campaign, C167, cumulative accounting, and exact embedded copies of the
  continuation and final clean-extract audits.
* `final_continuation_audit.json`: rematerialization of all 167 cases, repeated
  36-state full-abstraction audit, 320 fresh regional instances, fresh replay of
  C001--C165, direct recomputation of all 6,281 stored leaf minima, and a repeated
  18-mutation suite. It explicitly records why C166 was not fully replayed again.
* `final_clean_extract_audit.json`: predeclared replay of C061, C062, C065, C162,
  and C163 from a clean extracted candidate; all five accepted using 299 regional
  calls and five top-level checks. It is explicitly not a second full campaign.
* `branch_cases.csv`: one row for every completed case C001--C166, including
  expected/observed labels, nodes, leaves, regional calls, witnesses, and CPU.
* `fanout_control.json`: C167 cap result (`unknown_resource_exhaustion`).
* `full_abstraction_check.json`: original finite witness-construction audit.
* `region_crosscheck.json`: original 384-instance brute-force comparison of the
  producer and replayer regional algorithms on a four-value alphabet.
* `primitive_oracle.json`: all 65,536 two-byte assignments and canonical-pattern
  pilot; direct assignments remain separate from capped obligations.
* `mutation_suite.json`: 16 certificate and two JSON-parser mutations, all
  rejected in the original campaign.
* `resource_accounting.csv`: historical, smoke, original-final, C167,
  continuation, and final clean-extract rows under the frozen counting rule.
* `reference_audit.csv`: 48 unique cited bibliography entries with DOI or official
  proceedings URL, metadata authority, access date, verification scope, and role
  in the manuscript.
* `reference_integrity_audit.json`: structural reconciliation of 48 unique cited
  entries, 45 DOI records, three official URLs, 20 substantive-section scopes, and
  28 metadata/proceedings scopes.

The cumulative counted total is **99,999 of 100,000**, leaving one. Direct
concrete assignment checks total **650,557** and are not recast as solver calls.
The scientific sources used to produce these files should not be modified without
a new run and new cumulative accounting.
