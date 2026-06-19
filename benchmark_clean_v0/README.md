# Benchmark Clean v0

Frozen benchmark interface for FunGraph / SceneFun3D functional grounding and 3DGraphLLM+ multimodal experiments.

Created: 2026-05-08

This folder now has two layers:

- frozen source-of-truth benchmark files under `queries/`, `graphs/`, `geometry/`, `annotations/`, `human_annotations/`, and `raw_assets/`;
- model-facing exports under `exports/`, with the current mainline export at `exports/3dgraphllm_functional_eval_v1/`.

## Rule

Do not modify the files in `queries/`, `graphs/`, `geometry/`, or `annotations/` in place.

For the current 3DGraphLLM+ project, do not start from the old intern task plans. Start from:

```text
exports/3dgraphllm_functional_eval_v1/README.md
exports/3dgraphllm_functional_eval_v1/relation_conditioned_evidence/README.md
exports/3dgraphllm_functional_eval_v1/fungraph_full_modality_release_v1/README.md
STRUCTURE_AUDIT_20260618.md
```

If the frozen source interface needs to change, create a new folder such as `benchmark_clean_v1/` rather than silently editing v0.

## Canonical Files

For quick audits that do not need full scene graphs, use the lightweight query indices:

```text
queries/all_queries_index.jsonl
queries/train_queries_index.jsonl
queries/val_queries_index.jsonl
queries/test_queries_index.jsonl
```

These contain only query-level fields such as `scene_id`, `target_node_ids`, `anchor_node_id`, and `supporting_edge_ids`.

### SceneFun3D / OpenFunGraph

Use this file for SceneFun3D functional grounding queries:

```text
queries/scenefun3d_funrag_benchmark_enriched.json
```

SceneFun3D node geometry is here:

```text
geometry/scenefun3d_node_geom.json
```

It maps:

```text
scene_id -> node_id -> bbox_center / bbox_min / bbox_max
```

### 3DSSG

Use this file for 3DSSG spatial, semantic, and compositional queries:

```text
queries/3dssg_benchmark_enriched.json
```

Use this file for the corresponding 3DSSG scene graphs:

```text
graphs/3dssg_scene_graphs_enriched.json
```

## Unified Loader Compatibility

The historical project loader is:

```text
funrag/unified_dataset.py
```

Its canonical item schema is:

```text
query_id
dataset
scene_id
split
query
query_type
annotation_source
target_node_ids
target_labels
anchor_node_id
supporting_edge_id
supporting_edge_ids
action_verb
scene_graph.nodes
scene_graph.edges
_extra
```

The clean files preserve the enriched fields used by that loader, including `edge_id`, `edge_family`, `supporting_edge_id`, `supporting_edge_ids`, and SceneFun3D bbox fields where available.

## Folder Guide

```text
queries/
  Canonical benchmark query files.

graphs/
  External graph store needed by 3DSSG.
  SceneFun3D graphs are embedded in the query file.

geometry/
  Object-level geometry side information already available for SceneFun3D nodes.

annotations/
  Source OpenFunGraph annotations and labels, for auditing and multimodal alignment.

raw_assets/
  Pointers to raw SceneFun3D assets. Large point clouds are not copied here.

manifests/
  File inventory, audit outputs, and summary metadata.

exports/
  Model-facing exports derived from the frozen source files. The active multimodal interface is exports/3dgraphllm_functional_eval_v1/.

multimodal_extension/
  Legacy geometry/P0 perception sidecar retained for provenance. It is not the current 3DGraphLLM+ multimodal interface.

robot_trials/
  Legacy execution sidecar, not part of the current functional benchmark export.
```

## Current Mainline

Use this export for 3DGraphLLM reproduction and multimodal benchmark work:

```text
exports/3dgraphllm_functional_eval_v1/
```

Important status files:

```text
exports/3dgraphllm_functional_eval_v1/FULL_MULTIMODAL_BENCHMARK_STATUS.md
exports/3dgraphllm_functional_eval_v1/relation_conditioned_evidence/RELATION_EVIDENCE_STATUS.md
exports/3dgraphllm_functional_eval_v1/relation_conditioned_evidence/OFFICIAL_CROP_STATUS.md
exports/3dgraphllm_functional_eval_v1/relation_conditioned_evidence/FULL_PERCEPTION_EVIDENCE_STATUS.md
exports/3dgraphllm_functional_eval_v1/expansion_v1/README.md
exports/3dgraphllm_functional_eval_v1/expansion_v1/expansion_manifest_v1.json
exports/3dgraphllm_functional_eval_v1/expansion_v1/DENNIS_BENCHMARK_SIGNOFF_PACKET.md
exports/3dgraphllm_functional_eval_v1/fungraph_full_modality_release_v1/README.md
exports/3dgraphllm_functional_eval_v1/fungraph_full_modality_release_v1/dataset_manifest.json
exports/3dgraphllm_functional_eval_v1/BENCHMARK_CLAIM_AUDIT.md
```

Validate the export with:

```bash
python3 exports/3dgraphllm_functional_eval_v1/scripts/validate_export.py
```

Large regenerated crops and point-cloud segments live in ignored local folders under `relation_conditioned_evidence/`; commit manifests, reports, and QC metadata, not bulk raw visual assets. The exception is `relation_conditioned_evidence/full_perception_evidence/images/`, which contains lightweight committed evidence cards for the 683 / 683 full-coverage perception layer. Expansion scratch files are regenerated under ignored `expansion_v1/_intermediate/`; only final candidates, AI review views, manifest, Dennis packet, and compact evidence cards are tracked.
