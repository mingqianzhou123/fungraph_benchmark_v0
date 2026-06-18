# Benchmark Expansion v1 Status

This directory is a draft workspace for distribution audit, unique-relation expansion, and minimal-pair expansion. It does not replace frozen eval files.

## Current Export Audit

- Current query rows: 683
- Current unique scene-target-anchor-relation keys: 160
- Max paraphrases per relation group: 10

## Unique-Relation Expansion

- OpenFunGraph unique functional relations available: 195
- Template-generated query drafts: 585
- Previous-export depth-tested RGB-D crop relations: 48
- Relations not present in previous full-perception export: 35
- Target coverage policy: 3 query variants per unique relation.

## Minimal-Pair Expansion

- Auto-mined pair candidates: 105
- Changed-factor distribution: {'spatial_qualifier': 89, 'anchor_object': 15, 'functional_relation': 1}

## Boundary

Expansion query drafts and pair candidates are generated from verified graph relations, but their natural-language wording is not final human annotation. Use them for coverage planning, model debugging, and human review queues before paper-grade reporting.
Relations not present in the previous full-perception export need an evidence-generation pass before this draft is promoted to a frozen eval split.
