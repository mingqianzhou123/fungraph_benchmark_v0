#!/usr/bin/env python3
"""Build a FunTHOR-style benchmark quality layer.

The goal is not to copy FunTHOR's synthetic annotation process. It is to make
our export auditable against the same standard of multimodal evidence:
scene RGB-D-camera coverage, object/part-like geometry, visible evidence, and
functional-relation taxonomy.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = EXPORT_DIR / "benchmark_quality_v2"
EXPANSION_DIR = EXPORT_DIR / "expansion_v1"
RELATION_EVIDENCE_DIR = EXPORT_DIR / "relation_conditioned_evidence"

QUERY_FILES = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
    "expansion_functional_116": EXPANSION_DIR / "final_candidates" / "functional_balanced_116_frozen_candidate.jsonl",
}

MINIMAL_PAIR_FILES = {
    "minimal_pairs_28": EXPORT_DIR / "minimal_pairs_28_eval.jsonl",
    "expansion_minimal_pairs_60": EXPANSION_DIR / "final_candidates" / "minimal_pairs_expanded_60_frozen_candidate.jsonl",
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

FUNTHOR_RELATION_REFERENCE = {
    "source": "leggedrobotics/funthor-dataset annotation_rules/functional_relations_config.json",
    "relation_families": {
        "exact_match_affordance": [
            "can slice or cut",
            "can shred and chop",
            "fill with water",
            "hold and support",
            "operate and control",
            "switch on or off",
            "water and nourish",
        ],
        "proximity_dependent_relation": [
            "blocks water from leaving",
            "cover or uncover",
            "run water into",
        ],
        "part_object_operation": [
            "key in time and start",
            "press to start brewing",
            "press to start toasting",
            "pull to open",
            "push down to start toasting",
            "push to flush toilet",
            "turn on/off",
        ],
        "manual_or_ambiguous_assignment": [
            "stove knob to stove burner turn on/off",
        ],
    },
}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


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


def norm_text(value: Any) -> str:
    return str(value or "").strip().lower()


def relation_from_row(row: dict[str, Any]) -> str:
    edge = (row.get("supporting_edge_ids") or [None])[0]
    _, relation, _ = parse_edge(edge)
    return relation or norm_text(row.get("relation"))


def is_functional_part_label(label: str) -> bool:
    label = norm_text(label)
    return label in FUNCTIONAL_PART_LABELS or any(part in label for part in ["handle", "knob", "switch", "button", "faucet"])


def classify_relation(row: dict[str, Any]) -> dict[str, Any]:
    relation = norm_text(relation_from_row(row))
    target_label = norm_text(row.get("target_label") or (row.get("target_labels") or [""])[0])
    anchor_label = norm_text(row.get("anchor_label"))
    tags = set(row.get("difficulty_tags") or [])
    same_label = "same_label_disambiguation" in tags or int(row.get("num_same_label_distractors") or 0) > 0

    if any(term in relation for term in ["water flow", "fill with water", "run water", "provide power"]):
        primary = "proximity_dependent_relation"
        matching_strategy = "proximity_based"
    elif is_functional_part_label(target_label) and any(
        term in relation
        for term in ["open", "close", "adjust", "turn on", "turn off", "flush", "control", "rotate", "press", "pull"]
    ):
        primary = "part_object_operation"
        matching_strategy = "part_based"
    elif any(term in relation for term in ["control", "slice", "cut", "support", "operate"]):
        primary = "object_object_affordance"
        matching_strategy = "exact_match_affordance"
    else:
        primary = "object_object_affordance"
        matching_strategy = "exact_match_affordance"

    if same_label and target_label in {"knob", "handle", "remote", "light switch", "button", "button / knob"}:
        ambiguity = "ambiguous_one_to_one_assignment"
        requires_cardinality_reasoning = target_label in {"knob", "handle", "remote", "button", "button / knob"}
    elif same_label:
        ambiguity = "same_label_visual_disambiguation"
        requires_cardinality_reasoning = False
    else:
        ambiguity = "not_same_label_ambiguous"
        requires_cardinality_reasoning = False

    return {
        "relation": relation,
        "target_label": target_label,
        "anchor_label": anchor_label,
        "funthor_style_category": primary,
        "funthor_style_matching_strategy": matching_strategy,
        "ambiguity_type": ambiguity,
        "requires_cardinality_or_global_scene_reasoning": requires_cardinality_reasoning,
        "is_functional_part_target": is_functional_part_label(target_label),
        "taxonomy_version": "funthor_style_v2_20260619",
    }


def load_object_manifest() -> tuple[list[dict[str, str]], dict[tuple[str, str], dict[str, str]]]:
    path = EXPORT_DIR / "full_object_modality_manifest.csv"
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    by_key = {(row["scene_id"], row["node_id"]): row for row in rows}
    return rows, by_key


def build_modality_audit() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    readiness = read_json(EXPORT_DIR / "full_multimodal_readiness.json")
    object_rows, _ = load_object_manifest()
    capture_rows: list[dict[str, str]]
    with (EXPORT_DIR / "full_scene_capture_manifest.csv").open("r", encoding="utf-8", newline="") as f:
        capture_rows = list(csv.DictReader(f))

    by_scene_objects: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in object_rows:
        by_scene_objects[row["scene_id"]].append(row)

    by_scene_captures: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in capture_rows:
        by_scene_captures[row["scene_id"]].append(row)

    rows = []
    for scene_id in sorted(readiness["scene_ready"]):
        scene_ready = readiness["scene_ready"][scene_id]
        objects = by_scene_objects.get(scene_id, [])
        captures = by_scene_captures.get(scene_id, [])
        n_functional_parts = sum(is_functional_part_label(row.get("label", "")) for row in objects)
        n_visible_like = sum(row.get("has_record_camera") == "True" or row.get("has_image_feature") == "True" for row in objects)
        rows.append({
            "scene_id": scene_id,
            "n_captures": scene_ready["n_captures"],
            "n_rgb_depth_camera_triplets": scene_ready["n_rgb_depth_intrinsic_triplets"],
            "has_rgb": all(row.get("has_rgb") == "True" for row in captures),
            "has_depth": all(row.get("has_depth") == "True" for row in captures),
            "has_intrinsics": all(row.get("has_intrinsics") == "True" for row in captures),
            "has_camera_trajectory": all(row.get("has_trajectory") == "True" for row in captures),
            "has_scene_pointcloud": all(row.get("laser_scan_exists") == "True" for row in captures),
            "n_candidate_objects": len(objects),
            "n_functional_part_like_nodes": n_functional_parts,
            "all_objects_have_point_segments": all(row.get("has_point_segment") == "True" for row in objects),
            "all_objects_have_bbox_geometry": all(row.get("has_bbox_geometry") == "True" for row in objects),
            "all_objects_have_record_camera": all(row.get("has_record_camera") == "True" for row in objects),
            "all_objects_have_point_features": all(row.get("has_point_feature") == "True" for row in objects),
            "all_objects_have_image_features": all(row.get("has_image_feature") == "True" for row in objects),
            "visible_subset_equivalent": "implicit_record_camera_and_image_feature" if n_visible_like == len(objects) else "partial",
            "object_part_hierarchy_equivalent": "functional_part_like_nodes_without_explicit_parent_hierarchy",
            "funthor_style_full_ready": bool(scene_ready["full_scene_ready"]) and n_functional_parts > 0,
        })

    summary = {
        "status": "funthor_style_full_modality_audit_ready",
        "funthor_reference": {
            "scenes": 12,
            "rgbd_frames": 720,
            "nodes": 621,
            "functional_edges": 164,
            "modalities": ["rgb", "depth", "camera_pose", "intrinsics", "pointcloud", "object_metadata", "part_annotations", "functional_relations", "visible_subset"],
        },
        "our_export": {
            "scenes": readiness["n_scenes"],
            "rgbd_camera_triplets": readiness["n_frame_rgbd_camera_triplets"],
            "candidate_objects": readiness["n_export_candidate_objects"],
            "scenes_full_raw_ready": readiness["n_scenes_full_ready"],
            "all_scenes_full_raw_ready": readiness["all_scenes_full_ready"],
            "scenes_with_functional_part_like_nodes": sum(row["n_functional_part_like_nodes"] > 0 for row in rows),
            "scenes_funthor_style_full_ready": sum(row["funthor_style_full_ready"] for row in rows),
            "object_part_hierarchy_status": "partial: functional parts are explicit candidate nodes, but parent-child hierarchy is not yet a first-class exported table",
            "visible_subset_status": "implicit: record-camera/image-feature coverage exists per object; no separate visible/node_list.pkl analogue",
        },
    }
    return rows, summary


def build_query_taxonomy(object_by_key: dict[tuple[str, str], dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    evidence_rows = {
        row.get("query_id"): row
        for row in read_jsonl(RELATION_EVIDENCE_DIR / "full_perception_evidence_index.jsonl")
        if row.get("query_id")
    }
    all_rows = []
    split_counts = {}
    for split_name, path in QUERY_FILES.items():
        rows = read_jsonl(path)
        split_counts[split_name] = len(rows)
        for row in rows:
            taxonomy = classify_relation(row)
            scene_id = row.get("scene_id")
            target_id = row.get("target_node_id") or (row.get("target_node_ids") or [""])[0]
            anchor_id = row.get("anchor_node_id")
            target_manifest = object_by_key.get((str(scene_id), str(target_id)), {})
            anchor_manifest = object_by_key.get((str(scene_id), str(anchor_id)), {})
            evidence = evidence_rows.get(row.get("query_id"), {})
            all_rows.append({
                "query_id": row.get("query_id"),
                "split_name": split_name,
                "scene_id": scene_id,
                "target_node_id": target_id,
                "anchor_node_id": anchor_id,
                "target_label": row.get("target_label") or (row.get("target_labels") or [""])[0],
                "anchor_label": row.get("anchor_label"),
                "relation": taxonomy["relation"],
                "funthor_style_category": taxonomy["funthor_style_category"],
                "funthor_style_matching_strategy": taxonomy["funthor_style_matching_strategy"],
                "ambiguity_type": taxonomy["ambiguity_type"],
                "requires_cardinality_or_global_scene_reasoning": taxonomy["requires_cardinality_or_global_scene_reasoning"],
                "is_functional_part_target": taxonomy["is_functional_part_target"],
                "has_rgbd_camera_evidence": bool(evidence.get("has_rgbd_evidence") or evidence.get("has_depth_tested_rgbd_crop") or row.get("has_depth_tested_rgbd_crop")),
                "perception_evidence_tier": evidence.get("evidence_tier") or row.get("perception_evidence_tier"),
                "target_has_point_segment": target_manifest.get("has_point_segment") == "True",
                "target_has_bbox_geometry": target_manifest.get("has_bbox_geometry") == "True",
                "target_has_record_camera": target_manifest.get("has_record_camera") == "True",
                "anchor_has_point_segment": anchor_manifest.get("has_point_segment") == "True" if anchor_id else None,
                "supporting_edge_ids": row.get("supporting_edge_ids") or [],
                "paper_use_allowed": bool(row.get("paper_use_allowed", True)),
                "human_review_required": bool(row.get("human_review_required", False)),
            })

    category_counts = Counter(row["funthor_style_category"] for row in all_rows)
    matching_counts = Counter(row["funthor_style_matching_strategy"] for row in all_rows)
    ambiguity_counts = Counter(row["ambiguity_type"] for row in all_rows)
    relation_counts = Counter(row["relation"] for row in all_rows)
    summary = {
        "status": "funthor_style_relation_taxonomy_ready",
        "taxonomy_version": "funthor_style_v2_20260619",
        "reference": FUNTHOR_RELATION_REFERENCE,
        "n_queries_indexed": len(all_rows),
        "split_counts": split_counts,
        "category_counts": dict(sorted(category_counts.items())),
        "matching_strategy_counts": dict(sorted(matching_counts.items())),
        "ambiguity_counts": dict(sorted(ambiguity_counts.items())),
        "n_unique_relations": len(relation_counts),
        "top_relations": [{"relation": rel, "n": n} for rel, n in relation_counts.most_common(25)],
        "paper_use_note": "Taxonomy is deterministic and auditable; expansion candidates still require human wording/evidence signoff before paper use.",
    }
    return all_rows, summary


def build_pair_taxonomy(query_taxonomy: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_query = {row["query_id"]: row for row in query_taxonomy}
    pair_rows = []
    split_counts = {}
    for split_name, path in MINIMAL_PAIR_FILES.items():
        rows = read_jsonl(path)
        split_counts[split_name] = len(rows)
        for pair in rows:
            qa = by_query.get(pair.get("query_a_id"), {})
            qb = by_query.get(pair.get("query_b_id"), {})
            categories = sorted({qa.get("funthor_style_category"), qb.get("funthor_style_category")} - {None})
            ambiguity = sorted({qa.get("ambiguity_type"), qb.get("ambiguity_type")} - {None})
            pair_rows.append({
                "pair_id": pair.get("pair_id"),
                "split_name": split_name,
                "scene_id": pair.get("scene_id"),
                "query_a_id": pair.get("query_a_id"),
                "query_b_id": pair.get("query_b_id"),
                "changed_factor": pair.get("changed_factor"),
                "funthor_style_categories": categories,
                "ambiguity_types": ambiguity,
                "requires_cardinality_or_global_scene_reasoning": bool(
                    qa.get("requires_cardinality_or_global_scene_reasoning")
                    or qb.get("requires_cardinality_or_global_scene_reasoning")
                    or "same_label" in norm_text(pair.get("changed_factor"))
                ),
                "pair_role": "primary_minimal_pair" if split_name == "minimal_pairs_28" else "expansion_candidate_needs_human_review",
                "why_hard": pair.get("why_hard"),
            })
    summary = {
        "status": "funthor_style_minimal_pair_taxonomy_ready",
        "n_pairs_indexed": len(pair_rows),
        "split_counts": split_counts,
        "category_counts": dict(sorted(Counter(cat for row in pair_rows for cat in row["funthor_style_categories"]).items())),
        "ambiguity_counts": dict(sorted(Counter(amb for row in pair_rows for amb in row["ambiguity_types"]).items())),
        "n_pairs_requiring_cardinality_or_global_scene_reasoning": sum(row["requires_cardinality_or_global_scene_reasoning"] for row in pair_rows),
    }
    return pair_rows, summary


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0]) if rows else []
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def write_status(summary: dict[str, Any]) -> None:
    status = f"""# FunTHOR-Style Benchmark Quality Layer

Status: `{summary["status"]}`

This layer aligns the FunGraph/3DGraphLLM export with the evidence standard used by FunTHOR:
RGB-D-camera coverage, scene pointclouds, object/part-like geometry, visible evidence, and
typed functional relations.

## What is now explicit

- `funthor_style_modality_audit.csv`: scene-level RGB, depth, pose/trajectory, intrinsics, pointcloud, object geometry, image/point feature coverage.
- `query_relation_taxonomy_index.jsonl`: every functional query plus expansion candidate is tagged with a FunTHOR-style relation category.
- `minimal_pair_taxonomy_index.jsonl`: primary and expansion minimal pairs are tagged with ambiguity and global-reasoning requirements.
- `relation_taxonomy_v2.json`: deterministic taxonomy summary and FunTHOR reference relation families.

## Current benchmark status

- Scenes: {summary["full_modality_summary"]["our_export"]["scenes"]} total, {summary["full_modality_summary"]["our_export"]["scenes_full_raw_ready"]} full raw-ready.
- RGB-D-camera triplets: {summary["full_modality_summary"]["our_export"]["rgbd_camera_triplets"]}.
- Candidate objects / functional parts: {summary["full_modality_summary"]["our_export"]["candidate_objects"]} objects, {summary["full_modality_summary"]["our_export"]["scenes_with_functional_part_like_nodes"]} scenes with functional part-like nodes.
- Functional query rows indexed: {summary["relation_taxonomy_summary"]["n_queries_indexed"]}.
- Minimal-pair rows indexed: {summary["minimal_pair_taxonomy_summary"]["n_pairs_indexed"]}.

## Remaining gap to true FunTHOR parity

The raw modality stack is complete. The two remaining semantic gaps are:

1. Export object-part hierarchy as a first-class table, not only as functional part-like nodes.
2. Export an explicit visible subset table, rather than relying on record-camera/image-feature coverage.

These are now tracked as benchmark quality requirements rather than hidden assumptions.
"""
    (OUT_DIR / "FUNTHOR_STYLE_BENCHMARK_STATUS.md").write_text(status, encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    modality_rows, modality_summary = build_modality_audit()
    object_rows, object_by_key = load_object_manifest()
    query_taxonomy, relation_summary = build_query_taxonomy(object_by_key)
    pair_taxonomy, pair_summary = build_pair_taxonomy(query_taxonomy)

    full_summary = {
        "status": "funthor_style_quality_layer_ready",
        "built_from": {
            "query_files": {name: str(path.relative_to(EXPORT_DIR)) for name, path in QUERY_FILES.items()},
            "minimal_pair_files": {name: str(path.relative_to(EXPORT_DIR)) for name, path in MINIMAL_PAIR_FILES.items()},
            "object_manifest": "full_object_modality_manifest.csv",
            "scene_capture_manifest": "full_scene_capture_manifest.csv",
        },
        "full_modality_summary": modality_summary,
        "relation_taxonomy_summary": relation_summary,
        "minimal_pair_taxonomy_summary": pair_summary,
        "canonical_files": [
            "FUNTHOR_STYLE_BENCHMARK_STATUS.md",
            "funthor_style_readiness.json",
            "funthor_style_modality_audit.csv",
            "relation_taxonomy_v2.json",
            "query_relation_taxonomy_index.jsonl",
            "minimal_pair_taxonomy_index.jsonl",
        ],
    }

    write_csv(OUT_DIR / "funthor_style_modality_audit.csv", modality_rows)
    write_jsonl(OUT_DIR / "query_relation_taxonomy_index.jsonl", query_taxonomy)
    write_jsonl(OUT_DIR / "minimal_pair_taxonomy_index.jsonl", pair_taxonomy)
    write_json(OUT_DIR / "relation_taxonomy_v2.json", relation_summary)
    write_json(OUT_DIR / "funthor_style_readiness.json", full_summary)
    write_status(full_summary)

    print(json.dumps({
        "status": full_summary["status"],
        "n_modality_scene_rows": len(modality_rows),
        "n_query_taxonomy_rows": len(query_taxonomy),
        "n_minimal_pair_taxonomy_rows": len(pair_taxonomy),
        "output_dir": str(OUT_DIR.relative_to(EXPORT_DIR)),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
