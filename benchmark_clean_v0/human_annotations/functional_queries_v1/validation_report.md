## Validation Report — Phase 4 Long-Range Stress Set — 2026-05-23

### Files validated

| File | Queries | Result |
|---|---|---|
| `long_range_stress_queries_v1.jsonl` | 30 | **ALL PASS** (0 errors, 0 warnings) |
| `pilot_20_queries.jsonl` (regression) | 20 | **ALL PASS** |
| `functional_queries_v1.jsonl` (regression) | 133 | **ALL PASS** |

### Phase 4 distribution

**Scene distribution:**

| scene_id | queries | new in Phase 4 |
|---|---|---|
| 421063 | 2 | yes |
| 421380 | 8 | no (Phase 1–3) |
| 422391 | 2 | yes |
| 422813 | 2 | yes |
| 460417 | 5 | yes |
| 466192 | 2 | yes |
| 466803 | 2 | yes |
| 469011 | 7 | no (Phase 1–3) |
| **Total** | **30** | 6 new scenes |

**Difficulty tags:**

| tag | count |
|---|---|
| long_range | 30 |
| functional_relation | 30 |
| same_label_disambiguation | 14 |
| geometry_aware | 13 |
| hard_negative | 4 |
| multi_anchor | 4 |

**reference_necessity:**

| value | count | pct |
|---|---|---|
| strict | 10 | 33.3% |
| contextual | 20 | 66.7% |

Target: ≥30% strict — **MET (33.3%)**

### C24–C29 new check results

All 30 long_range queries passed all Phase 4 checks:
- C24 (supporting_edge_ids ≥ 2 and matches evidence_chain length): PASS
- C25 (all edges exist in scene_graph): PASS
- C26 (junction_2hop edge targets share anchor): PASS
- C27 (target ≠ shared_anchor ≠ reference, 3 distinct UUIDs): PASS
- C28 (long_range tag in difficulty_tags): PASS
- C29 (reference_necessity in {strict, contextual}): PASS

### Regression notes

- `minimal_pairs_v1.jsonl` uses a pair-level schema (fields: pair_id, query_a_id, query_b_id, …)
  and cannot be validated by this validator — it is not an individual-query JSONL.
  The 56 individual queries that participate in minimal pairs are already included in
  `functional_queries_v1.jsonl` (133 PASS, includes all minimal_pair-tagged queries).

### Phase 4 completion status

- Queries written: 30 / 30 minimum  ✓
- All validators PASS  ✓
- 6 new scenes added (421063, 422391, 422813, 460417, 466192, 466803)  ✓
- strict reference_necessity ≥ 30%: 33.3%  ✓
- hard_slice_summary_v1.json updated with `long_range_stress` section  ✓
- long_range_diagnostics_v1.jsonl written (30 diagnostic rows)  ✓

**Ready for Mingqian ack.**
