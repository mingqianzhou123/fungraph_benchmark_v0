# Relation-Conditioned Evidence

This directory is the query-conditioned multimodal layer for the FunGraph 3DGraphLLM export.

Primary key:

```text
relation_key = query_id|target_node_id|anchor_node_id
```

Files:

- `relation_evidence_index.jsonl`: one row per query relation, with target and anchor object sidecars, native 3DGraphLLM feature keys, supporting edges, and candidate frame references.
- `query_relation_index.jsonl`: query id to relation keys.
- `relation_frame_candidates.jsonl`: RGB-D-camera frame triplets selected as raw candidates for later projection/crop generation.
- `minimal_pair_relation_index.jsonl`: minimal-pair rows linked to relation keys.
- `relation_evidence_summary.json`: machine-readable coverage summary.
- `RELATION_EVIDENCE_STATUS.md`: human-readable status and boundary notes.
- `projection_dryrun_index.jsonl`: placeholder projection metadata for target/anchor point segments in candidate RGB-D frames.
- `projection_dryrun_summary.json`: projection dry-run coverage summary.
- `PROJECTION_DRYRUN_STATUS.md`: human-readable projection dry-run status and boundary notes.
- `official_crop_index.jsonl`: one row per relation with selected depth-tested co-visible crop views, or a failure reason.
- `official_frame_projection_index.jsonl`: depth-tested projection metadata for top full-frame-mined candidates.
- `official_crop_summary.json`: machine-readable frozen crop/QC coverage summary.
- `OFFICIAL_CROP_STATUS.md`: human-readable frozen crop/QC status.
- `p4_qc_report.csv`: relation-level QC table with readiness and failure reasons.
- `p4_sanity_examples.html` and `qc_overlays/`: small diagnostic overlay page for visual spot-checking.
- `sample_load_relation_evidence.py`: tiny loader for querying this layer.

Important boundary: `official_*` crop metadata is the frozen depth-tested evidence layer. Large crop images are generated under ignored `crops_local/` and are not committed; `qc_overlays/` are small diagnostic spot-check artifacts, not training data.
