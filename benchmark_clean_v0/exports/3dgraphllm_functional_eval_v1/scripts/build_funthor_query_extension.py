#!/usr/bin/env python3
"""Generate FunTHOR functional queries and merge them into the clean release.

This implements the multi-dataset query protocol Dennis suggested: every
functional scene-graph edge becomes a fixed number of query families, so query
coverage is defined by protocol rather than ad hoc prompting.
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
RELEASE_DIR = EXPORT_DIR / "fungraph_full_modality_release_v1"
FUNTHOR_DIR = RELEASE_DIR / "external" / "funthor_v1"
HF_DATASET = "leggedrobotics/funthor-dataset"
HF_API = f"https://huggingface.co/api/datasets/{HF_DATASET}"
HF_RAW = f"https://huggingface.co/datasets/{HF_DATASET}/raw/main"


def fetch_json(url: str) -> Any:
    with urllib.request.urlopen(url, timeout=90) as resp:
        return json.loads(resp.read())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def discover_scenes() -> list[str]:
    api = fetch_json(HF_API)
    scenes = sorted({sib["rfilename"].split("/", 1)[0] for sib in api["siblings"] if sib["rfilename"].startswith("FloorPlan")})
    return [scene for scene in scenes if scene.endswith("_physics")]


def scene_raw(scene: str, rel_path: str) -> str:
    return f"{HF_RAW}/{scene}/{rel_path}"


def relation_phrase(relation: str) -> str:
    relation = relation.strip()
    return relation if relation else "perform the functional relation with"


def clean_scene_id(scene: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", scene).strip("_").lower()


def load_scene(scene: str) -> dict[str, Any]:
    annotations = fetch_json(scene_raw(scene, "annotations_aggregated.json"))
    visibility = fetch_json(scene_raw(scene, "visible/visibility_stats.json"))
    relations = fetch_json(scene_raw(scene, "functional_relations.json"))
    object_metadata = fetch_json(scene_raw(scene, "object_metadata.json"))

    visibility_stats = visibility.get("stats", {})
    nodes = []
    for ann in annotations:
        node_id = str(ann["node_id"])
        label = str(ann.get("label") or "")
        if label == "Undefined":
            continue
        vis = visibility_stats.get(node_id, {})
        nodes.append({
            "node_id": node_id,
            "object_id": ann.get("object_id"),
            "label": label,
            "is_part": bool(ann.get("is_part")),
            "n_point_indices": len(ann.get("point_indices") or []),
            "point_annotation_source": f"{scene}/annotations_aggregated.json",
            "is_visible": bool(vis.get("is_visible", False)),
            "n_visible_points": int(vis.get("n_visible_points") or 0),
            "visibility_ratio": float(vis.get("visibility_ratio") or 0),
        })
    nodes_by_id = {node["node_id"]: node for node in nodes}
    visible_candidate_ids = sorted(node_id for node_id, node in nodes_by_id.items() if node["is_visible"])
    if not visible_candidate_ids:
        visible_candidate_ids = sorted(nodes_by_id)

    normalized_edges = []
    for idx, edge in enumerate(relations):
        first = str(edge["first_node_id"])
        second = str(edge["second_node_id"])
        first_node = nodes_by_id.get(first)
        second_node = nodes_by_id.get(second)
        both_visible = bool(first_node and second_node and first_node["is_visible"] and second_node["is_visible"])
        normalized_edges.append({
            "edge_index": idx,
            "edge_id": f"{first}|{edge['relation']}|{second}",
            "relation_type": edge.get("relation_type"),
            "first_node_id": first,
            "first_object_id": edge.get("first_object_id"),
            "first_label": edge.get("first_label"),
            "relation": edge.get("relation"),
            "second_node_id": second,
            "second_object_id": edge.get("second_object_id"),
            "second_label": edge.get("second_label"),
            "both_endpoints_visible": both_visible,
        })

    return {
        "scene_id": f"funthor/{scene}",
        "funthor_scene": scene,
        "nodes": nodes,
        "object_metadata_summary": {
            "n_objects": len(object_metadata),
            "n_objects_with_parts": sum(bool(obj.get("has_parts_annotation")) for obj in object_metadata),
        },
        "functional_relations": normalized_edges,
        "candidate_node_ids": visible_candidate_ids,
        "raw_assets": {
            "hf_dataset": HF_DATASET,
            "scene_root": f"{HF_RAW}/{scene}/",
            "rgb_glob": f"{scene}/dataset/color/*.png",
            "depth_glob": f"{scene}/dataset/depth/*.png",
            "pose_glob": f"{scene}/dataset/pose/*.npy",
            "intrinsics": f"{scene}/dataset/intrinsics.npy",
            "pointcloud": f"{scene}/pointcloud.ply",
        },
    }


def query_templates(edge: dict[str, Any]) -> list[tuple[str, str, str]]:
    first = edge["first_label"]
    second = edge["second_label"]
    rel = relation_phrase(edge["relation"])
    return [
        ("functional_element_selection", edge["first_node_id"], f"Which {first} should I use to {rel} the {second}?"),
        ("functional_element_selection", edge["first_node_id"], f"Identify the {first} that can {rel} the {second}."),
        ("functional_element_selection", edge["first_node_id"], f"I need to {rel} the {second}; select the correct {first}."),
        ("affected_object_selection", edge["second_node_id"], f"What object is affected when using the {first} to {rel}?"),
        ("affected_object_selection", edge["second_node_id"], f"The {first} is used to {rel}; which {second} is the target object?"),
    ]


def classify_edge(edge: dict[str, Any]) -> dict[str, Any]:
    relation_type = edge.get("relation_type") or ""
    first_label = str(edge.get("first_label") or "")
    if relation_type == "part_based" or first_label in {"Handle", "Button", "Lever", "StoveKnob", "LightSwitch", "Faucet", "Keypad", "FlushLever"}:
        category = "part_object_operation"
    elif relation_type == "proximity_based":
        category = "proximity_dependent_relation"
    elif relation_type == "manual_annotation":
        category = "ambiguous_one_to_one_assignment"
    else:
        category = "object_object_affordance"
    return {
        "relation_category": category,
        "matching_strategy": relation_type,
        "requires_global_assignment_reasoning": relation_type == "manual_annotation" or first_label in {"StoveKnob", "LightSwitch"},
    }


def generate_queries(scene_pkg: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    scene_slug = clean_scene_id(scene_pkg["funthor_scene"])
    candidate_ids = scene_pkg["candidate_node_ids"]
    for edge in scene_pkg["functional_relations"]:
        if not edge["both_endpoints_visible"]:
            continue
        taxonomy = classify_edge(edge)
        for variant, (family, target_id, text) in enumerate(query_templates(edge)):
            query_id = f"funthor_v1_{scene_slug}_e{edge['edge_index']:03d}_{family}_v{variant}"
            target_label = edge["first_label"] if target_id == edge["first_node_id"] else edge["second_label"]
            rows.append({
                "query_id": query_id,
                "dataset": "funthor",
                "scene_id": scene_pkg["scene_id"],
                "source_scene_id": scene_pkg["funthor_scene"],
                "split": "funthor_functional_queries_v1",
                "query_type": "functional",
                "query_family": family,
                "annotation_source": "funthor_rule_based_functional_scenegraph_protocol_v1",
                "source": "funthor_functional_relations_protocol_generated_v1",
                "query_text": text,
                "prompt": text,
                "target_node_id": target_id,
                "target_node_ids": [target_id],
                "target_label": target_label,
                "target_labels": [target_label],
                "anchor_node_id": edge["second_node_id"] if family == "functional_element_selection" else edge["first_node_id"],
                "anchor_label": edge["second_label"] if family == "functional_element_selection" else edge["first_label"],
                "supporting_edge_ids": [edge["edge_id"]],
                "candidate_node_ids": candidate_ids,
                "n_candidates": len(candidate_ids),
                "functional_edge": edge,
                "functional_taxonomy": taxonomy,
                "difficulty_tags": ["functional_relation", taxonomy["relation_category"], family],
                "paper_use_allowed": False,
                "human_review_required": True,
                "dennis_signoff_required": True,
            })
    return rows


def generate_minimal_pairs(queries: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    by_edge_family = defaultdict(list)
    for row in queries:
        edge = row["functional_edge"]
        if row["query_family"] != "functional_element_selection":
            continue
        key = (row["scene_id"], edge["relation"], edge["first_label"], edge["second_label"])
        by_edge_family[key].append(row)

    pairs = []
    seen = set()
    for key, rows in sorted(by_edge_family.items()):
        # Use the first template variant only, then pair distinct target instances.
        v0 = [row for row in rows if row["query_id"].endswith("_v0")]
        by_target = {}
        for row in v0:
            by_target.setdefault(row["target_node_id"], row)
        candidates = list(by_target.values())
        if len(candidates) < 2:
            continue
        for i in range(len(candidates)):
            for j in range(i + 1, len(candidates)):
                a, b = candidates[i], candidates[j]
                pair_key = tuple(sorted([a["query_id"], b["query_id"]]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)
                pairs.append({
                    "pair_id": f"funthor_minpair_v1_{len(pairs):04d}",
                    "dataset": "funthor",
                    "scene_id": a["scene_id"],
                    "query_a_id": a["query_id"],
                    "query_b_id": b["query_id"],
                    "changed_factor": "functional_element_instance",
                    "pair_family": "same_label_functional_element_assignment",
                    "why_hard": "Same scene, same relation, same endpoint labels; model must select the correct functional element instance rather than a label prior.",
                    "paper_use_allowed": False,
                    "human_review_required": True,
                    "dennis_signoff_required": True,
                })
                if len(pairs) >= cap:
                    return pairs
    return pairs


def write_protocol_doc(query_count: int, pair_count: int, edge_count: int, visible_edge_count: int) -> None:
    doc = f"""# Multi-Dataset Functional Query Protocol v1

This protocol defines how functional queries are generated across FunGraph/SceneFun3D and FunTHOR-style functional scene graph datasets.

## Unit

The atomic unit is a directed functional edge:

```text
functional_element_or_subject --relation--> affected_or_anchor_object
```

For FunGraph this edge comes from OpenFunGraph / SceneFun3D relations. For FunTHOR this edge comes from `functional_relations.json`.

## Candidate Set

- FunGraph: exported candidate objects for the scene.
- FunTHOR: visible, non-`Undefined` nodes from `visible/visibility_stats.json` and `annotations_aggregated.json`.

## Query Families

For every visible functional edge, FunTHOR v1 generates exactly 5 queries:

- 3 x `functional_element_selection`: answer is the first node / functional element.
- 2 x `affected_object_selection`: answer is the second node / affected object.

Every generated query keeps `supporting_edge_ids`, target ids, candidate ids, relation category, matching strategy, and review flags.

## Minimal Pairs

For same-scene, same-label, same-relation functional elements, the protocol creates `same_label_functional_element_assignment` minimal pairs. These are diagnostic until human/Dennis signoff.

## FunTHOR v1 Counts

- Raw functional edges: {edge_count}
- Visible endpoint edges used for query generation: {visible_edge_count}
- Generated FunTHOR functional queries: {query_count}
- Generated FunTHOR minimal pairs: {pair_count}

## Paper-Use Boundary

The FunTHOR queries are rule-grounded but still protocol-generated. They are included in the benchmark release as external dataset coverage and should remain paper-disabled until wording review, evidence spot-check, and Dennis signoff.
"""
    (RELEASE_DIR / "query_protocol_v1.md").write_text(doc, encoding="utf-8")


def update_release_manifest(funthor_manifest: dict[str, Any], query_count: int, pair_count: int) -> None:
    manifest_path = RELEASE_DIR / "dataset_manifest.json"
    manifest = read_json(manifest_path)
    manifest["external_datasets"] = {
        "funthor_v1": {
            "dataset": HF_DATASET,
            "manifest": "external/funthor_v1/funthor_manifest.json",
            "query_split": "splits/funthor_functional_queries_v1.jsonl",
            "minimal_pair_split": "splits/funthor_minimal_pairs_v1.jsonl",
            "n_scenes": funthor_manifest["counts"]["n_scenes"],
            "n_nodes": funthor_manifest["counts"]["n_nodes"],
            "n_functional_edges": funthor_manifest["counts"]["n_functional_edges"],
            "n_generated_queries": query_count,
            "n_generated_minimal_pairs": pair_count,
            "paper_use_allowed": False,
        }
    }
    manifest["query_protocol"] = "query_protocol_v1.md"
    manifest["counts"]["n_external_funthor_queries"] = query_count
    manifest["counts"]["n_external_funthor_minimal_pairs"] = pair_count
    manifest["counts"]["n_total_release_query_rows_including_external"] = (
        sum(split.get("n_rows", 0) for split in manifest.get("split_summary", {}).values()) + query_count + pair_count
    )
    write_json(manifest_path, manifest)


def write_readme(query_count: int, pair_count: int) -> None:
    readme = f"""# FunTHOR v1 External Extension

This folder stores compact FunTHOR metadata used to generate external functional-query coverage for the FunGraph full-modality release.

Files:

- `funthor_manifest.json`: compact scene/node/edge metadata, raw HF asset pointers, and counts.
- `../../splits/funthor_functional_queries_v1.jsonl`: protocol-generated functional queries.
- `../../splits/funthor_minimal_pairs_v1.jsonl`: same-label functional-element diagnostic pairs.
- `../../query_protocol_v1.md`: shared multi-dataset query protocol.

Generated queries: {query_count}
Generated minimal pairs: {pair_count}

The generated rows are paper-disabled until human wording review, visual/evidence spot-check, and Dennis signoff.
"""
    (FUNTHOR_DIR / "README.md").write_text(readme, encoding="utf-8")



def update_release_readme(query_count: int, pair_count: int) -> None:
    readme_path = RELEASE_DIR / "README.md"
    if not readme_path.exists():
        return
    text = readme_path.read_text(encoding="utf-8")
    if "query_protocol_v1.md" not in text:
        text = text.replace(
            "  splits/*.jsonl\n  scenes/<scene_id>/",
            "  query_protocol_v1.md\n  splits/*.jsonl\n  external/funthor_v1/funthor_manifest.json\n  scenes/<scene_id>/",
        )
    block = f"""
## External FunTHOR Extension

Dennis suggested defining one query protocol across functional-scenegraph datasets. This release now includes FunTHOR as an external dataset:

- `query_protocol_v1.md` defines the shared generation protocol.
- `external/funthor_v1/funthor_manifest.json` stores compact FunTHOR scene/node/edge metadata and HF raw asset pointers.
- `splits/funthor_functional_queries_v1.jsonl` contains {query_count} protocol-generated FunTHOR functional queries.
- `splits/funthor_minimal_pairs_v1.jsonl` contains {pair_count} same-label functional-element diagnostic pairs.

These rows are rule-grounded but still paper-disabled until human wording review, evidence spot-check, and Dennis signoff.
"""
    if "## External FunTHOR Extension" not in text:
        text = text.replace("## Boundary\n", block + "\n## Boundary\n")
    readme_path.write_text(text, encoding="utf-8")

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--minimal-pair-cap", type=int, default=200)
    args = parser.parse_args()

    scenes = discover_scenes()
    scene_pkgs = [load_scene(scene) for scene in scenes]
    queries = [query for scene in scene_pkgs for query in generate_queries(scene)]
    pairs = generate_minimal_pairs(queries, args.minimal_pair_cap)

    raw_edges = sum(len(scene["functional_relations"]) for scene in scene_pkgs)
    visible_edges = sum(sum(edge["both_endpoints_visible"] for edge in scene["functional_relations"]) for scene in scene_pkgs)
    relation_counts = Counter(edge["relation"] for scene in scene_pkgs for edge in scene["functional_relations"])
    manifest = {
        "status": "funthor_external_functional_extension_ready",
        "dataset": HF_DATASET,
        "source_url": f"https://huggingface.co/datasets/{HF_DATASET}",
        "query_protocol": "../../query_protocol_v1.md",
        "raw_asset_policy": "Raw RGB-D, pose, intrinsics, and pointcloud files stay on Hugging Face and are referenced by URL/path; this manifest stores compact graph metadata only.",
        "counts": {
            "n_scenes": len(scene_pkgs),
            "n_nodes": sum(len(scene["nodes"]) for scene in scene_pkgs),
            "n_visible_candidate_nodes": sum(len(scene["candidate_node_ids"]) for scene in scene_pkgs),
            "n_functional_edges": raw_edges,
            "n_visible_endpoint_edges": visible_edges,
            "n_generated_queries": len(queries),
            "n_generated_minimal_pairs": len(pairs),
            "n_unique_relations": len(relation_counts),
        },
        "relation_counts": dict(sorted(relation_counts.items())),
        "scenes": scene_pkgs,
    }

    write_json(FUNTHOR_DIR / "funthor_manifest.json", manifest)
    write_jsonl(RELEASE_DIR / "splits" / "funthor_functional_queries_v1.jsonl", queries)
    write_jsonl(RELEASE_DIR / "splits" / "funthor_minimal_pairs_v1.jsonl", pairs)
    write_protocol_doc(len(queries), len(pairs), raw_edges, visible_edges)
    write_readme(len(queries), len(pairs))
    update_release_manifest(manifest, len(queries), len(pairs))
    update_release_readme(len(queries), len(pairs))

    print(json.dumps({
        "status": "funthor_external_functional_extension_ready",
        "n_scenes": len(scene_pkgs),
        "n_edges": raw_edges,
        "n_visible_edges": visible_edges,
        "n_queries": len(queries),
        "n_minimal_pairs": len(pairs),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
