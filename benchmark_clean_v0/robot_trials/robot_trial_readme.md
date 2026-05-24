# Robot Trials Sidecar — README

## Purpose

This directory provides a **lightweight execution sidecar** that connects benchmark grounding results to robot action primitives. Given that the functional query benchmark identifies *which* object a robot should interact with, this sidecar supplies the **where** (3D interaction point) and **how** (action primitive) for a physical robot.

This is not a full multimodal pipeline. It does not use CLIP, image features, segmentation masks, or depth images.

---

## What This Is NOT

- Not a replacement for a perception/grounding pipeline — the robot still needs to localize the object in real sensor data.
- Not CLIP-based or image-based — interaction points are 3D bbox centers from SceneFun3D geometry.
- Not a complete manipulation planner — approach axis and grasp orientation are heuristic approximations.
- Color and material attributes are **unavailable** in the source scene graphs; no color-based action selection is performed.

---

## How to Use

1. **Grounding**: Run your query grounding system on a query from `functional_queries_v1.jsonl`. It returns a `target_node_id`.
2. **Lookup action**: Find `(scene_id, node_id)` in `robot_execution_sidecar_v1.jsonl` → get `interaction_point` (3D), `robot_action`, `approach_axis`.
3. **Execute**: Send the action primitive + 3D target to your robot controller.
4. **Evaluate**: Compare executed target vs. ground-truth `target_node_id` in `robot_trial_manifest_v1.jsonl`.

---

## File Descriptions

### `robot_execution_sidecar_v1.jsonl`

One row per interactive node per relation type (192 rows total). Fields:

| Field | Type | Description |
|---|---|---|
| `scene_id` | str | SceneFun3D scene identifier |
| `node_id` | str | UUID of the interactive node (the robot acts on this) |
| `node_label` | str | Object label from scene graph |
| `relation_type` | str | Functional relation (e.g. "pull to open or close") |
| `anchor_node_id` | str | UUID of the appliance/fixture this node acts on |
| `bbox_center_3d` | [x,y,z] | 3D center of the node's bounding box (in scene coordinates) |
| `bbox_extent_3d` | [dx,dy,dz] | Bounding box dimensions |
| `interaction_point` | [x,y,z] | Approximated 3D interaction point (= bbox_center_3d) |
| `approach_axis` | str | Heuristic: "front", "top", or "unknown" |
| `affordance_type` | str | "pull", "press", "rotate", or "none" |
| `robot_action` | str | "pull_handle", "press_button", "rotate_knob", or "none" |
| `execution_feasible` | bool | True if geometry data is available |
| `safety_notes` | str | Short safety annotation |

**Coverage**: 192/192 rows have `execution_feasible=true`; 179/192 have `robot_action != "none"`.

### `robot_trial_manifest_v1.jsonl`

**25 queries** hand-selected from `functional_queries_v1.jsonl` as the best candidates for physical robot or qualitative demo use. Selection criteria (all must pass):

- Target node has geometry (bbox available)
- Target node in sidecar with `execution_feasible=true`
- `robot_action` is one of: `pull_handle`, `press_button`, `rotate_knob`
- `num_same_label_distractors ≥ 1` (there is a same-label ambiguity the robot must resolve)
- No color words in query text (color not supported)

From the 121 queries passing all filters, the top 25 are selected by:
1. Highest `num_same_label_distractors` first (hardest to guess = best demo of grounding value)
2. Diversity: max 5 per scene, all 3 action types guaranteed
3. Scene distribution: 420683×5, 421254×5, 421380×5, 421602×5, 469011×5

Fields per row:

| Field | Description |
|---|---|
| `trial_id` | Unique trial identifier (robot_trial_v1_XXXXXX) |
| `query_id` | Source query from functional_queries_v1 |
| `scene_id` | Scene |
| `query_text` | Natural language query |
| `target_node_id` | Ground-truth target node |
| `target_label` | Target object label |
| `route_expected` | Current routing label. In this manifest all rows use `funrag_prior`; future manifests may use `funrag_verifier` when verifier-selected trials are added |
| `robot_action` | Action primitive |
| `approach_axis` | Heuristic approach direction |
| `interaction_point` | 3D target point |
| `success_metric` | Suggested evaluation metric |
| `why_robot_cares` | Why correct target matters for robot task |
| `failure_consequence` | What happens if wrong target is selected |
| `num_same_label_distractors` | Number of same-label distractor nodes |
| `difficulty_tags` | From source query |

---

## Limitations

1. **Interaction point approximation**: `interaction_point = bbox_center_3d`. For handles and drawers, the true grasp point is offset toward the front face — this is an approximation.
2. **Approach axis is heuristic**: Based on label keywords only. "handle" → "front"; "ceiling light" → "top". Not computed from geometry.
3. **Grasp orientation not provided**: Full 6-DOF grasp planning requires additional work beyond this sidecar.
4. **z-axis is vertical** (per CLAUDE.md): `bbox_center[2]` is the up axis. Scene coordinates have per-scene registration offsets — do not compare z values across scenes.
5. **13 rows with `robot_action="none"`**: These correspond to `provide power` relations (electric outlets powering appliances). These are diagnostic-only — no robot action is appropriate.

---

## Scripts

- `scripts/build_robot_execution_sidecar.py` — generates `robot_execution_sidecar_v1.jsonl` from `SceneFun3D.relations.json` + geometry + enriched benchmark
- `scripts/build_robot_trial_manifest.py` — filters `functional_queries_v1.jsonl` to produce `robot_trial_manifest_v1.jsonl`

Run from repo root:

```powershell
python benchmark_clean_v0\robot_trials\scripts\build_robot_execution_sidecar.py
python benchmark_clean_v0\robot_trials\scripts\build_robot_trial_manifest.py
```
