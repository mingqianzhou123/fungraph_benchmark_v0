"""Replace q038-q040 (C13 duplicates) with 3 new oven-handle strict queries.

q038/q039/q040 shared supporting_edge_ids with q021/q022/q023 (C13 violation).
Replacement: oven handle (47d6518d) with different reference knobs (2nd-left,
middle, 2nd-right), giving distinct supporting_edge_ids per oven pair 2/3/4.
"""
import json

path = "benchmark_clean_v0/human_annotations/functional_queries_v1/long_range_stress_queries_v1.jsonl"

with open(path, encoding="utf-8") as f:
    queries = [json.loads(l) for l in f if l.strip()]

replacements = {
    "lr_v1_000038": {
        "query_id": "lr_v1_000038",
        "scene_id": "469011",
        "query_text": "Pull the handle that opens the door of the kitchen appliance whose settings are also adjusted by the second-from-left rotating knob on its panel.",
        "query_type": "functional",
        "target_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "supporting_edge_ids": [
            "47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552",
            "06b684bb-7a5c-4717-847a-d343bd6824d9|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552"
        ],
        "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "is_long_range": True,
        "evidence_chain": ["handle --pull to open or close--> oven", "knob --rotate to adjust the setting--> oven"],
        "source": "human_phase4",
        "target_label": "handle",
        "anchor_label": "oven",
        "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "shared_anchor_label": "oven",
        "reference_node_id": "06b684bb-7a5c-4717-847a-d343bd6824d9",
        "reference_label": "knob",
        "reference_relation": "rotate to adjust the setting",
        "long_range_pattern": "junction_2hop",
        "evidence_hop_count": 2,
        "reference_necessity": "strict",
        "geometry_cues": [],
        "num_same_label_distractors": 1,
        "is_label_only_solvable": False,
        "notes": "Strict: 2 handles in scene (47d6518d oven, 2abcdace fridge). Fridge has no knob; oven has 5. Reference second-from-left knob (06b684bb, x=2.528) -> oven -> handle 47d6518d. Distinct supporting_edges from q031 (uses d003c3b8) and q032 (uses 85f5f2f0)."
    },
    "lr_v1_000039": {
        "query_id": "lr_v1_000039",
        "scene_id": "469011",
        "query_text": "Pull the handle that opens the door of the kitchen appliance whose settings are also adjusted by the middle rotating knob on its panel.",
        "query_type": "functional",
        "target_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "supporting_edge_ids": [
            "47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552",
            "28e9ec26-d38b-45a2-9614-9fe6a8d69211|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552"
        ],
        "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "is_long_range": True,
        "evidence_chain": ["handle --pull to open or close--> oven", "knob --rotate to adjust the setting--> oven"],
        "source": "human_phase4",
        "target_label": "handle",
        "anchor_label": "oven",
        "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "shared_anchor_label": "oven",
        "reference_node_id": "28e9ec26-d38b-45a2-9614-9fe6a8d69211",
        "reference_label": "knob",
        "reference_relation": "rotate to adjust the setting",
        "long_range_pattern": "junction_2hop",
        "evidence_hop_count": 2,
        "reference_necessity": "strict",
        "geometry_cues": [],
        "num_same_label_distractors": 1,
        "is_label_only_solvable": False,
        "notes": "Strict: 2 handles (47d6518d oven, 2abcdace fridge). Reference middle knob (28e9ec26, x=2.581) -> oven -> handle 47d6518d. Fridge has no knob. Distinct supporting_edges from q031, q032, q038."
    },
    "lr_v1_000040": {
        "query_id": "lr_v1_000040",
        "scene_id": "469011",
        "query_text": "Pull the handle that opens the door of the kitchen appliance whose settings are also adjusted by the second-from-right rotating knob on its panel.",
        "query_type": "functional",
        "target_node_id": "47d6518d-dce3-4c45-8cfc-34c56bbb3454",
        "anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "supporting_edge_ids": [
            "47d6518d-dce3-4c45-8cfc-34c56bbb3454|pull to open or close|8e66432e-ee5a-4009-9ad5-f53d29772552",
            "76002344-9de9-476f-a43e-d822d1cdb592|rotate to adjust the setting|8e66432e-ee5a-4009-9ad5-f53d29772552"
        ],
        "difficulty_tags": ["long_range", "functional_relation", "same_label_disambiguation", "geometry_aware"],
        "is_long_range": True,
        "evidence_chain": ["handle --pull to open or close--> oven", "knob --rotate to adjust the setting--> oven"],
        "source": "human_phase4",
        "target_label": "handle",
        "anchor_label": "oven",
        "shared_anchor_node_id": "8e66432e-ee5a-4009-9ad5-f53d29772552",
        "shared_anchor_label": "oven",
        "reference_node_id": "76002344-9de9-476f-a43e-d822d1cdb592",
        "reference_label": "knob",
        "reference_relation": "rotate to adjust the setting",
        "long_range_pattern": "junction_2hop",
        "evidence_hop_count": 2,
        "reference_necessity": "strict",
        "geometry_cues": [],
        "num_same_label_distractors": 1,
        "is_label_only_solvable": False,
        "notes": "Strict: 2 handles (47d6518d oven, 2abcdace fridge). Reference second-from-right knob (76002344, x=2.700) -> oven -> handle 47d6518d. Fridge has no knob. Distinct supporting_edges from q031, q032, q038, q039."
    }
}

updated = []
for q in queries:
    qid = q["query_id"]
    if qid in replacements:
        updated.append(replacements[qid])
        print(f"Replaced {qid}")
    else:
        updated.append(q)

with open(path, "w", encoding="utf-8") as f:
    for q in updated:
        f.write(json.dumps(q, ensure_ascii=False) + "\n")

print(f"Done. Total: {len(updated)}")
strict = sum(1 for q in updated if q.get("reference_necessity") == "strict")
print(f"Strict: {strict}/{len(updated)} = {strict/len(updated)*100:.1f}%")
