# Benchmark Claim Audit - 2026-06-18

This file pins down what the current benchmark can and cannot support. It is a claim guardrail for 3DGraphLLM+ paper planning, not a marketing summary.

## Current Frozen Export

Allowed claims:

- The current 3DGraphLLM-facing export has 683 functional query rows across `functional_500`, `human_133`, and `long_range_50`.
- Those 683 rows collapse to 160 unique `scene-target-anchor-relation` units. Raw row count must not be presented as independent relation coverage.
- The old frozen functional export has full visual evidence coverage: 683 / 683 rows have an inspectable evidence card.
- Within that old full-perception layer, 240 rows have strict depth-tested RGB-D crop evidence and 443 rows use GT pointcloud-render fallback.

Forbidden or unsafe claims:

- Do not claim the existing `functional_500` contains 500 unique functional relations.
- Do not claim every old export row has real camera RGB-D crop evidence; many rows are pointcloud-render fallback.
- Do not use old free-form 3DGraphLLM language-generation scores as functional grounding accuracy.

## Expansion v1 Draft

Allowed claims:

- OpenFunGraph source currently exposes 195 unique functional relation instances over 20 scenes.
- `expansion_v1` contains 585 template-generated draft query variants, three per unique source relation.
- The review workspace contains 195 unique-relation review rows, 585 query wording rows, and 105 minimal-pair review rows.
- The balanced freeze-candidate functional split has 116 rows over 21 exact relation types, with a maximum of 15 rows per exact relation.
- The expanded minimal-pair freeze-candidate split has 60 pairs with changed-factor distribution `{'anchor_object': 15, 'functional_relation': 1, 'spatial_qualifier': 44}`.

Forbidden or unsafe claims:

- Do not call `functional_balanced_116_frozen_candidate.jsonl` a final frozen benchmark split. Its `paper_use_allowed` flag is false until human review and Dennis signoff.
- Do not report the 585 template variants as human-authored queries.
- Do not report the 105 auto-mined minimal pairs as validated contrast pairs before review.
- Do not claim the expansion proves a symbolic graph information ceiling. It only provides coverage and contrast candidates for testing that hypothesis.

## Expansion Perception Evidence

Allowed claims:

- The expansion freeze-candidate evidence layer has 116 / 116 visual evidence cards.
- It adds pointcloud-render evidence for 21 freeze candidates that were not present in the previous full-perception export.
- 46 expansion candidates inherit previous depth-tested RGB-D crop metadata.

Forbidden or unsafe claims:

- Do not claim all 116 expansion candidates have newly mined depth-tested camera crops.
- Do not describe pointcloud-render fallback as real RGB-D camera evidence.
- Do not merge expansion evidence into paper-critical results without review, because query wording is still template-generated.

## Paper-Grade Requirements Before Reporting Expansion Results

A result table using expansion candidates needs all of the following:

1. Human review decisions filled for query wording and target validity.
2. Minimal-pair validity decisions filled for contrast quality.
3. Evidence cards present and manually spot-checked for promoted candidates.
4. Dennis signoff on the final split definition and the exact claims.
5. A frozen manifest that records the final row ids, excluded rows, exclusion reasons, and no post-hoc threshold changes.

## Recommended Paper Wording Right Now

Safe wording:

> We construct a SceneFun3D/OpenFunGraph functional grounding export with 683 query rows, audit its 160 unique scene-target-anchor-relation units, and build a draft expansion workspace covering 195 unique source functional relations. The current paper-critical frozen export has full inspectable visual evidence coverage, while the expansion split remains a review-gated candidate set.

Unsafe wording:

> We benchmark 3DGraphLLM on 500 independent multimodal functional relations.

Reason: the 500-row split is paraphrase-heavy and contains only 83 unique relation units inside `functional_500`.
