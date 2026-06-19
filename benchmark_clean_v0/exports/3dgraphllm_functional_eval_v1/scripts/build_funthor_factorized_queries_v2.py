#!/usr/bin/env python3
"""Build factorized FunTHOR functional queries.

v1 was a simple template expansion over FunTHOR functional edges. v2 keeps the
same grounded edges, but varies controlled scientific factors:

    Functional Query Type x Spatial Scope x Anchor Visibility

Spatial scope is a property of the relation. Query type and anchor visibility
are varied per relation to test whether models depend on explicit anchor names.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
RELEASE_DIR = EXPORT_DIR / "fungraph_full_modality_release_v1"
FUNTHOR_DIR = RELEASE_DIR / "external" / "funthor_v1"
FUNTHOR_MANIFEST = FUNTHOR_DIR / "funthor_manifest.json"
OUTPUT = RELEASE_DIR / "splits" / "funthor_functional_queries_factorized_v2.jsonl"

QUERY_TYPES = {
    "functional_element_selection",
    "target_object_selection",
    "relation_verification",
    "state_change_goal_completion",
    "ambiguous_instance_minimal_pair",
    "functional_affordance_selection",
    "functional_consequence_prediction",
}
SPATIAL_SCOPES = {"local", "remote"}
ANCHOR_VISIBILITIES = {"anchor_explicit", "anchor_implicit", "anchor_hidden"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def snake(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def words(label: str) -> str:
    text = re.sub(r"(?<!^)(?=[A-Z])", " ", str(label or "")).strip()
    return text.lower()


def classify_spatial_scope(edge: dict[str, Any]) -> str:
    first = edge["first_label"]
    second = edge["second_label"]
    relation = edge["relation"]
    if first in {"LightSwitch", "RemoteControl"}:
        return "remote"
    if relation == "switch on or off" and second in {"LightFixture", "Television"}:
        return "remote"
    return "local"


def relation_category(edge: dict[str, Any]) -> str:
    relation_type = edge.get("relation_type") or ""
    first = edge["first_label"]
    if relation_type == "part_based" or first in {"Handle", "Button", "Lever", "StoveKnob", "LightSwitch", "Faucet", "Keypad", "FlushLever"}:
        return "part_object_operation"
    if relation_type == "proximity_based":
        return "proximity_dependent_relation"
    if relation_type == "manual_annotation":
        return "ambiguous_one_to_one_assignment"
    return "object_object_affordance"


def control_phrase(edge: dict[str, Any]) -> str:
    first = edge["first_label"]
    relation = edge["relation"]
    if first == "Handle":
        return "pull"
    if first in {"Button", "LightSwitch", "RemoteControl", "Keypad", "FlushLever"}:
        return "press"
    if first in {"StoveKnob", "Faucet"}:
        return "turn"
    if first == "Lever":
        return "push down"
    if relation in {"can slice or cut", "can shred and chop"}:
        return "use"
    return "interact with"


def goal_phrase(edge: dict[str, Any]) -> str:
    first = edge["first_label"]
    second = edge["second_label"]
    relation = edge["relation"]
    if relation in {"can slice or cut", "can shred and chop"}:
        return "prepare the food by cutting it"
    if first == "LightSwitch":
        return "light up this area"
    if first == "StoveKnob":
        return "start cooking"
    if first == "RemoteControl":
        return "start watching something"
    if first == "Keypad":
        return "heat food"
    if first == "Button" and second == "CoffeeMachine":
        return "make coffee"
    if first in {"Lever", "Button"} and second == "Toaster":
        return "make toast"
    if first == "FlushLever":
        return "flush after use"
    if first == "Plunger":
        return "clear a blocked toilet"
    if first in {"Blinds", "Curtains"}:
        return "change the light coming through the window"
    if first == "ShowerCurtain":
        return "keep water from spilling out"
    if first == "WateringCan":
        return "take care of the plant"
    if first == "Knife":
        return "prepare the food by cutting it"
    if first == "Faucet" and relation == "fill with water":
        return "fill the container with water"
    if first == "Faucet":
        return "get water flowing"
    if first == "Handle" and second in {"Cabinet", "Drawer", "Dresser"}:
        return "access the storage space"
    if first == "Handle" and second == "Door":
        return "go through the closed passage"
    if first == "Handle" and second == "Fridge":
        return "get something cold from inside"
    if first == "Handle" and second in {"Oven", "Microwave"}:
        return "put food into the appliance"
    return f"use the scene function: {edge['relation']}"


def target_general_name(edge: dict[str, Any]) -> str:
    second = edge["second_label"]
    if second in {"Cabinet", "Drawer", "Dresser"}:
        return "storage area"
    if second in {"Oven", "Microwave", "CoffeeMachine", "Toaster"}:
        return "appliance"
    if second in {"StoveBurner"}:
        return "cooking area"
    if second in {"LightFixture"}:
        return "lighting"
    if second in {"Sink", "Bathtub", "Kettle"}:
        return "water target"
    if second in {"Window"}:
        return "window area"
    return "target object"


def consequence_phrase(edge: dict[str, Any]) -> str:
    second = words(edge["second_label"])
    relation = edge["relation"]
    if relation == "pull to open":
        return f"the {second} opens"
    if relation in {"turn on/off", "switch on or off"}:
        return f"the {second} changes its on/off state"
    if relation == "run water into":
        return f"water flows into the {second}"
    if relation == "fill with water":
        return f"the {second} can be filled with water"
    if relation == "operate and control":
        return f"the {second} can be controlled"
    if relation == "key in time and start":
        return f"the {second} starts after a time is entered"
    if relation == "press to start brewing":
        return "coffee brewing starts"
    if relation in {"press to start toasting", "push down to start toasting"}:
        return "toasting starts"
    if relation == "push to flush toilet":
        return "the toilet flushes"
    if relation == "plunge to unclog":
        return "the blockage can be cleared"
    if relation == "blocks water from leaving":
        return "water is kept inside the bathing area"
    if relation == "cover or uncover":
        return f"the {second} is covered or uncovered"
    if relation in {"can slice or cut", "can shred and chop"}:
        return f"the {second} can be cut or chopped"
    if relation == "water and nourish":
        return f"the {second} receives water"
    return f"the relation '{relation}' is executed"


def is_ambiguous(edge: dict[str, Any], group_counts: Counter[tuple[str, str, str, str]]) -> bool:
    key = (edge["scene_id"], edge["first_label"], edge["relation"], edge["second_label"])
    return group_counts[key] > 1


def templates_for_edge(edge: dict[str, Any], ambiguous: bool) -> list[dict[str, Any]]:
    first = words(edge["first_label"])
    second = words(edge["second_label"])
    relation = edge["relation"]
    action = control_phrase(edge)
    goal = goal_phrase(edge)
    general_target = target_general_name(edge)
    consequence = consequence_phrase(edge)

    rows = [
        {
            "functional_query_type": "functional_element_selection",
            "anchor_visibility": "anchor_explicit",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "direct",
            "query_text": f"Which {first} should I {action} to affect the {second}?",
        },
        {
            "functional_query_type": "functional_element_selection",
            "anchor_visibility": "anchor_implicit",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "instruction",
            "query_text": f"I need to {goal} near this {general_target}. What should I {action}?",
        },
        {
            "functional_query_type": "functional_element_selection",
            "anchor_visibility": "anchor_hidden",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "goal_only",
            "query_text": f"I want to {goal}. What should I interact with?",
        },
        {
            "functional_query_type": "state_change_goal_completion",
            "anchor_visibility": "anchor_explicit",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "scenario",
            "query_text": f"To make the {second} do its function, which {first} should be used?",
        },
        {
            "functional_query_type": "state_change_goal_completion",
            "anchor_visibility": "anchor_hidden",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "scenario",
            "query_text": f"I am trying to {goal}. Which scene element should I use?",
        },
        {
            "functional_query_type": "target_object_selection",
            "anchor_visibility": "anchor_explicit",
            "answer_target": "affected_or_anchor_object",
            "answer_node_ids": [edge["second_node_id"]],
            "answer_format": "node_selection",
            "language_style": "direct",
            "query_text": f"Which {second} is affected by this {first}?",
        },
        {
            "functional_query_type": "relation_verification",
            "anchor_visibility": "anchor_explicit",
            "answer_target": "functional_relation",
            "answer_node_ids": [edge["first_node_id"], edge["second_node_id"]],
            "answer_format": "boolean",
            "answer_boolean": True,
            "language_style": "verification",
            "query_text": f"Does this {first} perform '{relation}' on the {second}?",
        },
        {
            "functional_query_type": "functional_consequence_prediction",
            "anchor_visibility": "anchor_implicit",
            "answer_target": "functional_consequence",
            "answer_node_ids": [edge["second_node_id"]],
            "answer_format": "text",
            "answer_text": consequence,
            "language_style": "consequence",
            "query_text": f"What happens if I {action} this {first}?",
        },
        {
            "functional_query_type": "functional_affordance_selection",
            "anchor_visibility": "anchor_hidden",
            "answer_target": "functional_element",
            "answer_node_ids": [edge["first_node_id"]],
            "answer_format": "node_selection",
            "language_style": "affordance",
            "query_text": f"Which object or part can help me {goal}?",
        },
    ]

    if ambiguous:
        rows.extend([
            {
                "functional_query_type": "ambiguous_instance_minimal_pair",
                "anchor_visibility": "anchor_explicit",
                "answer_target": "functional_element",
                "answer_node_ids": [edge["first_node_id"]],
                "answer_format": "node_selection",
                "language_style": "disambiguation",
                "query_text": f"There are multiple {first}s here. Which one is linked to this {second}?",
            },
            {
                "functional_query_type": "ambiguous_instance_minimal_pair",
                "anchor_visibility": "anchor_hidden",
                "answer_target": "functional_element",
                "answer_node_ids": [edge["first_node_id"]],
                "answer_format": "node_selection",
                "language_style": "disambiguation_goal_only",
                "query_text": f"Several similar controls are present. I want to {goal}; which one should I use?",
            },
        ])
    return rows


def edge_scene_id(scene_id: str, edge: dict[str, Any]) -> dict[str, Any]:
    out = dict(edge)
    out["scene_id"] = scene_id
    return out


def build_rows(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    visible_edges = [
        edge_scene_id(scene["scene_id"], edge)
        for scene in manifest["scenes"]
        for edge in scene["functional_relations"]
        if edge["both_endpoints_visible"]
    ]
    group_counts = Counter((e["scene_id"], e["first_label"], e["relation"], e["second_label"]) for e in visible_edges)
    candidates_by_scene = {scene["scene_id"]: scene["candidate_node_ids"] for scene in manifest["scenes"]}

    rows: list[dict[str, Any]] = []
    for edge in visible_edges:
        spatial_scope = classify_spatial_scope(edge)
        category = relation_category(edge)
        ambiguous = is_ambiguous(edge, group_counts)
        scene_slug = snake(edge["scene_id"].split("/", 1)[-1])
        edge_slug = f"e{edge['edge_index']:03d}"
        for variant_idx, frame in enumerate(templates_for_edge(edge, ambiguous)):
            if ambiguous:
                difficulty = "hard_ambiguous_instance"
            elif spatial_scope == "remote" and frame["anchor_visibility"] == "anchor_hidden":
                difficulty = "hard_remote_anchor_hidden"
            elif spatial_scope == "remote":
                difficulty = "remote"
            elif frame["anchor_visibility"] == "anchor_hidden":
                difficulty = "anchor_hidden"
            else:
                difficulty = "standard"
            query_id = (
                f"funthor_v2_{scene_slug}_{edge_slug}_"
                f"{frame['functional_query_type']}_{frame['anchor_visibility']}_v{variant_idx:02d}"
            )
            answer_node_ids = frame["answer_node_ids"]
            target_node_id = answer_node_ids[0] if answer_node_ids else None
            target_label = edge["first_label"] if target_node_id == edge["first_node_id"] else edge["second_label"]
            row = {
                "query_id": query_id,
                "dataset": "funthor",
                "scene_id": edge["scene_id"],
                "source_scene_id": edge["scene_id"].split("/", 1)[-1],
                "split": "funthor_functional_queries_factorized_v2",
                "generation_version": "factorized_v2",
                "source": "funthor_factorized_functional_relation_protocol_v2",
                "annotation_source": "funthor_functional_relations_json_with_factorized_query_protocol_v2",
                "query_text": frame["query_text"],
                "prompt": frame["query_text"],
                "functional_query_type": frame["functional_query_type"],
                "query_family": frame["functional_query_type"],
                "spatial_scope": spatial_scope,
                "anchor_visibility": frame["anchor_visibility"],
                "answer_target": frame["answer_target"],
                "answer_format": frame["answer_format"],
                "target_node_id": target_node_id,
                "target_node_ids": answer_node_ids,
                "target_label": target_label,
                "target_labels": [target_label],
                "anchor_node_id": edge["second_node_id"],
                "anchor_label": edge["second_label"],
                "functional_element_node_id": edge["first_node_id"],
                "functional_element_label": edge["first_label"],
                "affected_object_node_id": edge["second_node_id"],
                "affected_object_label": edge["second_label"],
                "candidate_node_ids": candidates_by_scene[edge["scene_id"]],
                "n_candidates": len(candidates_by_scene[edge["scene_id"]]),
                "supporting_edge_ids": [edge["edge_id"]],
                "functional_edge": {k: v for k, v in edge.items() if k != "scene_id"},
                "functional_taxonomy": {
                    "relation_category": category,
                    "matching_strategy": edge.get("relation_type"),
                    "spatial_scope": spatial_scope,
                    "anchor_visibility": frame["anchor_visibility"],
                    "is_ambiguous_instance_group": ambiguous,
                },
                "difficulty_tags": [
                    "functional_relation",
                    frame["functional_query_type"],
                    spatial_scope,
                    frame["anchor_visibility"],
                    category,
                    difficulty,
                ],
                "paper_use_allowed": False,
                "human_review_required": True,
                "dennis_signoff_required": True,
                "use_for": ["training_candidate", "diagnostic_eval_candidate"],
                "notes": "Factorized v2 row. Query wording varies controlled factors; answer remains grounded in the FunTHOR functional edge.",
            }
            if "answer_boolean" in frame:
                row["answer_boolean"] = frame["answer_boolean"]
            if "answer_text" in frame:
                row["answer_text"] = frame["answer_text"]
            rows.append(row)
    return rows


def update_manifest(rows: list[dict[str, Any]]) -> None:
    release_manifest_path = RELEASE_DIR / "dataset_manifest.json"
    release_manifest = read_json(release_manifest_path)
    external = release_manifest.setdefault("external_datasets", {}).setdefault("funthor_v1", {})
    external["factorized_v2_query_split"] = "splits/funthor_functional_queries_factorized_v2.jsonl"
    external["n_factorized_v2_queries"] = len(rows)
    external["factorized_v2_axes"] = ["functional_query_type", "spatial_scope", "anchor_visibility"]
    release_manifest["counts"]["n_external_funthor_factorized_v2_queries"] = len(rows)
    base_release_rows = sum(split.get("n_rows", 0) for split in release_manifest.get("split_summary", {}).values())
    release_manifest["counts"]["n_total_release_query_rows_including_external"] = (
        base_release_rows
        + release_manifest["counts"].get("n_external_funthor_queries", 0)
        + release_manifest["counts"].get("n_external_funthor_minimal_pairs", 0)
        + len(rows)
    )
    write_json(release_manifest_path, release_manifest)

    funthor_manifest = read_json(FUNTHOR_MANIFEST)
    funthor_manifest["counts"]["n_factorized_v2_queries"] = len(rows)
    funthor_manifest["factorized_v2"] = {
        "query_split": "../../splits/funthor_functional_queries_factorized_v2.jsonl",
        "axes": ["functional_query_type", "spatial_scope", "anchor_visibility"],
        "query_type_counts": dict(sorted(Counter(row["functional_query_type"] for row in rows).items())),
        "spatial_scope_counts": dict(sorted(Counter(row["spatial_scope"] for row in rows).items())),
        "anchor_visibility_counts": dict(sorted(Counter(row["anchor_visibility"] for row in rows).items())),
        "answer_format_counts": dict(sorted(Counter(row["answer_format"] for row in rows).items())),
        "paper_use_allowed": False,
    }
    write_json(FUNTHOR_MANIFEST, funthor_manifest)


def update_docs(rows: list[dict[str, Any]]) -> None:
    protocol_path = RELEASE_DIR / "query_protocol_v1.md"
    text = protocol_path.read_text(encoding="utf-8")
    block = f"""
## FunTHOR Factorized v2

FunTHOR v2 keeps the same grounded functional edges but varies three controlled factors:

```text
Functional Query Type x Spatial Scope x Anchor Visibility
```

- `functional_query_type`: what the question asks, e.g. selecting a functional element, selecting an affected object, verifying a relation, completing a goal, or predicting a consequence.
- `spatial_scope`: whether the functional relation is local or remote. This is assigned from the relation itself.
- `anchor_visibility`: whether the query explicitly names the anchor object, only hints at it, or hides it behind a goal.

Generated FunTHOR factorized v2 queries: {len(rows)}

These rows are still paper-disabled until wording review, evidence spot-check, and Dennis signoff.
"""
    if "## FunTHOR Factorized v2" not in text:
        text = text.replace("## Paper-Use Boundary\n", block + "\n## Paper-Use Boundary\n")
        protocol_path.write_text(text, encoding="utf-8")

    release_readme = RELEASE_DIR / "README.md"
    readme = release_readme.read_text(encoding="utf-8")
    if "funthor_functional_queries_factorized_v2.jsonl" not in readme:
        readme = readme.replace(
            "- `splits/funthor_functional_queries_v1.jsonl` contains 805 protocol-generated FunTHOR functional queries.",
            "- `splits/funthor_functional_queries_v1.jsonl` contains 805 template-v1 FunTHOR functional queries for smoke testing.\n"
            f"- `splits/funthor_functional_queries_factorized_v2.jsonl` contains {len(rows)} factorized FunTHOR queries over Functional Query Type x Spatial Scope x Anchor Visibility.",
        )
        release_readme.write_text(readme, encoding="utf-8")

    funthor_readme = FUNTHOR_DIR / "README.md"
    text = funthor_readme.read_text(encoding="utf-8")
    if "Factorized v2 queries" not in text:
        text += f"""

Factorized v2 queries: {len(rows)}

`../../splits/funthor_functional_queries_factorized_v2.jsonl` is the newer controlled split. It keeps v1's grounded functional edges but varies `functional_query_type`, `spatial_scope`, and `anchor_visibility` so we can measure which factor drives model performance.
"""
        funthor_readme.write_text(text, encoding="utf-8")


def main() -> None:
    manifest = read_json(FUNTHOR_MANIFEST)
    rows = build_rows(manifest)
    write_jsonl(OUTPUT, rows)
    update_manifest(rows)
    update_docs(rows)
    print(json.dumps({
        "status": "funthor_factorized_v2_ready",
        "n_queries": len(rows),
        "query_type_counts": dict(sorted(Counter(row["functional_query_type"] for row in rows).items())),
        "spatial_scope_counts": dict(sorted(Counter(row["spatial_scope"] for row in rows).items())),
        "anchor_visibility_counts": dict(sorted(Counter(row["anchor_visibility"] for row in rows).items())),
        "answer_format_counts": dict(sorted(Counter(row["answer_format"] for row in rows).items())),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
