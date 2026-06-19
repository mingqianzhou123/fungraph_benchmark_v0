#!/usr/bin/env python3
"""Build a clean FunTHOR-inspired full-modality release package.

This package is the human-facing benchmark layout. It keeps the existing
3DGraphLLM adapter files as build inputs, but presents the benchmark as a small
set of dataset-level files plus one compact scene folder per scene.
"""

from __future__ import annotations

import csv
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
RELEASE_DIR = EXPORT_DIR / "fungraph_full_modality_release_v1"
ANNOTATION_DIR = BENCHMARK_ROOT / "annotations" / "openfungraph"
RELATIONS_PATH = ANNOTATION_DIR / "SceneFun3D.relations.json"
GEOMETRY_PATH = BENCHMARK_ROOT / "geometry" / "scenefun3d_node_geom.json"

QUERY_SPLITS = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
    "minimal_pairs_28": EXPORT_DIR / "minimal_pairs_28_eval.jsonl",
    "expansion_functional_116_candidates": EXPORT_DIR / "expansion_v1" / "final_candidates" / "functional_balanced_116_frozen_candidate.jsonl",
    "expansion_minimal_pairs_60_candidates": EXPORT_DIR / "expansion_v1" / "final_candidates" / "minimal_pairs_expanded_60_frozen_candidate.jsonl",
}

FUNCTIONAL_PART_LABELS = {
    "button",
    "button / knob",
    "electric outlet",
    "faucet",
    "faucet / handle",
    "flush button",
    "handle",
    "handle / faucet",
    "knob",
    "lever",
    "light switch",
    "remote",
    "switch",
    "switch panel / electric outlet",
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def parse_edge(edge: str | None) -> tuple[str | None, str | None, str | None]:
    if not edge:
        return None, None, None
    parts = str(edge).split("|")
    if len(parts) != 3:
        return None, None, None
    return parts[0], parts[1], parts[2]


def relation_from_row(row: dict[str, Any]) -> str:
    edge = (row.get("supporting_edge_ids") or [None])[0]
    _, relation, _ = parse_edge(edge)
    return relation or str(row.get("relation") or "")


def norm(value: Any) -> str:
    return str(value or "").strip().lower()


def is_functional_part_label(label: str) -> bool:
    label = norm(label)
    return label in FUNCTIONAL_PART_LABELS or any(part in label for part in ["handle", "knob", "switch", "button", "faucet"])


def classify_relation(row: dict[str, Any]) -> dict[str, Any]:
    relation = norm(relation_from_row(row))
    target_label = norm(row.get("target_label") or (row.get("target_labels") or [""])[0])
    tags = set(row.get("difficulty_tags") or [])
    same_label = "same_label_disambiguation" in tags or int(row.get("num_same_label_distractors") or 0) > 0
    if any(term in relation for term in ["water flow", "fill with water", "run water", "provide power"]):
        category = "proximity_dependent_relation"
        strategy = "proximity_based"
    elif is_functional_part_label(target_label) and any(term in relation for term in ["open", "close", "adjust", "turn", "flush", "control", "rotate", "press", "pull"]):
        category = "part_object_operation"
        strategy = "part_based"
    else:
        category = "object_object_affordance"
        strategy = "exact_match_affordance"
    if same_label and target_label in {"knob", "handle", "remote", "button", "button / knob", "light switch"}:
        ambiguity = "ambiguous_one_to_one_assignment"
    elif same_label:
        ambiguity = "same_label_visual_disambiguation"
    else:
        ambiguity = "not_same_label_ambiguous"
    return {
        "relation": relation,
        "category": category,
        "matching_strategy": strategy,
        "ambiguity_type": ambiguity,
        "is_functional_part_target": is_functional_part_label(target_label),
    }


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def load_inputs() -> dict[str, Any]:
    object_rows = load_csv(EXPORT_DIR / "full_object_modality_manifest.csv")
    capture_rows = load_csv(EXPORT_DIR / "full_scene_capture_manifest.csv")
    frame_rows = read_jsonl(EXPORT_DIR / "full_scene_frame_index.jsonl")
    readiness = read_json(EXPORT_DIR / "full_multimodal_readiness.json")
    geometry = read_json(GEOMETRY_PATH)
    relations = read_json(RELATIONS_PATH)
    evidence = {row.get("query_id"): row for row in read_jsonl(EXPORT_DIR / "relation_conditioned_evidence" / "full_perception_evidence_index.jsonl") if row.get("query_id")}
    return {
        "objects": object_rows,
        "captures": capture_rows,
        "frames": frame_rows,
        "readiness": readiness,
        "geometry": geometry,
        "relations": relations,
        "evidence": evidence,
    }


def build_nodes(scene_id: str, object_rows: list[dict[str, str]], geometry: dict[str, Any]) -> list[dict[str, Any]]:
    nodes = []
    for row in sorted(object_rows, key=lambda x: int(x.get("object_id") or 0)):
        node_id = row["node_id"]
        label = row["label"]
        nodes.append({
            "node_id": node_id,
            "object_id": int(row.get("object_id") or 0),
            "native_scene_id": row.get("native_scene_id"),
            "native_feature_key": row.get("native_feature_key"),
            "label": label,
            "is_functional_part_like": is_functional_part_label(label),
            "point_annotation": {
                "source_file": "annotations/openfungraph/SceneFun3D.annotations.json",
                "source_lookup": {"scene_id": scene_id, "annot_id": node_id},
                "n_point_indices": int(row.get("n_point_indices") or 0),
                "has_point_segment": row.get("has_point_segment") == "True",
            },
            "geometry": geometry.get(scene_id, {}).get(node_id, {}),
            "modality": {
                "has_record_camera": row.get("has_record_camera") == "True",
                "has_bbox_geometry": row.get("has_bbox_geometry") == "True",
                "has_point_feature": row.get("has_point_feature") == "True",
                "has_image_feature": row.get("has_image_feature") == "True",
                "object_full_ready": row.get("object_full_ready") == "True",
            },
        })
    return nodes


def build_functional_relations(scene_id: str, relations: list[dict[str, Any]], labels_by_node: dict[str, str]) -> list[dict[str, Any]]:
    out = []
    for rel in relations:
        if str(rel.get("scene_id")) != str(scene_id):
            continue
        first = str(rel.get("first_node_annot_id"))
        second = str(rel.get("second_node_annot_id"))
        relation = str(rel.get("description"))
        out.append({
            "relation_id": rel.get("relation_id"),
            "first_node_id": first,
            "first_label": labels_by_node.get(first),
            "relation": relation,
            "second_node_id": second,
            "second_label": labels_by_node.get(second),
            "edge_id": f"{first}|{relation}|{second}",
            "annotation_source": "openfungraph_scenefun3d_relation",
        })
    return sorted(out, key=lambda r: (r["relation"], r["first_label"] or "", r["second_label"] or "", r["first_node_id"]))


def summarize_frames(frames: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "n_frames": len(frames),
        "n_rgb": sum(bool(row.get("has_rgb")) for row in frames),
        "n_depth": sum(bool(row.get("has_depth")) for row in frames),
        "n_intrinsics": sum(bool(row.get("has_intrinsics")) for row in frames),
        "capture_ids": sorted({row.get("capture_id") for row in frames}),
    }


def build_scene_packages(inputs: dict[str, Any]) -> list[dict[str, Any]]:
    objects_by_scene: dict[str, list[dict[str, str]]] = defaultdict(list)
    captures_by_scene: dict[str, list[dict[str, str]]] = defaultdict(list)
    frames_by_scene: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in inputs["objects"]:
        objects_by_scene[str(row["scene_id"])].append(row)
    for row in inputs["captures"]:
        captures_by_scene[str(row["scene_id"])].append(row)
    for row in inputs["frames"]:
        frames_by_scene[str(row["scene_id"])].append(row)

    scene_manifest = []
    for scene_id in sorted(objects_by_scene):
        nodes = build_nodes(scene_id, objects_by_scene[scene_id], inputs["geometry"])
        labels_by_node = {node["node_id"]: node["label"] for node in nodes}
        relations = build_functional_relations(scene_id, inputs["relations"], labels_by_node)
        frames = sorted(frames_by_scene.get(scene_id, []), key=lambda r: (str(r.get("capture_id")), str(r.get("frame_stem"))))
        captures = sorted(captures_by_scene.get(scene_id, []), key=lambda r: str(r.get("capture_id")))
        scene_ready = inputs["readiness"]["scene_ready"].get(scene_id, {})
        visible_nodes = [node for node in nodes if node["modality"]["has_record_camera"] or node["modality"]["has_image_feature"]]
        scene_dir = RELEASE_DIR / "scenes" / scene_id
        write_jsonl(scene_dir / "frames.jsonl", frames)
        scene_package = {
            "scene_id": scene_id,
            "split": captures[0].get("split") if captures else None,
            "scene_asset": {
                "laser_scan_rel_path": captures[0].get("laser_scan_rel_path") if captures else None,
                "laser_scan_exists": all(row.get("laser_scan_exists") == "True" for row in captures),
            },
            "dataset": {
                "frame_index_rel_path": f"scenes/{scene_id}/frames.jsonl",
                "frame_summary": summarize_frames(frames),
                "captures": [
                    {
                        "capture_id": row.get("capture_id"),
                        "capture_rel_dir": row.get("capture_rel_dir"),
                        "trajectory_rel_paths": row.get("trajectory_rel_paths"),
                        "n_rgb_depth_intrinsic_triplets": int(row.get("n_rgb_depth_intrinsic_triplets") or 0),
                        "capture_full_ready": row.get("capture_full_ready") == "True",
                    }
                    for row in captures
                ],
            },
            "node_list": nodes,
            "object_metadata": {
                "format_note": "Each exported candidate is represented as one node. Functional parts are explicit nodes; parent-child hierarchy is not asserted unless present in source labels.",
                "n_nodes": len(nodes),
                "n_functional_part_like_nodes": sum(node["is_functional_part_like"] for node in nodes),
                "labels": sorted({node["label"] for node in nodes}),
            },
            "annotations_aggregated": {
                "format_note": "Point indices are not duplicated here; use source_file/source_lookup under each node.point_annotation.",
                "source_file": "annotations/openfungraph/SceneFun3D.annotations.json",
                "n_nodes_with_point_segments": sum(node["point_annotation"]["has_point_segment"] for node in nodes),
            },
            "functional_relations": relations,
            "visible": {
                "definition": "visible-subset analogue based on object record-camera or image-feature availability",
                "node_ids": [node["node_id"] for node in visible_nodes],
                "visibility_stats": {
                    "n_visible_nodes": len(visible_nodes),
                    "n_total_nodes": len(nodes),
                    "visible_ratio": round(len(visible_nodes) / len(nodes), 6) if nodes else 0,
                },
            },
            "readiness": {
                "full_scene_ready": bool(scene_ready.get("full_scene_ready")),
                "n_rgb_depth_intrinsic_triplets": int(scene_ready.get("n_rgb_depth_intrinsic_triplets") or 0),
                "funthor_style_raw_modalities_present": all([
                    captures,
                    all(row.get("has_rgb") == "True" for row in captures),
                    all(row.get("has_depth") == "True" for row in captures),
                    all(row.get("has_intrinsics") == "True" for row in captures),
                    all(row.get("has_trajectory") == "True" for row in captures),
                    all(row.get("laser_scan_exists") == "True" for row in captures),
                ]),
            },
        }
        write_json(scene_dir / "scene.json", scene_package)
        scene_manifest.append({
            "scene_id": scene_id,
            "split": scene_package["split"],
            "scene_json": f"scenes/{scene_id}/scene.json",
            "frames_jsonl": f"scenes/{scene_id}/frames.jsonl",
            "n_nodes": len(nodes),
            "n_functional_part_like_nodes": scene_package["object_metadata"]["n_functional_part_like_nodes"],
            "n_functional_relations": len(relations),
            "n_frames": len(frames),
            "full_scene_ready": scene_package["readiness"]["full_scene_ready"],
        })
    return scene_manifest


def build_splits(evidence: dict[str, Any]) -> dict[str, Any]:
    split_summary = {}
    for name, src in QUERY_SPLITS.items():
        rows = read_jsonl(src)
        enriched = []
        for row in rows:
            if "query_id" in row:
                rel = classify_relation(row)
                ev = evidence.get(row["query_id"], {})
                row = dict(row)
                row["functional_taxonomy"] = rel
                row["visual_evidence"] = {
                    "visual_evidence_ready": bool(ev.get("visual_evidence_ready")),
                    "evidence_tier": ev.get("evidence_tier") or row.get("perception_evidence_tier"),
                    "primary_visual_rel_path": ev.get("primary_visual_rel_path"),
                    "has_depth_tested_rgbd_crop": bool(ev.get("has_depth_tested_rgbd_crop") or row.get("has_depth_tested_rgbd_crop")),
                }
            enriched.append(row)
        dst = RELEASE_DIR / "splits" / f"{name}.jsonl"
        write_jsonl(dst, enriched)
        split_summary[name] = {
            "source_rel_path": str(src.relative_to(EXPORT_DIR)),
            "release_rel_path": str(dst.relative_to(RELEASE_DIR)),
            "n_rows": len(enriched),
            "paper_use_allowed": not name.startswith("expansion_"),
        }
    return split_summary


def write_dataset_level_files(scene_manifest: list[dict[str, Any]], split_summary: dict[str, Any], inputs: dict[str, Any]) -> None:
    labels = sorted({row["label"] for row in inputs["objects"]})
    functional_labels = sorted({label for label in labels if is_functional_part_label(label)})
    relation_counter = Counter(str(rel.get("description")) for rel in inputs["relations"])
    write_json(RELEASE_DIR / "dataset_unique_labels.json", labels)
    write_json(RELEASE_DIR / "dataset_functional_labels.json", functional_labels)
    write_json(RELEASE_DIR / "dataset_unique_relations.json", sorted(relation_counter))
    write_json(RELEASE_DIR / "annotation_rules" / "functional_relation_taxonomy.json", {
        "status": "funthor_inspired_taxonomy_ready",
        "source_inspiration": "leggedrobotics/funthor-dataset annotation_rules/functional_relations_config.json",
        "categories": {
            "object_object_affordance": "Functional relation between two whole-object-like nodes.",
            "part_object_operation": "Functional part-like target operates, opens, adjusts, switches, presses, pulls, or controls an anchor object.",
            "proximity_dependent_relation": "Relation whose plausibility depends on spatial proximity or shared physical channel such as water/power.",
            "ambiguous_one_to_one_assignment": "Same-label functional parts require global scene/cardinality reasoning, e.g. knob-to-appliance assignment.",
        },
        "functional_part_labels": functional_labels,
        "relation_counts": dict(sorted(relation_counter.items())),
    })
    manifest = {
        "status": "fungraph_full_modality_release_ready",
        "release_version": "fungraph_full_modality_release_v1_20260619",
        "design_reference": "FunTHOR-style layout: dataset-level label/relation files, annotation rules, query splits, and one scene package per scene with RGB-D-camera-pointcloud references.",
        "raw_asset_policy": "Large RGB/depth/pointcloud files are referenced by relative path and are not duplicated into this release folder.",
        "source_export": str(EXPORT_DIR),
        "counts": {
            "n_scenes": len(scene_manifest),
            "n_candidate_nodes": sum(row["n_nodes"] for row in scene_manifest),
            "n_functional_part_like_nodes": sum(row["n_functional_part_like_nodes"] for row in scene_manifest),
            "n_functional_relations": sum(row["n_functional_relations"] for row in scene_manifest),
            "n_frames": sum(row["n_frames"] for row in scene_manifest),
            "n_unique_labels": len(labels),
            "n_unique_functional_labels": len(functional_labels),
            "n_unique_relations": len(relation_counter),
        },
        "canonical_structure": {
            "dataset_manifest": "dataset_manifest.json",
            "labels": "dataset_unique_labels.json",
            "functional_labels": "dataset_functional_labels.json",
            "relations": "dataset_unique_relations.json",
            "annotation_rules": "annotation_rules/functional_relation_taxonomy.json",
            "splits": "splits/*.jsonl",
            "scenes": "scenes/<scene_id>/scene.json + frames.jsonl",
        },
        "split_summary": split_summary,
        "scene_manifest": scene_manifest,
        "remaining_semantic_gaps": [
            "Object-part parent hierarchy is not fully asserted; functional parts are explicit nodes with source annotation pointers.",
            "Visible subset is an explicit release field derived from record-camera/image-feature coverage, not a separate sensor ray-tracing table.",
            "Expansion splits remain paper-disabled until human wording review, visual evidence spot-check, and Dennis signoff.",
        ],
    }
    write_json(RELEASE_DIR / "dataset_manifest.json", manifest)

    readme = f"""# FunGraph Full-Modality Release v1

This is the human-facing benchmark package for the 3DGraphLLM+ multimodal functional-reasoning work.
It is organized after the FunTHOR release pattern, but uses compact metadata and relative raw-asset pointers instead of duplicating large files.

## Structure

```text
fungraph_full_modality_release_v1/
  dataset_manifest.json
  dataset_unique_labels.json
  dataset_functional_labels.json
  dataset_unique_relations.json
  annotation_rules/functional_relation_taxonomy.json
  splits/*.jsonl
  scenes/<scene_id>/
    scene.json
    frames.jsonl
```

## Current Counts

- Scenes: {manifest['counts']['n_scenes']}
- Candidate nodes: {manifest['counts']['n_candidate_nodes']}
- Functional part-like nodes: {manifest['counts']['n_functional_part_like_nodes']}
- Functional relations: {manifest['counts']['n_functional_relations']}
- RGB-D-camera frame rows: {manifest['counts']['n_frames']}
- Unique labels: {manifest['counts']['n_unique_labels']}
- Unique relation strings: {manifest['counts']['n_unique_relations']}

## What To Read First

1. `dataset_manifest.json` for global counts, scene paths, split paths, and remaining semantic gaps.
2. `scenes/<scene_id>/scene.json` for one scene's nodes, functional relations, modality readiness, and visible subset analogue.
3. `splits/functional_500.jsonl` and `splits/human_133.jsonl` for current frozen eval queries.
4. `splits/expansion_functional_116_candidates.jsonl` only as paper-disabled candidates requiring human/Dennis signoff.

## Boundary

This package is a clean release view over the existing export. It does not move or copy raw RGB-D images, depth frames, laser scans, or the full OpenFunGraph point-index arrays. Those are referenced by relative paths and source pointers.
"""
    (RELEASE_DIR / "README.md").write_text(readme, encoding="utf-8")


def main() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True)
    inputs = load_inputs()
    scene_manifest = build_scene_packages(inputs)
    split_summary = build_splits(inputs["evidence"])
    write_dataset_level_files(scene_manifest, split_summary, inputs)
    print(json.dumps({
        "status": "fungraph_full_modality_release_ready",
        "release_dir": str(RELEASE_DIR.relative_to(EXPORT_DIR)),
        "n_scenes": len(scene_manifest),
        "n_files": sum(1 for _ in RELEASE_DIR.rglob("*") if _.is_file()),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
