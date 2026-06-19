# FunTHOR-Style Benchmark Quality Layer

Status: `funthor_style_quality_layer_ready`

This layer aligns the FunGraph/3DGraphLLM export with the evidence standard used by FunTHOR:
RGB-D-camera coverage, scene pointclouds, object/part-like geometry, visible evidence, and
typed functional relations.

## What is now explicit

- `funthor_style_modality_audit.csv`: scene-level RGB, depth, pose/trajectory, intrinsics, pointcloud, object geometry, image/point feature coverage.
- `query_relation_taxonomy_index.jsonl`: every functional query plus expansion candidate is tagged with a FunTHOR-style relation category.
- `minimal_pair_taxonomy_index.jsonl`: primary and expansion minimal pairs are tagged with ambiguity and global-reasoning requirements.
- `relation_taxonomy_v2.json`: deterministic taxonomy summary and FunTHOR reference relation families.

## Current benchmark status

- Scenes: 20 total, 20 full raw-ready.
- RGB-D-camera triplets: 13039.
- Candidate objects / functional parts: 317 objects, 20 scenes with functional part-like nodes.
- Functional query rows indexed: 799.
- Minimal-pair rows indexed: 88.

## Remaining gap to true FunTHOR parity

The raw modality stack is complete. The two remaining semantic gaps are:

1. Export object-part hierarchy as a first-class table, not only as functional part-like nodes.
2. Export an explicit visible subset table, rather than relying on record-camera/image-feature coverage.

These are now tracked as benchmark quality requirements rather than hidden assumptions.
