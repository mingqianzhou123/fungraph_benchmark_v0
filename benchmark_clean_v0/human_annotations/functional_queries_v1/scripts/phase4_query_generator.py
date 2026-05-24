"""Phase 4: Long-Range Stress Query Generator.

Generates `long_range_stress_queries_v1.jsonl` and `long_range_diagnostics_v1.jsonl`
from hand-crafted junction-2hop specs. Idempotent — re-running produces the same
output. All UUIDs and edges are validated against frozen scene_graph data.

Schema follows phase4.md §"Schema 详解". Each query has:
  - is_long_range = True
  - supporting_edge_ids: 2 edges sharing the anchor (junction 2-hop)
  - target_node_id ≠ shared_anchor_node_id ≠ reference_node_id

Outputs:
    long_range_stress_queries_v1.jsonl  - 30 main queries
    long_range_diagnostics_v1.jsonl     - matching diagnostics (1-to-1)
    (stdout)                              - per-spec validation log
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
ENRICH_PATH = BENCH_ROOT / "queries" / "scenefun3d_funrag_benchmark_enriched.json"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
OUT_MAIN = OUT_DIR / "long_range_stress_queries_v1.jsonl"
OUT_DIAG = OUT_DIR / "long_range_diagnostics_v1.jsonl"

# ---------------------------------------------------------------------------
# 30 hand-crafted query specifications.
#
# Each spec contains:
#   id              - lr_v1_NNNNNN
#   scene_id        - SceneFun3D scene_id
#   target_uuid     - source UUID of edge 1 (the operated element)
#   target_rel      - relation of edge 1 (target -> anchor)
#   anchor_uuid     - shared anchor (right side of both edges)
#   reference_uuid  - source UUID of edge 2
#   reference_rel   - relation of edge 2 (reference -> anchor)
#   query_text      - natural-language query
#   tags            - difficulty_tags (must include "long_range")
#   geom_cues       - optional list (strings like "leftmost", "topmost")
#   ref_necessity   - "strict" or "contextual"
#   label_only      - is_label_only_solvable (bool)
#   fail_modes      - expected_failure_modes (list)
#   notes           - one-line rationale
# ---------------------------------------------------------------------------

SPECS = [
    # ==============================================================
    # 469011 oven (5 strict queries) — 5 knob targets + 1 handle ref
    # Knob x-positions (left to right):
    #   d003c3b8 (x=2.492) leftmost
    #   06b684bb (x=2.528) 2nd-from-left
    #   28e9ec26 (x=2.581) middle
    #   76002344 (x=2.700) 2nd-from-right
    #   85f5f2f0 (x=2.814) rightmost
    # Without reference, "leftmost knob that rotates an appliance" -> 6 rotate-knobs
    # in scene (5 on oven + 1 on dishwasher); leftmost flips to ba5246d7 (x=0.848).
    # With reference, narrows to 5 oven knobs.
    # ==============================================================
    {
        "id": "lr_v1_000001",
        "scene_id": "469011",
        "target_uuid": "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "reference_uuid": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "reference_rel": "pull to open or close",
        "query_text": "Rotate the leftmost knob that adjusts a kitchen appliance whose door is pulled open by a handle.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["leftmost"],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_dishwasher_knob", "pick_cabinet_knob", "pick_handle_as_target"],
        "notes": "Strict: erasing 'pulled open by a handle' lets leftmost flip to dishwasher knob ba5246d7 (x=0.848). With reference, candidates narrow to 5 oven knobs; leftmost = d003c3b8 (x=2.492).",
    },
    {
        "id": "lr_v1_000002",
        "scene_id": "469011",
        "target_uuid": "06b684bb-7a5c-4717-847a-d343bd6824d9",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "reference_uuid": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "reference_rel": "pull to open or close",
        "query_text": "Rotate the second-from-left knob that adjusts a kitchen appliance whose door is pulled open by a handle.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["second-from-left"],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_other_oven_knob", "pick_cabinet_knob"],
        "notes": "Strict: among 5 oven knobs, 2nd-from-left x=2.528.",
    },
    {
        "id": "lr_v1_000003",
        "scene_id": "469011",
        "target_uuid": "28e9ec26-d38b-45a2-9614-9fe6a8d69211",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "reference_uuid": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "reference_rel": "pull to open or close",
        "query_text": "Rotate the middle knob that adjusts a kitchen appliance whose door is pulled open by a handle.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["middle"],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_other_oven_knob"],
        "notes": "Strict: among 5 oven knobs, middle (3rd) x=2.581.",
    },
    {
        "id": "lr_v1_000004",
        "scene_id": "469011",
        "target_uuid": "76002344-9de9-476f-a43e-d822d1cdb592",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "reference_uuid": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "reference_rel": "pull to open or close",
        "query_text": "Rotate the second-from-right knob that adjusts a kitchen appliance whose door is pulled open by a handle.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["second-from-right"],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_other_oven_knob"],
        "notes": "Strict: among 5 oven knobs, 2nd-from-right x=2.700.",
    },
    {
        "id": "lr_v1_000005",
        "scene_id": "469011",
        "target_uuid": "85f5f2f0-ef9b-4e32-a0de-cd8a7f54db4b",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "reference_uuid": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "reference_rel": "pull to open or close",
        "query_text": "Rotate the rightmost knob that adjusts a kitchen appliance whose door is pulled open by a handle.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["rightmost"],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_other_oven_knob"],
        "notes": "Strict: among 5 oven knobs, rightmost x=2.814.",
    },

    # ==============================================================
    # 469011 fridge (2 strict queries)
    # ==============================================================
    {
        "id": "lr_v1_000006",
        "scene_id": "469011",
        "target_uuid": "548a6569-5c70-4d7b-9f10-0ece005e6c00",
        "target_rel": "provide power",
        "anchor_uuid": "7fddf637-3da9-4511-b4b4-fc6a042db72c",
        "reference_uuid": "2abcdace-ba3f-45c0-8dce-eac4de015ee8",
        "reference_rel": "pull to open or close",
        "query_text": "Which electric outlet provides power to an appliance whose door is pulled open by a handle?",
        "tags": ["long_range", "functional_relation", "hard_negative"],
        "geom_cues": [],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_outlet_powering_hood", "pick_unconnected_outlet"],
        "notes": "Strict: scene has 2 power-providing outlets (548a6569->fridge, 0146b63e->exhaust hood). Without reference, both qualify. With 'handle pulls door open' filter, hood has no handle -> only fridge -> outlet 548a6569.",
    },
    {
        "id": "lr_v1_000007",
        "scene_id": "469011",
        "target_uuid": "2abcdace-ba3f-45c0-8dce-eac4de015ee8",
        "target_rel": "pull to open or close",
        "anchor_uuid": "7fddf637-3da9-4511-b4b4-fc6a042db72c",
        "reference_uuid": "548a6569-5c70-4d7b-9f10-0ece005e6c00",
        "reference_rel": "provide power",
        "query_text": "Which handle pulls open the door of an appliance that is also powered by an electric outlet?",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "hard_negative"],
        "geom_cues": [],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_oven_handle"],
        "notes": "Strict: scene has 2 handles (2abcdace->fridge, 47d6518d->oven). Oven is NOT powered by outlet; fridge is. With reference filter -> 2abcdace.",
    },

    # ==============================================================
    # 421380 TV stand (8 contextual queries) — door knob + drawer knob
    # All on same TV stand 6e39c1ea; TV stand is unique anchor in scene
    # so reference is contextual (provides 2-hop evidence but doesn't
    # strictly disambiguate).
    #
    # Door knobs left-to-right:
    #   bc40c514 (x=0.652) leftmost
    #   9db14ed4 (x=0.690) 2nd-from-left
    #   f263ca02 (x=1.848) 2nd-from-right
    #   64dde80b (x=1.885) rightmost
    #
    # Cluster A (x~1.07) drawer knobs top-to-bottom by z:
    #   282c10c9 z=193.749 topmost
    #   927cd15d z=193.658
    #   f26835a1 z=193.568
    #   bb923245 z=193.478
    #   08a1222a z=193.346 bottommost
    # Cluster B (x~1.47) drawer knobs top-to-bottom:
    #   352d3a71 z=193.750 topmost
    #   73839439 z=193.660
    #   1365989c z=193.568
    #   8fa63b99 z=193.477
    #   2569559b z=193.348 bottommost
    # ==============================================================
    {
        "id": "lr_v1_000008",
        "scene_id": "421380",
        "target_uuid": "bc40c514-1f23-4a0f-b9c6-a3aee1416269",
        "target_rel": "pull to open or close",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "282c10c9-3020-4333-b468-cb3197b80940",
        "reference_rel": "pull to open or close a drawer",
        "query_text": "Pull the leftmost knob that opens a cabinet door of a television stand whose top-row drawer is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["leftmost"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_drawer_knob_as_target", "pick_radiator_knob"],
        "notes": "Contextual: TV stand is unique anchor in scene; reference (drawer knob) doesn't narrow anchor. Target leftmost door knob bc40c514 (x=0.652).",
    },
    {
        "id": "lr_v1_000009",
        "scene_id": "421380",
        "target_uuid": "9db14ed4-ed96-4e43-a12d-7a1a865f0161",
        "target_rel": "pull to open or close",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "927cd15d-3bd7-4709-b88d-6e4c8b8afca4",
        "reference_rel": "pull to open or close a drawer",
        "query_text": "Pull the second-from-left knob that opens a cabinet door of a television stand whose second-row drawer is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["second-from-left"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_drawer_knob"],
        "notes": "Contextual: 4 door knobs, 2nd-from-left x=0.690.",
    },
    {
        "id": "lr_v1_000010",
        "scene_id": "421380",
        "target_uuid": "f263ca02-a3c0-4b5f-bd3e-2866f0c9a9ec",
        "target_rel": "pull to open or close",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "bb923245-a044-4875-b548-bee144ca7d2a",
        "reference_rel": "pull to open or close a drawer",
        "query_text": "Pull the second-from-right knob that opens a cabinet door of a television stand whose middle drawer is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["second-from-right"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_drawer_knob"],
        "notes": "Contextual: 4 door knobs, 2nd-from-right x=1.848.",
    },
    {
        "id": "lr_v1_000011",
        "scene_id": "421380",
        "target_uuid": "64dde80b-d956-4d15-8305-58466e31648f",
        "target_rel": "pull to open or close",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "08a1222a-4837-49cf-a0c6-836d236311a0",
        "reference_rel": "pull to open or close a drawer",
        "query_text": "Pull the rightmost knob that opens a cabinet door of a television stand whose bottom-row drawer is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "geom_cues": ["rightmost"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_drawer_knob"],
        "notes": "Contextual: 4 door knobs, rightmost x=1.885.",
    },
    {
        "id": "lr_v1_000012",
        "scene_id": "421380",
        "target_uuid": "282c10c9-3020-4333-b468-cb3197b80940",
        "target_rel": "pull to open or close a drawer",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "bc40c514-1f23-4a0f-b9c6-a3aee1416269",
        "reference_rel": "pull to open or close",
        "query_text": "Pull the topmost drawer knob in the inner-left column of a television stand whose leftmost cabinet door is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware", "multi_anchor"],
        "geom_cues": ["topmost", "inner-left column"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_door_knob", "pick_other_cluster_drawer_knob"],
        "notes": "Contextual: cluster A topmost drawer knob 282c10c9 (x=1.068, z=193.749). Reference identifies TV stand but anchor is unique.",
    },
    {
        "id": "lr_v1_000013",
        "scene_id": "421380",
        "target_uuid": "352d3a71-9681-4a32-aecd-1d89a929bd7b",
        "target_rel": "pull to open or close a drawer",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "64dde80b-d956-4d15-8305-58466e31648f",
        "reference_rel": "pull to open or close",
        "query_text": "Pull the topmost drawer knob in the inner-right column of a television stand whose rightmost cabinet door is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware", "multi_anchor"],
        "geom_cues": ["topmost", "inner-right column"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_cluster_A_drawer_knob", "pick_door_knob"],
        "notes": "Contextual: cluster B topmost drawer knob 352d3a71 (x=1.468, z=193.750).",
    },
    {
        "id": "lr_v1_000014",
        "scene_id": "421380",
        "target_uuid": "08a1222a-4837-49cf-a0c6-836d236311a0",
        "target_rel": "pull to open or close a drawer",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "bc40c514-1f23-4a0f-b9c6-a3aee1416269",
        "reference_rel": "pull to open or close",
        "query_text": "Pull the bottommost drawer knob in the inner-left column of a television stand whose leftmost cabinet door is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware", "multi_anchor"],
        "geom_cues": ["bottommost", "inner-left column"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_topmost_drawer_knob", "pick_cluster_B_drawer_knob"],
        "notes": "Contextual: cluster A bottommost drawer knob 08a1222a (z=193.346).",
    },
    {
        "id": "lr_v1_000015",
        "scene_id": "421380",
        "target_uuid": "2569559b-e5fd-4e92-a533-308098b6becd",
        "target_rel": "pull to open or close a drawer",
        "anchor_uuid": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "reference_uuid": "64dde80b-d956-4d15-8305-58466e31648f",
        "reference_rel": "pull to open or close",
        "query_text": "Pull the bottommost drawer knob in the inner-right column of a television stand whose rightmost cabinet door is opened by another knob.",
        "tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware", "multi_anchor"],
        "geom_cues": ["bottommost", "inner-right column"],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_topmost_drawer_knob", "pick_cluster_A_drawer_knob"],
        "notes": "Contextual: cluster B bottommost drawer knob 2569559b (z=193.348).",
    },

    # ==============================================================
    # 460417 washing machine + dryer (5 queries; mostly contextual; q17 strict)
    # ==============================================================
    {
        "id": "lr_v1_000016",
        "scene_id": "460417",
        "target_uuid": "ca9e7157-7222-4429-8629-add94f3fc620",
        "target_rel": "press to open or close, or adjust the setting",
        "anchor_uuid": "66ce5acd-9d4e-4b6b-af9e-fde601c66cb6",
        "reference_uuid": "a6956e03-3809-409c-b16d-cee0ef3e1246",
        "reference_rel": "rotate or press to adjust the setting",
        "query_text": "Press the button on an appliance whose setting is also adjusted by a separate rotate-and-press knob/button.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_unrelated_button"],
        "notes": "Contextual: scene has only one 'press' source on washing machine; target ca9e7157 is unique without reference.",
    },
    {
        "id": "lr_v1_000017",
        "scene_id": "460417",
        "target_uuid": "a6956e03-3809-409c-b16d-cee0ef3e1246",
        "target_rel": "rotate or press to adjust the setting",
        "anchor_uuid": "66ce5acd-9d4e-4b6b-af9e-fde601c66cb6",
        "reference_uuid": "ca9e7157-7222-4429-8629-add94f3fc620",
        "reference_rel": "press to open or close, or adjust the setting",
        "query_text": "Rotate the knob that adjusts an appliance also operated by a press button.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_dryer_knob", "pick_oven_knob"],
        "notes": "Strict: scene has 2 rotate-adjust knobs (a6956e03 on WM, f845e4b3 on dryer). Reference 'press button' filters to WM (dryer has no press source). -> a6956e03.",
    },
    {
        "id": "lr_v1_000018",
        "scene_id": "460417",
        "target_uuid": "59552624-a2f6-4e2b-9a25-9d62b675cada",
        "target_rel": "provide power",
        "anchor_uuid": "66ce5acd-9d4e-4b6b-af9e-fde601c66cb6",
        "reference_uuid": "ca9e7157-7222-4429-8629-add94f3fc620",
        "reference_rel": "press to open or close, or adjust the setting",
        "query_text": "Which electric outlet provides power to an appliance whose setting is adjusted by pressing a button?",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_shared_outlet"],
        "notes": "Contextual: both 59552624 and 9f510124 power WM. Reference doesn't narrow further. Picked 59552624 as canonical 'powers the appliance'.",
    },
    {
        "id": "lr_v1_000019",
        "scene_id": "460417",
        "target_uuid": "9f510124-f6aa-4b15-9aa0-4eece6c68650",
        "target_rel": "provide power",
        "anchor_uuid": "3f5fc8ad-60c9-4b6e-a323-a919410bdd1a",
        "reference_uuid": "f845e4b3-a202-4e17-8100-a41736068ffc",
        "reference_rel": "rotate to adjust the setting",
        "query_text": "Which electric outlet provides power to an appliance whose setting is adjusted by rotating a knob, without any press button?",
        "tags": ["long_range", "functional_relation", "hard_negative"],
        "geom_cues": [],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_outlet_powering_WM"],
        "notes": "Strict: scene outlets 59552624 (powers WM only) and 9f510124 (powers WM+dryer). WM has press button; dryer doesn't. 'No press button' filters to dryer; outlets powering dryer = 9f510124 only.",
    },
    {
        "id": "lr_v1_000020",
        "scene_id": "460417",
        "target_uuid": "f845e4b3-a202-4e17-8100-a41736068ffc",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "3f5fc8ad-60c9-4b6e-a323-a919410bdd1a",
        "reference_uuid": "9f510124-f6aa-4b15-9aa0-4eece6c68650",
        "reference_rel": "provide power",
        "query_text": "Rotate the knob that adjusts an appliance whose only control elements are this knob and an outlet providing power.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_WM_knob_button"],
        "notes": "Contextual: dryer's only interactive elements are this knob + outlet. WM has additional button. Reference is contextual since 'rotate' filter + 'only knob and outlet' already narrows to dryer.",
    },

    # ==============================================================
    # 421063 sink + bathtub (2 contextual queries)
    # ==============================================================
    {
        "id": "lr_v1_000021",
        "scene_id": "421063",
        "target_uuid": "b0e7459d-07a3-41a9-af61-18f99260e1d3",
        "target_rel": "press or rotate to control the water flow",
        "anchor_uuid": "c4a12f33-c0ab-45d2-bea0-9710e08ef8c4",
        "reference_uuid": "a54cd1df-50ca-4ca9-b3c0-136fe9224393",
        "reference_rel": "control the water flow",
        "query_text": "Press or rotate the button/knob that controls water flow into the sink, where the same flow is also controlled by a faucet/handle.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_bathtub_button"],
        "notes": "Contextual: sink directly named in query_text. Reference adds 2-hop evidence (faucet controls same water flow) but doesn't strictly disambiguate.",
    },
    {
        "id": "lr_v1_000022",
        "scene_id": "421063",
        "target_uuid": "1e33ac6a-7344-4c07-a5a0-d3ff74760222",
        "target_rel": "press or rotate to control the water flow",
        "anchor_uuid": "b0e10097-ce1f-46d7-8905-b820e381c43e",
        "reference_uuid": "8c74ba89-2f15-4638-97e0-c1a8c294a25e",
        "reference_rel": "control the water flow",
        "query_text": "Press or rotate the button/knob that controls water flow into the bathtub, where the same flow is also controlled by a faucet/handle.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_sink_button"],
        "notes": "Contextual: bathtub directly named.",
    },

    # ==============================================================
    # 422813 bathroom sink + bathtub (2 contextual queries)
    # ==============================================================
    {
        "id": "lr_v1_000023",
        "scene_id": "422813",
        "target_uuid": "1deb7d86-ff85-4dd9-bab3-fefffa2ddcdb",
        "target_rel": "press or rotate to control the water flow",
        "anchor_uuid": "649f5431-e6cb-4760-a70f-ffa2ed3ac707",
        "reference_uuid": "b012412a-0a59-46b6-a39c-0be4984a68b3",
        "reference_rel": "control the water flow",
        "query_text": "Press or rotate the button/knob that controls water flow into the bathroom sink, where the same flow is also controlled by a handle/faucet.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_bathtub_button"],
        "notes": "Contextual: bathroom sink directly named.",
    },
    {
        "id": "lr_v1_000024",
        "scene_id": "422813",
        "target_uuid": "8315a573-603f-4a3c-9fc6-902a8ab19ad0",
        "target_rel": "press or rotate to control the water flow",
        "anchor_uuid": "bb70dccc-863c-446d-a1b2-66ca94a389ed",
        "reference_uuid": "381968b3-9045-484b-bf77-ea95b427a529",
        "reference_rel": "control the water flow",
        "query_text": "Press or rotate the button/knob that controls water flow into the bathtub, where the same flow is also controlled by a handle/faucet.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": ["pick_bathroom_sink_button"],
        "notes": "Contextual: bathtub directly named.",
    },

    # ==============================================================
    # 422391 TV (1 strict + 1 contextual)
    # ==============================================================
    {
        "id": "lr_v1_000025",
        "scene_id": "422391",
        "target_uuid": "661e73fc-d5d2-4fb5-bf4b-c58fd161a5f0",
        "target_rel": "provide power",
        "anchor_uuid": "f0591cae-944d-4804-80f2-b1495c33437b",
        "reference_uuid": "e4a3d21d-915d-43d2-8559-8b9d2974a622",
        "reference_rel": "control",
        "query_text": "Which electric outlet or power strip provides power to a device that is also operated by a remote control?",
        "tags": ["long_range", "functional_relation", "hard_negative"],
        "geom_cues": [],
        "ref_necessity": "strict",
        "label_only": False,
        "fail_modes": ["pick_outlet_powering_non_TV_device"],
        "notes": "Strict: scene may have other power-providing outlets to non-TV devices; 'controlled by remote' filters to TV only -> outlet 661e73fc.",
    },
    {
        "id": "lr_v1_000026",
        "scene_id": "422391",
        "target_uuid": "e4a3d21d-915d-43d2-8559-8b9d2974a622",
        "target_rel": "control",
        "anchor_uuid": "f0591cae-944d-4804-80f2-b1495c33437b",
        "reference_uuid": "661e73fc-d5d2-4fb5-bf4b-c58fd161a5f0",
        "reference_rel": "provide power",
        "query_text": "Which remote control operates the television that is powered by an electric outlet or power strip?",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": [],
        "notes": "Contextual: TV directly named; single remote in scene, so target unique without reference.",
    },

    # ==============================================================
    # 466192 bathroom sink (2 contextual queries)
    # ==============================================================
    {
        "id": "lr_v1_000027",
        "scene_id": "466192",
        "target_uuid": "9311f0c0-33b1-4b61-8ef7-1d2dc24c903a",
        "target_rel": "control the water flow",
        "anchor_uuid": "87da20eb-b2be-450b-b42e-b9d6f49ca0d4",
        "reference_uuid": "83da9fe4-5d04-4f73-b9dd-f3a91d273cd0",
        "reference_rel": "press or rotate to  control the water flow",
        "query_text": "Which faucet/knob/handle controls water flow into the bathroom sink, where the same flow is also controlled by a button/knob that can be pressed or rotated?",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": [],
        "notes": "Contextual: single bathroom sink in scene; target unique even without reference.",
    },
    {
        "id": "lr_v1_000028",
        "scene_id": "466192",
        "target_uuid": "83da9fe4-5d04-4f73-b9dd-f3a91d273cd0",
        "target_rel": "press or rotate to  control the water flow",
        "anchor_uuid": "87da20eb-b2be-450b-b42e-b9d6f49ca0d4",
        "reference_uuid": "9311f0c0-33b1-4b61-8ef7-1d2dc24c903a",
        "reference_rel": "control the water flow",
        "query_text": "Press or rotate the button/knob that controls water flow into the bathroom sink, where the same flow is also controlled by a faucet/knob/handle.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": [],
        "notes": "Contextual: single bathroom sink; reverse-direction pair of q027.",
    },

    # ==============================================================
    # 466803 washing machine (2 contextual queries) — power strip case
    # ==============================================================
    {
        "id": "lr_v1_000029",
        "scene_id": "466803",
        "target_uuid": "94276ce1-f267-425a-87fb-7cd12d491730",
        "target_rel": "rotate to adjust the setting",
        "anchor_uuid": "6c6ea5f0-b56c-4055-9596-7aa2fa455c25",
        "reference_uuid": "ab926265-13ac-459c-8d19-b6b66ef491da",
        "reference_rel": "provide power",
        "query_text": "Rotate the knob that adjusts the setting of a washing machine which is powered by a power strip.",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": [],
        "notes": "Contextual: single washing machine in scene; target unique even without reference.",
    },
    {
        "id": "lr_v1_000030",
        "scene_id": "466803",
        "target_uuid": "ab926265-13ac-459c-8d19-b6b66ef491da",
        "target_rel": "provide power",
        "anchor_uuid": "6c6ea5f0-b56c-4055-9596-7aa2fa455c25",
        "reference_uuid": "94276ce1-f267-425a-87fb-7cd12d491730",
        "reference_rel": "rotate to adjust the setting",
        "query_text": "Which power strip provides power to a washing machine whose setting is adjusted by rotating a knob?",
        "tags": ["long_range", "functional_relation"],
        "geom_cues": [],
        "ref_necessity": "contextual",
        "label_only": False,
        "fail_modes": [],
        "notes": "Contextual: single power strip in scene; reverse-direction pair of q029.",
    },
]


# ---------------------------------------------------------------------------


def load_scene_graphs(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    out: dict[str, dict] = {}
    for item in data["data"]:
        sid = item["scene_id"]
        if sid not in out and item.get("scene_graph"):
            out[sid] = item["scene_graph"]
    return out


def load_geometry(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def euclidean(a: list, b: list) -> float:
    return ((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2) ** 0.5


def build_edge_lookup(sg: dict) -> dict[tuple, str]:
    """Return {(src_uuid, relation, tgt_uuid): edge_id_string}."""
    out: dict[tuple, str] = {}
    for e in sg.get("edges", []):
        eid = e["edge_id"]
        parts = eid.split("|")
        if len(parts) != 3:
            continue
        out[(parts[0], parts[1], parts[2])] = eid
    return out


def build_node_lookup(sg: dict) -> dict[str, str]:
    """Return {node_id: label}."""
    return {n["node_id"]: n["label"] for n in sg.get("nodes", [])}


def count_same_label_distractors(target_label: str, target_uuid: str, sg: dict) -> tuple[int, list[str]]:
    """Count same-label nodes (excluding target and 'unknown' label)."""
    if target_label == "unknown":
        return 0, []
    distractors = [
        n["node_id"] for n in sg.get("nodes", [])
        if n["label"] == target_label and n["node_id"] != target_uuid
    ]
    return len(distractors), distractors


def main():
    scene_graphs = load_scene_graphs(ENRICH_PATH)
    geom = load_geometry(GEOM_PATH)
    print(f"Loaded {len(scene_graphs)} scene graphs, {len(geom)} geom entries")

    main_rows: list[dict] = []
    diag_rows: list[dict] = []
    seen_ids: set[str] = set()

    for i, spec in enumerate(SPECS):
        sid = spec["scene_id"]
        if sid not in scene_graphs:
            sys.exit(f"ERROR spec[{i}] {spec['id']}: scene_id {sid} not in enriched JSON")
        sg = scene_graphs[sid]
        scene_geom = geom.get(sid, {})
        nodes = build_node_lookup(sg)
        edge_lookup = build_edge_lookup(sg)

        if spec["id"] in seen_ids:
            sys.exit(f"ERROR spec[{i}]: duplicate query_id {spec['id']}")
        seen_ids.add(spec["id"])

        # Verify all UUIDs exist
        for key, uuid in (
            ("target_uuid", spec["target_uuid"]),
            ("anchor_uuid", spec["anchor_uuid"]),
            ("reference_uuid", spec["reference_uuid"]),
        ):
            if uuid not in nodes:
                sys.exit(f"ERROR spec[{i}] {spec['id']}: {key} {uuid} not in scene {sid} nodes")

        # Verify both edges exist
        e1_key = (spec["target_uuid"], spec["target_rel"], spec["anchor_uuid"])
        e2_key = (spec["reference_uuid"], spec["reference_rel"], spec["anchor_uuid"])
        if e1_key not in edge_lookup:
            sys.exit(f"ERROR spec[{i}] {spec['id']}: edge_1 {e1_key} not in scene_graph")
        if e2_key not in edge_lookup:
            sys.exit(f"ERROR spec[{i}] {spec['id']}: edge_2 {e2_key} not in scene_graph")

        target_label = nodes[spec["target_uuid"]]
        anchor_label = nodes[spec["anchor_uuid"]]
        reference_label = nodes[spec["reference_uuid"]]

        # Distinct-UUID check
        if len({spec["target_uuid"], spec["anchor_uuid"], spec["reference_uuid"]}) != 3:
            sys.exit(f"ERROR spec[{i}] {spec['id']}: target/anchor/reference UUIDs not all distinct")

        # Same-label distractor count
        n_distractors, distractor_uuids = count_same_label_distractors(target_label, spec["target_uuid"], sg)

        # Geometric distance
        tac_dist = None
        t_center = scene_geom.get(spec["target_uuid"], {}).get("bbox_center")
        a_center = scene_geom.get(spec["anchor_uuid"], {}).get("bbox_center")
        if t_center and a_center:
            tac_dist = round(euclidean(t_center, a_center), 3)

        # Build main row
        main_row = {
            "query_id": spec["id"],
            "scene_id": sid,
            "query_text": spec["query_text"],
            "query_type": "functional",
            "target_node_id": spec["target_uuid"],
            "anchor_node_id": spec["anchor_uuid"],
            "supporting_edge_ids": [edge_lookup[e1_key], edge_lookup[e2_key]],
            "difficulty_tags": spec["tags"],
            "is_long_range": True,
            "evidence_chain": [
                f"{target_label} --{spec['target_rel']}--> {anchor_label}",
                f"{reference_label} --{spec['reference_rel']}--> {anchor_label}",
            ],
            "source": "human_phase4",
            "target_label": target_label,
            "anchor_label": anchor_label,
            "shared_anchor_node_id": spec["anchor_uuid"],
            "shared_anchor_label": anchor_label,
            "reference_node_id": spec["reference_uuid"],
            "reference_label": reference_label,
            "reference_relation": spec["reference_rel"],
            "long_range_pattern": "junction_2hop",
            "evidence_hop_count": 2,
            "reference_necessity": spec["ref_necessity"],
            "geometry_cues": spec["geom_cues"],
            "num_same_label_distractors": n_distractors,
            "is_label_only_solvable": spec["label_only"],
            "notes": spec["notes"],
        }

        diag_row = {
            "query_id": spec["id"],
            "scene_id": sid,
            "is_label_only_solvable": spec["label_only"],
            "num_same_label_distractors": n_distractors,
            "expected_failure_modes": spec["fail_modes"],
            "distractor_node_ids": distractor_uuids,
            "geometry_cues_used": spec["geom_cues"],
            "evidence_hop_count": 2,
            "long_range_pattern": "junction_2hop",
            "reference_necessity": spec["ref_necessity"],
            "target_anchor_3d_distance_m": tac_dist if tac_dist is not None else None,
        }

        main_rows.append(main_row)
        diag_rows.append(diag_row)

    # Write outputs
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_MAIN.open("w", encoding="utf-8") as f:
        for row in main_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    with OUT_DIAG.open("w", encoding="utf-8") as f:
        for row in diag_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Wrote {len(main_rows)} queries to {OUT_MAIN.name}")
    print(f"Wrote {len(diag_rows)} diagnostics to {OUT_DIAG.name}")

    # Summary stats
    print()
    print("=== Phase 4 query generation summary ===")
    print(f"Total queries:        {len(main_rows)}")
    print(f"  by scene:")
    by_scene: dict[str, int] = defaultdict(int)
    for r in main_rows:
        by_scene[r["scene_id"]] += 1
    for s, c in sorted(by_scene.items(), key=lambda x: -x[1]):
        print(f"    {s}: {c}")
    print(f"  by shared_anchor_label:")
    by_anchor: dict[str, int] = defaultdict(int)
    for r in main_rows:
        by_anchor[r["shared_anchor_label"]] += 1
    for a, c in sorted(by_anchor.items(), key=lambda x: -x[1]):
        print(f"    {a}: {c}")
    print(f"  reference_necessity:")
    by_nec: dict[str, int] = defaultdict(int)
    for r in main_rows:
        by_nec[r["reference_necessity"]] += 1
    for n, c in sorted(by_nec.items()):
        pct = c / len(main_rows) * 100
        print(f"    {n}: {c} ({pct:.0f}%)")
    print(f"  evidence_hop_count: all = 2")
    print(f"  is_label_only_solvable=True: {sum(1 for r in main_rows if r['is_label_only_solvable'])}")


if __name__ == "__main__":
    main()
