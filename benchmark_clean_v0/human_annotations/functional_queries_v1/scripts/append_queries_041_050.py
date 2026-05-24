"""Append queries lr_v1_000041 through lr_v1_000050 to long_range_stress_queries_v1.jsonl.

New scenes: 421254 (4 queries), 422007 (3 queries), 421267 (3 queries).
All are junction_2hop with handle/knob targets on dresser/cabinet anchors.
strict: 6 new, contextual: 4 new -> total after append: strict=26/50=52%.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT_FILE = ROOT / "benchmark_clean_v0" / "human_annotations" / "functional_queries_v1" / "long_range_stress_queries_v1.jsonl"

NEW_QUERIES = [

# ===== SCENE 421254 (4 queries, knob target, dresser/chest-of-drawers anchor) =====
# Two "dresser / chest of drawers" anchors: f1f234c5 (LEFT, x~-1.77) and 97164eaa (RIGHT, x~-0.85)
# 20 total knobs in scene -> 19 same-label distractors per target knob
# LEFT dresser 9 knobs layout (by z desc, x):
#   row1: 8ab6af8d(left-col,z=212.93), a0f8f1a0(right-col,z=212.93)
#   row2: ac42e1c2(left-col,z=212.78), b0aa5f30(right-col,z=212.77)
#   row3: 044038ae(left-col,z=212.61), 6aa841fa(right-col,z=212.61)
#   row4: 2b17304a(left-col,z=212.45), 15a1acd9(right-col,z=212.44)
#   row5: 482d7642(right-col only, z=212.29)
# RIGHT dresser 8 knobs layout:
#   row1: 9bb22a10(left-col,z=212.93), addeffee(right-col,z=212.93)
#   row2: da2d25fc(left-col,z=212.70), 2ffdc7cc(right-col,z=212.70)
#   row3: 3025d034(left-col,z=212.48), f75e1a27(right-col,z=212.48)
#   row4: 0635ce47(left-col,z=212.26), 877bb40d(right-col,z=212.26)

{
    "query_id": "lr_v1_000041",
    "scene_id": "421254",
    "query_text": "Pull the topmost left-column knob on the larger dresser whose second-row left-column knob is directly below it on the same piece of furniture.",
    "query_type": "functional",
    "target_node_id": "8ab6af8d-3cad-4fad-bf78-157916578132",
    "anchor_node_id": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
    "supporting_edge_ids": [
        "8ab6af8d-3cad-4fad-bf78-157916578132|pull to open or close a drawer|f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "ac42e1c2-3ed4-447f-8147-cd903d8eefc5|pull to open or close a drawer|f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "ac42e1c2-3ed4-447f-8147-cd903d8eefc5",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["topmost", "left-column", "second-row", "directly below"],
    "num_same_label_distractors": 19,
    "is_label_only_solvable": False,
    "notes": "Strict: two dresser/chest-of-drawers anchors in scene; anchor label alone gives 2 dressers x multiple knobs. Reference (2nd-row left-col knob on same anchor f1f234c5) disambiguates to left dresser and confirms left column geometry.",
},

{
    "query_id": "lr_v1_000042",
    "scene_id": "421254",
    "query_text": "Pull the topmost right-column knob on the dresser that also has a third-row right-column knob on the same piece of furniture.",
    "query_type": "functional",
    "target_node_id": "a0f8f1a0-fe8d-4eae-b655-66ac3b1ca05f",
    "anchor_node_id": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
    "supporting_edge_ids": [
        "a0f8f1a0-fe8d-4eae-b655-66ac3b1ca05f|pull to open or close a drawer|f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "6aa841fa-6898-401d-a750-0f521b4cafe7|pull to open or close a drawer|f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "6aa841fa-6898-401d-a750-0f521b4cafe7",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["topmost", "right-column", "third-row"],
    "num_same_label_distractors": 19,
    "is_label_only_solvable": False,
    "notes": "Strict: scene has two dresser/chest-of-drawers anchors. Without reference, topmost right-col knob could belong to either dresser. Reference (3rd-row right-col, anchor f1f234c5) uniquely identifies left dresser because row layout differs between the two dressers.",
},

{
    "query_id": "lr_v1_000043",
    "scene_id": "421254",
    "query_text": "Pull the right-side knob in the topmost row of the dresser whose left-side knob in the same top row is positioned immediately to the left of it.",
    "query_type": "functional",
    "target_node_id": "addeffee-87e2-4f20-98bd-589c425f0f07",
    "anchor_node_id": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
    "supporting_edge_ids": [
        "addeffee-87e2-4f20-98bd-589c425f0f07|pull to open or close a drawer|97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "9bb22a10-e42b-46fb-af9b-8a8df7d3f6b3|pull to open or close a drawer|97164eaa-1cf8-49ff-9024-f20d4d64f13e"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "9bb22a10-e42b-46fb-af9b-8a8df7d3f6b3",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "contextual",
    "geometry_cues": ["right-side", "topmost", "left-side", "same top row", "immediately to the left"],
    "num_same_label_distractors": 19,
    "is_label_only_solvable": False,
    "notes": "Contextual: both dressers share the same label, making anchor label alone insufficient to pick the dresser. Reference (top-row left-col knob on same anchor 97164eaa) corroborates the right dresser and top row, but geometry cue 'immediately to the left' provides partial within-row disambiguation.",
},

{
    "query_id": "lr_v1_000044",
    "scene_id": "421254",
    "query_text": "Pull the right-column knob in the lowest drawer row of the dresser that also has a left-column knob at the same height in its bottom row.",
    "query_type": "functional",
    "target_node_id": "877bb40d-b6d8-4716-b958-320b07e6f8d8",
    "anchor_node_id": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
    "supporting_edge_ids": [
        "877bb40d-b6d8-4716-b958-320b07e6f8d8|pull to open or close a drawer|97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "0635ce47-455a-4933-b421-cd5601b7203f|pull to open or close a drawer|97164eaa-1cf8-49ff-9024-f20d4d64f13e"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "0635ce47-455a-4933-b421-cd5601b7203f",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "contextual",
    "geometry_cues": ["right-column", "lowest drawer row", "left-column", "same height", "bottom row"],
    "num_same_label_distractors": 19,
    "is_label_only_solvable": False,
    "notes": "Contextual: two dressers with identical label. Reference (bottom-row left-col on same anchor 97164eaa) corroborates anchor identity and bottom row. Geometry cues 'lowest row right-column' can partly narrow candidates but anchor label ambiguity requires the reference for full disambiguation.",
},

# ===== SCENE 422007 (3 queries, knob target, dresser/chest-of-drawers anchor) =====
# One "dresser / chest of drawers" (8abfd9fd) with 6 knobs in 3 rows x 2 cols
# One "cabinet / closet" (176a66cb) with 6 knobs in 3 rows x 2 cols
# 13 total knobs in scene -> 12 same-label distractors per target knob
# Dresser knobs (by z desc, x):
#   row1: e46875af(left-col,z=171.89,x=-1.85), 10205bba(right-col,z=171.89,x=-1.46)
#   row2: 5bdc73ae(left-col,z=171.67,x=-1.85), 61397967(right-col,z=171.66,x=-1.46)
#   row3: 43347ad2(left-col,z=171.41,x=-1.85), 529788c6(right-col,z=171.41,x=-1.47)

{
    "query_id": "lr_v1_000045",
    "scene_id": "422007",
    "query_text": "Pull the top-row left-column knob on the dresser whose top-row right-column knob is directly beside it on the same piece of furniture.",
    "query_type": "functional",
    "target_node_id": "e46875af-6491-4159-9306-19911e41515c",
    "anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "supporting_edge_ids": [
        "e46875af-6491-4159-9306-19911e41515c|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061",
        "10205bba-224b-4807-9db9-d32b9d656899|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "10205bba-224b-4807-9db9-d32b9d656899",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["top-row", "left-column", "right-column", "directly beside"],
    "num_same_label_distractors": 12,
    "is_label_only_solvable": False,
    "notes": "Strict: scene has two furniture pieces with knobs (dresser and cabinet/closet), both with knobs at overlapping z ranges. Anchor label (dresser/chest of drawers) is unique, but within the dresser there are 6 knobs. Reference (top-right knob, same anchor) uniquely pins the top row and confirms the left-col assignment.",
},

{
    "query_id": "lr_v1_000046",
    "scene_id": "422007",
    "query_text": "Pull the bottom-row left-column knob on the dresser that also has a bottom-row right-column knob at the same height on the same furniture.",
    "query_type": "functional",
    "target_node_id": "43347ad2-c581-495f-a584-e6ac18620789",
    "anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "supporting_edge_ids": [
        "43347ad2-c581-495f-a584-e6ac18620789|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061",
        "529788c6-7f9b-48af-81e8-13ba7a2b2499|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "529788c6-7f9b-48af-81e8-13ba7a2b2499",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["bottom-row", "left-column", "right-column", "same height"],
    "num_same_label_distractors": 12,
    "is_label_only_solvable": False,
    "notes": "Strict: dresser has 6 knobs in 3 rows. Bottom-row knobs of cabinet/closet are at similar z (~171.41) creating height ambiguity. Without reference, bottom-left knob could be on either furniture piece. Reference (bottom-right on dresser anchor 8abfd9fd) resolves the anchor and confirms row.",
},

{
    "query_id": "lr_v1_000047",
    "scene_id": "422007",
    "query_text": "Pull the middle-row right-column knob on the dresser that also has a middle-row left-column knob on its same furniture piece.",
    "query_type": "functional",
    "target_node_id": "61397967-d5dc-4a02-905a-fadb3e966abc",
    "anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "supporting_edge_ids": [
        "61397967-d5dc-4a02-905a-fadb3e966abc|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061",
        "5bdc73ae-9e12-4d44-8821-bb748b42866f|pull to open or close a drawer|8abfd9fd-4b8a-421a-981d-32f56cae3061"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "knob --pull to open or close a drawer--> dresser / chest of drawers",
        "knob --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "knob",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "8abfd9fd-4b8a-421a-981d-32f56cae3061",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "5bdc73ae-9e12-4d44-8821-bb748b42866f",
    "reference_label": "knob",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "contextual",
    "geometry_cues": ["middle-row", "right-column", "left-column"],
    "num_same_label_distractors": 12,
    "is_label_only_solvable": False,
    "notes": "Contextual: anchor (dresser/chest of drawers) is unique in scene. Within the dresser, middle-row right-col is one of 6 knobs. Reference (middle-row left-col on same anchor) corroborates row identity but combined geometry cues already substantially narrow the candidates on this unique dresser.",
},

# ===== SCENE 421267 (3 queries, handle target, dresser/chest-of-drawers anchor) =====
# One "dresser / chest of drawers" (7a40a053) with 6 handles via "pull to open or close a drawer"
# One "glass door" (e32e7ae8) with 2 handles via "rotate to open or close" (different relation)
# 8 total handles in scene -> 7 same-label distractors per target handle
# Dresser handles (by z desc, x):
#   row1: a525305a(right-col,z=215.21,x=-2.37), d4851784(left-col,z=215.21,x=-2.73)
#   row2: 64769d1c(right-col,z=214.98,x=-2.37), d1aa6377(left-col,z=214.98,x=-2.72)
#   row3: e5005f56(right-col,z=214.72,x=-2.37), 9a1fc970(left-col,z=214.72,x=-2.72)

{
    "query_id": "lr_v1_000048",
    "scene_id": "421267",
    "query_text": "Pull the top-row left-column handle on the dresser whose top-row right-column handle is directly to its right on the same piece of furniture.",
    "query_type": "functional",
    "target_node_id": "d4851784-f51f-426a-acf3-ca0eeb595add",
    "anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "supporting_edge_ids": [
        "d4851784-f51f-426a-acf3-ca0eeb595add|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36",
        "a525305a-4203-4fff-9d2f-54dec37a7722|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "handle --pull to open or close a drawer--> dresser / chest of drawers",
        "handle --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "handle",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "a525305a-4203-4fff-9d2f-54dec37a7722",
    "reference_label": "handle",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["top-row", "left-column", "right-column", "directly to its right"],
    "num_same_label_distractors": 7,
    "is_label_only_solvable": False,
    "notes": "Strict: 8 handles in scene (6 dresser + 2 glass-door). Anchor (dresser/chest of drawers) is unique, narrowing to 6 handles. Glass door handles (z~215.57) overlap in height with top-row dresser handles (z~215.21), creating ambiguity. Reference (top-right handle on same anchor) conclusively identifies the dresser and top row.",
},

{
    "query_id": "lr_v1_000049",
    "scene_id": "421267",
    "query_text": "Pull the bottom-row left-column handle on the dresser that also has a bottom-row right-column handle at the same height on its furniture.",
    "query_type": "functional",
    "target_node_id": "9a1fc970-494b-4e42-8529-98a91f255ba7",
    "anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "supporting_edge_ids": [
        "9a1fc970-494b-4e42-8529-98a91f255ba7|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36",
        "e5005f56-18e2-444e-9d2c-d6fb588fb672|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "handle --pull to open or close a drawer--> dresser / chest of drawers",
        "handle --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "handle",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "e5005f56-18e2-444e-9d2c-d6fb588fb672",
    "reference_label": "handle",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "strict",
    "geometry_cues": ["bottom-row", "left-column", "right-column", "same height"],
    "num_same_label_distractors": 7,
    "is_label_only_solvable": False,
    "notes": "Strict: 8 handles in scene. Dresser bottom-row handles (z~214.72) are the lowest of the 6 dresser handles, but without knowing the anchor, model could confuse with glass-door handles (z~215.57) or middle-row dresser handles. Reference (bottom-right on same anchor) confirms both dresser and bottom row.",
},

{
    "query_id": "lr_v1_000050",
    "scene_id": "421267",
    "query_text": "Pull the middle-row right-column handle on the dresser that also has a middle-row left-column handle on the same piece of furniture.",
    "query_type": "functional",
    "target_node_id": "64769d1c-3a54-4e23-872d-cf2a5770db2b",
    "anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "supporting_edge_ids": [
        "64769d1c-3a54-4e23-872d-cf2a5770db2b|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36",
        "d1aa6377-5e75-44be-a4b0-e32c4330edc3|pull to open or close a drawer|7a40a053-a0ee-459d-86c4-fbc6f520cf36"
    ],
    "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
    "is_long_range": True,
    "evidence_chain": [
        "handle --pull to open or close a drawer--> dresser / chest of drawers",
        "handle --pull to open or close a drawer--> dresser / chest of drawers"
    ],
    "source": "human_phase4",
    "target_label": "handle",
    "anchor_label": "dresser / chest of drawers",
    "shared_anchor_node_id": "7a40a053-a0ee-459d-86c4-fbc6f520cf36",
    "shared_anchor_label": "dresser / chest of drawers",
    "reference_node_id": "d1aa6377-5e75-44be-a4b0-e32c4330edc3",
    "reference_label": "handle",
    "reference_relation": "pull to open or close a drawer",
    "long_range_pattern": "junction_2hop",
    "evidence_hop_count": 2,
    "reference_necessity": "contextual",
    "geometry_cues": ["middle-row", "right-column", "left-column"],
    "num_same_label_distractors": 7,
    "is_label_only_solvable": False,
    "notes": "Contextual: anchor (dresser/chest of drawers) is unique in scene, narrowing to 6 dresser handles. Reference (middle-row left-col on same anchor) corroborates anchor and row, but combined geometry cues 'middle-row right-column' on the only dresser substantially narrow the target already.",
},

]


def main() -> None:
    with OUT_FILE.open("a", encoding="utf-8") as f:
        for q in NEW_QUERIES:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    print(f"Appended {len(NEW_QUERIES)} queries to {OUT_FILE.name}")

    lines = OUT_FILE.read_text(encoding="utf-8").splitlines()
    print(f"Total queries in file: {len(lines)}")

    strict = sum(1 for ln in lines if json.loads(ln).get("reference_necessity") == "strict")
    contextual = sum(1 for ln in lines if json.loads(ln).get("reference_necessity") == "contextual")
    print(f"strict: {strict} ({strict/len(lines)*100:.1f}%), contextual: {contextual} ({contextual/len(lines)*100:.1f}%)")

    scenes = {}
    for ln in lines:
        sid = json.loads(ln)["scene_id"]
        scenes[sid] = scenes.get(sid, 0) + 1
    print("Scene distribution:", dict(sorted(scenes.items())))


if __name__ == "__main__":
    main()
