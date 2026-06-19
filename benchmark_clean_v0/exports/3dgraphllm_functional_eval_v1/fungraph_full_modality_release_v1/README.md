# FunGraph Full-Modality Release v1

This is the human-facing benchmark package for the 3DGraphLLM+ multimodal functional-reasoning work.
It is organized after the FunTHOR release pattern, but uses compact metadata and relative raw-asset pointers instead of duplicating large files.

## Structure

```text
fungraph_full_modality_release_v1/
  dataset_manifest.json
  dataset_unique_labels.json
  dataset_functional_labels.json
  dataset_unique_relations.json
  annotation_rules/functional_relation_taxonomy.json
  query_protocol_v1.md
  splits/*.jsonl
  external/funthor_v1/funthor_manifest.json
  scenes/<scene_id>/
    scene.json
    frames.jsonl
```

## Current Counts

- Scenes: 20
- Candidate nodes: 317
- Functional part-like nodes: 209
- Functional relations: 195
- RGB-D-camera frame rows: 13039
- Unique labels: 54
- Unique relation strings: 21

## What To Read First

1. `dataset_manifest.json` for global counts, scene paths, split paths, and remaining semantic gaps.
2. `scenes/<scene_id>/scene.json` for one scene's nodes, functional relations, modality readiness, and visible subset analogue.
3. `splits/functional_500.jsonl` and `splits/human_133.jsonl` for current frozen eval queries.
4. `splits/expansion_functional_116_candidates.jsonl` only as paper-disabled candidates requiring human/Dennis signoff.


- `splits/fungraph_existing_queries_categorized_v2.jsonl` contains 799 existing FunGraph/SceneFun3D queries annotated with Functional Query Type x Spatial Scope x Anchor Visibility.

## External FunTHOR Extension

Dennis suggested defining one query protocol across functional-scenegraph datasets. This release now includes FunTHOR as an external dataset:

- `query_protocol_v1.md` defines the shared generation protocol.
- `external/funthor_v1/funthor_manifest.json` stores compact FunTHOR scene/node/edge metadata and HF raw asset pointers.
- `splits/funthor_functional_queries_v1.jsonl` contains 805 template-v1 FunTHOR functional queries for smoke testing.
- `splits/funthor_functional_queries_factorized_v2.jsonl` contains 1655 factorized FunTHOR queries over Functional Query Type x Spatial Scope x Anchor Visibility.
- `splits/funthor_minimal_pairs_v1.jsonl` contains 200 same-label functional-element diagnostic pairs.

These rows are rule-grounded but still paper-disabled until human wording review, evidence spot-check, and Dennis signoff.

## Boundary

This package is a clean release view over the existing export. It does not move or copy raw RGB-D images, depth frames, laser scans, or the full OpenFunGraph point-index arrays. Those are referenced by relative paths and source pointers.
