# 3DGraphLLM Adapter Smoke Test

Date: 2026-06-18

## Command

Run from the local 3DGraphLLM repository root:

```bash
PYTHONPATH=. CUDA_VISIBLE_DEVICES=7 /home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python tasks/train.py \
  /home/mz560/fungraph_benchmark_v0/benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/native_3dgraphllm/config_fungraph_eval.py \
  output_dir /home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1 \
  evaluate True \
  pretrained_path ./demo/3dgraphllm.pth \
  model.llama_model_path ./Meta-Llama-3-8B-Instruct \
  model.low_resource True \
  wandb.enable False \
  gpu_num 1 \
  batch_size 1 \
  val_tag fungraph_smoke_1 \
  train_tag fungraph_smoke_1 \
  do_save False
```

## Result

The run completed full model loading and one-sample generation.

Output files:

```text
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/config.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/preds_fungraph_smoke_1.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/scores_fungraph_smoke_1.json
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1/train.log
```

The generated prediction confirms that the FunGraph native packet can pass
through the original 3DGraphLLM model entrypoint.

## Scientific Status

This first smoke test was an integration-only run with fallback tensor files. It
should not be used as evidence for a multimodal performance claim.

## Real Modality Adapter Smoke Test

After replacing the zero fallback tensors with real SceneFun3D point/color,
RGB-D/camera, and relative-geometry adapter features, the one-query full-model
smoke test completed again.

Output directory:

```text
/home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1_real_modalities
```

This confirms that the modality-complete native packet passes through the
original 3DGraphLLM model entrypoint. The features are real SceneFun3D modality
features but not pretrained Uni3D/video-network embeddings.

## FunGraph Evaluator Smoke Test

The real-modality smoke output was evaluated with:

```bash
/home/mz560/3dgraphllm_plus_data/envs/3dgraphllm/bin/python \
  benchmark_clean_v0/exports/3dgraphllm_functional_eval_v1/scripts/evaluate_fungraph_predictions.py \
  --preds /home/mz560/3dgraphllm_plus_data/eval_out/fungraph_smoke_1_real_modalities/preds_fungraph_smoke_1.json
```

Result:

```json
{
  "multiple_valid_obj_token_rate": 0.0,
  "n": 1,
  "n_target_obj_appears_anywhere": 0,
  "n_with_multiple_valid_obj_tokens": 0,
  "n_with_obj_token": 0,
  "n_with_single_valid_obj_token": 0,
  "n_without_obj_token": 1,
  "obj_token_rate": 0.0,
  "primary_acc_all": 0.0,
  "primary_acc_when_obj_token": null,
  "single_valid_obj_token_rate": 0.0,
  "target_obj_anywhere_rate": 0.0
}
```

The model ran end-to-end but did not emit an explicit `<OBJxxx>` token, so the
FunGraph primary localization metric is zero for this smoke sample.
