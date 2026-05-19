"""Phase 3 revision: compose 30 minimal pairs with self-describing schema.

Replaces phase3_pair_builder.py + phase3_retag_minimal_pair.py.

Driven by Mingqian's 2026-05-19 review feedback:
  - 30 pairs total (10 from mining of existing 20 pairs + 20 newly written)
  - All pairs live in functional_queries_v1.jsonl (no separate file)
  - Each participating query carries minimal_pair_id / minimal_pair_role /
    minimal_pair_partner_id (bidirectional self-describing schema)
  - Pilot queries roll back their minimal_pair tag (rule: same-file pairs only)
  - Reduce knob/handle dominance; new queries use natural language without
    coordinate annotations like "x=1.07"

Outputs (in-place modifications):
  - pilot_20_queries.jsonl: remove `minimal_pair` tag from 7 queries
  - functional_queries_v1.jsonl: keep/drop `minimal_pair` tag on existing
    queries based on KEPT_MINING_PAIRS; add 3 self-describing fields to
    queries in kept pairs; append 40 new queries (000114-000153) with full
    schema + self-describing fields
  - minimal_pairs_v1.jsonl: rewrite as 30 pair derived view
  - hard_slice_summary_v1.json: recompute difficulty_tag_counts and
    minimal_pairs section

Idempotent: re-running produces identical output.
"""
from __future__ import annotations
import json
import math
from collections import Counter, OrderedDict
from pathlib import Path

BENCH_ROOT = Path(__file__).resolve().parents[3]
QUERY_DIR = BENCH_ROOT / "human_annotations" / "functional_queries_v1"
GEOM_PATH = BENCH_ROOT / "geometry" / "scenefun3d_node_geom.json"

PILOT_PATH = QUERY_DIR / "pilot_20_queries.jsonl"
MAIN_PATH = QUERY_DIR / "functional_queries_v1.jsonl"
PAIRS_PATH = QUERY_DIR / "minimal_pairs_v1.jsonl"
HS_PATH = QUERY_DIR / "hard_slice_summary_v1.json"
EXISTING_PAIRS_PATH = QUERY_DIR / "minimal_pairs_v1.jsonl"


# ============================================================================
# 10 MINING PAIRS to KEEP (out of original 20)
# ============================================================================
# Kept pair_ids from previous minimal_pairs_v1.jsonl (15 main-only available;
# we pick 10 for diversity across changed_factor and scene). The full pair row
# is read from the existing minimal_pairs_v1.jsonl by pair_id, so we just list
# the IDs here.
KEPT_MINING_PAIR_IDS = [
    "minpair_v1_000001",  # 421380 cluster A vertical step (spatial)
    "minpair_v1_000003",  # 421380 column-switch (spatial)
    "minpair_v1_000007",  # 421602 dresser vertical (spatial)
    "minpair_v1_000009",  # 469011 oven horizontal step (spatial)
    "minpair_v1_000012",  # 421380 remote left-right (geom_dir)
    "minpair_v1_000014",  # 469011 oven row endpoints (geom_dir)
    "minpair_v1_000015",  # 420683 two nightstands (anchor_object)
    "minpair_v1_000017",  # 421254 two dressers (anchor_object)
    # Final mining = 8 pairs (down from 10 to resolve query-id conflicts:
    # q067 was shared between pair_005 + pair_017 -> dropped pair_005;
    # q104 was shared between pair_001 + pair_020 -> dropped pair_020.
    # functional_relation slot is filled by new pair_039 instead.)
]

# Pairs we DROP (kept here for traceability only):
#   - minpair_v1_000002 (cluster B mirror of 001 -- redundant)
#   - minpair_v1_000004 (pilot+main mixed -- same-file rule)
#   - minpair_v1_000005 (shares q067 with pair_017; pair_017 anchor_object wins)
#   - minpair_v1_000006 (cluster vertical redundant with 001)
#   - minpair_v1_000008 (vertical redundant with 007)
#   - minpair_v1_000010 (vertical redundant with 007)
#   - minpair_v1_000011 (overlaps minpair_012 in 421380)
#   - minpair_v1_000013 (pilot+main mixed)
#   - minpair_v1_000016 (pilot+main mixed)
#   - minpair_v1_000018 (all-pilot)
#   - minpair_v1_000019 (all-pilot)
#   - minpair_v1_000020 (shares q104 with pair_001; functional_relation
#                        slot taken by new pair_039 instead)


# ============================================================================
# 40 NEW QUERIES (000114-000153)
# ============================================================================
# Each tuple: (short_id, scene_id, target_node_id, anchor_node_id, relation,
#              target_label, anchor_label, query_text,
#              difficulty_tags_extra, num_same_label_distractors,
#              is_label_only_solvable, geometry_cues, expected_failure_modes,
#              notes)
# `difficulty_tags` always includes "minimal_pair" automatically. The first
# tag in `difficulty_tags_extra` should describe the primary slice (e.g.,
# "spatial_qualifier").
NEW_QUERIES = [
    # ----- Pair 21: outlet anchor_object direct (469011) -----
    ("000114", "469011",
     "548a6569-5c70-4d7b-9f10-0ece005e6c00", "7fddf637-3da9-4511-b4b4-fc6a042db72c",
     "provide power", "electric outlet", "fridge",
     "Which outlet provides power to the refrigerator?",
     ["functional_relation"], 5, False,
     [], ["choose_other_outlet", "label_only_shortcut"],
     "Phase 3 new: direct language form. Pairs with 000115 (outlet->hood)."),
    ("000115", "469011",
     "0146b63e-698d-4337-9a8b-f7b1a25c05f7", "3d0352ee-0916-4a98-b353-a083f97c9fd7",
     "provide power", "electric outlet", "exhaust hood / ventilation fan",
     "Which outlet provides power to the exhaust hood above the stove?",
     ["functional_relation"], 5, False,
     [], ["choose_other_outlet"],
     "Phase 3 new: direct language form. Pairs with 000114 (outlet->fridge)."),

    # ----- Pair 22: outlet anchor_object indirect/hard_negative (469011) -----
    ("000116", "469011",
     "548a6569-5c70-4d7b-9f10-0ece005e6c00", "7fddf637-3da9-4511-b4b4-fc6a042db72c",
     "provide power", "electric outlet", "fridge",
     "I need to keep my groceries cold for the week. Which power source supports that appliance?",
     ["functional_relation", "hard_negative"], 5, False,
     [], ["label_only_shortcut", "ignore_functional_relation"],
     "Phase 3 new: indirect hard_negative form (no 'outlet' or 'fridge' words). Pairs with 000117."),
    ("000117", "469011",
     "0146b63e-698d-4337-9a8b-f7b1a25c05f7", "3d0352ee-0916-4a98-b353-a083f97c9fd7",
     "provide power", "electric outlet", "exhaust hood / ventilation fan",
     "I want to vent the cooking smoke out of the kitchen. Which power source supports that appliance?",
     ["functional_relation", "hard_negative"], 5, False,
     [], ["label_only_shortcut", "ignore_functional_relation"],
     "Phase 3 new: indirect hard_negative form. Pairs with 000116."),

    # ----- Pair 23: handle anchor_object NEW (469011 handle->fridge vs handle->oven) -----
    ("000118", "469011",
     "2abcdace-ba3f-45c0-8dce-eac4de015ee8", "7fddf637-3da9-4511-b4b4-fc6a042db72c",
     "pull to open or close", "handle", "fridge",
     "Pull the handle to open the refrigerator door.",
     ["endpoint_ambiguity"], 1, False,
     [], ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
     "Phase 3 new: handle->fridge. Pairs with 000119 (handle->oven)."),
    ("000119", "469011",
     "47d6518d-dce3-4c45-8cfc-34c56bbb3454", "8e66432e-ee5a-4009-9ad5-f53d29772552",
     "pull to open or close", "handle", "oven",
     "Pull the handle to open the oven door.",
     ["endpoint_ambiguity"], 1, False,
     [], ["choose_anchor_instead_of_target", "same_label_wrong_instance"],
     "Phase 3 new: handle->oven. Pairs with 000118 (handle->fridge)."),

    # ----- Pair 24: oven knob horizontal step clean lang (469011) -----
    ("000120", "469011",
     "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8", "8e66432e-ee5a-4009-9ad5-f53d29772552",
     "rotate to adjust the setting", "knob", "oven",
     "Turn the leftmost burner control on the oven panel to adjust its heat.",
     ["same_label_disambiguation", "geometry_aware"], 4, False,
     ["leftmost"], ["choose_adjacent_knob_in_row"],
     "Phase 3 new: oven knob leftmost (clean lang, no coords). Pairs with 000121."),
    ("000121", "469011",
     "06b684bb-7a5c-4717-847a-d343bd6824d9", "8e66432e-ee5a-4009-9ad5-f53d29772552",
     "rotate to adjust the setting", "knob", "oven",
     "Turn the knob just right of the leftmost on the oven control panel.",
     ["same_label_disambiguation", "geometry_aware"], 4, False,
     ["just-right-of-leftmost"], ["choose_adjacent_knob_in_row"],
     "Phase 3 new: oven knob 2nd-from-left (clean lang). Pairs with 000120."),

    # ----- Pair 25: oven knob row endpoints clean lang (469011) -----
    ("000122", "469011",
     "85f5f2f0-ef9b-4e32-a0de-cd8a7f54db4b", "8e66432e-ee5a-4009-9ad5-f53d29772552",
     "rotate to adjust the setting", "knob", "oven",
     "Turn the rightmost burner control on the oven to adjust its heat.",
     ["same_label_disambiguation", "geometry_aware"], 4, False,
     ["rightmost"], ["choose_adjacent_knob_in_row", "choose_leftmost_knob"],
     "Phase 3 new: oven knob rightmost (clean lang). Pairs with 000123 (leftmost)."),
    ("000123", "469011",
     "d003c3b8-3330-4adf-8c1e-6c8c9f2245f8", "8e66432e-ee5a-4009-9ad5-f53d29772552",
     "rotate to adjust the setting", "knob", "oven",
     "Turn the burner control at the opposite end of the oven panel from the rightmost knob.",
     ["same_label_disambiguation", "geometry_aware"], 4, False,
     ["opposite-of-rightmost"], ["choose_rightmost_knob", "choose_middle"],
     "Phase 3 new: oven knob leftmost via relative reference. Pairs with 000122."),

    # ----- Pair 26: TV remote 421380 (clean lang of minpair_012) -----
    ("000124", "421380",
     "c44a2818-7f0c-4200-bda1-915f3ade1731", "8b0f6a88-2f0e-4f44-ad59-65dec8b2aca1",
     "control", "remote", "television",
     "Pick up the remote sitting closer to the left edge of the TV stand and use it to change channels.",
     ["same_label_disambiguation", "geometry_aware"], 1, False,
     ["left"], ["choose_other_remote"],
     "Phase 3 new: 421380 left remote, natural language no coords. Pairs with 000125."),
    ("000125", "421380",
     "d75da7cf-4a4b-40fc-ac77-ffd1dd8edb6b", "8b0f6a88-2f0e-4f44-ad59-65dec8b2aca1",
     "control", "remote", "television",
     "Pick up the remote sitting closer to the right edge of the TV stand and use it to change channels.",
     ["same_label_disambiguation", "geometry_aware"], 1, False,
     ["right"], ["choose_other_remote"],
     "Phase 3 new: 421380 right remote, natural language. Pairs with 000124."),

    # ----- Pair 27: TV remote 421254 (clean lang of minpair_013) -----
    ("000126", "421254",
     "560f1e2c-e62d-4f1e-93e8-3acbf61433cd", "8bd6869b-b734-4041-a3e5-0cd3e3b18d0e",
     "control", "remote", "television",
     "Use the remote placed to the right side of the TV to change channels.",
     ["same_label_disambiguation", "geometry_aware"], 1, False,
     ["right"], ["choose_other_remote"],
     "Phase 3 new: 421254 right remote, clean lang. Pairs with 000127."),
    ("000127", "421254",
     "9c06f662-e551-484e-9559-a7d3c0b5b31d", "8bd6869b-b734-4041-a3e5-0cd3e3b18d0e",
     "control", "remote", "television",
     "Use the remote placed to the left side of the TV to change channels.",
     ["same_label_disambiguation", "geometry_aware"], 1, False,
     ["left"], ["choose_other_remote"],
     "Phase 3 new: 421254 left remote, clean lang. Pairs with 000126."),

    # ----- Pair 28: 421380 cluster A topmost-2ndtop clean lang -----
    ("000128", "421380",
     "282c10c9-3020-4333-b468-cb3197b80940", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the highest knob in the left drawer column under the TV to open its top drawer.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["highest", "left-column"], ["choose_adjacent_knob_in_column", "choose_wrong_column"],
     "Phase 3 new: cluster A topmost, no coordinates. Pairs with 000129."),
    ("000129", "421380",
     "927cd15d-3bd7-4709-b88d-6e4c8b8afca4", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the second-highest knob in the left drawer column under the TV.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["second-highest", "left-column"], ["choose_adjacent_knob_in_column", "choose_topmost"],
     "Phase 3 new: cluster A 2nd-from-top. Pairs with 000128."),

    # ----- Pair 29: 421380 cluster A middle-2ndbottom clean lang -----
    ("000130", "421380",
     "f26835a1-518e-4918-a492-c23cee451f0a", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the middle knob of the left drawer column under the television.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["middle", "left-column"], ["choose_adjacent_knob_in_column"],
     "Phase 3 new: cluster A middle. Pairs with 000131."),
    ("000131", "421380",
     "bb923245-a044-4875-b548-bee144ca7d2a", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the second-from-bottom knob in the left drawer column under the television.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["second-from-bottom", "left-column"], ["choose_adjacent_knob_in_column"],
     "Phase 3 new: cluster A 2nd-from-bottom. Pairs with 000130."),

    # ----- Pair 30: 421380 cluster A endpoints clean lang -----
    ("000132", "421380",
     "08a1222a-4837-49cf-a0c6-836d236311a0", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the lowest knob in the left drawer column under the television to open the bottom drawer.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["lowest", "left-column"], ["choose_adjacent_knob_in_column", "choose_topmost"],
     "Phase 3 new: cluster A bottommost. Pairs with 000133 (topmost)."),
    ("000133", "421380",
     "282c10c9-3020-4333-b468-cb3197b80940", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the topmost knob of the left drawer column under the television, opposite end from the lowest.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["topmost", "opposite-of-lowest", "left-column"], ["choose_lowest"],
     "Phase 3 new: cluster A topmost via relative reference. Pairs with 000132."),

    # ----- Pair 31: 421380 cluster B endpoints clean lang -----
    ("000134", "421380",
     "352d3a71-9681-4a32-aecd-1d89a929bd7b", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the topmost knob in the right drawer column under the TV stand.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["topmost", "right-column"], ["choose_lowest", "choose_wrong_column"],
     "Phase 3 new: cluster B topmost, clean lang. Pairs with 000135."),
    ("000135", "421380",
     "2569559b-e5fd-4e92-a533-308098b6becd", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the bottommost knob in the right drawer column under the TV stand.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["bottommost", "right-column"], ["choose_topmost", "choose_wrong_column"],
     "Phase 3 new: cluster B bottommost. Pairs with 000134."),

    # ----- Pair 32: 421380 cluster B mid-step clean lang -----
    ("000136", "421380",
     "73839439-0110-43e5-bb6e-d2883e193874", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the second-from-top knob in the right drawer column under the TV.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["second-from-top", "right-column"], ["choose_topmost"],
     "Phase 3 new: cluster B 2nd-top. Pairs with 000137."),
    ("000137", "421380",
     "8fa63b99-b099-4906-a608-5325add561e4", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the second-from-bottom knob in the right drawer column under the TV.",
     ["same_label_disambiguation", "geometry_aware"], 14, False,
     ["second-from-bottom", "right-column"], ["choose_bottommost"],
     "Phase 3 new: cluster B 2nd-bottom. Pairs with 000136."),

    # ----- Pair 33: cluster A vs B same rank (2nd-top) -----
    ("000138", "421380",
     "927cd15d-3bd7-4709-b88d-6e4c8b8afca4", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the upper-middle knob in the left column under the TV.",
     ["same_label_disambiguation", "geometry_aware", "multi_anchor"], 14, False,
     ["upper-middle", "left-column"], ["choose_wrong_column"],
     "Phase 3 new: cluster A 2nd-top via 'upper-middle' wording. Pairs with 000139 (cross-column)."),
    ("000139", "421380",
     "73839439-0110-43e5-bb6e-d2883e193874", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the upper-middle knob in the right column under the TV.",
     ["same_label_disambiguation", "geometry_aware", "multi_anchor"], 14, False,
     ["upper-middle", "right-column"], ["choose_wrong_column"],
     "Phase 3 new: cluster B 2nd-top via 'upper-middle' wording. Pairs with 000138."),

    # ----- Pair 34: 421254 cross-dresser anchor_object clean lang -----
    ("000140", "421254",
     "9bb22a10-e42b-46fb-af9b-8a8df7d3f6b3", "97164eaa-1cf8-49ff-9024-f20d4d64f13e",
     "pull to open or close a drawer", "knob", "dresser / chest of drawers",
     "Open the top-left drawer of the right-hand dresser by pulling its knob.",
     ["same_label_disambiguation", "multi_anchor"], 19, False,
     ["top-left", "right-hand-dresser"], ["choose_other_dresser"],
     "Phase 3 new: 421254 anchor 97164eaa. Pairs with 000141 (anchor f1f234c5)."),
    ("000141", "421254",
     "8ab6af8d-3cad-4fad-bf78-157916578132", "f1f234c5-0f2c-4fd0-aaf5-91a02c121ccb",
     "pull to open or close a drawer", "knob", "dresser / chest of drawers",
     "Open the top-left drawer of the left-hand dresser by pulling its knob.",
     ["same_label_disambiguation", "multi_anchor"], 19, False,
     ["top-left", "left-hand-dresser"], ["choose_other_dresser"],
     "Phase 3 new: 421254 anchor f1f234c5. Pairs with 000140."),

    # ----- Pair 35: 420683 cross-nightstand anchor_object clean lang -----
    ("000142", "420683",
     "7478eaa4-362a-4613-9d6e-d41b794f41b9", "6eabdfdc-d41c-4511-a841-08b177fd3d4b",
     "pull to open or close", "knob", "nightstand drawer",
     "Pull the knob to open the drawer of the nightstand on the right side of the bed.",
     ["same_label_disambiguation", "multi_anchor"], 8, False,
     ["right-side-of-bed"], ["choose_other_nightstand"],
     "Phase 3 new: 420683 anchor 6eabdfdc (right nightstand). Pairs with 000143."),
    ("000143", "420683",
     "875242c5-10d3-4dd4-95ec-d20799e913c3", "ef11c37b-4be8-4b73-aa2e-ff2d1a9ea5ff",
     "pull to open or close", "knob", "nightstand drawer",
     "Pull the knob to open the drawer of the nightstand on the other side of the bed.",
     ["same_label_disambiguation", "multi_anchor"], 8, False,
     ["other-side-of-bed"], ["choose_other_nightstand"],
     "Phase 3 new: 420683 anchor ef11c37b. Pairs with 000142."),

    # ----- Pair 36: 421013 cross-nightstand anchor_object clean lang -----
    ("000144", "421013",
     "7f13ad67-a21a-4ed2-9bc1-c0e330ebfbb4", "600ca2b3-a6fd-4360-8279-2e91df4d6851",
     "pull to open or close a drawer", "handle", "dresser / nightstand",
     "Pull the handle to open a drawer of the nightstand beside the headboard.",
     ["same_label_disambiguation", "multi_anchor"], 8, False,
     ["beside-headboard"], ["choose_other_nightstand"],
     "Phase 3 new: 421013 anchor 600ca2b3. Pairs with 000145."),
    ("000145", "421013",
     "4375aca4-619a-49e3-9bb5-abcd2fdc203f", "e810c10f-8b4a-4fd1-8ae1-0d51fd3e2295",
     "pull to open or close a drawer", "handle", "dresser / nightstand",
     "Pull the handle to open a drawer of the nightstand on the opposite side of the room.",
     ["same_label_disambiguation", "multi_anchor"], 8, False,
     ["opposite-side-of-room"], ["choose_other_nightstand"],
     "Phase 3 new: 421013 anchor e810c10f. Pairs with 000144."),

    # ----- Pair 37: 421602 cross-dresser anchor_object clean lang -----
    ("000146", "421602",
     "9fcd23c1-4638-41a9-a8d8-02bffa3e6a7c", "f4e41b55-ad6c-4f3c-a624-d139edd6f6c3",
     "pull to open or close a drawer", "handle", "dresser / chest of drawers",
     "Pull the handle of the topmost drawer on the dresser against the back wall.",
     ["same_label_disambiguation", "multi_anchor"], 10, False,
     ["topmost", "back-wall"], ["choose_other_dresser"],
     "Phase 3 new: 421602 anchor f4e41b55. Pairs with 000147."),
    ("000147", "421602",
     "90e6a8bd-5b0f-4991-8bbe-831acf0faa53", "340b66f3-ff28-4436-a311-ba6ba9202289",
     "pull to open or close a drawer", "handle", "dresser / chest of drawers",
     "Pull the handle of the bottommost drawer on the dresser placed beside the window.",
     ["same_label_disambiguation", "multi_anchor"], 10, False,
     ["bottommost", "beside-window"], ["choose_other_dresser"],
     "Phase 3 new: 421602 anchor 340b66f3. Pairs with 000146."),

    # ----- Pair 38: 421013 wardrobe clean lang (was minpair_004 mixed) -----
    ("000148", "421013",
     "217402c7-af78-4217-b70f-ef3bb65f71d4", "a00be285-5f92-4254-aadd-83e7182b5db9",
     "pull to open or close", "handle", "wardrobe",
     "Pull the bottommost handle of the tall wardrobe to open its bottom compartment.",
     ["same_label_disambiguation", "geometry_aware"], 8, False,
     ["bottommost"], ["choose_adjacent_handle"],
     "Phase 3 new: 421013 wardrobe bottommost handle. Pairs with 000149."),
    ("000149", "421013",
     "d1cb8681-bd37-49eb-8d89-5f09d782a627", "a00be285-5f92-4254-aadd-83e7182b5db9",
     "pull to open or close", "handle", "wardrobe",
     "Pull the second-from-bottom handle of the tall wardrobe.",
     ["same_label_disambiguation", "geometry_aware"], 8, False,
     ["second-from-bottom"], ["choose_bottommost", "choose_topmost"],
     "Phase 3 new: 421013 wardrobe 2nd-from-bottom handle. Pairs with 000148."),

    # ----- Pair 39: 421380 functional_relation amplifier -----
    ("000150", "421380",
     "9db14ed4-ed96-4e43-a12d-7a1a865f0161", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close", "knob", "television stand / cabinet",
     "Pull the knob on the surface-mounted handle of the TV stand to open its side compartment door.",
     ["functional_relation", "endpoint_ambiguity"], 14, False,
     [], ["choose_drawer_cluster_knob"],
     "Phase 3 new: TV stand non-drawer knob, 'pull to open or close' relation. Pairs with 000151 (drawer cluster knob)."),
    ("000151", "421380",
     "1365989c-2223-4888-8465-ec59a7adea8e", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "Pull the middle knob of the right drawer column on the TV stand to slide out the third drawer.",
     ["functional_relation", "same_label_disambiguation", "geometry_aware"], 14, False,
     ["middle", "right-column"], ["choose_non_drawer_knob"],
     "Phase 3 new: TV stand drawer cluster knob, 'pull-to-open-a-drawer' relation. Pairs with 000150."),

    # ----- Pair 40: 421380 cluster A indirect/hard_negative variant -----
    ("000152", "421380",
     "927cd15d-3bd7-4709-b88d-6e4c8b8afca4", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "I want to store a small remote in the upper half of the left drawer column. Which knob should I pull?",
     ["same_label_disambiguation", "geometry_aware", "hard_negative"], 14, False,
     ["upper-half", "left-column"], ["label_only_shortcut"],
     "Phase 3 new: cluster A upper half via indirect storage scenario. Pairs with 000153."),
    ("000153", "421380",
     "bb923245-a044-4875-b548-bee144ca7d2a", "6e39c1ea-d3cd-4059-9b4f-c2a506d716e9",
     "pull to open or close a drawer", "knob", "television stand / cabinet",
     "I want to store a heavy book in the lower half of the left drawer column. Which knob should I pull?",
     ["same_label_disambiguation", "geometry_aware", "hard_negative"], 14, False,
     ["lower-half", "left-column"], ["label_only_shortcut"],
     "Phase 3 new: cluster A lower half via indirect storage scenario. Pairs with 000152."),
]


# ============================================================================
# 20 NEW PAIRS (pair_ids 000021-000040)
# ============================================================================
# Each tuple: (pair_id, query_a_short, query_b_short, changed_factor,
#              pair_evidence_used, why_hard, diff_summary, notes)
NEW_PAIRS = [
    ("minpair_v1_000021", "000114", "000115", "anchor_object",
     ["anchor_identity", "functional_edge"],
     "Same target_label 'electric outlet', same 'provide power' relation; only the powered appliance changes. Direct language form.",
     "outlet->fridge vs outlet->exhaust hood (direct natural language, no coords)",
     "Phase 3 anchor_object pair, direct lang. Companion to pair 000022 (indirect)."),

    ("minpair_v1_000022", "000116", "000117", "anchor_object",
     ["anchor_identity", "functional_edge"],
     "Same outlet/relation, different appliance. Queries avoid the words 'outlet', 'fridge', 'hood' -- model must reason about purpose to map to functional edge.",
     "outlet->fridge vs outlet->hood (indirect hard_negative language)",
     "Phase 3 anchor_object + hard_negative variant of pair 000021."),

    ("minpair_v1_000023", "000118", "000119", "anchor_object",
     ["anchor_identity"],
     "Two different handles, each attached to a different appliance (fridge vs oven). Both pull-to-open relation; only the anchor differs.",
     "handle->fridge vs handle->oven (kitchen, anchor_object)",
     "Phase 3 NEW topic not in mining: handle->appliance anchor_object pair."),

    ("minpair_v1_000024", "000120", "000121", "spatial_qualifier",
     ["geometry_x_axis"],
     "Oven panel knobs in horizontal row; only the within-row position changes by one step. Both queries refer to 'leftmost-relative' positions in natural language.",
     "oven knob leftmost vs just-right-of-leftmost (natural language)",
     "Phase 3 clean-lang variant of mining minpair_009 (no coordinates in text)."),

    ("minpair_v1_000025", "000122", "000123", "geometry_direction",
     ["geometry_x_axis"],
     "Strict left vs right endpoints of oven knob row. q123 uses relative-position reference ('opposite end from rightmost') to test compositional natural language.",
     "oven knob rightmost vs leftmost (via relative reference)",
     "Phase 3 clean-lang variant of mining minpair_014."),

    ("minpair_v1_000026", "000124", "000125", "geometry_direction",
     ["geometry_x_axis"],
     "Left vs right remote on the same TV stand. Clean natural language, no coordinates.",
     "421380 remote left vs right (natural language)",
     "Phase 3 clean-lang variant of mining minpair_012."),

    ("minpair_v1_000027", "000126", "000127", "geometry_direction",
     ["geometry_x_axis"],
     "Right vs left remote on the same TV. Natural language.",
     "421254 remote right vs left (natural language)",
     "Phase 3 clean-lang variant of mining minpair_013 (was pilot+main mixed)."),

    ("minpair_v1_000028", "000128", "000129", "spatial_qualifier",
     ["geometry_z_axis"],
     "Cluster A vertical rank by one step: highest vs second-highest. Natural language 'highest' / 'second-highest' replaces coordinate annotation.",
     "421380 cluster A topmost vs 2nd-top (clean lang)",
     "Phase 3 clean-lang variant of mining minpair_001."),

    ("minpair_v1_000029", "000130", "000131", "spatial_qualifier",
     ["geometry_z_axis"],
     "Cluster A middle vs second-from-bottom. Pair tests model's understanding of 'middle' as a position descriptor.",
     "421380 cluster A middle vs 2nd-bottom (clean lang)",
     "Phase 3 new mid-cluster step pair, no coordinates."),

    ("minpair_v1_000030", "000132", "000133", "geometry_direction",
     ["geometry_z_axis"],
     "Strict top vs bottom endpoints of cluster A. q133 uses relative reference ('opposite end from the lowest') to test natural language composition.",
     "421380 cluster A lowest vs topmost-via-relative-reference",
     "Phase 3 clean-lang variant of mining minpair_011."),

    ("minpair_v1_000031", "000134", "000135", "geometry_direction",
     ["geometry_z_axis"],
     "Strict top vs bottom of cluster B. Natural language.",
     "421380 cluster B topmost vs bottommost",
     "Phase 3 new cluster B geom_dir pair (not in original mining)."),

    ("minpair_v1_000032", "000136", "000137", "spatial_qualifier",
     ["geometry_z_axis"],
     "Cluster B 2nd-from-top vs 2nd-from-bottom. Tests fine vertical disambiguation in natural language.",
     "421380 cluster B 2nd-top vs 2nd-bottom",
     "Phase 3 new cluster B mid-step pair."),

    ("minpair_v1_000033", "000138", "000139", "spatial_qualifier",
     ["geometry_x_axis"],
     "Same vertical rank ('upper-middle') in different columns of TV stand. Tests horizontal column reference at same height.",
     "421380 cluster A vs B at upper-middle rank (cross-column)",
     "Phase 3 cross-column same-rank pair. Tags multi_anchor since column references the TV stand twice."),

    ("minpair_v1_000034", "000140", "000141", "anchor_object",
     ["anchor_identity"],
     "Same 'top-left' relative position on two different dressers in the same scene. Only the dresser anchor disambiguates.",
     "421254 anchor 97164eaa (right dresser) vs f1f234c5 (left dresser)",
     "Phase 3 clean-lang variant of mining minpair_017."),

    ("minpair_v1_000035", "000142", "000143", "anchor_object",
     ["anchor_identity"],
     "Two nightstands in the bedroom; same knob/relation; only anchor differs.",
     "420683 right nightstand vs other-side nightstand",
     "Phase 3 clean-lang variant of mining minpair_015."),

    ("minpair_v1_000036", "000144", "000145", "anchor_object",
     ["anchor_identity"],
     "Two nightstands in 421013; same handle/relation; different anchors.",
     "421013 nightstand 600ca2b3 (headboard side) vs e810c10f (opposite side)",
     "Phase 3 clean-lang replacement for mining minpair_016 (was pilot+main mixed)."),

    ("minpair_v1_000037", "000146", "000147", "anchor_object",
     ["anchor_identity"],
     "Two dressers in 421602; same handle/relation; different anchors. Targets are at opposite vertical extremes within their own anchors.",
     "421602 dresser f4e41b55 vs 340b66f3 (cross-dresser anchor_object)",
     "Phase 3 clean-lang replacement for mining minpair_018 (was all-pilot)."),

    ("minpair_v1_000038", "000148", "000149", "spatial_qualifier",
     ["geometry_z_axis"],
     "Wardrobe vertical step on same anchor.",
     "421013 wardrobe bottommost vs 2nd-from-bottom (clean lang)",
     "Phase 3 clean-lang variant of mining minpair_004 (was pilot+main mixed)."),

    ("minpair_v1_000039", "000150", "000151", "functional_relation",
     ["functional_edge"],
     "Same target_label 'knob' on same anchor 'TV stand', but the supporting relation differs. Amplifier of mining minpair_020 (the only functional_relation anchor in the 6-scene pool).",
     "TV stand: pull-to-open (side compartment) vs pull-to-open-a-drawer (drawer cluster)",
     "Phase 3 second functional_relation pair (alongside mining minpair_020) -- still bounded by 6-scene CAP."),

    ("minpair_v1_000040", "000152", "000153", "spatial_qualifier",
     ["geometry_z_axis"],
     "Cluster A upper half vs lower half via indirect storage scenario. Tests whether model can map intent ('store small remote' vs 'store heavy book') onto position.",
     "421380 cluster A upper-half vs lower-half (indirect hard_negative)",
     "Phase 3 hard_negative + spatial pair combining intent reasoning with vertical position."),
]


# ============================================================================
# Helper functions
# ============================================================================

def load_jsonl(path: Path) -> list[dict]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            out.append(json.loads(line))
    return out


def write_jsonl(path: Path, records: list[dict]) -> None:
    lines = [json.dumps(r, ensure_ascii=False) for r in records]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def load_geom() -> dict:
    return json.loads(GEOM_PATH.read_text(encoding="utf-8"))


def bbox_center(geom: dict, scene_id: str, node_id: str):
    return geom.get(scene_id, {}).get(node_id, {}).get("bbox_center")


def fmt_xyz(c):
    if c is None:
        return ""
    return f"{c[0]:.3f},{c[1]:.3f},{c[2]:.3f}"


def euclid(a, b):
    if a is None or b is None:
        return None
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


def build_new_query_dict(spec: tuple) -> dict:
    """Convert NEW_QUERIES tuple into the full JSONL query dict."""
    (short_id, scene_id, target_id, anchor_id, relation, target_label,
     anchor_label, query_text, tags_extra, n_distractors, label_only,
     geom_cues, fail_modes, notes) = spec

    query_id = f"human_func_v1_{short_id}"
    edge_id = f"{target_id}|{relation}|{anchor_id}"
    src_arrow = f"{target_label} --{relation}--> {anchor_label}"
    # difficulty_tags: always include functional_relation (universally true for
    # these queries) + minimal_pair + extras specified; order: extras first,
    # then minimal_pair as last (matches retag patch convention).
    base_tags = list(tags_extra)
    if "functional_relation" not in base_tags:
        base_tags.append("functional_relation")
    if "minimal_pair" not in base_tags:
        base_tags.append("minimal_pair")

    return {
        "query_id": query_id,
        "scene_id": scene_id,
        "query_text": query_text,
        "query_type": "functional",
        "target_node_id": target_id,
        "anchor_node_id": anchor_id,
        "supporting_edge_ids": [edge_id],
        "difficulty_tags": base_tags,
        "is_long_range": False,
        "evidence_chain": [src_arrow],
        "source": "human_phase3",
        "target_label": target_label,
        "anchor_label": anchor_label,
        "num_same_label_distractors": n_distractors,
        "is_label_only_solvable": label_only,
        "geometry_cues": geom_cues,
        "expected_failure_modes": fail_modes,
        "notes": notes,
        # minimal_pair fields filled in by attach_pair_fields below.
    }


def attach_pair_fields(query: dict, pair_id: str, role: str, partner_qid: str) -> None:
    """Add the 3 self-describing fields to a query dict in place."""
    query["minimal_pair_id"] = pair_id
    query["minimal_pair_role"] = role
    query["minimal_pair_partner_id"] = partner_qid


def strip_pair_fields(query: dict) -> None:
    """Remove the 3 self-describing fields AND the `minimal_pair` tag."""
    for field in ("minimal_pair_id", "minimal_pair_role", "minimal_pair_partner_id"):
        query.pop(field, None)
    tags = query.get("difficulty_tags", [])
    query["difficulty_tags"] = [t for t in tags if t != "minimal_pair"]


def ensure_minimal_pair_tag(query: dict) -> None:
    """Add `minimal_pair` to difficulty_tags if absent (idempotent)."""
    tags = query.get("difficulty_tags", [])
    if "minimal_pair" not in tags:
        tags.append("minimal_pair")
        query["difficulty_tags"] = tags


def short_id(qid: str) -> str:
    return qid.split("_")[-1]


# ============================================================================
# Main compose flow
# ============================================================================

def main() -> int:
    geom = load_geom()
    pilot = load_jsonl(PILOT_PATH)
    main_raw = load_jsonl(MAIN_PATH)
    # Idempotency: strip any previously-appended Phase 3 new queries (000114+)
    # so re-runs reproduce the same output deterministically.
    new_short_ids = {spec[0] for spec in NEW_QUERIES}
    main = [q for q in main_raw if q["query_id"].split("_")[-1] not in new_short_ids]
    if len(main_raw) != len(main):
        print(f"[idempotency] filtered out {len(main_raw) - len(main)} previously-appended Phase 3 queries from main file")
    existing_pairs = {p["pair_id"]: p for p in load_jsonl(EXISTING_PAIRS_PATH)}

    # ---- Step 1: Validate KEPT_MINING_PAIRS exist ----
    missing_pairs = [pid for pid in KEPT_MINING_PAIR_IDS if pid not in existing_pairs]
    if missing_pairs:
        raise RuntimeError(f"Missing kept mining pair IDs: {missing_pairs}")
    print(f"[step1] Kept {len(KEPT_MINING_PAIR_IDS)} mining pairs from existing file")

    # ---- Step 2: Compute the set of mining query IDs to retag ----
    mining_query_ids: set[str] = set()
    mining_pair_for_query: dict[str, tuple[str, str, str]] = {}
    # tuple = (pair_id, role, partner_id)
    for pid in KEPT_MINING_PAIR_IDS:
        p = existing_pairs[pid]
        a_id, b_id = p["query_a_id"], p["query_b_id"]
        mining_query_ids.add(a_id)
        mining_query_ids.add(b_id)
        mining_pair_for_query[a_id] = (pid, "a", b_id)
        mining_pair_for_query[b_id] = (pid, "b", a_id)
    print(f"[step2] Mining-retain queries: {len(mining_query_ids)} unique IDs")

    # ---- Step 3: Build new queries ----
    new_queries: list[dict] = [build_new_query_dict(spec) for spec in NEW_QUERIES]
    new_query_ids = {q["query_id"] for q in new_queries}
    if len(new_query_ids) != len(new_queries):
        raise RuntimeError("Duplicate query_id in NEW_QUERIES")
    print(f"[step3] Constructed {len(new_queries)} new query dicts")

    # ---- Step 4: Attach pair fields to new queries ----
    new_pair_for_query: dict[str, tuple[str, str, str]] = {}
    for spec in NEW_PAIRS:
        pid, a_short, b_short, *_ = spec
        a_qid = f"human_func_v1_{a_short}"
        b_qid = f"human_func_v1_{b_short}"
        if a_qid not in new_query_ids or b_qid not in new_query_ids:
            raise RuntimeError(f"NEW_PAIR {pid} references unknown query short_id: {a_short}/{b_short}")
        new_pair_for_query[a_qid] = (pid, "a", b_qid)
        new_pair_for_query[b_qid] = (pid, "b", a_qid)
    # Apply
    for q in new_queries:
        pid, role, partner = new_pair_for_query[q["query_id"]]
        attach_pair_fields(q, pid, role, partner)
    print(f"[step4] Attached pair fields to {len(new_queries)} new queries via {len(NEW_PAIRS)} new pairs")

    # ---- Step 5: Rewrite pilot file (strip minimal_pair from all 7 currently tagged) ----
    pilot_stripped = 0
    for q in pilot:
        if "minimal_pair" in q.get("difficulty_tags", []):
            strip_pair_fields(q)
            pilot_stripped += 1
    write_jsonl(PILOT_PATH, pilot)
    print(f"[step5] Pilot file: stripped minimal_pair tag from {pilot_stripped} queries (no pilot pairs in revised plan)")

    # ---- Step 6: Rewrite main file ----
    # For each existing query:
    #   - if in mining_query_ids: ensure minimal_pair tag + attach fields
    #   - else: strip minimal_pair tag and fields (rollback retag)
    main_kept_retag = 0
    main_stripped = 0
    for q in main:
        qid = q["query_id"]
        # Always start clean by stripping then conditionally re-add.
        had_tag = "minimal_pair" in q.get("difficulty_tags", [])
        strip_pair_fields(q)  # removes 3 fields + tag
        if qid in mining_query_ids:
            ensure_minimal_pair_tag(q)
            pid, role, partner = mining_pair_for_query[qid]
            attach_pair_fields(q, pid, role, partner)
            main_kept_retag += 1
        elif had_tag:
            main_stripped += 1
    # Append new queries
    main_after = main + new_queries
    write_jsonl(MAIN_PATH, main_after)
    print(f"[step6] Main file: {main_kept_retag} queries kept retag, {main_stripped} stripped; appended {len(new_queries)} new -> {len(main_after)} total")

    # ---- Step 7: Generate minimal_pairs_v1.jsonl as derived view ----
    pair_rows: list[dict] = []
    # 10 kept mining pairs first (preserving original row content)
    for pid in KEPT_MINING_PAIR_IDS:
        pair_rows.append(existing_pairs[pid])
    # Then 20 new pairs (build rows from spec + geometry)
    for spec in NEW_PAIRS:
        (pid, a_short, b_short, changed_factor, evidence, why_hard, diff_summary, notes) = spec
        a_qid = f"human_func_v1_{a_short}"
        b_qid = f"human_func_v1_{b_short}"
        qa = next(q for q in new_queries if q["query_id"] == a_qid)
        qb = next(q for q in new_queries if q["query_id"] == b_qid)
        ca = bbox_center(geom, qa["scene_id"], qa["target_node_id"])
        cb = bbox_center(geom, qb["scene_id"], qb["target_node_id"])
        d = euclid(ca, cb)
        rel_a = qa["supporting_edge_ids"][0].split("|", 2)[1]
        rel_b = qb["supporting_edge_ids"][0].split("|", 2)[1]
        shared = rel_a if rel_a == rel_b else None
        row = {
            "pair_id": pid,
            "scene_id": qa["scene_id"],
            "query_a_id": a_qid,
            "query_b_id": b_qid,
            "changed_factor": changed_factor,
            "why_hard": why_hard,
            "target_a_node_id": qa["target_node_id"],
            "target_b_node_id": qb["target_node_id"],
            "target_label": qa["target_label"],
            "anchor_a_node_id": qa["anchor_node_id"],
            "anchor_b_node_id": qb["anchor_node_id"],
            "shared_relation": shared,
            "relation_a": rel_a,
            "relation_b": rel_b,
            "target_a_xyz": fmt_xyz(ca),
            "target_b_xyz": fmt_xyz(cb),
            "target_geom_diff_m": round(d, 3) if d is not None else None,
            "pair_evidence_used": list(evidence),
            "diff_summary": diff_summary,
            "notes": notes,
        }
        pair_rows.append(row)
    write_jsonl(PAIRS_PATH, pair_rows)
    print(f"[step7] minimal_pairs_v1.jsonl: {len(pair_rows)} pair rows ({len(KEPT_MINING_PAIR_IDS)} kept + {len(NEW_PAIRS)} new)")

    # ---- Step 8: Recompute hard_slice_summary ----
    hs = json.loads(HS_PATH.read_text(encoding="utf-8"))
    counts = Counter()
    for q in main_after:
        for t in q.get("difficulty_tags", []):
            counts[t] += 1
    total = len(main_after)
    hs["total_queries"] = total
    hs["difficulty_tag_counts"] = dict(sorted(counts.items(), key=lambda x: -x[1]))
    hs["difficulty_tag_ratios_pct"] = {t: round(c / total * 100, 1) for t, c in counts.items()}

    # Recompute scene_distribution from main file
    scene_counts = Counter(q["scene_id"] for q in main_after)
    hs["scene_distribution"] = dict(sorted(scene_counts.items()))

    # Recompute label_only_solvable
    n_label_only = sum(1 for q in main_after if q.get("is_label_only_solvable"))
    hs["is_label_only_solvable_count"] = n_label_only
    hs["is_label_only_solvable_ratio_pct"] = round(n_label_only / total * 100, 1)

    # Recompute distractor histogram
    hist = Counter()
    for q in main_after:
        n = q.get("num_same_label_distractors", 0)
        if n == 0:
            bucket = "0"
        elif n == 1:
            bucket = "1"
        elif n <= 4:
            bucket = "2-4"
        elif n <= 9:
            bucket = "5-9"
        elif n <= 19:
            bucket = "10-19"
        else:
            bucket = "20+"
        hist[bucket] += 1
    hs["num_same_label_distractors_histogram"] = dict(hist)

    # multi_anchor x geometry_aware co-occurrence
    ma_ga = sum(
        1 for q in main_after
        if "multi_anchor" in q.get("difficulty_tags", [])
        and "geometry_aware" in q.get("difficulty_tags", [])
    )
    ga_only = sum(
        1 for q in main_after
        if "geometry_aware" in q.get("difficulty_tags", [])
        and "multi_anchor" not in q.get("difficulty_tags", [])
    )
    hs["multi_anchor_x_geometry_aware_co_occurrence"] = {
        "multi_anchor_AND_geometry_aware": ma_ga,
        "geometry_aware_only": ga_only,
    }

    # Recompute minimal_pairs section
    cf_counts = Counter(r["changed_factor"] for r in pair_rows)
    by_scene = Counter(r["scene_id"] for r in pair_rows)
    ev_counts = Counter()
    for r in pair_rows:
        for ev in r.get("pair_evidence_used", []) or []:
            ev_counts[ev] += 1

    n_pairs_main_only = 0
    n_pairs_pilot_only = 0
    n_pairs_mixed = 0
    n_pairs_with_phase3 = 0
    unique_q = set()
    new_q_used = 0
    for r in pair_rows:
        a, b = r["query_a_id"], r["query_b_id"]
        unique_q.add(a)
        unique_q.add(b)
        a_phase3 = a in new_query_ids
        b_phase3 = b in new_query_ids
        a_pilot = short_id(a) < "000021" and not a_phase3
        b_pilot = short_id(b) < "000021" and not b_phase3
        if a_phase3 or b_phase3:
            n_pairs_with_phase3 += 1
        if not a_pilot and not b_pilot:
            n_pairs_main_only += 1
        elif a_pilot and b_pilot:
            n_pairs_pilot_only += 1
        else:
            n_pairs_mixed += 1
        for q in (a, b):
            if q in new_query_ids:
                new_q_used += 1

    hs["minimal_pairs"] = {
        "total_pairs": len(pair_rows),
        "by_changed_factor": dict(sorted(cf_counts.items())),
        "by_scene": dict(sorted(by_scene.items())),
        "pair_evidence_used": dict(sorted(ev_counts.items())),
        "phase3_revision_anchors": {
            "target_pairs": 30,
            "achieved": len(pair_rows),
            "mining_kept": len(KEPT_MINING_PAIR_IDS),
            "new_pairs": len(NEW_PAIRS),
            "changed_factor_floor_each_class": 1,
            "all_4_classes_covered": all(c >= 1 for c in cf_counts.values()) and len(cf_counts) == 4,
        },
        "query_source_breakdown": {
            "n_pairs_using_main_only": n_pairs_main_only,
            "n_pairs_using_pilot_only": n_pairs_pilot_only,
            "n_pairs_mixed": n_pairs_mixed,
            "n_pairs_using_phase3_new_query": n_pairs_with_phase3,
            "n_unique_queries_referenced": len(unique_q),
            "n_phase3_new_queries": len(new_queries),
        },
        "note": (
            "Phase 3 revision (2026-05-19): 30 pairs = 10 mining (kept original "
            "pair_ids 001/003/005/007/009/012/014/015/017/020) + 20 newly written "
            "(pair_ids 021-040, queries 000114-000153). Self-describing schema: each "
            "participating query carries minimal_pair_id/role/partner_id fields. "
            "Pilot file pairs were dropped per same-file rule. "
            "FUNC_REL_CEILING_1 mitigated to 2 pairs (mining 020 + new 039) -- still "
            "structural limit of 1 unique anchor (421380 TV stand) in 6 scenes."
        ),
    }

    HS_PATH.write_text(json.dumps(hs, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"[step8] hard_slice_summary_v1.json: total_queries={total}, minimal_pair tag count={counts.get('minimal_pair', 0)}")

    # ---- Final summary ----
    print()
    print("===== Phase 3 revision compose complete =====")
    print(f"  pilot:                {len(pilot)} queries ({pilot_stripped} stripped of minimal_pair)")
    print(f"  main:                 {len(main_after)} queries ({main_kept_retag} mining-retagged + {len(new_queries)} new)")
    print(f"  minimal_pairs:        {len(pair_rows)} pairs ({len(KEPT_MINING_PAIR_IDS)} kept + {len(NEW_PAIRS)} new)")
    print(f"  changed_factor:       {dict(cf_counts)}")
    print(f"  scene:                {dict(by_scene)}")
    print(f"  pair_evidence:        {dict(ev_counts)}")
    print(f"  source breakdown:     main_only={n_pairs_main_only}, mixed={n_pairs_mixed}, pilot_only={n_pairs_pilot_only}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
