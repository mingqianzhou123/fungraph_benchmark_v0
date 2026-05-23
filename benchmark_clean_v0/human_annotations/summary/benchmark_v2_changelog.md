# Benchmark-v2 Changelog

## Phase 4 additions (2026-05-23)

**New file added:**

- `human_annotations/functional_queries_v1/long_range_stress_queries_v1.jsonl` — 40 long-range stress queries
  - Pattern: `junction_2hop` (all 40)
  - `reference_necessity`: 20 strict / 20 contextual (50.0% strict)
  - `long_range_pattern`: `junction_2hop` (bipartite graph; true 3-hop chain not possible)
  - `evidence_hop_count`: 2 (all queries)
  - New scenes: 421063, 422391, 422813, 460417, 466192, 466803 (6 new beyond Phase 1–3 scenes)
  - Shared scenes with main file: 421380 (8 queries), 469011 (12 queries)
  - Classification: **auxiliary stress slice** — NOT in main test split

**Scripts added:**

- `scripts/phase4_junction_audit.py` — discovers junction pairs across 20 geometry-covered scenes
- `scripts/phase4_junction_audit.csv` — 59 audit rows of viable junction pairs
- `scripts/append_queries_031_040.py` — appended 10 new strict queries (q031–q040) to long-range file
- `scripts/fix_queries_038_040.py` — replaced q038–q040 with correct oven-handle strict queries

---

## Phase 3 additions (2026-05-20)

**Files modified/added:**

- `human_annotations/functional_queries_v1/functional_queries_v1.jsonl` — expanded to 133 queries (minimal-pair and hard-slice expansion from Phase 2 base)
- `human_annotations/functional_queries_v1/minimal_pairs_v1.jsonl` — 28 contrastive pairs across 4 `changed_factor` classes (`spatial_qualifier` 11, `anchor_object` 9, `geometry_direction` 7, `functional_relation` 1)
- `human_annotations/functional_queries_v1/hard_slice_summary_v1.json` — updated slice statistics
- `human_annotations/functional_queries_v1/functional_query_diagnostics_v1.jsonl` — per-query diagnostic metadata

New scenes: none (all 6 Phase 1–3 scenes: 420683, 421013, 421254, 421380, 421602, 469011)

---

## Phase 1–2 baseline (pre-Phase 3)

- `pilot_20_queries.jsonl` — 20 pilot queries across 6 scenes
- `functional_queries_v1.jsonl` — initial Phase 1–2 queries (pre-minimal-pair expansion)
- All scripts in `scripts/`: `phase0_scene_audit.py`, `phase1_scene_explorer.py`, `phase2_query_generator.py`, `validate_functional_queries.py`

---

## What is NOT in the main benchmark split

- `long_range_stress_queries_v1.jsonl` — remains a separate auxiliary file until Mingqian approves merge into main split
- `robot_trials/` directory — execution sidecar only (3D bbox + action primitives); not a query benchmark
- `pilot_20_queries.jsonl` — pilot set; not part of the main 133-query set
