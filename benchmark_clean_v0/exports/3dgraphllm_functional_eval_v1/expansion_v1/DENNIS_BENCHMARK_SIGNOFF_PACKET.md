# Dennis Benchmark Signoff Packet - AI Pre-Review v1

This packet prepares a decision point. It does not replace Dennis signoff.

## Recommended Decisions

1. Approve the benchmark structure if you agree with a two-level evaluation: old frozen 683-row export for reproduction, and reviewed expansion candidates for stronger diagnostics.
2. Do not call the 116 functional candidates final until wording review is accepted.
3. Treat the minimal-pair candidates as diagnostics, not primary leaderboard rows, unless pair validity is manually confirmed.

## Functional Candidate Triage

- Total functional freeze candidates: 116
- AI recommended accept after human spot-check: 69
- Need wording revision before signoff: 38
- Need broader human review: 9
- Exact relation types: 21

Primary risk: many source labels contain slash-style merged labels such as `dresser / chest of drawers`; these are valid object labels but awkward natural language, so they should be rewritten before paper release.

## Minimal-Pair Triage

- Total pair candidates: 60
- AI recommended accept after human spot-check: 16
- Secondary diagnostic only: 34
- Need review or reject: 10

Primary risk: several auto-mined pairs do not both belong to the 116 functional candidate split, and a few anchor-object pairs keep the same target answer. These are useful diagnostics but weak as primary paper evidence.

## Files To Inspect

- `expansion_v1/ai_prereview_v1/functional_ai_prereview_v1.csv`
- `expansion_v1/ai_prereview_v1/minimal_pair_ai_prereview_v1.csv`
- `expansion_v1/ai_prereview_v1/functional_ai_recommended_accept_v1.jsonl`
- `expansion_v1/ai_prereview_v1/minimal_pair_ai_recommended_accept_v1.jsonl`

## Example Wording Revisions Needed

- `exp_func_v1_0029_v0`: Use the faucet / handle to control the water flow for the bathtub.
- `exp_func_v1_0030_v0`: Use the faucet / handle to control the water flow for the sink.
- `exp_func_v1_0118_v0`: Use the handle / faucet to control the water flow for the bathtub.
- `exp_func_v1_0117_v0`: Use the handle / faucet to control the water flow for the bathroom sink.
- `exp_func_v1_0153_v0`: Use the faucet / knob / handle to control the water flow for the bathroom sink.
- `exp_func_v1_0171_v0`: Use the faucet / handle to control the water flow for the kitchen sink.
- `exp_func_v1_0024_v0`: Use the handle / faucet to control the water flow for the sink.
- `exp_func_v1_0000_v0`: Use the switch panel / electric outlet to turn the ceiling light on or off.
- `exp_func_v1_0125_v0`: Use the light switch to turn the chandelier / ceiling light on or off.
- `exp_func_v1_0126_v0`: Use the light switch to turn the chandelier / ceiling light on or off.
- `exp_func_v1_0154_v0`: Use the button / knob to control the water flow for the bathroom sink.
- `exp_func_v1_0031_v0`: Use the button / knob to control the water flow for the bathtub.

## Signoff Questions

1. Should slash-label objects be rewritten into one canonical human-facing label before final split release?
2. Should expansion rows without previous depth-tested RGB-D crop metadata remain in the final split if they have pointcloud-render evidence?
3. Should minimal pairs be reported as a separate diagnostic table rather than merged into the main benchmark score?
4. Is the paper claim allowed to say `195 unique source functional relation instances` and `116 reviewed balanced candidates`, while avoiding `500 independent functional relations`?

## Current Guardrail

All AI pre-review outputs keep `paper_use_allowed=false`. A later human-reviewed manifest must explicitly record Dennis approval before paper use.
