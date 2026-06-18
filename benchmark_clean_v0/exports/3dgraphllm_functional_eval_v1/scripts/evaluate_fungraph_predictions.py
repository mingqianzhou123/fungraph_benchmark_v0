#!/usr/bin/env python3
"""Evaluate 3DGraphLLM predictions on the FunGraph functional export.

Primary metric: the model must emit an explicit ``<OBJxxx>`` token. Free-text
label overlap is reported only as a diagnostic and is not counted as accuracy.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import torch

EXPORT_DIR = Path(__file__).resolve().parents[1]
NATIVE_DIR = EXPORT_DIR / "native_3dgraphllm"

NATIVE_ANNO_FILES = {
    "functional_500": NATIVE_DIR / "fungraph_functional_500_val.json",
    "human_133": NATIVE_DIR / "fungraph_human_133_val.json",
    "long_range_50": NATIVE_DIR / "fungraph_long_range_50_val.json",
    "smoke_1": NATIVE_DIR / "fungraph_smoke_1_val.json",
}

EXPORT_QUERY_FILES = {
    "functional_500": EXPORT_DIR / "functional_500_eval.jsonl",
    "human_133": EXPORT_DIR / "human_133_eval.jsonl",
    "long_range_50": EXPORT_DIR / "long_range_50_eval.jsonl",
}

OBJ_RE = re.compile(r"<OBJ\s*(\d{1,3})\s*>", flags=re.IGNORECASE)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
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


def normalize_text(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def load_gold() -> dict[str, dict[str, Any]]:
    gold: dict[str, dict[str, Any]] = {}
    for split, path in NATIVE_ANNO_FILES.items():
        if not path.exists():
            continue
        for row in json.loads(path.read_text(encoding="utf-8")):
            qid = str(row["qid"])
            gold[qid] = {
                "query_id": qid,
                "split_name": split,
                "native_scene_id": str(row["scene_id"]),
                "source_scene_id": str(row["source_scene_id"]),
                "target_obj_id": int(row["obj_id"]),
                "target_node_id": str(row["target_node_id"]),
                "prompt": row.get("prompt", ""),
            }
    return gold


def load_query_meta() -> dict[str, dict[str, Any]]:
    meta: dict[str, dict[str, Any]] = {}
    for split, path in EXPORT_QUERY_FILES.items():
        if not path.exists():
            continue
        for row in read_jsonl(path):
            qid = str(row["query_id"])
            meta[qid] = {
                "export_split": split,
                "difficulty_tags": list(row.get("difficulty_tags") or []),
                "source": row.get("source"),
                "target_label": row.get("target_label"),
                "scene_id": str(row.get("scene_id")),
                "n_candidates": row.get("n_candidates"),
            }
    return meta


def load_scene_labels() -> dict[str, list[str]]:
    attrs = torch.load(NATIVE_DIR / "fungraph_scene3d_attributes.pt", map_location="cpu")
    return {scene_id: [str(x) for x in item.get("objects", [])] for scene_id, item in attrs.items()}


def parse_obj_ids(text: str) -> list[int]:
    return [int(match.group(1)) for match in OBJ_RE.finditer(text or "")]


def lexical_diagnostic(pred_text: str, labels: list[str]) -> dict[str, Any]:
    text = normalize_text(pred_text)
    hits: list[int] = []
    for idx, label in enumerate(labels):
        label_norm = normalize_text(label)
        if label_norm and label_norm in text:
            hits.append(idx)
    return {
        "lexical_label_hit_ids": hits,
        "lexical_unique_hit_id": hits[0] if len(hits) == 1 else None,
        "n_lexical_label_hits": len(hits),
    }


def safe_div(num: int | float, den: int | float) -> float | None:
    if den == 0:
        return None
    return float(num) / float(den)


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(rows)
    with_token = [row for row in rows if row["pred_obj_id"] is not None]
    correct = [row for row in rows if row["obj_token_correct"]]
    single_token = [row for row in rows if row["single_valid_obj_token"]]
    multi_token = [row for row in rows if row["n_valid_parsed_obj_tokens"] > 1]
    target_anywhere = [row for row in rows if row["target_obj_appears_anywhere"]]
    return {
        "n": n,
        "n_with_obj_token": len(with_token),
        "n_without_obj_token": n - len(with_token),
        "n_with_single_valid_obj_token": len(single_token),
        "n_with_multiple_valid_obj_tokens": len(multi_token),
        "n_target_obj_appears_anywhere": len(target_anywhere),
        "obj_token_rate": safe_div(len(with_token), n),
        "single_valid_obj_token_rate": safe_div(len(single_token), n),
        "multiple_valid_obj_token_rate": safe_div(len(multi_token), n),
        "target_obj_anywhere_rate": safe_div(len(target_anywhere), n),
        "primary_acc_all": safe_div(len(correct), n),
        "primary_acc_when_obj_token": safe_div(len(correct), len(with_token)),
    }


def grouped_metrics(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        values = row.get(key)
        if isinstance(values, list):
            for value in values:
                groups[str(value)].append(row)
        else:
            groups[str(values)].append(row)
    return {group: summarize(items) for group, items in sorted(groups.items())}


def pair_metrics(rows_by_qid: dict[str, dict[str, Any]]) -> dict[str, Any]:
    path = EXPORT_DIR / "minimal_pairs_28_eval.jsonl"
    if not path.exists():
        return {}
    pair_rows = read_jsonl(path)
    evaluated: list[dict[str, Any]] = []
    for pair in pair_rows:
        qa = str(pair["query_a_id"])
        qb = str(pair["query_b_id"])
        if qa not in rows_by_qid or qb not in rows_by_qid:
            continue
        a = rows_by_qid[qa]
        b = rows_by_qid[qb]
        both_tokens = a["pred_obj_id"] is not None and b["pred_obj_id"] is not None
        target_same = a["target_obj_id"] == b["target_obj_id"] and a["native_scene_id"] == b["native_scene_id"]
        pred_same = (
            both_tokens
            and a["native_scene_id"] == b["native_scene_id"]
            and a["pred_obj_id"] == b["pred_obj_id"]
        )
        evaluated.append(
            {
                "pair_id": pair["pair_id"],
                "changed_factor": pair.get("changed_factor"),
                "query_a_id": qa,
                "query_b_id": qb,
                "both_have_obj_token": both_tokens,
                "both_correct": bool(a["obj_token_correct"] and b["obj_token_correct"]),
                "prediction_collision": bool((not target_same) and pred_same),
            }
        )
    by_factor: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in evaluated:
        by_factor[str(row["changed_factor"])].append(row)
    return {
        "n_pairs_total": len(pair_rows),
        "n_pairs_evaluated": len(evaluated),
        "both_token_rate": safe_div(sum(row["both_have_obj_token"] for row in evaluated), len(evaluated)),
        "both_correct_rate": safe_div(sum(row["both_correct"] for row in evaluated), len(evaluated)),
        "collision_rate": safe_div(sum(row["prediction_collision"] for row in evaluated), len(evaluated)),
        "by_changed_factor": {
            factor: {
                "n": len(items),
                "both_correct_rate": safe_div(sum(row["both_correct"] for row in items), len(items)),
                "collision_rate": safe_div(sum(row["prediction_collision"] for row in items), len(items)),
            }
            for factor, items in sorted(by_factor.items())
        },
        "pairs": evaluated,
    }


def evaluate_predictions(preds_path: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    preds = json.loads(preds_path.read_text(encoding="utf-8"))
    gold = load_gold()
    meta = load_query_meta()
    scene_labels = load_scene_labels()

    per_query: list[dict[str, Any]] = []
    unknown_qids: list[str] = []
    duplicate_counter = Counter(str(row.get("qid")) for row in preds)
    for pred in preds:
        qid = str(pred.get("qid"))
        if qid not in gold:
            unknown_qids.append(qid)
            continue
        g = gold[qid]
        m = meta.get(qid, {})
        pred_text = str(pred.get("pred") or "")
        parsed = parse_obj_ids(pred_text)
        labels = scene_labels.get(g["native_scene_id"], [])
        valid_parsed = [obj_id for obj_id in parsed if 0 <= obj_id < len(labels)]
        pred_obj_id = valid_parsed[0] if valid_parsed else None
        target_obj_id = int(g["target_obj_id"])
        diag = lexical_diagnostic(pred_text, labels)
        per_query.append(
            {
                "query_id": qid,
                "duplicate_prediction_count": duplicate_counter[qid],
                "native_scene_id": g["native_scene_id"],
                "source_scene_id": g["source_scene_id"],
                "split_name": g["split_name"],
                "export_split": m.get("export_split", g["split_name"]),
                "difficulty_tags": m.get("difficulty_tags", []),
                "source": m.get("source"),
                "target_obj_id": target_obj_id,
                "target_node_id": g["target_node_id"],
                "target_label": m.get("target_label"),
                "pred_obj_id": pred_obj_id,
                "all_parsed_obj_ids": parsed,
                "valid_parsed_obj_ids": valid_parsed,
                "n_parsed_obj_tokens": len(parsed),
                "n_valid_parsed_obj_tokens": len(valid_parsed),
                "single_valid_obj_token": len(valid_parsed) == 1,
                "target_obj_appears_anywhere": target_obj_id in valid_parsed,
                "obj_token_correct": pred_obj_id == target_obj_id,
                "has_obj_token": pred_obj_id is not None,
                "pred_text": pred_text,
                **diag,
            }
        )

    rows_by_qid = {row["query_id"]: row for row in per_query}
    metrics = {
        "predictions_file": str(preds_path),
        "n_predictions": len(preds),
        "n_evaluated_predictions": len(per_query),
        "n_unknown_qids": len(unknown_qids),
        "unknown_qids": unknown_qids[:20],
        "overall": summarize(per_query),
        "by_export_split": grouped_metrics(per_query, "export_split"),
        "by_scene": grouped_metrics(per_query, "source_scene_id"),
        "by_difficulty_tag": grouped_metrics(per_query, "difficulty_tags"),
        "minimal_pair": pair_metrics(rows_by_qid),
    }
    return metrics, per_query


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--preds", type=Path, required=True, help="Path to preds_*.json from 3DGraphLLM.")
    parser.add_argument("--out-dir", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.out_dir or args.preds.parent
    metrics, per_query = evaluate_predictions(args.preds)
    write_json(out_dir / "fungraph_eval_metrics.json", metrics)
    write_jsonl(out_dir / "fungraph_eval_per_query.jsonl", per_query)
    print(json.dumps(metrics["overall"], indent=2, sort_keys=True))
    print(f"Wrote {out_dir / 'fungraph_eval_metrics.json'}")
    print(f"Wrote {out_dir / 'fungraph_eval_per_query.jsonl'}")


if __name__ == "__main__":
    main()
