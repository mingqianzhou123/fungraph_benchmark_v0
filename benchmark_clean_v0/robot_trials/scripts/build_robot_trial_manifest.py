"""Build robot_trial_manifest_v1.jsonl — selects 15–30 best demo-worthy queries
from functional_queries_v1.jsonl for physical robot or qualitative demo use.

Selection criteria (in order of priority):
  1. Target has geometry and execution_feasible=True
  2. robot_action is pull_handle / press_button / rotate_knob
  3. num_same_label_distractors >= 1 (ambiguity that requires grounding)
  4. No color words in query_text
  5. Ranked by num_same_label_distractors (harder = better demo)
  6. Diversity: max 5 per scene, all 3 action types represented, diverse target labels

TARGET: 25 trials (within 15–30 range).
"""
import json, pathlib, re, collections

ROOT = pathlib.Path(__file__).resolve().parents[3]

FQ_PATH      = ROOT / "benchmark_clean_v0/human_annotations/functional_queries_v1/functional_queries_v1.jsonl"
SIDECAR_PATH = ROOT / "benchmark_clean_v0/robot_trials/robot_execution_sidecar_v1.jsonl"
OUT_PATH     = ROOT / "benchmark_clean_v0/robot_trials/robot_trial_manifest_v1.jsonl"

TARGET_COUNT = 25  # within 15–30

COLOR_WORDS = re.compile(
    r"\b(red|blue|green|yellow|black|white|gray|grey|brown|pink|purple|orange|silver|gold|dark|light)\b",
    re.IGNORECASE,
)

SIMPLE_ACTIONS = {"pull_handle", "press_button", "rotate_knob"}


def route_expected(q: dict) -> str:
    # "prior" only if label alone is sufficient (is_label_only_solvable=True);
    # "funrag_prior" for all cases requiring FunRAG grounding to disambiguate
    return "prior" if q.get("is_label_only_solvable", False) else "funrag_prior"


def success_metric(robot_action: str) -> str:
    if robot_action == "pull_handle":
        return "target_acc|reach_bbox|action_success"
    if robot_action == "press_button":
        return "target_acc|point_at_bbox|action_success"
    if robot_action == "rotate_knob":
        return "target_acc|point_at_bbox|action_success"
    return "target_acc"


def why_robot_cares(target_label: str, robot_action: str, n_distractors: int) -> str:
    distractor_phrase = f"({n_distractors} same-label distractor{'s' if n_distractors != 1 else ''})"
    if robot_action == "pull_handle":
        return (f"Robot must grasp and pull the correct {target_label} {distractor_phrase} "
                f"to open/close; wrong target causes task failure or collision.")
    if robot_action == "press_button":
        return (f"Robot must press the correct {target_label} {distractor_phrase}; "
                f"pressing wrong control triggers unintended appliance state.")
    if robot_action == "rotate_knob":
        return (f"Robot must rotate the correct {target_label} {distractor_phrase}; "
                f"rotating wrong knob sets wrong appliance parameter.")
    return "Functional target identification required for task execution."


def failure_consequence(robot_action: str) -> str:
    if robot_action == "pull_handle":
        return "Opens/closes wrong appliance door; possible collision or task abort."
    if robot_action == "press_button":
        return "Activates wrong appliance or wrong function on same appliance."
    if robot_action == "rotate_knob":
        return "Sets wrong temperature/setting; potential safety hazard or appliance damage."
    return "Incorrect interaction target."


def main():
    with open(FQ_PATH, encoding="utf-8") as f:
        fq_queries = [json.loads(l) for l in f if l.strip()]

    with open(SIDECAR_PATH, encoding="utf-8") as f:
        sidecar_rows = [json.loads(l) for l in f if l.strip()]

    # (scene_id, node_id) → first sidecar row for that node
    sidecar_lookup: dict[tuple, dict] = {}
    for row in sidecar_rows:
        key = (row["scene_id"], row["node_id"])
        if key not in sidecar_lookup:
            sidecar_lookup[key] = row

    # --- Phase 1: filter ---
    candidates = []
    for q in fq_queries:
        target_id = q.get("target_node_id", "")
        scene_id  = q.get("scene_id", "")
        query_text = q.get("query_text", q.get("query", ""))

        sc = sidecar_lookup.get((scene_id, target_id))
        if sc is None or not sc["execution_feasible"]:
            continue
        if sc["robot_action"] not in SIMPLE_ACTIONS:
            continue
        if q.get("num_same_label_distractors", 0) < 1:
            continue
        if COLOR_WORDS.search(query_text):
            continue

        candidates.append((q, sc))

    # --- Phase 2: rank by num_same_label_distractors descending ---
    candidates.sort(key=lambda x: x[0].get("num_same_label_distractors", 0), reverse=True)

    # --- Phase 3: diverse selection (max 5/scene, all 3 action types covered) ---
    scene_counts: dict[str, int] = collections.defaultdict(int)
    action_counts: dict[str, int] = collections.defaultdict(int)
    MAX_PER_SCENE = 5

    # Ensure all three action types are represented first by reserving 1 slot each
    reserved: list = []
    covered_actions: set = set()
    for q, sc in candidates:
        if sc["robot_action"] not in covered_actions:
            reserved.append((q, sc))
            covered_actions.add(sc["robot_action"])
            scene_counts[q["scene_id"]] += 1
            action_counts[sc["robot_action"]] += 1
        if covered_actions == SIMPLE_ACTIONS:
            break

    # Fill remaining slots with highest-distractor candidates respecting scene cap
    remaining = [(q, sc) for q, sc in candidates if (q, sc) not in reserved]
    for q, sc in remaining:
        if len(reserved) >= TARGET_COUNT:
            break
        if scene_counts[q["scene_id"]] >= MAX_PER_SCENE:
            continue
        reserved.append((q, sc))
        scene_counts[q["scene_id"]] += 1
        action_counts[sc["robot_action"]] += 1

    # --- Phase 4: emit ---
    trial_rows = []
    for idx, (q, sc) in enumerate(reserved, start=1):
        n_dist = q.get("num_same_label_distractors", 0)
        row = {
            "trial_id": f"robot_trial_v1_{idx:06d}",
            "query_id": q["query_id"],
            "scene_id": q["scene_id"],
            "query_text": q.get("query_text", q.get("query", "")),
            "target_node_id": q.get("target_node_id", ""),
            "target_label": q.get("target_label", ""),
            "route_expected": route_expected(q),
            "robot_action": sc["robot_action"],
            "approach_axis": sc["approach_axis"],
            "interaction_point": sc["interaction_point"],
            "success_metric": success_metric(sc["robot_action"]),
            "why_robot_cares": why_robot_cares(q.get("target_label", ""), sc["robot_action"], n_dist),
            "failure_consequence": failure_consequence(sc["robot_action"]),
            "num_same_label_distractors": n_dist,
            "difficulty_tags": q.get("difficulty_tags", []),
        }
        trial_rows.append(row)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        for row in trial_rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Selected {len(trial_rows)} / {len(fq_queries)} queries for robot trials")
    print("  robot_action distribution:", dict(sorted(action_counts.items())))
    print("  scene distribution:", dict(sorted(scene_counts.items())))
    route_dist = collections.Counter(r["route_expected"] for r in trial_rows)
    print("  route_expected distribution:", dict(route_dist))
    print(f"Wrote {OUT_PATH}")


if __name__ == "__main__":
    main()
