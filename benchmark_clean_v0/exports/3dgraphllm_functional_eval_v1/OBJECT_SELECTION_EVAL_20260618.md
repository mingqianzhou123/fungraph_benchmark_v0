# Object-Selection Functional Eval: 2026-06-18

This run evaluates a controlled 3DGraphLLM answer protocol on the frozen
FunGraph `functional_500` split. The scenes, target objects, and query ids are
unchanged from the base native annotations, but each prompt asks the model to
answer with exactly one `<OBJxxx>` token.

This test is meant to separate two failure modes:

- answer-protocol failure: the model does not emit a parseable object id;
- grounding failure: the model emits a parseable object id, but selects the
  wrong object.

## Added Splits

`scripts/build_object_selection_splits.py` writes:

```text
native_3dgraphllm/fungraph_functional_500_objselect_val.json
native_3dgraphllm/fungraph_human_133_objselect_val.json
native_3dgraphllm/fungraph_long_range_50_objselect_val.json
native_3dgraphllm/fungraph_objselect_smoke_1_val.json
```

The generated prompt form is:

```text
Select the single object in the 3D scene that best satisfies this functional request.
Request: <original FunGraph prompt>
Answer with exactly one object id token in the format <OBJ###>.
Do not explain. Do not output more than one object id.
```

## Smoke Checks

The one-query object-selection smoke test showed that the original decode length
causes token repetition:

- `model.max_txt_len=64`: emitted multiple object ids.
- `model.max_txt_len=8`: still emitted multiple object ids.
- `model.max_txt_len=2`: emitted one object id, but it was wrong on the smoke
  query.

For the full controlled run, `model.max_txt_len=2` was used to reduce repeated
object-token output and force the test closer to first-token object selection.

## Full 500 Command

Run from `/home/mz560/3D scene graph project/3DGraphLLM`:

```bash
PYTHONPATH=. CUDA_VISIBLE_DEVICES=7 \
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python tasks/train.py \
  /home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm/config_fungraph_eval.py \
  output_dir /home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618 \
  evaluate True \
  pretrained_path ./demo/3dgraphllm.pth \
  model.llama_model_path ./Meta-Llama-3-8B-Instruct \
  model.low_resource True \
  model.max_txt_len 2 \
  wandb.enable False \
  gpu_num 1 \
  batch_size 1 \
  val_tag fungraph_functional_500_objselect \
  train_tag fungraph_functional_500_objselect \
  do_save False
```

## Outputs

```text
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/config.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/preds_fungraph_functional_500_objselect.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/scores_fungraph_functional_500_objselect.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/train.log
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/fungraph_eval_metrics.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_functional_500_objselect_max2_20260618/fungraph_eval_per_query.jsonl
```

## FunGraph Metrics

Primary metric: first valid explicit `<OBJxxx>` token must match the target
object id.

```json
{
  "n": 500,
  "n_with_obj_token": 103,
  "n_without_obj_token": 397,
  "n_with_single_valid_obj_token": 102,
  "n_with_multiple_valid_obj_tokens": 1,
  "n_target_obj_appears_anywhere": 21,
  "obj_token_rate": 0.206,
  "single_valid_obj_token_rate": 0.204,
  "multiple_valid_obj_token_rate": 0.002,
  "target_obj_anywhere_rate": 0.042,
  "primary_acc_all": 0.04,
  "primary_acc_when_obj_token": 0.1941747572815534
}
```

Compared with the original free-form run, object selection raises primary
accuracy from 0.2% to 4.0% and greatly reduces repeated valid object tokens.
However, 397/500 predictions still contain no object token, and only 20/500
queries are correct under the primary metric.

## Interpretation

The controlled prompt shows that part of the previous failure was an output
protocol mismatch. But the remaining performance is still far below what would
support a strong positive claim about original 3DGraphLLM functional grounding
on FunGraph.

This is useful evidence for our benchmark direction: the adapter can run
3DGraphLLM end to end, and the evaluator can separate protocol compliance from
object-selection correctness. Scientifically, the next gate should not be more
prompt polishing alone. It should test whether a real adaptation step, such as
a trained object-selection head, calibrated candidate ranking, or oracle-feature
upper bound, can close the gap.
