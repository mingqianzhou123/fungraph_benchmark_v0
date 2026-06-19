# Expansion v1

This directory is the cleaned expansion workspace for distribution audit, balanced freeze candidates, expansion evidence, AI pre-review, and Dennis signoff. It is not a final paper-frozen split.

## Canonical Files

```text
expansion_manifest_v1.json
DENNIS_BENCHMARK_SIGNOFF_PACKET.md
final_candidates/functional_balanced_116_frozen_candidate.jsonl
final_candidates/minimal_pairs_expanded_60_frozen_candidate.jsonl
ai_prereview_v1/ai_prereview_summary.json
ai_prereview_v1/functional_ai_prereview_v1.csv
ai_prereview_v1/minimal_pair_ai_prereview_v1.csv
ai_prereview_v1/functional_ai_recommended_accept_v1.jsonl
ai_prereview_v1/minimal_pair_ai_recommended_accept_v1.jsonl
perception_evidence/expansion_perception_evidence_summary.json
perception_evidence/expansion_perception_evidence_index.jsonl
perception_evidence/images/
```

## Current Counts

- Functional freeze candidates: 116, across 21 exact relation types.
- Expanded minimal-pair freeze candidates: 60.
- Expansion perception evidence: 116 / 116 visual evidence cards.
- AI pre-review: 69 functional candidates and 16 minimal pairs recommended for human/Dennis spot-check.

## Boundary

All expansion files remain `paper_use_allowed=false`. Use `DENNIS_BENCHMARK_SIGNOFF_PACKET.md` for the next human decision point. Intermediate drafts, pools, review HTML, and duplicate JSONL/CSV views are regenerated under `_intermediate/` and are intentionally not tracked.

## Rebuild

```bash
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_expansion_v1.py --pair-cap 200
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_freeze_candidates_v1.py
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_expansion_perception_evidence_v1.py --write-images
python3 benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/build_ai_prereview_v1.py
```
