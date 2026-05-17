"""Phase 2 functional query generator.

Reads frozen scene graphs + geometry, applies hand-crafted query specs to fresh
edges (those not used by pilot_20_queries.jsonl), emits:
  - functional_queries_v1.jsonl
  - functional_query_diagnostics_v1.jsonl
  - hard_slice_summary_v1.json

Stdlib-only. Run from repo root:
  python benchmark_clean_v0/human_annotations/functional_queries_v1/scripts/phase2_query_generator.py
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
ENRICH_PATH = BENCH_ROOT / "queries" / "scenefun3d_funrag_benchmark_enriched.json"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"
OUT_DIR = Path(__file__).resolve().parents[1]
JSONL_PATH = OUT_DIR / "functional_queries_v1.jsonl"
DIAG_PATH = OUT_DIR / "functional_query_diagnostics_v1.jsonl"
SUMMARY_PATH = OUT_DIR / "hard_slice_summary_v1.json"

SELECTED_SCENES = {"469011", "421254", "421380", "421602", "421013", "420683"}


# Each spec encodes ONE Phase 2 query. Auto-fields (query_id, evidence_chain,
# num_same_label_distractors, target_label, anchor_label, supporting_edge_ids)
# are filled from the scene graph in build_queries(). The spec only carries the
# author's intent (which edge, which tags, which natural-language query text,
# which geometry cues, what failure modes, whether label-only solvable).
SPECS = [
    # ------------------------------------------------------------
    # 420683 (8 queries)  — bedroom-like; knob×9, handle×2, mixed
    # ------------------------------------------------------------
    {
        "scene": "420683",
        "target": "eb945e52-a2d5-4257-8de1-3f340deb71c9",
        "anchor": "6564cece-b08a-4e99-aadc-7b9b84d48c14",
        "relation": "pull to open or close",
        "query_text": "Pull the door handle to open the bedroom door",
        "tags": ["simple_functional", "same_label_disambiguation", "endpoint_ambiguity"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Scene has 2 handles; the door has a unique handle attached to it. The other handle is on the window. Anchor uniquely identifies target via functional relation."
    },
    {
        "scene": "420683",
        "target": "7478eaa4-362a-4613-9d6e-d41b794f41b9",
        "anchor": "6eabdfdc-d41c-4511-a841-08b177fd3d4b",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the right-side nightstand drawer (near the second lamp at x=3.129)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["right"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_nightstand_knob"],
        "label_only_solvable": False,
        "notes": "Scene has 2 nightstand_drawer instances: 6eabdfdc (x=3.050, right of room) and ef11c37b (x=1.210). Each has 1 knob. Anchor x-position disambiguates which nightstand."
    },
    {
        "scene": "420683",
        "target": "875242c5-10d3-4dd4-95ec-d20799e913c3",
        "anchor": "ef11c37b-4be8-4b73-aa2e-ff2d1a9ea5ff",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the center nightstand drawer (the one near the bed lamp at x=1.284, not the one at far right)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["center"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_nightstand_knob"],
        "label_only_solvable": False,
        "notes": "ef11c37b nightstand_drawer at x=1.210 is the center one; the other is at x=3.050. Spatial multi-anchor reference (lamp + 'not the far one') disambiguates."
    },
    {
        "scene": "420683",
        "target": "1b45ca90-7c63-4bed-945b-ee564321a724",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the upper-left knob on the chest of drawers to open the top-left drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Chest 34ef21f3 has 6 knobs in 3x2 grid. Left column x≈0.46-0.47; right column x≈0.59-0.60. Target 1b45ca90 at (x=0.471, z=382.670) = upper-left."
    },
    {
        "scene": "420683",
        "target": "d9876b50-2eaf-4c07-8543-3f57f6813b25",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle-left knob on the chest of drawers (the one between the top-left and bottom-left knobs)",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Target d9876b50 at (x=0.467, z=382.396) = middle-left of 3x2 grid."
    },
    {
        "scene": "420683",
        "target": "8dec8ba5-ee16-44b1-a131-611ee615bba7",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the lower-left knob on the chest of drawers to open the bottom-left drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lower", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Target 8dec8ba5 at (x=0.457, z=382.121) = lower-left of 3x2 grid."
    },
    {
        "scene": "420683",
        "target": "d8c8183c-8054-4101-9a2b-1d2645194360",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle-right knob on the chest of drawers (the one between the upper-right and lower-right knobs)",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Target d8c8183c at (x=0.596, z=382.388) = middle-right of 3x2 grid."
    },
    {
        "scene": "420683",
        "target": "bd7938dd-0f75-4e1c-84a3-aa6294dc6b36",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the lower-right knob on the chest of drawers to open the bottom-right drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lower", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Target bd7938dd at (x=0.596, z=382.118) = lower-right of 3x2 grid."
    },
    # ------------------------------------------------------------
    # 421013 (6 queries)
    # ------------------------------------------------------------
    {
        "scene": "421013",
        "target": "5c71b546-bf86-49cd-9c7f-158a9c4b24e5",
        "anchor": "a00be285-5f92-4254-aadd-83e7182b5db9",
        "relation": "pull to open or close",
        "query_text": "Pull the topmost handle on the tall wardrobe to open its upper compartment",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["topmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_lower_handle"],
        "label_only_solvable": False,
        "notes": "Wardrobe a00be285 has 4 handles. Target 5c71b546 at z=215.704 is highest of the four (others: 215.456, 215.139, 214.915). z_range=2.170 supports vertical disambiguation."
    },
    {
        "scene": "421013",
        "target": "6ce409f0-d503-4282-bbda-8dd62e3d2ae3",
        "anchor": "a00be285-5f92-4254-aadd-83e7182b5db9",
        "relation": "pull to open or close",
        "query_text": "Pull the second-highest handle on the tall wardrobe (the one just below the top)",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_top_handle"],
        "label_only_solvable": False,
        "notes": "Target 6ce409f0 at z=215.456 is 2nd-from-top on wardrobe (after 5c71b546 at 215.704)."
    },
    {
        "scene": "421013",
        "target": "d1cb8681-bd37-49eb-8d89-5f09d782a627",
        "anchor": "a00be285-5f92-4254-aadd-83e7182b5db9",
        "relation": "pull to open or close",
        "query_text": "Pull the third-from-top handle on the tall wardrobe (the one above the lowest handle)",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lower"],
        "failure_modes": ["same_label_wrong_instance", "choose_lowest_handle"],
        "label_only_solvable": False,
        "notes": "Target d1cb8681 at z=215.139 is 3rd-from-top (above 217402c7 at 214.915 which is pilot 000014's lowest)."
    },
    {
        "scene": "421013",
        "target": "763b8e1e-ca12-4f8d-a0d9-cbdad0b699c2",
        "anchor": "600ca2b3-a6fd-4360-8279-2e91df4d6851",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the lower handle on the left-side nightstand (x=-0.133) to open its bottom drawer",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lower", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_nightstand_handle"],
        "label_only_solvable": False,
        "notes": "Scene has 2 nightstand variants: 600ca2b3 (left, x=-0.133) with 2 handles, e810c10f (right, x=1.662) with 2 handles. Target 763b8e1e at z=214.922 is lower of the pair on left nightstand (other = 7f13ad67 at z=215.147, pilot 000017)."
    },
    {
        "scene": "421013",
        "target": "4375aca4-619a-49e3-9bb5-abcd2fdc203f",
        "anchor": "e810c10f-8b4a-4fd1-8ae1-0d51fd3e2295",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the upper handle on the right-side nightstand (x=1.662, the one near the bed) to open its top drawer",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_nightstand_handle", "choose_lower_handle"],
        "label_only_solvable": False,
        "notes": "e810c10f nightstand at x=1.662 (right side) has 2 handles. Target 4375aca4 at z=215.133 is upper; sibling 363a1c6d at z=214.898 is lower."
    },
    {
        "scene": "421013",
        "target": "363a1c6d-0870-419a-a9e1-539b68463700",
        "anchor": "e810c10f-8b4a-4fd1-8ae1-0d51fd3e2295",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the lower handle on the right-side nightstand (x=1.662) to open its bottom drawer",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lower", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_nightstand_handle", "choose_upper_handle"],
        "label_only_solvable": False,
        "notes": "Sibling 4375aca4 at z=215.133 (upper); target 363a1c6d at z=214.898 (lower)."
    },
    # ------------------------------------------------------------
    # 421602 (9 queries)
    # ------------------------------------------------------------
    {
        "scene": "421602",
        "target": "1901053a-2215-40c3-8e3e-10ca3b402428",
        "anchor": "405c7c68-c579-4094-b2ee-4a02ad1828a8",
        "relation": "control, turn on or turn off",
        "query_text": "Press the switch that turns the ceiling light on or off",
        "tags": ["endpoint_ambiguity", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "ignore_functional_relation"],
        "label_only_solvable": False,
        "notes": "Switch and light are both interactive (endpoint ambiguity); functional relation 'control' is critical discriminator. Only 1 light switch and 1 ceiling light in scene, so anchor identifies target unambiguously once the relation is parsed correctly."
    },
    {
        "scene": "421602",
        "target": "2e9cd70e-9bcb-463e-8609-dc8c63d1facc",
        "anchor": "340b66f3-ff28-4436-a311-ba6ba9202289",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the upper handle on the right-side dresser (x=0.833) to open its top drawer",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_dresser_handle"],
        "label_only_solvable": False,
        "notes": "Two dressers: 340b66f3 (right, x=0.833) with 3 handles (90e6a8bd lowest pilot, d54793bc middle, 2e9cd70e upper). Target 2e9cd70e at z=170.567 is upper."
    },
    {
        "scene": "421602",
        "target": "d54793bc-ed8e-4883-a708-1299c03d038d",
        "anchor": "340b66f3-ff28-4436-a311-ba6ba9202289",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle handle on the right-side dresser (x=0.833), the one between the upper and lowest handles",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_dresser_handle"],
        "label_only_solvable": False,
        "notes": "Target d54793bc at z=170.379 is middle handle of right dresser (between 2e9cd70e at 170.567 and 90e6a8bd at 170.191)."
    },
    {
        "scene": "421602",
        "target": "cde51d66-3837-4fc6-bf48-16cb2189a7ed",
        "anchor": "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top handle on the left-side dresser (x=-1.808), the one just below the topmost handle",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_top_handle", "choose_other_dresser_handle"],
        "label_only_solvable": False,
        "notes": "Left dresser f4e41b55 has 5 handles by z: 9fcd23c1 top (170.932, pilot 000003), cde51d66 2nd (170.741), 7f9d7574 middle (170.553), 70b0480d 4th (170.360), 1fff26d6 bottom (170.175). Target = 2nd-from-top."
    },
    {
        "scene": "421602",
        "target": "7f9d7574-57e9-4963-af14-e6278c288313",
        "anchor": "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle handle on the left-side dresser (x=-1.808), the third one from the top of five drawers",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_handle"],
        "label_only_solvable": False,
        "notes": "Target 7f9d7574 at z=170.553 is middle of 5-handle vertical stack on left dresser."
    },
    {
        "scene": "421602",
        "target": "70b0480d-4014-4c34-a7c1-b8c37aa7faaa",
        "anchor": "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-bottom handle on the left-side dresser (x=-1.808), the one just above the lowest handle",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lower", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_lowest_handle"],
        "label_only_solvable": False,
        "notes": "Target 70b0480d at z=170.360 is 4th-from-top (2nd-from-bottom) of 5 left-dresser handles."
    },
    {
        "scene": "421602",
        "target": "1fff26d6-a1bc-4a03-bfa9-b4baf44f058d",
        "anchor": "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the lowest handle on the left-side dresser (x=-1.808) to open its bottom drawer",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_handle"],
        "label_only_solvable": False,
        "notes": "Target 1fff26d6 at z=170.175 is lowest of 5 left-dresser handles."
    },
    {
        "scene": "421602",
        "target": "c9adafa4-e9f4-469b-9f85-1fefacb17b22",
        "anchor": "0c6ed5cc-e7f3-45df-9d2c-bd355e32457f",
        "relation": "rotate to adjust the temperature",
        "query_text": "Rotate the knob on the radiator to adjust the room temperature",
        "tags": ["simple_functional", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["label_only_shortcut"],
        "label_only_solvable": True,
        "notes": "Only 1 knob in scene 421602; only 1 radiator. Trivially unique. Kept as a simple_functional baseline to avoid all-hard skew."
    },
    {
        "scene": "421602",
        "target": "13b01e96-5010-4c1a-8b09-c8346e420ea3",
        "anchor": "1293f172-4c8b-4f52-9c8d-745aeb42d7f1",
        "relation": "rotate to open or close",
        "query_text": "Rotate the door handle to open the door to the bedroom",
        "tags": ["same_label_disambiguation", "functional_relation", "endpoint_ambiguity"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Scene 421602 has 11 handles but only 1 connects to door via rotate-to-open-or-close. Anchor uniquely identifies target via functional relation."
    },
    # ------------------------------------------------------------
    # 421380 (3 queries)  — horizontal-only geometry; 5+5 knob
    #                       clusters indistinguishable, skipped.
    # ------------------------------------------------------------
    {
        "scene": "421380",
        "target": "c44a2818-7f0c-4200-bda1-915f3ade1731",
        "anchor": "8b0f6a88-2f0e-4f44-ad59-65dec8b2aca1",
        "relation": "control",
        "query_text": "Which remote on the left side (x=1.596) controls the television",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation", "geometry_aware", "functional_relation"],
        "geometry_cues": ["left"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Two remotes both control the TV in 421380: c44a2818 at x=1.596 (left) and d75da7cf at x=1.700 (right). Horizontal cue disambiguates. Endpoint ambiguity because TV is interactive."
    },
    {
        "scene": "421380",
        "target": "d75da7cf-4a4b-40fc-ac77-ffd1dd8edb6b",
        "anchor": "8b0f6a88-2f0e-4f44-ad59-65dec8b2aca1",
        "relation": "control",
        "query_text": "Which remote on the right side (x=1.700) controls the television",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation", "geometry_aware", "functional_relation"],
        "geometry_cues": ["right"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Mirror of left-remote query; x=1.700 disambiguates from c44a2818 at x=1.596."
    },
    {
        "scene": "421380",
        "target": "9db14ed4-ed96-4e43-a12d-7a1a865f0161",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close",
        "query_text": "Pull the second-leftmost knob on the television stand (the knob just right of the leftmost knob at x=0.652)",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["left"],
        "failure_modes": ["same_label_wrong_instance", "choose_leftmost_knob"],
        "label_only_solvable": False,
        "notes": "TV stand has 14 knobs in pull-edges. Target 9db14ed4 at x=0.690 is 2nd-leftmost (after pilot 000016's bc40c514 at x=0.652). NOTE: phase2.md修订 2 forbids vertical geometry for 421380 (z_range=0.802); only horizontal cues used. The other 12 fresh edges cluster at x≈1.07 and x≈1.47 with intra-cluster x-spread < 0.005m → not authored to avoid ambiguous answers."
    },
    # ------------------------------------------------------------
    # 469011 (19 queries)  — kitchen-like; knob×19, outlet×6,
    #                        handle×2, kitchen cabinets×9
    # ------------------------------------------------------------
    {
        "scene": "469011",
        "target": "2abcdace-ba3f-45c0-8dce-eac4de015ee8",
        "anchor": "7fddf637-3da9-4511-b4b4-fc6a042db72c",
        "relation": "pull to open or close",
        "query_text": "Pull the handle on the refrigerator to open the fridge door",
        "tags": ["simple_functional", "same_label_disambiguation", "endpoint_ambiguity"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Scene has 2 handles (and 1 faucet/handle = 'faucet / handle' which is a different label). Only 1 handle connects to fridge. Anchor uniquely identifies target."
    },
    {
        "scene": "469011",
        "target": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "pull to open or close",
        "query_text": "Pull the handle on the oven door to open the oven",
        "tags": ["simple_functional", "same_label_disambiguation", "endpoint_ambiguity"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "1 of 2 handles in scene connects to oven; the other to fridge. Anchor uniquely identifies target."
    },
    {
        "scene": "469011",
        "target": "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "rotate to adjust the setting",
        "query_text": "Rotate the leftmost burner knob on the oven control panel (x=2.492) to adjust the heat setting",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["leftmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_burner"],
        "label_only_solvable": False,
        "notes": "5 oven knobs on the front panel of the stove. Target d003c3b8 at x=2.492 is leftmost. Others by x: 06b684bb 2.528, 28e9ec26 2.581, 76002344 2.700, 85f5f2f0 2.814."
    },
    {
        "scene": "469011",
        "target": "06b684bb-7a5c-4717-847a-d343bd6824d9",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "rotate to adjust the setting",
        "query_text": "Rotate the second-from-left burner knob on the oven control panel (x=2.528) to adjust its heat setting",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_burner"],
        "label_only_solvable": False,
        "notes": "Target 06b684bb at x=2.528 is 2nd-leftmost of 5 oven knobs."
    },
    {
        "scene": "469011",
        "target": "28e9ec26-d38b-45a2-9614-9fe6a8d69211",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "rotate to adjust the setting",
        "query_text": "Rotate the middle burner knob on the oven control panel (x=2.581) to adjust its heat setting",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_burner"],
        "label_only_solvable": False,
        "notes": "Target 28e9ec26 at x=2.581 is middle of 5 oven knobs."
    },
    {
        "scene": "469011",
        "target": "76002344-9de9-476f-a43e-d822d1cdb592",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "rotate to adjust the setting",
        "query_text": "Rotate the second-from-right burner knob on the oven control panel (x=2.700) to adjust its heat setting",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_burner"],
        "label_only_solvable": False,
        "notes": "Target 76002344 at x=2.700 is 4th-from-left (2nd-from-right) of 5 oven knobs."
    },
    {
        "scene": "469011",
        "target": "85f5f2f0-ef9b-4e32-a0de-cd8a7f54db4b",
        "anchor": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "relation": "rotate to adjust the setting",
        "query_text": "Rotate the rightmost burner knob on the oven control panel (x=2.814) to adjust its heat setting",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["rightmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_burner"],
        "label_only_solvable": False,
        "notes": "Target 85f5f2f0 at x=2.814 is rightmost of 5 oven knobs."
    },
    {
        "scene": "469011",
        "target": "26d01e98-de8b-4574-91a6-6b4f62371315",
        "anchor": "d68f6e84-8842-429e-a877-dd6d951bc930",
        "relation": "pull to open or close",
        "query_text": "Pull the upper knob on the kitchen cabinet at x=1.537 to open its top compartment",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_cabinet_knob"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet d68f6e84 (x=1.537, z=-28.196) has 3 knobs stacked vertically: 26d01e98 (top, z=-27.873), 26facf7e (middle, z=-28.032), 8572a9c1 (bottom, z=-28.198). Target = top."
    },
    {
        "scene": "469011",
        "target": "26facf7e-0a3c-4c02-ae11-e6ce94dcdc33",
        "anchor": "d68f6e84-8842-429e-a877-dd6d951bc930",
        "relation": "pull to open or close",
        "query_text": "Pull the middle knob on the kitchen cabinet at x=1.537 (the one between the top and bottom knobs)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Cabinet d68f6e84's 3-knob vertical stack; target 26facf7e at z=-28.032 is middle."
    },
    {
        "scene": "469011",
        "target": "8572a9c1-67b2-4493-8cfe-d492a255c623",
        "anchor": "d68f6e84-8842-429e-a877-dd6d951bc930",
        "relation": "pull to open or close",
        "query_text": "Pull the lowest knob on the kitchen cabinet at x=1.537 to open its bottom compartment",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest"],
        "failure_modes": ["same_label_wrong_instance", "choose_upper_knob"],
        "label_only_solvable": False,
        "notes": "Cabinet d68f6e84's 3-knob vertical stack; target 8572a9c1 at z=-28.198 is lowest."
    },
    {
        "scene": "469011",
        "target": "60c75bed-76ac-430f-9ed8-790350f059b6",
        "anchor": "cdfa3f8b-1bdf-4b70-aa8a-8be5d157be07",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the leftmost lower kitchen cabinet (x=1.121, the one farthest to the left in the lower row)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["leftmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "9 kitchen cabinets in 469011; cdfa3f8b at x=1.121, z=-28.195 is leftmost in lower row. Target 60c75bed is its sole knob."
    },
    {
        "scene": "469011",
        "target": "d4432013-4335-4218-8276-da26c1bf64e4",
        "anchor": "a5cb3f02-1860-44e3-95c1-9799088474e0",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the kitchen cabinet at x=1.977 in the lower row to open it",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["left"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet a5cb3f02 at x=1.977, z=-28.196 is 2nd-from-left in lower row (after cdfa3f8b at 1.121). Target d4432013 is its sole knob."
    },
    {
        "scene": "469011",
        "target": "6dcb0d35-1950-4621-a2d7-c4ba3cb0f5d1",
        "anchor": "4507827d-3758-4e21-ac0c-75149e840d57",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the kitchen cabinet at x=2.335 in the lower row (the middle cabinet) to open it",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet 4507827d at x=2.335 is one of the middle cabinets in the lower row. Target 6dcb0d35 is its sole knob."
    },
    {
        "scene": "469011",
        "target": "9f732c04-b269-4e3b-982c-fb29cf75d515",
        "anchor": "ff93b24e-ee51-464d-81b9-737553b78364",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the kitchen cabinet at x=2.940 in the lower row (right-center) to open it",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet ff93b24e at x=2.940 in lower row is right-of-center. Target 9f732c04 is its sole knob."
    },
    {
        "scene": "469011",
        "target": "65d617ff-232c-4148-99bb-0286d46995b5",
        "anchor": "7b89239e-5681-403a-a1da-dd26e16be537",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the rightmost lower kitchen cabinet (x=3.018) to open it",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["rightmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet 7b89239e at x=3.018 is rightmost in lower row. Target 65d617ff is its sole knob."
    },
    {
        "scene": "469011",
        "target": "79d81cf3-381e-48cd-9bf6-aea8e7bd017c",
        "anchor": "78932c81-2e84-4f45-a579-f28174406741",
        "relation": "pull to open or close",
        "query_text": "Pull the upper knob on the lower kitchen cabinet at x=2.360 to open its upper drawer (the cabinet has two knobs stacked together)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_lower_knob_on_same_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet 78932c81 at x=2.360 has 2 knobs (79d81cf3 and 1a2ac79a) very close in x (2.373 vs 2.329) and z (-27.878 vs -27.879). Target 79d81cf3 at z=-27.878 nominally upper; sibling 1a2ac79a is at z=-27.879. [issue] tagged in notes: 1a2ac79a is intentionally NOT authored to avoid an ambiguous-twin query."
    },
    {
        "scene": "469011",
        "target": "a6844581-85cd-4300-9fed-bc1d7e5971a5",
        "anchor": "0b2e3fc2-7080-4e9f-aee6-1a18a9798952",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the upper-row kitchen cabinet at x=2.551 to open its upper compartment",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet 0b2e3fc2 at z=-26.981 (upper row vs lower row at z≈-28.19). Target a6844581 is its sole knob."
    },
    {
        "scene": "469011",
        "target": "98aa04b7-41b4-4339-aed9-0a1e01d51fd8",
        "anchor": "f985cca4-89e2-43f9-b8c2-5de77392b1f3",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the upper-row kitchen cabinet at x=2.219 to open its upper compartment",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_cabinet"],
        "label_only_solvable": False,
        "notes": "Kitchen cabinet f985cca4 at z=-26.990 is in upper row (vs lower row at z≈-28.19). Target 98aa04b7 is its sole knob."
    },
    {
        "scene": "469011",
        "target": "cb5cccda-b4e9-4933-8516-6c775c1f91f8",
        "anchor": "4a7d1c17-7c39-41cc-9b5c-6d169d0a9ca1",
        "relation": "pull to open or close",
        "query_text": "Pull the knob on the standalone cabinet (not a kitchen cabinet) at x=3.212 to open it",
        "tags": ["functional_relation", "hard_negative"],
        "geometry_cues": [],
        "failure_modes": ["confuse_cabinet_with_kitchen_cabinet", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Anchor 4a7d1c17 has label 'cabinet' (NOT 'kitchen cabinet'). Scene has 9 kitchen_cabinets and 1 cabinet. Tests label disambiguation between similar labels. Target cb5cccda is its sole knob."
    },
    # ------------------------------------------------------------
    # 421254 (20 queries)
    # ------------------------------------------------------------
    {
        "scene": "421254",
        "target": "9c06f662-e551-484e-9559-a7d3c0b5b31d",
        "anchor": "8bd6869b-b734-4041-a3e5-0cd3e3b18d0e",
        "relation": "control",
        "query_text": "Which remote on the left-hand side (x=-0.443, the one closer to the nightstand) controls the television",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation", "geometry_aware", "functional_relation"],
        "geometry_cues": ["left"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Sibling of pilot 000009. Two remotes control same TV: 560f1e2c at x=-0.330 (pilot's right one), 9c06f662 at x=-0.443 (this one, left). Target 9c06f662 has more-negative x."
    },
    # 8 knobs on dresser 97164eaa (x=-0.853, 'right' larger dresser).
    # Grid: left column x≈-1.12, right column x≈-0.72; rows by z.
    {
        "scene": "421254",
        "target": "9bb22a10-e42b-46fb-af9b-8a8df7d3f6b3",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the top-left knob on the right-side dresser at x=-0.853 (the topmost of the left column of drawers)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_dresser", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Dresser 97164eaa (x=-0.853) has 8 knobs in 2-col x 4-row grid. Left column x≈-1.12. Target 9bb22a10 at (x=-1.123, z=212.926) = top-left."
    },
    {
        "scene": "421254",
        "target": "da2d25fc-56d3-4b0f-8ada-778acac16871",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top left-column knob on the right-side dresser at x=-0.853",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target da2d25fc at (x=-1.125, z=212.703) = 2nd row in left column."
    },
    {
        "scene": "421254",
        "target": "3025d034-e4c9-4dc8-8711-ba7cda23b8e1",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the third-from-top left-column knob on the right-side dresser at x=-0.853",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 3025d034 at (x=-1.125, z=212.480) = 3rd row in left column."
    },
    {
        "scene": "421254",
        "target": "0635ce47-455a-4933-b421-cd5601b7203f",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottom-left knob on the right-side dresser at x=-0.853 (lowest knob in the left column)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 0635ce47 at (x=-1.128, z=212.256) = bottom-left."
    },
    {
        "scene": "421254",
        "target": "addeffee-87e2-4f20-98bd-589c425f0f07",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the top-right knob on the right-side dresser at x=-0.853 (topmost in the right column)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Target addeffee at (x=-0.726, z=212.925) = top-right (right column x≈-0.72)."
    },
    {
        "scene": "421254",
        "target": "2ffdc7cc-6746-4b6d-a2e5-35c078befc56",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top right-column knob on the right-side dresser at x=-0.853",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 2ffdc7cc at (x=-0.724, z=212.700) = 2nd row in right column."
    },
    {
        "scene": "421254",
        "target": "f75e1a27-55d7-4b2e-be1a-2d5596d69dd8",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the third-from-top right-column knob on the right-side dresser at x=-0.853",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target f75e1a27 at (x=-0.726, z=212.480) = 3rd row in right column."
    },
    {
        "scene": "421254",
        "target": "877bb40d-b6d8-4716-b958-320b07e6f8d8",
        "anchor": "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottom-right knob on the right-side dresser at x=-0.853 (lowest knob in the right column)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 877bb40d at (x=-0.726, z=212.255) = bottom-right."
    },
    # 9 knobs on dresser f1f234c5 (x=-1.766, 'left' larger dresser).
    # Asymmetric grid: left col 4 rows, right col 5 rows.
    {
        "scene": "421254",
        "target": "8ab6af8d-3cad-4fad-bf78-157916578132",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the top-left knob on the left-side dresser at x=-1.766 (topmost in the left column)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_dresser", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Dresser f1f234c5 (x=-1.766). Target 8ab6af8d at (x=-1.937, z=212.933) = top-left."
    },
    {
        "scene": "421254",
        "target": "ac42e1c2-3ed4-447f-8147-cd903d8eefc5",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top left-column knob on the left-side dresser at x=-1.766",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target ac42e1c2 at (x=-1.941, z=212.775) = 2nd row in left column."
    },
    {
        "scene": "421254",
        "target": "044038ae-cd3a-4874-837c-9f2e32a83b04",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the third-from-top left-column knob on the left-side dresser at x=-1.766",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 044038ae at (x=-1.942, z=212.613) = 3rd row in left column."
    },
    {
        "scene": "421254",
        "target": "2b17304a-ced6-4b4f-9c1b-32ec7ba8bc64",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottom-left knob on the left-side dresser at x=-1.766 (lowest knob in the left column)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 2b17304a at (x=-1.946, z=212.451) = bottom-left."
    },
    {
        "scene": "421254",
        "target": "a0f8f1a0-fe8d-4eae-b655-66ac3b1ca05f",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the top-right knob on the left-side dresser at x=-1.766 (topmost in the right column of 5 drawers)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "Right column has 5 rows. Target a0f8f1a0 at (x=-1.549, z=212.932) = top-right."
    },
    {
        "scene": "421254",
        "target": "b0aa5f30-4fae-4ca8-bc66-c0595b8fc754",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top right-column knob on the left-side dresser at x=-1.766",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target b0aa5f30 at (x=-1.552, z=212.770) = 2nd row in right column."
    },
    {
        "scene": "421254",
        "target": "6aa841fa-6898-401d-a750-0f521b4cafe7",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the third-from-top right-column knob on the left-side dresser at x=-1.766",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["middle", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 6aa841fa at (x=-1.557, z=212.612) = 3rd row in right column."
    },
    {
        "scene": "421254",
        "target": "15a1acd9-d48d-4011-bbdc-297619dfb62c",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the fourth-from-top right-column knob on the left-side dresser at x=-1.766",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lower", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 15a1acd9 at (x=-1.563, z=212.441) = 4th row in right column."
    },
    {
        "scene": "421254",
        "target": "482d7642-61c9-4161-b651-45dc8cb9e2ae",
        "anchor": "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottom-right knob on the left-side dresser at x=-1.766 (lowest in the right column of 5 drawers)",
        "tags": ["same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["lowest", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob"],
        "label_only_solvable": False,
        "notes": "Target 482d7642 at (x=-1.559, z=212.293) = bottom-right."
    },
    # 2 fresh nightstand knobs on 762c6ae7 (pilot used ba0e4f26 = top).
    {
        "scene": "421254",
        "target": "c0685f07-46ed-41c9-b3ce-4fc476c86c7c",
        "anchor": "762c6ae7-17cb-4f69-998b-ffe2c168d47f",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle knob on the nightstand at the back of the room (y=-1.881, x=-0.435) to open the middle drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_top_knob", "choose_bottom_knob"],
        "label_only_solvable": False,
        "notes": "Nightstand 762c6ae7 has 3 vertically-stacked knobs at x≈-0.446. By z: ba0e4f26 top (212.345, pilot 000010), c0685f07 middle (212.201), d2174346 bottom (212.048)."
    },
    {
        "scene": "421254",
        "target": "d2174346-66bb-4a99-8177-edcc8c7cd20b",
        "anchor": "762c6ae7-17cb-4f69-998b-ffe2c168d47f",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottom knob on the nightstand at the back of the room (y=-1.881) to open the bottom drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lowest"],
        "failure_modes": ["same_label_wrong_instance", "choose_top_knob", "choose_middle_knob"],
        "label_only_solvable": False,
        "notes": "Target d2174346 at z=212.048 is bottom of nightstand 762c6ae7's 3-knob vertical stack."
    },
    # ------------------------------------------------------------
    # PILOT-EDGE REUSES — 18 queries (q086-q103)
    # Reframe pilot's 20 instance keys with different query_text +
    # tag mix to add endpoint_ambiguity / hard_negative /
    # simple_functional balance per Mingqian feedback. NOTE: this
    # violates phase2.md "1 unique edge 1 query" guideline; tracked
    # as [issue] PILOT_EDGE_REUSE in annotation_notes.md. C13
    # within-file uniqueness preserved (each pilot edge reused once
    # in Phase 2 JSONL; pilot file is separate).
    # Two of these (q088, q094) are CORRECTIONS of pilot bugs.
    # ------------------------------------------------------------
    {
        "scene": "420683",
        "target": "e0047d50-015b-40d0-8910-f0c4b1fb5b7a",
        "anchor": "8a1b9af6-dc57-4766-98cb-f10cb6266656",
        "relation": "rotate to adjust the temperature",
        "query_text": "Rotate the radiator knob at the far-left of the room (x=-0.487) to make the bedroom warmer",
        "tags": ["simple_functional", "functional_relation", "same_label_disambiguation"],
        "geometry_cues": ["left"],
        "failure_modes": ["same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Pilot 000001 reuse with explicit x-position cue. 9 knobs in 420683; only this one connects to radiator. Simple_functional baseline kept; same_label tag added because target_label has 8 other instances."
    },
    {
        "scene": "421013",
        "target": "5c383fa1-c2de-46d9-8c87-969486e5e28d",
        "anchor": "2b27ebab-9f6f-4a35-8e8b-dca0f71aeeef",
        "relation": "rotate to open or close",
        "query_text": "Rotate the door handle (not push the door itself) to open the bedroom door",
        "tags": ["simple_functional", "endpoint_ambiguity", "same_label_disambiguation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Pilot 000002 reuse with explicit endpoint emphasis (handle vs door both interactive). 9 handles in scene; only 1 connects to door."
    },
    {
        "scene": "420683",
        "target": "465347e8-606a-4807-b89e-085cf8c578f3",
        "anchor": "34ef21f3-fb41-496f-afac-632e7ad4c34b",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the upper-right knob on the chest of drawers (the topmost knob in the right column at x=0.603) to open the top-right drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["upper", "right"],
        "failure_modes": ["same_label_wrong_instance", "choose_wrong_position_knob"],
        "label_only_solvable": False,
        "notes": "CORRECTION of pilot 000004 which had 6 valid answers among the chest's knobs. Phase 2 version adds explicit upper-right geometry → unique target = 465347e8 at (x=0.603, z=382.668). Pairs with q024 (upper-left), q025 (middle-left), q026 (lower-left), q027 (middle-right), q028 (lower-right) to cover the full 3x2 grid."
    },
    {
        "scene": "469011",
        "target": "4af16074-57d0-47e7-8be9-aa361472ae26",
        "anchor": "19d41c11-a30d-4f1b-bb52-5f8260af117f",
        "relation": "control the water flow",
        "query_text": "I need to wash my hands — which device do I turn to make water come out of the kitchen sink",
        "tags": ["hard_negative", "endpoint_ambiguity", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000005 reuse with hard_negative semantic indirection ('wash my hands' instead of 'control water flow'). Only 1 faucet in scene, 1 sink. Endpoint ambiguity between faucet (turner) and sink (recipient)."
    },
    {
        "scene": "469011",
        "target": "0146b63e-698d-4337-9a8b-f7b1a25c05f7",
        "anchor": "3d0352ee-0916-4a98-b353-a083f97c9fd7",
        "relation": "provide power",
        "query_text": "While cooking, I need to remove smoke from the kitchen — which power source must I check first to make sure the exhaust hood above the stove is plugged in",
        "tags": ["hard_negative", "functional_relation", "same_label_disambiguation"],
        "geometry_cues": [],
        "failure_modes": ["label_only_shortcut", "choose_wrong_outlet"],
        "label_only_solvable": False,
        "notes": "Pilot 000006 reuse with hard_negative cooking-context framing. 6 outlets in scene; only 1 powers the exhaust hood."
    },
    {
        "scene": "421380",
        "target": "44d68daa-9a11-483c-91fc-8771f75185a0",
        "anchor": "f422e864-7d94-4369-b4b4-d4c06bbe4739",
        "relation": "rotate to adjust the temperature",
        "query_text": "The living room feels cold tonight — which dial do I rotate on the radiator to make it warmer",
        "tags": ["hard_negative", "same_label_disambiguation", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000007 reuse with hard_negative semantic framing. 15 knobs in 421380 but only 1 connects to radiator (the rest go to TV stand / television)."
    },
    {
        "scene": "421602",
        "target": "31afb664-5958-490b-ba2d-4de7e0d0e632",
        "anchor": "631559ce-afb5-4459-9a00-7ec088bf4628",
        "relation": "pull to open or close",
        "query_text": "Pull the handle on the wooden cabinet near the window (not push the cabinet door directly) to access the shelves inside",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Pilot 000008 reuse with endpoint emphasis (handle vs cabinet both interactive). Cabinet 631559ce has 2 handles at virtually identical positions (31afb664 and 416fa12f); this query targets 31afb664 — the ambiguous-twin case noted in [issue] 421602_HANDLE_PAIR_UNDISTINGUISHABLE."
    },
    {
        "scene": "421254",
        "target": "560f1e2c-e62d-4f1e-93e8-3acbf61433cd",
        "anchor": "8bd6869b-b734-4041-a3e5-0cd3e3b18d0e",
        "relation": "control",
        "query_text": "I want to change the TV channel from the bed — which device do I press, the remote on the right side at x=-0.330, to send signals to the television",
        "tags": ["hard_negative", "endpoint_ambiguity", "same_label_disambiguation", "geometry_aware", "functional_relation"],
        "geometry_cues": ["right"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000009 reuse with hard_negative intent framing ('change the channel'). 2 remotes both control the TV; the right one at x=-0.330 disambiguates from q066's left one at x=-0.443."
    },
    {
        "scene": "421254",
        "target": "ba0e4f26-1e02-4745-92b6-e1035ba5252c",
        "anchor": "762c6ae7-17cb-4f69-998b-ffe2c168d47f",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the topmost knob on the back-of-room nightstand (y=-1.881, x=-0.435) — the uppermost of three vertically stacked knobs at z=212.345 — to open its top drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["topmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_middle_knob", "choose_bottom_knob"],
        "label_only_solvable": False,
        "notes": "CORRECTION of pilot 000010 which was ambiguous (3 valid answers among ba0e4f26 / c0685f07 / d2174346). Phase 2 version adds explicit 'topmost' + z=212.345 to uniquely pick ba0e4f26. Pairs with q064 (middle), q065 (bottom)."
    },
    {
        "scene": "469011",
        "target": "ba5246d7-ea68-4bd5-b390-45a1b4e8d58e",
        "anchor": "af49702a-b605-472e-8ba6-697e38979647",
        "relation": "rotate to adjust the setting or open or close",
        "query_text": "After loading dirty dishes, which control do I rotate to start the cleaning cycle on the dishwasher in the kitchen",
        "tags": ["hard_negative", "same_label_disambiguation", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["same_label_wrong_instance", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000011 reuse with semantic indirection ('start the cleaning cycle'). 19 knobs in scene; only 1 connects to dishwasher."
    },
    {
        "scene": "421013",
        "target": "eab8ec36-9674-4dc7-8c00-0c6478fc8f92",
        "anchor": "38486241-df60-4e9b-946a-2a05fce6d3eb",
        "relation": "control, turn on or turn off",
        "query_text": "It's getting dark in the bedroom — which interface do I press to illuminate the room from the ceiling",
        "tags": ["hard_negative", "endpoint_ambiguity", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000012 reuse with hard_negative semantic framing. Endpoint ambiguity between switch (target) and ceiling light (anchor)."
    },
    {
        "scene": "420683",
        "target": "560e4272-ce2c-4442-be41-413532b29fe2",
        "anchor": "7a6d5c52-dc92-4dac-b205-5f38b5e3b44b",
        "relation": "control, turn on or turn off",
        "query_text": "I just walked into the dark bedroom — which control on the wall do I activate to turn on the ceiling light",
        "tags": ["hard_negative", "endpoint_ambiguity", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000013 reuse with hard_negative semantic framing. Target label is 'switch panel / electric outlet' — a wall-mounted switch. Endpoint ambiguity with ceiling light."
    },
    {
        "scene": "421013",
        "target": "217402c7-af78-4217-b70f-ef3bb65f71d4",
        "anchor": "a00be285-5f92-4254-aadd-83e7182b5db9",
        "relation": "pull to open or close",
        "query_text": "Pull the lowest handle on the tall wardrobe (z=214.915, not push the wardrobe door directly) to access its bottom compartment",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lowest"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Pilot 000014 reuse with endpoint emphasis. Handle (target) vs wardrobe (anchor) both interactive. Target 217402c7 at z=214.915 is lowest of 4 wardrobe handles."
    },
    {
        "scene": "421602",
        "target": "9fcd23c1-4638-41a9-a8d8-02bffa3e6a7c",
        "anchor": "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
        "relation": "pull to open or close a drawer",
        "query_text": "I want to retrieve socks from the top drawer of the left-side dresser at x=-1.808 — which handle do I pull, the one at z=170.932 (highest of 5 stacked handles)",
        "tags": ["hard_negative", "same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["topmost", "left"],
        "failure_modes": ["same_label_wrong_instance", "choose_other_dresser", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000003 reuse with hard_negative intent framing ('retrieve socks'). Target 9fcd23c1 at z=170.932 is highest of 5 handles on left dresser."
    },
    {
        "scene": "421013",
        "target": "7f13ad67-a21a-4ed2-9bc1-c0e330ebfbb4",
        "anchor": "600ca2b3-a6fd-4360-8279-2e91df4d6851",
        "relation": "pull to open or close a drawer",
        "query_text": "While getting ready for bed, I want to grab a book — which handle do I pull on the left-side nightstand (x=-0.133) to access its upper drawer at z=215.147",
        "tags": ["hard_negative", "endpoint_ambiguity", "same_label_disambiguation", "multi_anchor", "geometry_aware"],
        "geometry_cues": ["upper", "left"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance", "choose_other_nightstand"],
        "label_only_solvable": False,
        "notes": "Pilot 000017 reuse with explicit upper-handle geometry (was missing in pilot version). Endpoint emphasis: handle vs nightstand both interactive."
    },
    {
        "scene": "469011",
        "target": "548a6569-5c70-4d7b-9f10-0ece005e6c00",
        "anchor": "7fddf637-3da9-4511-b4b4-fc6a042db72c",
        "relation": "provide power",
        "query_text": "Plug the appliance cord into the outlet that powers the fridge (the outlet, not the fridge plug itself), at x=-0.446, lower-left of the kitchen",
        "tags": ["endpoint_ambiguity", "hard_negative", "same_label_disambiguation", "functional_relation"],
        "geometry_cues": ["left"],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance", "label_only_shortcut"],
        "label_only_solvable": False,
        "notes": "Pilot 000018 reuse with endpoint emphasis. 6 outlets in scene; only 1 powers the fridge."
    },
    {
        "scene": "421254",
        "target": "51097855-7ce4-4893-8f0a-4715abeaec1c",
        "anchor": "0ea8a987-f639-4314-a3f3-78a5e6a3b5dc",
        "relation": "provide power",
        "query_text": "Plug the bedside lamp's cord into the electric outlet near the bed (x=-0.945) to power the lamp",
        "tags": ["simple_functional", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["label_only_shortcut"],
        "label_only_solvable": True,
        "notes": "Pilot 000019 reuse as another simple_functional baseline (only 1 outlet, 1 lamp in scene 421254 — both unique). Kept as label-only-solvable baseline."
    },
    {
        "scene": "420683",
        "target": "1bcde871-8765-4a7b-b2fa-92caeb16596e",
        "anchor": "74f9d3c4-241d-4a60-937d-92a11e9421c7",
        "relation": "rotate to open or close",
        "query_text": "Rotate the window handle (not push the window itself) to crack open the window for fresh air",
        "tags": ["endpoint_ambiguity", "same_label_disambiguation", "functional_relation"],
        "geometry_cues": [],
        "failure_modes": ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
        "label_only_solvable": False,
        "notes": "Pilot 000020 reuse with endpoint emphasis. Window (anchor) and handle (target) both interactive."
    },
    # ------------------------------------------------------------
    # 421380 INTRA-ANCHOR VERTICAL — 10 queries (q104-q113).
    # Mingqian acked 2026-05-16: phase1.md修订 2 relaxed to allow
    # intra-anchor upper/lower descriptors in 421380 (scene-wide
    # vertical still forbidden). TV stand 6e39c1ea has 14 knobs in
    # 2 vertical columns: cluster A (x≈1.07, 5 knobs, intra-cluster
    # z spread 0.4m) + cluster B (x≈1.47, 5 knobs, same spread).
    # All 10 are "pull to open or close a drawer" → TV stand.
    # ------------------------------------------------------------
    # --- Cluster A (x≈1.07, center-left column, 5 stacked drawers) ---
    {
        "scene": "421380",
        "target": "282c10c9-3020-4333-b468-cb3197b80940",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the topmost knob in the center-left column (x≈1.07) of the television stand to open its top drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["topmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column", "choose_wrong_column"],
        "label_only_solvable": False,
        "notes": "Cluster A (x≈1.07) has 5 knobs stacked vertically on the TV stand. Target 282c10c9 at (x=1.068, z=193.749) is topmost. z order: 08a1222a(193.346) < bb923245(193.478) < f26835a1(193.568) < 927cd15d(193.658) < 282c10c9(193.749). Intra-anchor vertical allowed per phase1.md修订 2 v2."
    },
    {
        "scene": "421380",
        "target": "927cd15d-3bd7-4709-b88d-6e4c8b8afca4",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top knob in the center-left column (x≈1.07) of the television stand to open the second drawer from the top",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_topmost_knob", "choose_middle_knob"],
        "label_only_solvable": False,
        "notes": "Cluster A 2nd-from-top. Target 927cd15d at (x=1.068, z=193.658)."
    },
    {
        "scene": "421380",
        "target": "f26835a1-518e-4918-a492-c23cee451f0a",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle knob in the center-left column (x≈1.07) of the television stand, the third drawer from the top of five",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column"],
        "label_only_solvable": False,
        "notes": "Cluster A middle row. Target f26835a1 at (x=1.067, z=193.568)."
    },
    {
        "scene": "421380",
        "target": "bb923245-a044-4875-b548-bee144ca7d2a",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-bottom knob in the center-left column (x≈1.07) of the television stand, the one just above the lowest drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lower"],
        "failure_modes": ["same_label_wrong_instance", "choose_bottommost_knob", "choose_middle_knob"],
        "label_only_solvable": False,
        "notes": "Cluster A 2nd-from-bottom. Target bb923245 at (x=1.068, z=193.478)."
    },
    {
        "scene": "421380",
        "target": "08a1222a-4837-49cf-a0c6-836d236311a0",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottommost knob in the center-left column (x≈1.07) of the television stand to open its bottom drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lowest"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column", "choose_wrong_column"],
        "label_only_solvable": False,
        "notes": "Cluster A bottommost. Target 08a1222a at (x=1.070, z=193.346)."
    },
    # --- Cluster B (x≈1.47, center-right column, 5 stacked drawers) ---
    {
        "scene": "421380",
        "target": "352d3a71-9681-4a32-aecd-1d89a929bd7b",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the topmost knob in the center-right column (x≈1.47) of the television stand to open its top drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["topmost"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column", "choose_wrong_column"],
        "label_only_solvable": False,
        "notes": "Cluster B (x≈1.47) has 5 knobs stacked vertically on the TV stand. z order: 2569559b(193.348) < 8fa63b99(193.477) < 1365989c(193.568) < 73839439(193.660) < 352d3a71(193.750). Target 352d3a71 at (x=1.468, z=193.750) is topmost."
    },
    {
        "scene": "421380",
        "target": "73839439-0110-43e5-bb6e-d2883e193874",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-top knob in the center-right column (x≈1.47) of the television stand to open the second drawer from the top",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["upper"],
        "failure_modes": ["same_label_wrong_instance", "choose_topmost_knob", "choose_middle_knob"],
        "label_only_solvable": False,
        "notes": "Cluster B 2nd-from-top. Target 73839439 at (x=1.467, z=193.660)."
    },
    {
        "scene": "421380",
        "target": "1365989c-2223-4888-8465-ec59a7adea8e",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the middle knob in the center-right column (x≈1.47) of the television stand, the third drawer from the top of five",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["middle"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column"],
        "label_only_solvable": False,
        "notes": "Cluster B middle row. Target 1365989c at (x=1.469, z=193.568)."
    },
    {
        "scene": "421380",
        "target": "8fa63b99-b099-4906-a608-5325add561e4",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the second-from-bottom knob in the center-right column (x≈1.47) of the television stand, the one just above the lowest drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lower"],
        "failure_modes": ["same_label_wrong_instance", "choose_bottommost_knob", "choose_middle_knob"],
        "label_only_solvable": False,
        "notes": "Cluster B 2nd-from-bottom. Target 8fa63b99 at (x=1.467, z=193.477)."
    },
    {
        "scene": "421380",
        "target": "2569559b-e5fd-4e92-a533-308098b6becd",
        "anchor": "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
        "relation": "pull to open or close a drawer",
        "query_text": "Pull the bottommost knob in the center-right column (x≈1.47) of the television stand to open its bottom drawer",
        "tags": ["same_label_disambiguation", "geometry_aware"],
        "geometry_cues": ["lowest"],
        "failure_modes": ["same_label_wrong_instance", "choose_adjacent_knob_in_column", "choose_wrong_column"],
        "label_only_solvable": False,
        "notes": "Cluster B bottommost. Target 2569559b at (x=1.469, z=193.348)."
    },
]


def load_scene_data():
    """Load scene graphs and geometry for the 6 selected scenes."""
    with ENRICH_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    graphs = {}
    for item in data["data"]:
        sid = item["scene_id"]
        if sid in SELECTED_SCENES and sid not in graphs:
            if item.get("scene_graph"):
                graphs[sid] = item["scene_graph"]
    with GEOM_PATH.open(encoding="utf-8") as f:
        geom = json.load(f)
    return graphs, geom


def build_queries(specs, graphs, geom):
    queries = []
    diagnostics = []
    next_id = 21  # continue from pilot's 20
    seen_instance_keys = set()
    for spec in specs:
        sid = spec["scene"]
        sg = graphs[sid]
        nodes_by_id = {n["node_id"]: n for n in sg["nodes"]}
        edges_by_id = {e["edge_id"]: e for e in sg["edges"]}
        target_nid = spec["target"]
        anchor_nid = spec["anchor"]
        edge_id = f"{target_nid}|{spec['relation']}|{anchor_nid}"
        if edge_id not in edges_by_id:
            raise ValueError(f"Edge not found in scene {sid}: {edge_id}")
        target_label = nodes_by_id[target_nid]["label"]
        anchor_label = nodes_by_id[anchor_nid]["label"]
        # real-label same-label count (exclude 'unknown' per phase1.md修订 1)
        same_label = sum(
            1 for n in sg["nodes"]
            if n["label"] == target_label and n["label"] != "unknown"
            and n["node_id"] != target_nid
        )
        # distractor node ids (same-label, excluding target itself and 'unknown')
        distractor_ids = [
            n["node_id"] for n in sg["nodes"]
            if n["label"] == target_label and n["label"] != "unknown"
            and n["node_id"] != target_nid
        ]
        instance_key = (target_nid, anchor_nid, edge_id)
        if instance_key in seen_instance_keys:
            raise ValueError(f"Duplicate instance key in specs: {instance_key}")
        seen_instance_keys.add(instance_key)
        qid = f"human_func_v1_{next_id:06d}"
        next_id += 1

        query = {
            "query_id": qid,
            "scene_id": sid,
            "query_text": spec["query_text"],
            "query_type": "functional",
            "target_node_id": target_nid,
            "anchor_node_id": anchor_nid,
            "supporting_edge_ids": [edge_id],
            "difficulty_tags": spec["tags"],
            "is_long_range": False,
            "evidence_chain": [f"{target_label} --{spec['relation']}--> {anchor_label}"],
            "source": "human",
            "target_label": target_label,
            "anchor_label": anchor_label,
            "num_same_label_distractors": same_label,
            "is_label_only_solvable": spec["label_only_solvable"],
            "notes": spec["notes"],
        }
        if spec["geometry_cues"]:
            query["geometry_cues"] = spec["geometry_cues"]
        if spec["failure_modes"]:
            query["expected_failure_modes"] = spec["failure_modes"]
        queries.append(query)

        diag = {
            "query_id": qid,
            "scene_id": sid,
            "is_label_only_solvable": spec["label_only_solvable"],
            "num_same_label_distractors": same_label,
            "expected_failure_modes": spec["failure_modes"],
            "distractor_node_ids": distractor_ids,
            "geometry_cues_used": spec["geometry_cues"],
            "evidence_hop_count": 1,
        }
        diagnostics.append(diag)

    return queries, diagnostics


def build_summary(queries, diagnostics):
    total = len(queries)
    tag_counts = Counter()
    scene_dist = Counter()
    label_only_solvable_count = 0
    for q in queries:
        for tag in q["difficulty_tags"]:
            tag_counts[tag] += 1
        scene_dist[q["scene_id"]] += 1
        if q.get("is_label_only_solvable"):
            label_only_solvable_count += 1

    distractor_hist = Counter()
    for d in diagnostics:
        n = d["num_same_label_distractors"]
        # bin: 0, 1, 2-4, 5-9, 10-19, 20+
        if n == 0:
            distractor_hist["0"] += 1
        elif n == 1:
            distractor_hist["1"] += 1
        elif n <= 4:
            distractor_hist["2-4"] += 1
        elif n <= 9:
            distractor_hist["5-9"] += 1
        elif n <= 19:
            distractor_hist["10-19"] += 1
        else:
            distractor_hist["20+"] += 1

    # multi_anchor x geometry_aware co-occurrence
    co_occur = Counter()
    for q in queries:
        tags = set(q["difficulty_tags"])
        if "multi_anchor" in tags and "geometry_aware" in tags:
            co_occur["multi_anchor_AND_geometry_aware"] += 1
        if "multi_anchor" in tags and "geometry_aware" not in tags:
            co_occur["multi_anchor_only"] += 1
        if "geometry_aware" in tags and "multi_anchor" not in tags:
            co_occur["geometry_aware_only"] += 1

    anchors = {
        "ideal_target": 150,
        "minimum": 80,
        "rationale": "Realistic cap from 6-scene edge supply (~79 fresh edges, with cluster knobs in 421380 reducing distinguishable edges further)."
    }

    return {
        "total_queries": total,
        "scene_distribution": dict(scene_dist),
        "difficulty_tag_counts": dict(tag_counts),
        "difficulty_tag_ratios_pct": {
            tag: round(100 * c / total, 1) for tag, c in tag_counts.items()
        },
        "is_label_only_solvable_count": label_only_solvable_count,
        "is_label_only_solvable_ratio_pct": round(100 * label_only_solvable_count / total, 1),
        "num_same_label_distractors_histogram": dict(distractor_hist),
        "multi_anchor_x_geometry_aware_co_occurrence": dict(co_occur),
        "phase2_anchors": anchors,
    }


def main():
    graphs, geom = load_scene_data()
    queries, diagnostics = build_queries(SPECS, graphs, geom)
    summary = build_summary(queries, diagnostics)

    with JSONL_PATH.open("w", encoding="utf-8") as f:
        for q in queries:
            f.write(json.dumps(q, ensure_ascii=False) + "\n")
    with DIAG_PATH.open("w", encoding="utf-8") as f:
        for d in diagnostics:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    with SUMMARY_PATH.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(queries)} queries to {JSONL_PATH}")
    print(f"Wrote {len(diagnostics)} diagnostics to {DIAG_PATH}")
    print(f"Wrote summary to {SUMMARY_PATH}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
