# Multi-Dataset Functional Query Protocol v1

This protocol defines how functional queries are generated across FunGraph/SceneFun3D and FunTHOR-style functional scene graph datasets.

## Unit

The atomic unit is a directed functional edge:

```text
functional_element_or_subject --relation--> affected_or_anchor_object
```

For FunGraph this edge comes from OpenFunGraph / SceneFun3D relations. For FunTHOR this edge comes from `functional_relations.json`.

## Candidate Set

- FunGraph: exported candidate objects for the scene.
- FunTHOR: visible, non-`Undefined` nodes from `visible/visibility_stats.json` and `annotations_aggregated.json`.

## Query Families

For every visible functional edge, FunTHOR v1 generates exactly 5 queries:

- 3 x `functional_element_selection`: answer is the first node / functional element.
- 2 x `affected_object_selection`: answer is the second node / affected object.

Every generated query keeps `supporting_edge_ids`, target ids, candidate ids, relation category, matching strategy, and review flags.

## Minimal Pairs

For same-scene, same-label, same-relation functional elements, the protocol creates `same_label_functional_element_assignment` minimal pairs. These are diagnostic until human/Dennis signoff.

## FunTHOR v1 Counts

- Raw functional edges: 164
- Visible endpoint edges used for query generation: 161
- Generated FunTHOR functional queries: 805
- Generated FunTHOR minimal pairs: 200

## Paper-Use Boundary

The FunTHOR queries are rule-grounded but still protocol-generated. They are included in the benchmark release as external dataset coverage and should remain paper-disabled until wording review, evidence spot-check, and Dennis signoff.
