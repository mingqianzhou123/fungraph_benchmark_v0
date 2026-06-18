#!/usr/bin/env python3
# Build relation-conditioned evidence manifests for the FunGraph export.
# Data-layer only: no model inference, no large crop/PLY assets.

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = EXPORT_DIR / "relation_conditioned_evidence"
QUERY_FILES = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def stable_hash(text: str, n: int = 12) -> str:
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:n]


def parse_edge(edge: str) -> dict[str, str]:
    parts = str(edge).split("|")
    if len(parts) != 3:
        return {"source_node_id": "", "relation": str(edge), "target_node_id": ""}
    return {"source_node_id": parts[0], "relation": parts[1], "target_node_id": parts[2]}


def load_object_manifest() -> dict[tuple[str, str], dict[str, Any]]:
    out = {}
    with (EXPORT_DIR / "full_object_modality_manifest.csv").open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            out[(str(row["scene_id"]), str(row["node_id"]))] = row
    return out


def load_frame_index() -> dict[str, list[dict[str, Any]]]:
    by_scene = defaultdict(list)
    for row in read_jsonl(EXPORT_DIR / "full_scene_frame_index.jsonl"):
        if row.get("frame_rgbd_camera_ready"):
            by_scene[str(row["scene_id"])].append(row)
    return by_scene


def select_frame_candidates(frames: list[dict[str, Any]], k: int) -> list[dict[str, Any]]:
    by_capture = defaultdict(list)
    for row in frames:
        by_capture[str(row["capture_id"])].append(row)
    selected = []
    for capture_id in sorted(by_capture):
        rows = sorted(by_capture[capture_id], key=lambda x: str(x["frame_stem"]))
        for idx in [0, len(rows) // 2, len(rows) - 1]:
            selected.append(rows[idx])
            if len(selected) >= k:
                return selected
    return selected[:k]


def object_sidecar(scene_id: str, node_id: str, objects: dict[tuple[str, str], dict[str, Any]]) -> dict[str, Any]:
    row = objects.get((scene_id, node_id))
    if not row:
        return {
            "node_id": node_id,
            "found": False,
            "label": None,
            "object_id": None,
            "native_scene_id": None,
            "native_feature_key": None,
            "n_point_indices": 0,
            "has_point_segment": False,
            "has_record_camera": False,
            "has_bbox_geometry": False,
            "has_point_feature": False,
            "has_image_feature": False,
        }
    return {
        "node_id": node_id,
        "found": True,
        "label": row.get("label"),
        "object_id": int(row["object_id"]),
        "native_scene_id": row.get("native_scene_id"),
        "native_feature_key": row.get("native_feature_key"),
        "n_point_indices": int(row.get("n_point_indices") or 0),
        "has_point_segment": row.get("has_point_segment") == "True",
        "has_record_camera": row.get("has_record_camera") == "True",
        "has_bbox_geometry": row.get("has_bbox_geometry") == "True",
        "has_point_feature": row.get("has_point_feature") == "True",
        "has_image_feature": row.get("has_image_feature") == "True",
    }


def build_relations(k_frames: int):
    objects = load_object_manifest()
    frames_by_scene = load_frame_index()
    relation_rows = []
    frame_rows = []
    query_rows = []
    qid_to_relation = {}

    for split_name, path in QUERY_FILES.items():
        for query in read_jsonl(path):
            scene_id = str(query["scene_id"])
            query_id = str(query["query_id"])
            target_node_id = str(query.get("target_node_id") or (query.get("target_node_ids") or [""])[0])
            anchor_node_id = str(query.get("anchor_node_id") or "NONE")
            anchor_missing = anchor_node_id in {"", "None", "NONE", "null"}
            if anchor_missing:
                anchor_node_id = "NONE"
            relation_key = f"{query_id}|{target_node_id}|{anchor_node_id}"
            relation_dir = stable_hash(relation_key)
            supporting_edges = [parse_edge(edge) for edge in query.get("supporting_edge_ids") or []]
            primary_edge = None
            for edge in supporting_edges:
                if edge["source_node_id"] == target_node_id and edge["target_node_id"] == anchor_node_id:
                    primary_edge = edge
                    break
            if primary_edge is None and supporting_edges:
                primary_edge = supporting_edges[0]

            target_sidecar = object_sidecar(scene_id, target_node_id, objects)
            anchor_sidecar = None if anchor_missing else object_sidecar(scene_id, anchor_node_id, objects)
            candidate_frames = select_frame_candidates(frames_by_scene.get(scene_id, []), k_frames)
            frame_refs = []
            for rank, frame in enumerate(candidate_frames):
                frame_key = f"{relation_key}|{frame['capture_id']}|{frame['frame_stem']}"
                frame_rows.append({
                    "relation_key": relation_key,
                    "frame_key": frame_key,
                    "rank": rank,
                    "scene_id": scene_id,
                    "capture_id": frame["capture_id"],
                    "frame_stem": frame["frame_stem"],
                    "rgb_rel_path": frame["rgb_rel_path"],
                    "depth_rel_path": frame["depth_rel_path"],
                    "intrinsics_rel_path": frame["intrinsics_rel_path"],
                    "selection_rule_version": "scene_representative_rgbd_camera_triplets_v1_not_projected",
                    "co_visible_certified": False,
                    "projection_status": "not_projected_yet",
                })
                frame_refs.append(frame_key)

            relation_ready = bool(
                target_sidecar["found"]
                and target_sidecar["has_point_segment"]
                and target_sidecar["has_bbox_geometry"]
                and target_sidecar["has_point_feature"]
                and target_sidecar["has_image_feature"]
                and (anchor_missing or (anchor_sidecar and anchor_sidecar["found"] and anchor_sidecar["has_point_segment"] and anchor_sidecar["has_bbox_geometry"]))
                and len(frame_refs) > 0
            )
            row = {
                "relation_key": relation_key,
                "relation_dir": relation_dir,
                "query_id": query_id,
                "export_split": split_name,
                "source": query.get("source"),
                "scene_id": scene_id,
                "query_text": query.get("query_text") or query.get("prompt"),
                "target_node_id": target_node_id,
                "target_label": query.get("target_label") or target_sidecar.get("label"),
                "anchor_node_id": anchor_node_id,
                "anchor_label": query.get("anchor_label") or (None if anchor_missing else anchor_sidecar.get("label") if anchor_sidecar else None),
                "anchor_missing": anchor_missing,
                "primary_relation": primary_edge["relation"] if primary_edge else None,
                "supporting_edges": supporting_edges,
                "difficulty_tags": query.get("difficulty_tags") or [],
                "expected_failure_modes": query.get("expected_failure_modes") or [],
                "num_same_label_distractors": query.get("num_same_label_distractors"),
                "target_object": target_sidecar,
                "anchor_object": anchor_sidecar,
                "candidate_frame_keys": frame_refs,
                "n_candidate_frames": len(frame_refs),
                "point_segment_status": "target_anchor_ready" if relation_ready and not anchor_missing else "target_ready_anchor_missing" if relation_ready else "incomplete",
                "crop_status": "frame_candidates_ready_not_projected",
                "relation_evidence_ready": relation_ready,
            }
            relation_rows.append(row)
            qid_to_relation[query_id] = row
            query_rows.append({
                "query_id": query_id,
                "export_split": split_name,
                "scene_id": scene_id,
                "relation_keys": [relation_key],
                "n_relations": 1,
                "all_relation_evidence_ready": relation_ready,
            })
    return relation_rows, frame_rows, query_rows, qid_to_relation


def build_minimal_pair_links(qid_to_relation: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for pair in read_jsonl(EXPORT_DIR / "minimal_pairs_28_eval.jsonl"):
        qa = str(pair["query_a_id"])
        qb = str(pair["query_b_id"])
        ra = qid_to_relation.get(qa)
        rb = qid_to_relation.get(qb)
        rows.append({
            "pair_id": pair["pair_id"],
            "scene_id": pair.get("scene_id"),
            "changed_factor": pair.get("changed_factor"),
            "query_a_id": qa,
            "query_b_id": qb,
            "relation_key_a": ra["relation_key"] if ra else None,
            "relation_key_b": rb["relation_key"] if rb else None,
            "target_a_node_id": pair.get("target_a_node_id"),
            "target_b_node_id": pair.get("target_b_node_id"),
            "anchor_a_node_id": pair.get("anchor_a_node_id"),
            "anchor_b_node_id": pair.get("anchor_b_node_id"),
            "both_relations_ready": bool(ra and rb and ra["relation_evidence_ready"] and rb["relation_evidence_ready"]),
            "why_hard": pair.get("why_hard"),
        })
    return rows


def write_status(relation_rows, frame_rows, pair_rows) -> dict[str, Any]:
    by_split = Counter(row["export_split"] for row in relation_rows)
    ready_by_split = Counter(row["export_split"] for row in relation_rows if row["relation_evidence_ready"])
    summary = {
        "status": "relation_conditioned_evidence_index_ready_not_projected",
        "n_relations": len(relation_rows),
        "n_relation_evidence_ready": sum(row["relation_evidence_ready"] for row in relation_rows),
        "n_frame_candidates": len(frame_rows),
        "n_minimal_pairs": len(pair_rows),
        "n_minimal_pairs_ready": sum(row["both_relations_ready"] for row in pair_rows),
        "by_split": {split: {"n": by_split[split], "ready": ready_by_split[split]} for split in sorted(by_split)},
        "important_boundary": "Frame candidates are RGB-D-camera triplets from the same scene, not yet projection-certified co-visible crops. Use them as projector/crop inputs, not final crop evidence.",
    }
    write_json(EVIDENCE_DIR / "relation_evidence_summary.json", summary)
    lines = [
        "# Relation-Conditioned Evidence Status",
        "",
        "This directory connects each functional query to target-anchor multimodal evidence. It does not run baselines or model inference.",
        "",
        "## Result",
        "",
        f"- Status: `{summary['status']}`",
        f"- Relations indexed: {summary['n_relations']}",
        f"- Relations with target/anchor point and feature sidecars ready: {summary['n_relation_evidence_ready']} / {summary['n_relations']}",
        f"- Frame candidates: {summary['n_frame_candidates']}",
        f"- Minimal pairs linked: {summary['n_minimal_pairs_ready']} / {summary['n_minimal_pairs']}",
        "",
        "## Boundary",
        "",
        summary["important_boundary"],
        "",
        "The next data-only step is a projection/crop pass that writes co-visible crop metadata under the same `relation_key` values.",
    ]
    (EVIDENCE_DIR / "RELATION_EVIDENCE_STATUS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary


def write_readme() -> None:
    lines = [
        "# Relation-Conditioned Evidence",
        "",
        "This directory is the query-conditioned multimodal layer for the FunGraph 3DGraphLLM export.",
        "",
        "Primary key:",
        "",
        "```text",
        "relation_key = query_id|target_node_id|anchor_node_id",
        "```",
        "",
        "Files:",
        "",
        "- `relation_evidence_index.jsonl`: one row per query relation, with target and anchor object sidecars, native 3DGraphLLM feature keys, supporting edges, and candidate frame references.",
        "- `query_relation_index.jsonl`: query id to relation keys.",
        "- `relation_frame_candidates.jsonl`: RGB-D-camera frame triplets selected as raw candidates for later projection/crop generation.",
        "- `minimal_pair_relation_index.jsonl`: minimal-pair rows linked to relation keys.",
        "- `relation_evidence_summary.json`: machine-readable coverage summary.",
        "- `RELATION_EVIDENCE_STATUS.md`: human-readable status and boundary notes.",
        "- `sample_load_relation_evidence.py`: tiny loader for querying this layer.",
        "",
        "Important boundary: frame candidates are not yet co-visible crop evidence. They are full RGB-D-camera triplets ready for a projection/visibility pass. Large raw crops and exported pointclouds should remain local unless explicitly approved.",
    ]
    (EVIDENCE_DIR / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_loader() -> None:
    lines = [
        "#!/usr/bin/env python3",
        "from __future__ import annotations",
        "import argparse",
        "import json",
        "from pathlib import Path",
        "ROOT = Path(__file__).resolve().parent",
        "def read_jsonl(path: Path):",
        "    with path.open('r', encoding='utf-8') as f:",
        "        for line in f:",
        "            line = line.strip()",
        "            if line:",
        "                yield json.loads(line)",
        "def main() -> None:",
        "    parser = argparse.ArgumentParser()",
        "    parser.add_argument('--query-id')",
        "    parser.add_argument('--relation-key')",
        "    args = parser.parse_args()",
        "    relations = {row['relation_key']: row for row in read_jsonl(ROOT / 'relation_evidence_index.jsonl')}",
        "    qrels = {row['query_id']: row for row in read_jsonl(ROOT / 'query_relation_index.jsonl')}",
        "    frames_by_relation = {}",
        "    for row in read_jsonl(ROOT / 'relation_frame_candidates.jsonl'):",
        "        frames_by_relation.setdefault(row['relation_key'], []).append(row)",
        "    if args.relation_key:",
        "        keys = [args.relation_key]",
        "    elif args.query_id:",
        "        keys = qrels.get(args.query_id, {}).get('relation_keys', [])",
        "    else:",
        "        raise SystemExit('Pass --query-id or --relation-key')",
        "    out = []",
        "    for key in keys:",
        "        item = dict(relations[key])",
        "        item['frame_candidates'] = frames_by_relation.get(key, [])",
        "        out.append(item)",
        "    print(json.dumps(out, indent=2, ensure_ascii=False))",
        "if __name__ == '__main__':",
        "    main()",
    ]
    path = EVIDENCE_DIR / "sample_load_relation_evidence.py"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.chmod(0o755)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k-frames", type=int, default=6)
    args = parser.parse_args()
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    relation_rows, frame_rows, query_rows, qid_to_relation = build_relations(args.k_frames)
    pair_rows = build_minimal_pair_links(qid_to_relation)
    write_jsonl(EVIDENCE_DIR / "relation_evidence_index.jsonl", relation_rows)
    write_jsonl(EVIDENCE_DIR / "relation_frame_candidates.jsonl", frame_rows)
    write_jsonl(EVIDENCE_DIR / "query_relation_index.jsonl", query_rows)
    write_jsonl(EVIDENCE_DIR / "minimal_pair_relation_index.jsonl", pair_rows)
    summary = write_status(relation_rows, frame_rows, pair_rows)
    write_readme()
    write_loader()
    print(json.dumps(summary, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
