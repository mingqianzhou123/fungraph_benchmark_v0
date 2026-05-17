# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **frozen data benchmark** (`benchmark_clean_v0/`) for CoRL 2026 FunRAG / FCGP (Function-Conditioned Graph Propagation) experiments — not a code library with build/test infrastructure. Two parallel sidecar extension workstreams append new data on top of the frozen base; the lead ("Mingqian") consumes those outputs for the method/paper.

There is **no package manager, no test framework, no lint config**. Scripts are standard-library Python (no pip deps), run directly. Working shell is Windows PowerShell.

## The frozen / sidecar architecture (most important rule)

**Never modify** anything under these paths — they are the frozen benchmark interface other people consume:

```
benchmark_clean_v0/queries/        benchmark_clean_v0/graphs/
benchmark_clean_v0/geometry/       benchmark_clean_v0/annotations/
benchmark_clean_v0/manifests/      benchmark_clean_v0/multimodal_extension/
benchmark_clean_v0/INTERN_GEOMETRY_TASK_PLAN.md
```

When you find a problem in a frozen file, **do not fix it in place**. Append a log entry to the relevant `annotation_notes.md` or `validation_report.md` using the convention:

```
[issue] scope=... problem=... suggested_fix=...
```

New work goes into one of two sidecar dirs (depending on which workstream you're in):

| Workstream | Sidecar dir | Phase plans live in |
|---|---|---|
| Geometry / multimodal extension | [benchmark_clean_v0/multimodal_extension/](benchmark_clean_v0/multimodal_extension/) | [multimodal_extension/summary/](benchmark_clean_v0/multimodal_extension/summary/) |
| Human functional-query annotation | [benchmark_clean_v0/human_annotations/functional_queries_v1/](benchmark_clean_v0/human_annotations/functional_queries_v1/) | [human_annotations/summary/phase_clarify/](benchmark_clean_v0/human_annotations/summary/phase_clarify/) |

`multimodal_extension/` is itself frozen relative to the human-annotation workstream — i.e., when you're doing annotation, treat `multimodal_extension/` as read-only and log conflicts as issues.

## Key data files

Lightweight (one query per line, no embedded scene graphs — prefer for audits):
- [queries/all_queries_index.jsonl](benchmark_clean_v0/queries/all_queries_index.jsonl), plus `train_/val_/test_queries_index.jsonl`

Full benchmark (embedded `scene_graph.nodes` / `scene_graph.edges` per query):
- [queries/scenefun3d_funrag_benchmark_enriched.json](benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json) — **top-level is `{"metadata":..., "data":[...]}` and each item in `data` is one *query* (not one scene)**. A given `scene_id` appears in many items; the same `scene_graph` is copied into each. Iterate over `data`, dedup by `scene_id` if you want scenes.
- [queries/3dssg_benchmark_enriched.json](benchmark_clean_v0/queries/3dssg_benchmark_enriched.json) for the 3DSSG split (graphs are external in `graphs/3dssg_scene_graphs_enriched.json`).

Geometry:
- [geometry/scenefun3d_node_geom.json](benchmark_clean_v0/geometry/scenefun3d_node_geom.json) — `scene_id → node_id → {bbox_center, bbox_min, bbox_max}`. **Only 20 of 23 SceneFun3D scenes have geometry; the audit-passed working set is those 20.**

## Coordinate-axis gotcha (verified, contested)

`bbox_center[2]` (z) is **the vertical/up axis** for scene-internal comparisons — verified by `ceiling light` ranking #1 on z in 3/3 scenes with ceiling lights, #5/#10/#13 on y. Phase 2 of the multimodal extension recorded "高度轴 = y" in [multimodal_extension/summary/phase2.md](benchmark_clean_v0/multimodal_extension/summary/phase2.md) and built `height_from_floor_m = center_y - scene_min_y` on that assumption; this is logged as an issue in the human-annotation `annotation_notes.md`. **Do not silently "fix" phase2 outputs** — surface the conflict, let Mingqian rule.

z values have a large global registration offset that varies per scene (z range ~−28 in one scene, ~+383 in another). The offset is a constant translation, so scene-*internal* z ordering remains valid for upper/lower comparisons. Don't use z values across scenes without normalization.

## Running the scripts

All scripts are stdlib-only Python — no env setup needed. Run from the repo root in PowerShell:

```powershell
# Geometry coverage audit (phase 1 of multimodal extension)
python benchmark_clean_v0\multimodal_extension\scripts\phase1_coverage_audit.py

# Node-level geometry feature bank (phase 2)
python benchmark_clean_v0\multimodal_extension\scripts\phase2_node_geometry_features.py

# Scene/edge selection audit for human annotation (phase 0)
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase0_scene_audit.py

# Dump per-scene node/edge/same-label summary for pilot writing (phase 1)
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\phase1_scene_explorer.py

# Validate a human-query JSONL (13 checks + Phase 1 distribution analysis)
python benchmark_clean_v0\human_annotations\functional_queries_v1\scripts\validate_functional_queries.py `
  benchmark_clean_v0\human_annotations\functional_queries_v1\pilot_20_queries.jsonl
```

The validator writes `validation_report.md` next to the input JSONL and exits non-zero on any ERROR.

## Human annotation: JSONL schema and tag taxonomy

Schema enforced by the validator (from `TASK_PLAN_BENCHMARK_QUALITY_EXTENSION.md` Section 5):

```
query_id, scene_id, query_text, query_type, target_node_id, anchor_node_id,
supporting_edge_ids (list of "src|relation|tgt"), difficulty_tags (list),
is_long_range (bool), evidence_chain (list of "src_label --relation--> tgt_label"),
source, notes
```

**Direction trap:** `supporting_edge_ids` are `"src|relation|tgt"` strings from the scene graph. In query semantics, `target_node_id` = edge's `src` (the thing the user operates), `anchor_node_id` = edge's `tgt` (the thing affected). C7/C8 of the validator check this — most bugs in early pilots came from inverting it.

Valid difficulty tags (don't invent new ones):

```
simple_functional, functional_relation, same_label_disambiguation,
endpoint_ambiguity, geometry_aware, multi_anchor, hard_negative,
minimal_pair, long_range
```

## Concepts that get conflated (re-read before using them)

These four terms are deceptively similar — they have been confused multiple times in the working log:

- **`long_range`** (TASK_PLAN Section 6): evidence chain ≥ 2 graph hops. Pilot queries must all be `is_long_range: false`; long-range goes in a separate file `long_range_stress_queries_v1.jsonl`.
- **"spatially long-range"** (Research Plan §8.5): 3D distance between target and anchor is large. Independent axis from graph hops — a remote single-hop edge (switch → ceiling light) is short on graph hops but long in 3D distance.
- **`local` / `remote` edge** (OpenFunGraph CVPR'25 Sec. 1/3): physical attachment vs physical separation. local = interactive element is *part of* the object (handle-door); remote = element operates the object from a distance (switch-light, outlet-fridge). **This is a physical-relation distinction, not a verb-type distinction.** Verb groupings (opens/pulls vs controls/powers) are an implementation-side proxy in research-plan Table 1.
- **TASK_PLAN Section 8 "10 local functional"**: here "local" means local-range (single hop), reading against `long_range`. It is **not** OpenFunGraph's local-type edge. The pilot 10 "local functional" mixes physical-local edges (knob→radiator) with single-hop remote edges (outlet→fridge).

## Workflow gates (don't skip)

Both workstreams have an escalation gate that must stop and wait for Mingqian's review:

- **Multimodal Phase 1 → Phase 2:** geometry coverage audit must pass `ready_for_phase_2 = true` in `coverage_summary.json` before building the feature bank.
- **Human annotation Phase 1 → Phase 2:** the 20-query pilot must be reviewed before scaling to 80+. The pilot file is [pilot_20_queries.jsonl](benchmark_clean_v0/human_annotations/functional_queries_v1/pilot_20_queries.jsonl) and the gate is documented at the end of [annotation_notes.md](benchmark_clean_v0/human_annotations/functional_queries_v1/annotation_notes.md).

## `annotation_notes.md` format (TASK_PLAN Section 17)

Append-only working log. Each phase appends **one** section:

```
## Phase X progress — YYYY-MM-DD

Did:           ...
Counts:        ...
Potential issues:  ...   (use [issue] ... suggested_fix=... format)
Files ready for review: ...
```

Don't split a phase into multiple `##` sections (`progress` + `revision` + `review note` etc.). Consolidate corrections back into the four standard subsections; preserve historical claims as `[issue] (已修正) ...` entries.

## Common citation pitfall

When citing the FCGP research plan or the OpenFunGraph paper to justify schema/data decisions, distinguish:
- **What the paper literally says** (model-side training mechanism, formulation choice)
- **What you're inferring from it** (schema constraint, data requirement)

Multiple working-log issues turned out to be over-inferences: the paper described a *training-time* operation (e.g., "the gate is trained with weak supervision; each functional query has a supporting edge, and that edge has a normalized edge family"), and the inference jumped to "benchmark schema must store `edge_family`". The relation text already in `supporting_edge_id` is enough — the family mapping happens model-side. Re-read the original passage before promoting an inference into a `[issue]` against the schema.
