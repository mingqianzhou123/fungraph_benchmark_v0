#!/usr/bin/env python3
"""Build the 3DGraphLLM functional evaluation export.

This script is the only supported way to regenerate the export files in this
folder. It does not modify frozen benchmark sources.
"""

from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

BENCHMARK_ROOT = Path(__file__).resolve().parents[3]
EXPORT_DIR = Path(__file__).resolve().parents[1]

QUERY_INDEX = BENCHMARK_ROOT / "queries" / "all_queries_index.jsonl"
FEATURE_INDEX = BENCHMARK_ROOT / "multimodal_extension" / "feature_index.json"
RAW_ASSET_MANIFEST = BENCHMARK_ROOT / "raw_assets" / "scenefun3d_raw_asset_manifest.csv"
GEOMETRY_COVERAGE = BENCHMARK_ROOT / "multimodal_extension" / "geometry_coverage_report.csv"
P0_AVAILABILITY = BENCHMARK_ROOT / "multimodal_extension" / "perception" / "p0_raw_modality_availability.csv"
HUMAN_DIR = BENCHMARK_ROOT / "human_annotations" / "functional_queries_v1"
HUMAN_FUNCTIONAL = HUMAN_DIR / "functional_queries_v1.jsonl"
MINIMAL_PAIRS = HUMAN_DIR / "minimal_pairs_v1.jsonl"
LONG_RANGE = HUMAN_DIR / "long_range_stress_queries_v1.jsonl"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def write_json(path: Path, obj: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def load_feature_index() -> tuple[dict[str, Any], dict[str, list[str]]]:
    data = json.loads(FEATURE_INDEX.read_text(encoding="utf-8"))
    candidates: dict[str, list[str]] = defaultdict(list)
    for key, item in data.items():
        scene_id = str(item["scene_id"])
        node_id = str(item["node_id"])
        candidates[scene_id].append(node_id)
    return data, {scene: sorted(nodes) for scene, nodes in candidates.items()}


def load_coverage_rows() -> dict[str, dict[str, str]]:
    if not GEOMETRY_COVERAGE.exists():
        return {}
    with GEOMETRY_COVERAGE.open("r", encoding="utf-8", newline="") as f:
        return {row["query_id"]: row for row in csv.DictReader(f)}


def load_p0_rows() -> dict[str, dict[str, str]]:
    if not P0_AVAILABILITY.exists():
        return {}
    with P0_AVAILABILITY.open("r", encoding="utf-8", newline="") as f:
        return {row["scene_id"]: row for row in csv.DictReader(f)}


def load_scene_asset_rows() -> dict[str, dict[str, str]]:
    rows: dict[str, dict[str, str]] = {}
    if RAW_ASSET_MANIFEST.exists():
        with RAW_ASSET_MANIFEST.open("r", encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                if row.get("asset_type") == "laser_scan_ply" and row.get("scene_id"):
                    rows[row["scene_id"]] = row
    return rows


def bool_from_csv(value: Any) -> bool:
    return str(value).strip().lower() == "true"


def derive_generated_tags(row: dict[str, Any], coverage: dict[str, str] | None) -> list[str]:
    tags = ["functional_relation"]
    if coverage:
        try:
            same_label_count = int(coverage.get("same_label_count") or 0)
        except ValueError:
            same_label_count = 0
        if same_label_count > 1 or bool_from_csv(coverage.get("has_same_label_distractor")):
            tags.append("same_label_disambiguation")
    if row.get("anchor_node_id"):
        tags.append("endpoint_ambiguity")
    return sorted(set(tags))


def normalize_query(
    row: dict[str, Any],
    *,
    export_source: str,
    candidates_by_scene: dict[str, list[str]],
    coverage_by_query: dict[str, dict[str, str]],
) -> dict[str, Any]:
    scene_id = str(row["scene_id"])
    target_node_ids = row.get("target_node_ids")
    if target_node_ids is None:
        target_node_ids = [row.get("target_node_id")]
    target_node_ids = [str(x) for x in target_node_ids if x]

    supporting_edge_ids = row.get("supporting_edge_ids")
    if supporting_edge_ids is None and row.get("supporting_edge_id"):
        supporting_edge_ids = [row.get("supporting_edge_id")]
    supporting_edge_ids = [str(x) for x in (supporting_edge_ids or []) if x]

    query_text = row.get("query") or row.get("query_text")
    target_labels = row.get("target_labels")
    if target_labels is None and row.get("target_label"):
        target_labels = [row.get("target_label")]
    target_labels = [str(x) for x in (target_labels or []) if x]

    coverage = coverage_by_query.get(str(row["query_id"]))
    difficulty_tags = row.get("difficulty_tags") or derive_generated_tags(row, coverage)
    candidate_node_ids = candidates_by_scene.get(scene_id, [])

    return {
        "query_id": str(row["query_id"]),
        "scene_id": scene_id,
        "split": row.get("split"),
        "dataset": row.get("dataset", "scenefun3d"),
        "query_type": row.get("query_type", "functional"),
        "query_text": query_text,
        "prompt": query_text,
        "target_node_ids": target_node_ids,
        "target_node_id": target_node_ids[0] if target_node_ids else None,
        "target_labels": target_labels,
        "target_label": target_labels[0] if target_labels else row.get("target_label"),
        "anchor_node_id": row.get("anchor_node_id"),
        "anchor_label": row.get("anchor_label"),
        "supporting_edge_ids": supporting_edge_ids,
        "candidate_node_ids": candidate_node_ids,
        "n_candidates": len(candidate_node_ids),
        "difficulty_tags": sorted(set(str(tag) for tag in difficulty_tags)),
        "source": export_source,
        "annotation_source": row.get("annotation_source") or row.get("source"),
        "is_label_only_solvable": row.get("is_label_only_solvable"),
        "num_same_label_distractors": row.get("num_same_label_distractors")
        if row.get("num_same_label_distractors") is not None
        else (int(coverage["same_label_count"]) - 1 if coverage and coverage.get("same_label_count") else None),
        "expected_failure_modes": row.get("expected_failure_modes", []),
        "geometry_cues": row.get("geometry_cues") or row.get("geometry_cues_used", []),
    }


def build_answer_key(*groups: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    answer_key: dict[str, dict[str, Any]] = {}
    for rows in groups:
        for row in rows:
            answer_key[row["query_id"]] = {
                "scene_id": row["scene_id"],
                "target_node_ids": row["target_node_ids"],
                "target_node_id": row["target_node_id"],
                "source": row["source"],
            }
    return answer_key


def build_node_mapping(feature_index: dict[str, Any]) -> dict[str, Any]:
    mapping: dict[str, Any] = {}
    for key, item in sorted(feature_index.items()):
        mapping[key] = {
            "scene_id": str(item["scene_id"]),
            "node_id": str(item["node_id"]),
            "graph_node_id": str(item["node_id"]),
            "feature_row": item.get("feature_row"),
            "has_bbox": bool(item.get("has_bbox")),
            "3dgraphllm_object_id": None,
            "mapping_status": "pending_native_3dgraphllm_asset_alignment",
        }
    return mapping


def write_candidate_objects(candidates_by_scene: dict[str, list[str]]) -> None:
    rows = [
        {
            "scene_id": scene_id,
            "candidate_node_ids": node_ids,
            "n_candidates": len(node_ids),
            "candidate_key_format": "{scene_id}/{node_id}",
        }
        for scene_id, node_ids in sorted(candidates_by_scene.items())
    ]
    write_jsonl(EXPORT_DIR / "candidate_objects.jsonl", rows)


def write_scene_asset_manifest(scene_assets: dict[str, dict[str, str]], p0_rows: dict[str, dict[str, str]]) -> None:
    scene_ids = sorted(set(scene_assets) | set(p0_rows))
    fields = [
        "scene_id",
        "split_hint",
        "laser_scan_ply",
        "image_projection_ready",
        "point_segment_ready",
        "bbox_only",
        "raw_modality_failure_reason",
    ]
    with (EXPORT_DIR / "scene_asset_manifest.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for scene_id in scene_ids:
            asset = scene_assets.get(scene_id, {})
            p0 = p0_rows.get(scene_id, {})
            writer.writerow(
                {
                    "scene_id": scene_id,
                    "split_hint": p0.get("split_hint") or asset.get("split"),
                    "laser_scan_ply": asset.get("source_path") or p0.get("source_raw_path", ""),
                    "image_projection_ready": p0.get("image_projection_ready", ""),
                    "point_segment_ready": p0.get("point_segment_ready", ""),
                    "bbox_only": p0.get("bbox_only", ""),
                    "raw_modality_failure_reason": p0.get("failure_reason", ""),
                }
            )


def count_tags(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        counts.update(row.get("difficulty_tags", []))
    return dict(sorted(counts.items()))


def main() -> None:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    feature_index, candidates_by_scene = load_feature_index()
    coverage_by_query = load_coverage_rows()
    p0_rows = load_p0_rows()
    scene_assets = load_scene_asset_rows()

    all_queries = read_jsonl(QUERY_INDEX)
    generated_functional_test = sorted(
        [
            row
            for row in all_queries
            if row.get("dataset") == "scenefun3d"
            and row.get("query_type") == "functional"
            and row.get("split") == "test"
        ],
        key=lambda row: str(row["query_id"]),
    )
    functional_500_source = generated_functional_test[:500]

    functional_500 = [
        normalize_query(
            row,
            export_source="generated_scenefun3d_functional_test",
            candidates_by_scene=candidates_by_scene,
            coverage_by_query=coverage_by_query,
        )
        for row in functional_500_source
    ]
    human_133 = [
        normalize_query(
            row,
            export_source="human_functional_v1",
            candidates_by_scene=candidates_by_scene,
            coverage_by_query=coverage_by_query,
        )
        for row in read_jsonl(HUMAN_FUNCTIONAL)
    ]
    long_range_50 = [
        normalize_query(
            row,
            export_source="human_long_range_v1",
            candidates_by_scene=candidates_by_scene,
            coverage_by_query=coverage_by_query,
        )
        for row in read_jsonl(LONG_RANGE)
    ]
    minimal_pairs = read_jsonl(MINIMAL_PAIRS)

    write_jsonl(EXPORT_DIR / "functional_500_eval.jsonl", functional_500)
    write_jsonl(EXPORT_DIR / "human_133_eval.jsonl", human_133)
    write_jsonl(EXPORT_DIR / "long_range_50_eval.jsonl", long_range_50)
    write_jsonl(EXPORT_DIR / "minimal_pairs_28_eval.jsonl", minimal_pairs)
    write_json(EXPORT_DIR / "answer_key.json", build_answer_key(functional_500, human_133, long_range_50))
    write_json(EXPORT_DIR / "node_id_mapping.json", build_node_mapping(feature_index))
    write_candidate_objects(candidates_by_scene)
    write_scene_asset_manifest(scene_assets, p0_rows)

    slice_metadata = {
        "functional_500": {
            "n": len(functional_500),
            "selection_policy": "SceneFun3D functional test split, sorted by query_id, first 500 rows",
            "difficulty_tag_counts": count_tags(functional_500),
            "scene_counts": dict(sorted(Counter(row["scene_id"] for row in functional_500).items())),
        },
        "human_133": {
            "n": len(human_133),
            "difficulty_tag_counts": count_tags(human_133),
            "scene_counts": dict(sorted(Counter(row["scene_id"] for row in human_133).items())),
        },
        "minimal_pairs_28": {
            "n": len(minimal_pairs),
            "changed_factor_counts": dict(sorted(Counter(row.get("changed_factor") for row in minimal_pairs).items())),
            "scene_counts": dict(sorted(Counter(row.get("scene_id") for row in minimal_pairs).items())),
        },
        "long_range_50": {
            "n": len(long_range_50),
            "difficulty_tag_counts": count_tags(long_range_50),
            "scene_counts": dict(sorted(Counter(row["scene_id"] for row in long_range_50).items())),
        },
    }
    write_json(EXPORT_DIR / "slice_metadata.json", slice_metadata)

    export_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_files": {
            "query_index": str(QUERY_INDEX.relative_to(BENCHMARK_ROOT)),
            "feature_index": str(FEATURE_INDEX.relative_to(BENCHMARK_ROOT)),
            "raw_asset_manifest": str(RAW_ASSET_MANIFEST.relative_to(BENCHMARK_ROOT)),
            "p0_availability": str(P0_AVAILABILITY.relative_to(BENCHMARK_ROOT)),
            "human_functional": str(HUMAN_FUNCTIONAL.relative_to(BENCHMARK_ROOT)),
            "minimal_pairs": str(MINIMAL_PAIRS.relative_to(BENCHMARK_ROOT)),
            "long_range": str(LONG_RANGE.relative_to(BENCHMARK_ROOT)),
        },
        "counts": {
            "functional_500_eval": len(functional_500),
            "human_133_eval": len(human_133),
            "minimal_pairs_28_eval": len(minimal_pairs),
            "long_range_50_eval": len(long_range_50),
            "candidate_scenes": len(candidates_by_scene),
            "candidate_nodes": sum(len(nodes) for nodes in candidates_by_scene.values()),
            "p0_image_projection_ready_scenes": sum(bool_from_csv(row.get("image_projection_ready")) for row in p0_rows.values()),
            "p0_point_segment_ready_scenes": sum(bool_from_csv(row.get("point_segment_ready")) for row in p0_rows.values()),
        },
    }
    write_json(EXPORT_DIR / "export_summary.json", export_summary)


if __name__ == "__main__":
    main()
