#!/usr/bin/env python3
"""Build factorized FunGraph/SceneFun3D functional queries.

This creates new controlled query variants from the release scene functional
relations, rather than relabeling old benchmark questions.

Axes:
    Functional Query Type x Spatial Scope x Anchor Visibility
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
RELEASE_DIR = EXPORT_DIR / "fungraph_full_modality_release_v1"
OUTPUT = RELEASE_DIR / "splits" / "fungraph_functional_queries_factorized_v2.jsonl"
SUMMARY = RELEASE_DIR / "fungraph_factorized_v2_summary.json"

REMOTE_FUNCTIONAL_LABELS = {"light switch", "switch panel", "remote", "electric outlet", "power strip"}
REMOTE_RELATION_KEYWORDS = {"provide power", "control, turn on or turn off", "control"}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def snake(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", norm(text)).strip("_")


def clean_label(label: Any) -> str:
    return norm(label).replace(" / ", " or ")


def primary_label(label: Any) -> str:
    return norm(str(label).split("/")[0])


def relation_category(edge: dict[str, Any]) -> str:
    first = norm(edge["first_label"])
    relation = norm(edge["relation"])
    if any(x in first for x in ["handle", "knob", "button", "switch", "faucet"]):
        return "part_object_operation"
    if any(x in first for x in ["outlet", "power strip", "remote"]):
        return "object_object_affordance"
    if "drawer" in relation or "open" in relation or "adjust" in relation:
        return "part_object_operation"
    return "object_object_affordance"


def matching_strategy(edge: dict[str, Any]) -> str:
    first = norm(edge["first_label"])
    relation = norm(edge["relation"])
    if any(x in first for x in ["handle", "knob", "button", "switch", "faucet"]):
        return "part_based"
    if "provide power" in relation or "control" == relation:
        return "manual_or_functional_assignment"
    return "relation_based"


def bbox_distance(first_node: dict[str, Any] | None, second_node: dict[str, Any] | None) -> float | None:
    if not first_node or not second_node:
        return None
    try:
        return float(math.dist(first_node["geometry"]["bbox_center"], second_node["geometry"]["bbox_center"]))
    except (KeyError, TypeError, ValueError):
        return None


def classify_spatial_scope(edge: dict[str, Any], distance: float | None) -> str:
    first = norm(edge["first_label"])
    relation = norm(edge["relation"])
    if any(label in first for label in REMOTE_FUNCTIONAL_LABELS):
        return "remote"
    if relation in REMOTE_RELATION_KEYWORDS:
        return "remote"
    if distance is not None and distance >= 2.5:
        return "remote"
    return "local"


def control_phrase(edge: dict[str, Any]) -> str:
    first = norm(edge["first_label"])
    relation = norm(edge["relation"])
    if "pull" in relation:
        return "pull"
    if "press" in relation or "button" in first or "switch" in first or "remote" in first:
        return "press"
    if "rotate" in relation or "knob" in first or "faucet" in first:
        return "turn"
    if "power" in relation:
        return "plug into or use"
    return "interact with"


def goal_phrase(edge: dict[str, Any]) -> str:
    first = norm(edge["first_label"])
    second = norm(edge["second_label"])
    relation = norm(edge["relation"])
    if "light" in second or "chandelier" in second:
        return "light up this area"
    if "television" in second:
        return "start watching something"
    if "lamp" in second:
        return "turn on a nearby lamp"
    if "provide power" in relation:
        return "power the device"
    if "water flow" in relation:
        return "get water running"
    if "flush" in relation or "toilet" in second:
        return "flush after use"
    if "temperature" in relation and "radiator" in second:
        return "warm up the room"
    if "temperature" in relation or ("setting" in relation and "oven" in second):
        return "start cooking or adjust heat"
    if "setting" in relation and any(x in second for x in ["washing machine", "dryer", "dishwasher"]):
        return "run the appliance with the right setting"
    if "fridge" in second:
        return "get something cold from inside"
    if "oven" in second or "microwave" in second:
        return "put food into the appliance"
    if "trash" in second:
        return "throw something away"
    if any(x in second for x in ["drawer", "dresser", "cabinet", "closet", "wardrobe", "nightstand", "chest"]):
        return "access the storage space"
    if "door" in second:
        return "go through the closed passage"
    if "window" in second:
        return "open or close the window"
    if "faucet" in first:
        return "get water running"
    return f"use the scene function: {edge['relation']}"


def target_general_name(edge: dict[str, Any]) -> str:
    second = norm(edge["second_label"])
    if any(x in second for x in ["drawer", "dresser", "cabinet", "closet", "wardrobe", "nightstand", "chest"]):
        return "storage area"
    if any(x in second for x in ["oven", "microwave", "dishwasher", "washing machine", "dryer"]):
        return "appliance"
    if any(x in second for x in ["sink", "bathtub"]):
        return "water fixture"
    if "light" in second or "chandelier" in second:
        return "lighting"
    if "television" in second:
        return "entertainment device"
    if "door" in second:
        return "doorway"
    return "target object"


def consequence_phrase(edge: dict[str, Any]) -> str:
    second = clean_label(edge["second_label"])
    relation = norm(edge["relation"])
    if "open" in relation and "close" in relation:
        return f"the {second} opens or closes"
    if "provide power" in relation:
        return f"the {second} can receive power"
    if "control, turn on or turn off" in relation:
        return f"the {second} changes its on/off state"
    if relation == "control":
        return f"the {second} is controlled"
    if "water flow" in relation:
        return f"water flow changes at the {second}"
    if "temperature" in relation:
        return f"the {second} temperature changes"
    if "setting" in relation:
        return f"the {second} setting changes"
    if "flush" in relation:
        return "the toilet flushes"
    return f"the functional relation '{edge['relation']}' is executed"


def is_ambiguous(edge: dict[str, Any], group_counts: Counter[tuple[str, str, str, str]]) -> bool:
    key = (edge["scene_id"], norm(edge["first_label"]), norm(edge["relation"]), norm(edge["second_label"]))
    return group_counts[key] > 1


def templates_for_edge(edge: dict[str, Any], ambiguous: bool) -> list[dict[str, Any]]:
    first = clean_label(edge["first_label"])
    second = clean_label(edge["second_label"])
    first_primary = primary_label(edge["first_label"])
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
            "query_text": f"To make the {second} do its function, which {first_primary} should be used?",
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
            "query_text": f"Which {second} is affected by this {first_primary}?",
        },
        {
            "functional_query_type": "relation_verification",
            "anchor_visibility": "anchor_explicit",
            "answer_target": "functional_relation",
            "answer_node_ids": [edge["first_node_id"], edge["second_node_id"]],
            "answer_format": "boolean",
            "answer_boolean": True,
            "language_style": "verification",
            "query_text": f"Does this {first_primary} perform '{relation}' on the {second}?",
        },
        {
            "functional_query_type": "functional_consequence_prediction",
            "anchor_visibility": "anchor_implicit",
            "answer_target": "functional_consequence",
            "answer_node_ids": [edge["second_node_id"]],
            "answer_format": "text",
            "answer_text": consequence,
            "language_style": "consequence",
            "query_text": f"What happens if I {action} this {first_primary}?",
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


def load_scene_packages() -> list[dict[str, Any]]:
    return [read_json(path) for path in sorted((RELEASE_DIR / "scenes").glob("*/scene.json"))]


def build_rows(scene_packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scene_nodes = {
        str(scene["scene_id"]): {str(node["node_id"]): node for node in scene["node_list"]}
        for scene in scene_packages
    }
    edges = []
    for scene in scene_packages:
        candidate_ids = [str(node["node_id"]) for node in scene["node_list"]]
        for edge in scene["functional_relations"]:
            row = dict(edge)
            row["scene_id"] = str(scene["scene_id"])
            row["candidate_node_ids"] = candidate_ids
            row["dataset"] = "scenefun3d"
            edges.append(row)

    group_counts = Counter((e["scene_id"], norm(e["first_label"]), norm(e["relation"]), norm(e["second_label"])) for e in edges)
    rows: list[dict[str, Any]] = []
    for edge in edges:
        nodes = scene_nodes[edge["scene_id"]]
        first_node = nodes.get(str(edge["first_node_id"]))
        second_node = nodes.get(str(edge["second_node_id"]))
        distance = bbox_distance(first_node, second_node)
        spatial_scope = classify_spatial_scope(edge, distance)
        category = relation_category(edge)
        strategy = matching_strategy(edge)
        ambiguous = is_ambiguous(edge, group_counts)
        scene_slug = snake(edge["scene_id"])
        edge_slug = f"e{len(rows):05d}"
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
                f"fungraph_v2_{scene_slug}_{edge_slug}_"
                f"{frame['functional_query_type']}_{frame['anchor_visibility']}_v{variant_idx:02d}"
            )
            answer_node_ids = frame["answer_node_ids"]
            target_node_id = answer_node_ids[0] if answer_node_ids else None
            if target_node_id == edge["first_node_id"]:
                target_label = edge["first_label"]
            elif target_node_id == edge["second_node_id"]:
                target_label = edge["second_label"]
            else:
                target_label = edge["first_label"]

            out = {
                "query_id": query_id,
                "dataset": "scenefun3d",
                "scene_id": edge["scene_id"],
                "split": "fungraph_functional_queries_factorized_v2",
                "generation_version": "factorized_v2",
                "source": "fungraph_factorized_functional_relation_protocol_v2",
                "annotation_source": "openfungraph_scenefun3d_relation_with_factorized_query_protocol_v2",
                "query_text": frame["query_text"],
                "prompt": frame["query_text"],
                "query_type": "functional",
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
                "candidate_node_ids": edge["candidate_node_ids"],
                "n_candidates": len(edge["candidate_node_ids"]),
                "supporting_edge_ids": [edge["edge_id"]],
                "functional_edge": {k: v for k, v in edge.items() if k not in {"candidate_node_ids", "dataset"}},
                "functional_taxonomy": {
                    "relation": edge["relation"],
                    "relation_category": category,
                    "matching_strategy": strategy,
                    "functional_query_type": frame["functional_query_type"],
                    "spatial_scope": spatial_scope,
                    "anchor_visibility": frame["anchor_visibility"],
                    "target_anchor_distance_m": distance,
                    "is_ambiguous_instance_group": ambiguous,
                    "taxonomy_version": "fungraph_factorized_query_v2",
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
                "notes": "Generated from SceneFun3D/OpenFunGraph functional relations with controlled factorized query axes.",
            }
            if "answer_boolean" in frame:
                out["answer_boolean"] = frame["answer_boolean"]
            if "answer_text" in frame:
                out["answer_text"] = frame["answer_text"]
            rows.append(out)
    return rows


def update_manifest(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    path = RELEASE_DIR / "dataset_manifest.json"
    manifest = read_json(path)
    generated = manifest.setdefault("generated_splits", {})
    generated["fungraph_functional_queries_factorized_v2"] = {
        "path": "splits/fungraph_functional_queries_factorized_v2.jsonl",
        "summary": "fungraph_factorized_v2_summary.json",
        "n_rows": len(rows),
        "source": "release scene functional_relations",
        "axes": ["functional_query_type", "spatial_scope", "anchor_visibility"],
        "paper_use_allowed": False,
    }
    manifest["counts"]["n_fungraph_factorized_v2_queries"] = len(rows)
    manifest["counts"]["fungraph_factorized_v2"] = summary["counts"]
    write_json(path, manifest)


def update_docs(n_rows: int) -> None:
    protocol_path = RELEASE_DIR / "query_protocol_v1.md"
    text = protocol_path.read_text(encoding="utf-8")
    block = f"""
## FunGraph Factorized v2

FunGraph/SceneFun3D v2 generates new queries directly from release functional relations. It uses the same controlled axes as FunTHOR v2:

```text
Functional Query Type x Spatial Scope x Anchor Visibility
```

Generated FunGraph/SceneFun3D factorized v2 queries: {n_rows}

These rows are paper-disabled until wording review, evidence spot-check, and Dennis signoff.
"""
    if "## FunGraph Factorized v2" not in text:
        text = text.replace("## FunGraph Existing Query Taxonomy v2\n", block + "\n## FunGraph Existing Query Taxonomy v2\n")
        protocol_path.write_text(text, encoding="utf-8")

    readme_path = RELEASE_DIR / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "fungraph_functional_queries_factorized_v2.jsonl" not in readme:
        line = (
            f"- `splits/fungraph_functional_queries_factorized_v2.jsonl` contains {n_rows} newly generated FunGraph/SceneFun3D factorized queries over Functional Query Type x Spatial Scope x Anchor Visibility.\n"
        )
        readme = readme.replace("- `splits/fungraph_existing_queries_categorized_v2.jsonl`", line + "- `splits/fungraph_existing_queries_categorized_v2.jsonl`")
        readme_path.write_text(readme, encoding="utf-8")


def main() -> None:
    scene_packages = load_scene_packages()
    rows = build_rows(scene_packages)
    summary = {
        "status": "fungraph_factorized_v2_ready",
        "paper_use_allowed": False,
        "human_review_required": True,
        "dennis_signoff_required": True,
        "source": "release scene functional_relations",
        "counts": {
            "n_scenes": len(scene_packages),
            "n_source_functional_relations": sum(len(scene["functional_relations"]) for scene in scene_packages),
            "n_rows": len(rows),
            "by_functional_query_type": dict(sorted(Counter(row["functional_query_type"] for row in rows).items())),
            "by_spatial_scope": dict(sorted(Counter(row["spatial_scope"] for row in rows).items())),
            "by_anchor_visibility": dict(sorted(Counter(row["anchor_visibility"] for row in rows).items())),
            "by_answer_format": dict(sorted(Counter(row["answer_format"] for row in rows).items())),
        },
        "taxonomy_axes": ["functional_query_type", "spatial_scope", "anchor_visibility"],
        "notes": "Newly generated candidate split; canonical old eval splits are unchanged.",
    }
    write_jsonl(OUTPUT, rows)
    write_json(SUMMARY, summary)
    update_manifest(rows, summary)
    update_docs(len(rows))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
