"""Build robot_execution_sidecar_v1.jsonl from SceneFun3D relations + geometry.

For each interactive (source) node in SceneFun3D.relations.json, produces a row with:
  - 3D bbox center, extent, interaction_point (= bbox center)
  - affordance_type and robot_action (rule-based, no CLIP)
  - approach_axis (heuristic by label)
  - execution_feasible (geometry available)
  - safety_notes
"""
import json, os, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[3]  # fungraph_benchmark_v0/

RELATIONS_PATH = ROOT / "benchmark_clean_v0/annotations/openfungraph/SceneFun3D.relations.json"
GEOM_PATH = ROOT / "benchmark_clean_v0/geometry/scenefun3d_node_geom.json"
ENRICHED_PATH = ROOT / "benchmark_clean_v0/queries/scenefun3d_funrag_benchmark_enriched.json"
OUT_PATH = ROOT / "benchmark_clean_v0/robot_trials/robot_execution_sidecar_v1.jsonl"

# ---------------------------------------------------------------------------
# Action mapping (relation_type → affordance_type, robot_action)
# ---------------------------------------------------------------------------
ACTION_MAP = {
    "pull to open or close":                    ("pull",   "pull_handle"),
    "pull to open or close a drawer":           ("pull",   "pull_handle"),
    "pull or rotate to open or close":          ("pull",   "pull_handle"),
    "rotate to open or close":                  ("rotate", "rotate_knob"),
    "rotate to adjust the setting":             ("rotate", "rotate_knob"),
    "rotate to adjust the temperature":         ("rotate", "rotate_knob"),
    "rotate to adjust setting or temperature":  ("rotate", "rotate_knob"),
    "rotate to adjust the setting or open or close": ("rotate", "rotate_knob"),
    "rotate to control the water flow":         ("rotate", "rotate_knob"),
    "rotate to flush":                          ("rotate", "rotate_knob"),
    "rotate or press to adjust the setting":    ("rotate", "rotate_knob"),
    "control the water flow":                   ("press",  "press_button"),
    "press or rotate to control the water flow": ("press", "press_button"),
    "press or rotate to  control the water flow": ("press", "press_button"),  # typo in data
    "press or rotate to open":                  ("press",  "press_button"),
    "press or rotate to flush":                 ("press",  "press_button"),
    "press to open or close, or adjust the setting": ("press", "press_button"),
    "control":                                  ("press",  "press_button"),
    "control, turn on or turn off":             ("press",  "press_button"),
    "push to flush":                            ("press",  "press_button"),
    "provide power":                            ("none",   "none"),
}

# Approach axis heuristic by target node label keywords
def approach_axis(label: str) -> str:
    label_l = label.lower()
    if any(k in label_l for k in ("drawer", "handle", "door")):
        return "front"
    if any(k in label_l for k in ("knob", "button", "switch", "remote", "outlet", "power strip")):
        return "front"
    if any(k in label_l for k in ("ceiling", "light")):
        return "top"
    return "unknown"

# Safety notes heuristic
def safety_notes(label: str, robot_action: str) -> str:
    label_l = label.lower()
    if robot_action == "none":
        return "Diagnostic-only node; no physical robot action."
    if "outlet" in label_l or "power" in label_l:
        return "Electrical component — ensure insulated gripper."
    if "flush" in robot_action or "water" in label_l or "faucet" in label_l:
        return "Water-contact risk — protect robot wrist."
    if robot_action == "pull_handle":
        return "Ensure door/drawer clearance before pulling."
    return ""


def main():
    with open(RELATIONS_PATH, encoding="utf-8") as f:
        relations = json.load(f)

    with open(GEOM_PATH, encoding="utf-8") as f:
        geom = json.load(f)

    # Build node_id -> label from enriched benchmark
    with open(ENRICHED_PATH, encoding="utf-8") as f:
        enriched = json.load(f)
    node_labels: dict[str, str] = {}
    for item in enriched["data"]:
        for node in item.get("scene_graph", {}).get("nodes", []):
            nid = node.get("node_id") or node.get("id", "")
            lbl = node.get("label") or node.get("node_label", "")
            if nid and lbl:
                node_labels[nid] = lbl

    seen: set[tuple] = set()  # (scene_id, node_id, relation_type) deduplicate
    rows = []

    for rel in relations:
        scene_id = rel["scene_id"]
        relation_type = rel["description"]
        source_node_id = rel["first_node_annot_id"]  # the interactive node that acts
        target_anchor_id = rel["second_node_annot_id"]  # the appliance / fixture

        key = (scene_id, source_node_id, relation_type)
        if key in seen:
            continue
        seen.add(key)

        node_label = node_labels.get(source_node_id, "unknown")
        affordance_type, robot_action = ACTION_MAP.get(relation_type, ("none", "none"))

        # Geometry
        scene_geom = geom.get(scene_id, {})
        node_geom = scene_geom.get(source_node_id)
        if node_geom:
            c = node_geom["bbox_center"]
            mn = node_geom["bbox_min"]
            mx = node_geom["bbox_max"]
            bbox_center_3d = [round(c[0], 4), round(c[1], 4), round(c[2], 4)]
            bbox_extent_3d = [
                round(mx[0] - mn[0], 4),
                round(mx[1] - mn[1], 4),
                round(mx[2] - mn[2], 4),
            ]
            interaction_point = bbox_center_3d
            execution_feasible = True
        else:
            bbox_center_3d = None
            bbox_extent_3d = None
            interaction_point = None
            execution_feasible = False

        row = {
            "scene_id": scene_id,
            "node_id": source_node_id,
            "node_label": node_label,
            "relation_type": relation_type,
            "anchor_node_id": target_anchor_id,
            "bbox_center_3d": bbox_center_3d,
            "bbox_extent_3d": bbox_extent_3d,
            "interaction_point": interaction_point,
            "approach_axis": approach_axis(node_label),
            "affordance_type": affordance_type,
            "robot_action": robot_action,
            "execution_feasible": execution_feasible,
            "safety_notes": safety_notes(node_label, robot_action),
        }
        rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    feasible = sum(1 for r in rows if r["execution_feasible"])
    actionable = sum(1 for r in rows if r["robot_action"] != "none")
    print(f"Wrote {len(rows)} rows to {OUT_PATH}")
    print(f"  execution_feasible: {feasible}/{len(rows)}")
    print(f"  actionable (robot_action != none): {actionable}/{len(rows)}")
    action_dist = {}
    for r in rows:
        action_dist[r["robot_action"]] = action_dist.get(r["robot_action"], 0) + 1
    print("  robot_action distribution:", dict(sorted(action_dist.items())))


if __name__ == "__main__":
    main()
