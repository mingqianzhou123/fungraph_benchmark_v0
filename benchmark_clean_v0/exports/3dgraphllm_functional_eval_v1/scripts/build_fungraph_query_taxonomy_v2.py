#!/usr/bin/env python3
"""Categorize existing FunGraph/SceneFun3D queries with the factorized taxonomy.

This does not rewrite the original benchmark queries. It creates a derived view
that annotates existing rows with:

    Functional Query Type x Spatial Scope x Anchor Visibility

The output is meant for analysis and controlled slicing while preserving the
canonical release splits unchanged.
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
SPLITS_DIR = RELEASE_DIR / "splits"
OUTPUT = SPLITS_DIR / "fungraph_existing_queries_categorized_v2.jsonl"
SUMMARY = RELEASE_DIR / "fungraph_query_taxonomy_v2_summary.json"

SOURCE_SPLITS = [
    "functional_500.jsonl",
    "human_133.jsonl",
    "long_range_50.jsonl",
    "expansion_functional_116_candidates.jsonl",
]

REMOTE_FUNCTIONAL_LABELS = {
    "light switch",
    "switch",
    "remote",
    "remote control",
    "electric outlet",
    "outlet",
    "power outlet",
}
REMOTE_RELATION_KEYWORDS = {
    "provide power",
    "control, turn on or turn off",
    "turn on or turn off",
    "turn on/off",
}
GOAL_PHRASES = (
    "i need",
    "i want",
    "make ",
    "to make",
    "trying to",
    "brighten",
    "light up",
    "start",
    "cook",
    "open the",
)
IMPERATIVE_ACTIONS = (
    "pull ",
    "press ",
    "rotate ",
    "turn ",
    "use ",
    "activate ",
)


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def norm(text: Any) -> str:
    return re.sub(r"\s+", " ", str(text or "").lower()).strip()


def label_variants(label: str) -> list[str]:
    label = norm(label)
    variants = {label}
    for part in re.split(r"[/(),;]", label):
        part = norm(part)
        if len(part) >= 3:
            variants.add(part)
    return sorted(v for v in variants if v)


def load_scene_nodes() -> dict[str, dict[str, dict[str, Any]]]:
    scenes: dict[str, dict[str, dict[str, Any]]] = {}
    for scene_path in sorted((RELEASE_DIR / "scenes").glob("*/scene.json")):
        scene = read_json(scene_path)
        scenes[str(scene["scene_id"])] = {str(node["node_id"]): node for node in scene["node_list"]}
    return scenes


def parse_first_edge(row: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    edges = row.get("supporting_edge_ids") or []
    if not edges:
        return None, None, None
    parts = str(edges[0]).split("|")
    if len(parts) < 3:
        return None, None, None
    return parts[0], parts[1], parts[2]


def node_label(scene_nodes: dict[str, dict[str, Any]], node_id: Any) -> str | None:
    node = scene_nodes.get(str(node_id))
    if not node:
        return None
    return node.get("label")


def infer_anchor_label(row: dict[str, Any], scene_nodes: dict[str, dict[str, Any]], edge_second_id: str | None) -> str | None:
    if row.get("anchor_label"):
        return row["anchor_label"]
    if edge_second_id:
        inferred = node_label(scene_nodes, edge_second_id)
        if inferred:
            return inferred
    if row.get("anchor_node_id"):
        return node_label(scene_nodes, row["anchor_node_id"])
    return None


def infer_functional_element_label(row: dict[str, Any], scene_nodes: dict[str, dict[str, Any]], edge_first_id: str | None) -> str | None:
    if row.get("target_label"):
        return row["target_label"]
    if edge_first_id:
        return node_label(scene_nodes, edge_first_id)
    return None


def distance_between(scene_nodes: dict[str, dict[str, Any]], first_id: Any, second_id: Any) -> float | None:
    first = scene_nodes.get(str(first_id))
    second = scene_nodes.get(str(second_id))
    if not first or not second:
        return None
    try:
        return math.dist(first["geometry"]["bbox_center"], second["geometry"]["bbox_center"])
    except (KeyError, TypeError, ValueError):
        return None


def classify_functional_query_type(row: dict[str, Any], text: str) -> str:
    tags = set(row.get("difficulty_tags") or [])
    if "minimal_pair" in tags or (row.get("num_same_label_distractors") or 0) >= 2 and row.get("geometry_cues"):
        return "ambiguous_instance_minimal_pair"
    if "?" in text and any(x in text for x in ["does ", "is this ", "can this "]):
        return "relation_verification"
    if text.startswith(IMPERATIVE_ACTIONS):
        return "functional_element_selection"
    if any(phrase in text for phrase in GOAL_PHRASES):
        return "state_change_goal_completion"
    return "functional_element_selection"


def classify_spatial_scope(
    row: dict[str, Any],
    relation: str | None,
    functional_label: str | None,
    distance: float | None,
) -> str:
    tags = set(row.get("difficulty_tags") or [])
    relation_text = norm(relation or (row.get("functional_taxonomy") or {}).get("relation"))
    functional_text = norm(functional_label)
    if "long_range" in tags:
        return "remote"
    if functional_text in REMOTE_FUNCTIONAL_LABELS:
        return "remote"
    if relation_text in REMOTE_RELATION_KEYWORDS:
        return "remote"
    if distance is not None:
        return "remote" if distance >= 2.5 else "local"
    return "local"


def classify_anchor_visibility(text: str, anchor_label: str | None) -> str:
    variants = label_variants(anchor_label or "")
    if any(variant in text for variant in variants):
        return "anchor_explicit"
    if any(token in text for token in [" this ", " that ", " here", " nearby", " near ", " there", " it "]):
        return "anchor_implicit"
    return "anchor_hidden"


def categorize_row(row: dict[str, Any], original_split: str, scene_nodes: dict[str, dict[str, Any]]) -> dict[str, Any]:
    first_id, relation, second_id = parse_first_edge(row)
    anchor_node_id = row.get("anchor_node_id") or second_id
    anchor_label = infer_anchor_label(row, scene_nodes, second_id)
    functional_label = infer_functional_element_label(row, scene_nodes, first_id)
    text = norm(row.get("query_text") or row.get("prompt"))
    distance = distance_between(scene_nodes, row.get("target_node_id") or first_id, anchor_node_id)
    functional_query_type = classify_functional_query_type(row, text)
    spatial_scope = classify_spatial_scope(row, relation, functional_label, distance)
    anchor_visibility = classify_anchor_visibility(f" {text} ", anchor_label)

    out = dict(row)
    out["original_split_file"] = original_split
    out["generation_version"] = "existing_query_categorized_v2"
    out["taxonomy_review_status"] = "auto_labeled_needs_spot_check"
    out["functional_query_type"] = functional_query_type
    out["query_family"] = functional_query_type
    out["spatial_scope"] = spatial_scope
    out["anchor_visibility"] = anchor_visibility
    out["answer_target"] = "functional_element"
    out["answer_format"] = "node_selection"
    if anchor_label and not out.get("anchor_label"):
        out["anchor_label"] = anchor_label
    if anchor_node_id and not out.get("anchor_node_id"):
        out["anchor_node_id"] = anchor_node_id
    taxonomy = dict(out.get("functional_taxonomy") or {})
    taxonomy.update({
        "functional_query_type": functional_query_type,
        "spatial_scope": spatial_scope,
        "anchor_visibility": anchor_visibility,
        "anchor_label_auto_inferred": anchor_label,
        "target_anchor_distance_m": distance,
        "taxonomy_version": "fungraph_existing_query_taxonomy_v2",
    })
    out["functional_taxonomy"] = taxonomy
    tags = list(out.get("difficulty_tags") or [])
    for tag in [functional_query_type, spatial_scope, anchor_visibility]:
        if tag not in tags:
            tags.append(tag)
    out["difficulty_tags"] = tags
    out["paper_use_allowed"] = bool(out.get("paper_use_allowed", False))
    out["human_review_required"] = True
    out["dennis_signoff_required"] = True
    return out


def update_release_manifest(rows: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    manifest_path = RELEASE_DIR / "dataset_manifest.json"
    manifest = read_json(manifest_path)
    derived = manifest.setdefault("derived_splits", {})
    derived["fungraph_existing_queries_categorized_v2"] = {
        "path": "splits/fungraph_existing_queries_categorized_v2.jsonl",
        "summary": "fungraph_query_taxonomy_v2_summary.json",
        "n_rows": len(rows),
        "source_splits": SOURCE_SPLITS,
        "axes": ["functional_query_type", "spatial_scope", "anchor_visibility"],
        "paper_use_allowed": False,
    }
    manifest["counts"]["n_fungraph_existing_queries_categorized_v2"] = len(rows)
    manifest["counts"]["fungraph_existing_query_taxonomy_v2"] = summary["counts"]
    write_json(manifest_path, manifest)


def update_docs(n_rows: int) -> None:
    protocol_path = RELEASE_DIR / "query_protocol_v1.md"
    text = protocol_path.read_text(encoding="utf-8")
    block = f"""
## FunGraph Existing Query Taxonomy v2

The original FunGraph/SceneFun3D release queries are preserved unchanged. A derived categorized view adds the same analysis axes used for FunTHOR v2:

```text
Functional Query Type x Spatial Scope x Anchor Visibility
```

Categorized existing FunGraph/SceneFun3D queries: {n_rows}

This view is for slicing, diagnostics, and model-analysis tables. It is auto-labeled and requires spot-checking before paper claims.
"""
    if "## FunGraph Existing Query Taxonomy v2" not in text:
        text = text.replace("## FunTHOR Factorized v2\n", block + "\n## FunTHOR Factorized v2\n")
        protocol_path.write_text(text, encoding="utf-8")

    readme_path = RELEASE_DIR / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    if "fungraph_existing_queries_categorized_v2.jsonl" not in readme:
        insert = (
            "- `splits/fungraph_existing_queries_categorized_v2.jsonl` contains "
            f"{n_rows} existing FunGraph/SceneFun3D queries annotated with Functional Query Type x Spatial Scope x Anchor Visibility.\n"
        )
        readme = readme.replace("## External FunTHOR Extension\n", insert + "\n## External FunTHOR Extension\n")
        readme_path.write_text(readme, encoding="utf-8")


def main() -> None:
    scenes = load_scene_nodes()
    rows: list[dict[str, Any]] = []
    for split_name in SOURCE_SPLITS:
        for row in read_jsonl(SPLITS_DIR / split_name):
            scene_nodes = scenes.get(str(row["scene_id"]), {})
            rows.append(categorize_row(row, split_name, scene_nodes))

    summary = {
        "status": "fungraph_existing_query_taxonomy_v2_ready",
        "paper_use_allowed": False,
        "human_review_required": True,
        "dennis_signoff_required": True,
        "source_splits": SOURCE_SPLITS,
        "counts": {
            "n_rows": len(rows),
            "by_original_split": dict(sorted(Counter(row["original_split_file"] for row in rows).items())),
            "by_functional_query_type": dict(sorted(Counter(row["functional_query_type"] for row in rows).items())),
            "by_spatial_scope": dict(sorted(Counter(row["spatial_scope"] for row in rows).items())),
            "by_anchor_visibility": dict(sorted(Counter(row["anchor_visibility"] for row in rows).items())),
            "by_dataset": dict(sorted(Counter(row["dataset"] for row in rows).items())),
        },
        "taxonomy_axes": ["functional_query_type", "spatial_scope", "anchor_visibility"],
        "notes": "Auto-labeled derived view; canonical source split files are unchanged.",
    }

    write_jsonl(OUTPUT, rows)
    write_json(SUMMARY, summary)
    update_release_manifest(rows, summary)
    update_docs(len(rows))
    print(json.dumps(summary, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
