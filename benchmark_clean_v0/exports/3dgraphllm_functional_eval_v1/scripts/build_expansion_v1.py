#!/usr/bin/env python3
"""Build distribution audit and benchmark expansion drafts.

This script does not replace frozen eval files. It creates an auditable
`expansion_v1/` workspace with:

- distribution audit for current exported functional queries;
- full OpenFunGraph unique functional relation pool;
- template-generated query drafts covering every unique relation;
- automatically mined minimal-pair candidates for human review.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
BENCHMARK_ROOT = EXPORT_DIR.parents[1]
OUT_DIR = EXPORT_DIR / "expansion_v1"
ANNOTATION_DIR = BENCHMARK_ROOT / "annotations" / "openfungraph"
RELATIONS_PATH = ANNOTATION_DIR / "SceneFun3D.relations.json"
ANNOTATIONS_PATH = ANNOTATION_DIR / "SceneFun3D.annotations.json"
GEOMETRY_PATH = BENCHMARK_ROOT / "geometry" / "scenefun3d_node_geom.json"
OBJECT_MANIFEST = EXPORT_DIR / "full_object_modality_manifest.csv"
FULL_PERCEPTION_INDEX = EXPORT_DIR / "relation_conditioned_evidence" / "full_perception_evidence_index.jsonl"

CURRENT_QUERY_FILES = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
}


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r, ensure_ascii=False, sort_keys=True) + "\n" for r in rows), encoding="utf-8")


def relation_key(scene_id: str, target: str, anchor: str, relation: str) -> tuple[str, str, str, str]:
    return str(scene_id), str(target), str(anchor), str(relation)


def edge_id(scene_id: str, target: str, anchor: str, relation: str) -> str:
    return f"{target}|{relation}|{anchor}"


def parse_edge(edge: str) -> tuple[str, str, str]:
    parts = str(edge).split("|")
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return "", "", ""


def load_object_rows() -> tuple[dict[tuple[str, str], dict[str, str]], dict[str, list[str]]]:
    objects: dict[tuple[str, str], dict[str, str]] = {}
    candidates: dict[str, list[str]] = defaultdict(list)
    with OBJECT_MANIFEST.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            scene_id = str(row["scene_id"])
            node_id = str(row["node_id"])
            objects[(scene_id, node_id)] = row
            if row.get("is_export_candidate") == "True":
                candidates[scene_id].append(node_id)
    return objects, {k: sorted(v) for k, v in candidates.items()}


def load_openfungraph_relations() -> list[dict[str, Any]]:
    objects, candidates = load_object_rows()
    perception_by_pair = {}
    if FULL_PERCEPTION_INDEX.exists():
        for row in read_jsonl(FULL_PERCEPTION_INDEX):
            perception_by_pair[(row["scene_id"], row["target_node_id"], row["anchor_node_id"])] = row

    raw_relations = json.loads(RELATIONS_PATH.read_text(encoding="utf-8"))
    geometry = json.loads(GEOMETRY_PATH.read_text(encoding="utf-8"))
    rows = []
    seen = set()
    for rel in raw_relations:
        scene_id = str(rel["scene_id"])
        target = str(rel["first_node_annot_id"])
        anchor = str(rel["second_node_annot_id"])
        desc = str(rel["description"])
        key = relation_key(scene_id, target, anchor, desc)
        if key in seen:
            continue
        seen.add(key)
        target_obj = objects.get((scene_id, target), {})
        anchor_obj = objects.get((scene_id, anchor), {})
        tgeom = geometry.get(scene_id, {}).get(target, {})
        ageom = geometry.get(scene_id, {}).get(anchor, {})
        perception = perception_by_pair.get((scene_id, target, anchor), {})
        rows.append({
            "relation_id": rel.get("relation_id"),
            "scene_id": scene_id,
            "target_node_id": target,
            "target_label": target_obj.get("label"),
            "anchor_node_id": anchor,
            "anchor_label": anchor_obj.get("label"),
            "relation": desc,
            "supporting_edge_id": edge_id(scene_id, target, anchor, desc),
            "candidate_node_ids": candidates.get(scene_id, []),
            "n_candidates": len(candidates.get(scene_id, [])),
            "target_bbox_center": tgeom.get("bbox_center"),
            "anchor_bbox_center": ageom.get("bbox_center"),
            "target_object_full_ready": target_obj.get("object_full_ready") == "True",
            "anchor_object_full_ready": anchor_obj.get("object_full_ready") == "True",
            "perception_evidence_tier": perception.get("evidence_tier", "not_in_previous_export"),
            "has_depth_tested_rgbd_crop": bool(perception.get("has_depth_tested_rgbd_crop", False)),
            "source": "openfungraph_relation",
        })
    return sorted(rows, key=lambda r: (r["scene_id"], r["relation"], r["target_label"] or "", r["anchor_label"] or "", r["target_node_id"]))


def task_phrase(relation: str, anchor_label: str | None) -> str:
    anchor = anchor_label or "object"
    mapping = [
        ("provide power", f"power the {anchor}"),
        ("control the water flow", f"control the water flow for the {anchor}"),
        ("flush", f"flush the {anchor}"),
        ("control, turn on or turn off", f"turn the {anchor} on or off"),
        ("control", f"control the {anchor}"),
        ("adjust the temperature", f"adjust the temperature of the {anchor}"),
        ("adjust the setting", f"adjust the setting of the {anchor}"),
        ("open or close a drawer", f"open or close the drawer on the {anchor}"),
        ("open or close", f"open or close the {anchor}"),
    ]
    for needle, phrase in mapping:
        if needle in relation:
            return phrase
    return f"perform '{relation}' on the {anchor}"


def query_templates(row: dict[str, Any]) -> list[str]:
    target = row["target_label"] or "functional part"
    anchor = row["anchor_label"] or "object"
    rel = row["relation"]
    phrase = task_phrase(rel, anchor)
    return [
        f"Use the {target} to {phrase}.",
        f"Which {target} should I use to {phrase}?",
        f"I need to {phrase}; identify the correct {target}.",
    ]


def build_query_drafts(unique_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = []
    for idx, row in enumerate(unique_rows):
        for variant, text in enumerate(query_templates(row)):
            qid = f"exp_func_v1_{idx:04d}_v{variant}"
            out.append({
                "query_id": qid,
                "scene_id": row["scene_id"],
                "split": "expansion_v1_draft",
                "dataset": "scenefun3d",
                "query_type": "functional",
                "annotation_source": "template_generated_needs_human_review",
                "source": "openfungraph_unique_relation_expansion_v1",
                "query_text": text,
                "prompt": text,
                "target_node_id": row["target_node_id"],
                "target_node_ids": [row["target_node_id"]],
                "target_label": row["target_label"],
                "target_labels": [row["target_label"]],
                "anchor_node_id": row["anchor_node_id"],
                "anchor_label": row["anchor_label"],
                "supporting_edge_ids": [row["supporting_edge_id"]],
                "candidate_node_ids": row["candidate_node_ids"],
                "n_candidates": row["n_candidates"],
                "difficulty_tags": sorted(set(["functional_relation", "endpoint_ambiguity"] + (["same_label_disambiguation"] if row["target_label_count_in_scene"] > 1 else []))),
                "expected_failure_modes": ["template_language_may_need_human_rewrite"],
                "unique_relation_id": row["unique_relation_id"],
                "perception_evidence_tier": row["perception_evidence_tier"],
                "has_depth_tested_rgbd_crop": row["has_depth_tested_rgbd_crop"],
            })
    return out


def distance(a: list[float] | None, b: list[float] | None) -> float | None:
    if not a or not b:
        return None
    return math.sqrt(sum((float(x) - float(y)) ** 2 for x, y in zip(a, b)))


def xyz_text(xyz: list[float] | None) -> str:
    if not xyz:
        return ""
    return ",".join(f"{float(v):.3f}" for v in xyz)


def axis_tag(a: list[float] | None, b: list[float] | None) -> str:
    if not a or not b:
        return "geometry_unknown"
    diffs = [abs(float(x) - float(y)) for x, y in zip(a, b)]
    axis = max(range(3), key=lambda i: diffs[i])
    return ["geometry_x_axis", "geometry_y_axis", "geometry_z_axis"][axis]


def build_minimal_pair_candidates(unique_rows: list[dict[str, Any]], cap: int) -> list[dict[str, Any]]:
    pairs = []
    seen: set[tuple[str, str]] = set()

    def add_pair(a: dict[str, Any], b: dict[str, Any], changed: str, evidence: list[str], why: str) -> None:
        if a["unique_relation_id"] == b["unique_relation_id"]:
            return
        key = tuple(sorted([a["unique_relation_id"], b["unique_relation_id"]]))
        if key in seen:
            return
        seen.add(key)
        d = distance(a.get("target_bbox_center"), b.get("target_bbox_center"))
        pid = f"exp_minpair_v1_{len(pairs) + 1:06d}"
        pairs.append({
            "pair_id": pid,
            "status": "auto_mined_candidate_needs_human_review",
            "scene_id": a["scene_id"],
            "query_a_id": a["canonical_query_id"],
            "query_b_id": b["canonical_query_id"],
            "changed_factor": changed,
            "why_hard": why,
            "target_a_node_id": a["target_node_id"],
            "target_b_node_id": b["target_node_id"],
            "target_label": a["target_label"],
            "anchor_a_node_id": a["anchor_node_id"],
            "anchor_b_node_id": b["anchor_node_id"],
            "anchor_a_label": a["anchor_label"],
            "anchor_b_label": b["anchor_label"],
            "shared_relation": a["relation"] if a["relation"] == b["relation"] else None,
            "relation_a": a["relation"],
            "relation_b": b["relation"],
            "target_a_xyz": xyz_text(a.get("target_bbox_center")),
            "target_b_xyz": xyz_text(b.get("target_bbox_center")),
            "target_geom_diff_m": round(d, 3) if d is not None else None,
            "pair_evidence_used": evidence,
            "diff_summary": f"{changed}: {a['target_label']}->{a['anchor_label']} vs {b['target_label']}->{b['anchor_label']}",
            "notes": "Auto-mined from OpenFunGraph unique relation pool; human wording/review required before paper finalization.",
        })

    grouped: dict[tuple[Any, ...], list[dict[str, Any]]] = defaultdict(list)
    for r in unique_rows:
        grouped[(r["scene_id"], r["relation"], r["anchor_node_id"], r["target_label"])].append(r)
    for group in grouped.values():
        if len(group) < 2:
            continue
        group = sorted(group, key=lambda r: (r.get("target_bbox_center") or [0, 0, 0], r["target_node_id"]))
        for a, b in zip(group, group[1:]):
            add_pair(
                a,
                b,
                "spatial_qualifier",
                [axis_tag(a.get("target_bbox_center"), b.get("target_bbox_center"))],
                "Same scene, same anchor, same relation, and same target label; only the target object's position changes.",
            )

    grouped = defaultdict(list)
    for r in unique_rows:
        grouped[(r["scene_id"], r["relation"], r["target_label"], r["anchor_label"])].append(r)
    for group in grouped.values():
        by_anchor = defaultdict(list)
        for r in group:
            by_anchor[r["anchor_node_id"]].append(r)
        if len(by_anchor) < 2:
            continue
        reps = [sorted(v, key=lambda x: x["target_node_id"])[0] for v in by_anchor.values()]
        reps = sorted(reps, key=lambda r: r["anchor_node_id"])
        for a, b in zip(reps, reps[1:]):
            add_pair(
                a,
                b,
                "anchor_object",
                ["anchor_identity", "functional_edge"],
                "Same scene, same target label, same relation, and same anchor label; only the concrete anchor object changes.",
            )

    grouped = defaultdict(list)
    for r in unique_rows:
        grouped[(r["scene_id"], r["anchor_node_id"], r["target_label"])].append(r)
    for group in grouped.values():
        by_rel = defaultdict(list)
        for r in group:
            by_rel[r["relation"]].append(r)
        if len(by_rel) < 2:
            continue
        reps = [sorted(v, key=lambda x: x["target_node_id"])[0] for v in by_rel.values()]
        reps = sorted(reps, key=lambda r: r["relation"])
        for a, b in zip(reps, reps[1:]):
            add_pair(
                a,
                b,
                "functional_relation",
                ["functional_edge"],
                "Same scene, same anchor, and same target label; the functional relation changes.",
            )

    return pairs[:cap]


def audit_current() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    perception_by_relation_key = {}
    if FULL_PERCEPTION_INDEX.exists():
        for prow in read_jsonl(FULL_PERCEPTION_INDEX):
            perception_by_relation_key[prow["relation_key"]] = prow

    rows = []
    for split, path in CURRENT_QUERY_FILES.items():
        for row in read_jsonl(path):
            edge = (row.get("supporting_edge_ids") or [""])[0]
            target, relation, anchor = parse_edge(edge)
            target = row.get("target_node_id") or (row.get("target_node_ids") or [target])[0]
            anchor = row.get("anchor_node_id") or anchor
            rkey = f"{row['query_id']}|{target}|{anchor}"
            prow = perception_by_relation_key.get(rkey, {})
            rows.append({
                **row,
                "target_label": row.get("target_label") or prow.get("target_label"),
                "anchor_label": row.get("anchor_label") or prow.get("anchor_label"),
                "_export_split": split,
                "_relation": relation,
                "_relation_key": relation_key(row["scene_id"], target, anchor, relation),
            })
    by_split = Counter(r["_export_split"] for r in rows)
    unique_by_split = {s: len({r["_relation_key"] for r in rows if r["_export_split"] == s}) for s in by_split}
    relation_counts = Counter(r["_relation"] for r in rows)
    label_pair_counts = Counter((r.get("target_label"), r.get("anchor_label")) for r in rows)
    scene_counts = Counter(r["scene_id"] for r in rows)
    duplicate_groups = Counter(r["_relation_key"] for r in rows)
    summary = {
        "status": "distribution_audit_ready",
        "n_query_rows": len(rows),
        "n_unique_scene_target_anchor_relation": len({r["_relation_key"] for r in rows}),
        "by_split": {s: {"n_query_rows": by_split[s], "n_unique_relations": unique_by_split[s]} for s in sorted(by_split)},
        "top_relations": [{"relation": k, "n": v} for k, v in relation_counts.most_common(20)],
        "top_target_anchor_label_pairs": [{"target_label": k[0], "anchor_label": k[1], "n": v} for k, v in label_pair_counts.most_common(20)],
        "top_scenes": [{"scene_id": k, "n": v} for k, v in scene_counts.most_common(20)],
        "n_relation_groups_with_multiple_paraphrases": sum(1 for v in duplicate_groups.values() if v > 1),
        "max_paraphrases_per_relation": max(duplicate_groups.values()) if duplicate_groups else 0,
    }
    return summary, rows


def enrich_unique_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scene_target_label_counts = Counter((r["scene_id"], r["target_label"]) for r in rows)
    scene_relation_counts = Counter((r["scene_id"], r["relation"]) for r in rows)
    for idx, row in enumerate(rows):
        row["unique_relation_id"] = f"openfungraph_rel_v1_{idx:04d}"
        row["canonical_query_id"] = f"exp_func_v1_{idx:04d}_v0"
        row["target_label_count_in_scene"] = scene_target_label_counts[(row["scene_id"], row["target_label"])]
        row["relation_count_in_scene"] = scene_relation_counts[(row["scene_id"], row["relation"])]
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row.get(k) for k in fieldnames})


def write_report(current: dict[str, Any], pool_summary: dict[str, Any], pair_summary: dict[str, Any]) -> None:
    lines = [
        "# Benchmark Expansion v1 Status",
        "",
        "This directory is a draft workspace for distribution audit, unique-relation expansion, and minimal-pair expansion. It does not replace frozen eval files.",
        "",
        "## Current Export Audit",
        "",
        f"- Current query rows: {current['n_query_rows']}",
        f"- Current unique scene-target-anchor-relation keys: {current['n_unique_scene_target_anchor_relation']}",
        f"- Max paraphrases per relation group: {current['max_paraphrases_per_relation']}",
        "",
        "## Unique-Relation Expansion",
        "",
        f"- OpenFunGraph unique functional relations available: {pool_summary['n_unique_relations']}",
        f"- Template-generated query drafts: {pool_summary['n_query_drafts']}",
        f"- Previous-export depth-tested RGB-D crop relations: {pool_summary['n_depth_tested_rgbd_crop_relations']}",
        f"- Relations not present in previous full-perception export: {pool_summary['n_non_previous_export_relations']}",
        f"- Target coverage policy: 3 query variants per unique relation.",
        "",
        "## Minimal-Pair Expansion",
        "",
        f"- Auto-mined pair candidates: {pair_summary['n_pair_candidates']}",
        f"- Changed-factor distribution: {pair_summary['changed_factor_counts']}",
        "",
        "## Boundary",
        "",
        "Expansion query drafts and pair candidates are generated from verified graph relations, but their natural-language wording is not final human annotation. Use them for coverage planning, model debugging, and human review queues before paper-grade reporting.",
        "Relations not present in the previous full-perception export need an evidence-generation pass before this draft is promoted to a frozen eval split.",
    ]
    rendered = "\n".join(lines) + "\n"
    (OUT_DIR / "EXPANSION_STATUS.md").write_text(rendered, encoding="utf-8")
    (OUT_DIR / "README.md").write_text(rendered, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pair-cap", type=int, default=200)
    args = parser.parse_args()

    current_summary, _ = audit_current()
    unique_rows = enrich_unique_rows(load_openfungraph_relations())
    query_rows = build_query_drafts(unique_rows)
    pair_rows = build_minimal_pair_candidates(unique_rows, args.pair_cap)

    pool_summary = {
        "status": "unique_relation_expansion_pool_ready",
        "n_unique_relations": len(unique_rows),
        "n_query_drafts": len(query_rows),
        "n_scenes": len({r["scene_id"] for r in unique_rows}),
        "n_depth_tested_rgbd_crop_relations": sum(r["has_depth_tested_rgbd_crop"] for r in unique_rows),
        "n_non_previous_export_relations": sum(r["perception_evidence_tier"] == "not_in_previous_export" for r in unique_rows),
        "relation_counts": Counter(r["relation"] for r in unique_rows),
        "target_label_counts": Counter(r["target_label"] for r in unique_rows),
    }
    pool_summary["relation_counts"] = dict(pool_summary["relation_counts"].most_common())
    pool_summary["target_label_counts"] = dict(pool_summary["target_label_counts"].most_common())
    pair_summary = {
        "status": "minimal_pair_expansion_candidates_ready",
        "n_pair_candidates": len(pair_rows),
        "changed_factor_counts": dict(Counter(r["changed_factor"] for r in pair_rows).most_common()),
    }

    write_json(OUT_DIR / "distribution_audit.json", current_summary)
    write_json(OUT_DIR / "unique_relation_expansion_summary.json", pool_summary)
    write_json(OUT_DIR / "minimal_pair_expansion_summary.json", pair_summary)
    write_jsonl(OUT_DIR / "unique_relation_pool_v1.jsonl", unique_rows)
    write_jsonl(OUT_DIR / "functional_unique_relation_585_draft.jsonl", query_rows)
    write_jsonl(OUT_DIR / "minimal_pair_candidates_v1.jsonl", pair_rows)
    write_csv(
        OUT_DIR / "unique_relation_pool_v1.csv",
        unique_rows,
        ["unique_relation_id", "scene_id", "target_label", "target_node_id", "relation", "anchor_label", "anchor_node_id", "target_label_count_in_scene", "perception_evidence_tier", "has_depth_tested_rgbd_crop"],
    )
    write_csv(
        OUT_DIR / "minimal_pair_candidates_v1.csv",
        pair_rows,
        ["pair_id", "changed_factor", "scene_id", "target_label", "relation_a", "relation_b", "anchor_a_label", "anchor_b_label", "target_geom_diff_m", "pair_evidence_used", "query_a_id", "query_b_id"],
    )
    write_report(current_summary, pool_summary, pair_summary)
    print(json.dumps({"current": current_summary, "pool": pool_summary, "pairs": pair_summary}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
