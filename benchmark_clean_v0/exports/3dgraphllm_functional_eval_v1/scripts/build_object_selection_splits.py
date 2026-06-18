#!/usr/bin/env python3
"""Build controlled object-selection 3DGraphLLM eval splits.

These splits preserve the same scenes, target objects, and query ids as the
base FunGraph native annotations, but replace the free-form task prompt with an
explicit answer protocol: exactly one ``<OBJxxx>`` token and no explanation.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

EXPORT_DIR = Path(__file__).resolve().parents[1]
NATIVE_DIR = EXPORT_DIR / "native_3dgraphllm"

SOURCE_SPLITS = {
    "functional_500": "fungraph_functional_500_val.json",
    "human_133": "fungraph_human_133_val.json",
    "long_range_50": "fungraph_long_range_50_val.json",
}


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.write("\n")


def object_selection_prompt(task_prompt: str) -> str:
    prompt = " ".join(str(task_prompt).split())
    return (
        "Select the single object in the 3D scene that best satisfies this functional request. "
        f"Request: {prompt} "
        "Answer with exactly one object id token in the format <OBJ###>. "
        "Do not explain. Do not output more than one object id."
    )


def convert_rows(rows: list[dict[str, Any]], eval_type: str) -> list[dict[str, Any]]:
    converted: list[dict[str, Any]] = []
    for row in rows:
        new_row = dict(row)
        new_row["base_prompt"] = row.get("prompt", "")
        new_row["prompt"] = object_selection_prompt(str(row.get("prompt", "")))
        new_row["eval_type"] = eval_type
        converted.append(new_row)
    return converted


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--native-dir", type=Path, default=NATIVE_DIR)
    args = parser.parse_args()

    native_dir = args.native_dir
    counts: dict[str, int] = {}
    built: dict[str, list[dict[str, Any]]] = {}
    for split, filename in SOURCE_SPLITS.items():
        source_path = native_dir / filename
        rows = json.loads(source_path.read_text(encoding="utf-8"))
        eval_type = f"{split}_objselect"
        converted = convert_rows(rows, eval_type)
        out_path = native_dir / f"fungraph_{split}_objselect_val.json"
        write_json(out_path, converted)
        counts[eval_type] = len(converted)
        built[split] = converted

    smoke = built["functional_500"][:1]
    write_json(native_dir / "fungraph_objselect_smoke_1_val.json", smoke)
    counts["objselect_smoke_1"] = len(smoke)
    print(json.dumps(counts, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
