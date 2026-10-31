# Next session — do not start now

- [ ] Investigate and test **GLM-5.3-Flash IQ3_XXS** against the validated IQ1_S target. Identify the intended publisher/variant first (likely Unsloth UD-IQ3_XXS).
  - **BLOCKED by current size policy for the known Unsloth variant (~120GB).** The100,000,000,000-byte total-weight ceiling remains mandatory. Before any download/preparation/inference, pin and sum exact shard sizes. Proceed only with a verified <=100GB variant or explicit user approval to change the ceiling. This TODO is NOT such approval.
  - Preserve the running IQ1_S weights, pack and winning config in `IQ1S_TARGET.md`. AJ weights/pack were explicitly deleted in026; only its manifest/config/results/image remain.
  - Commit/push settings before experiments. Reuse established engines; no silent expert pruning/skipping/requantization or context reduction.
  - Replay the exact012 repository-code request, cold engine, cached0, natural EOS. Compare against IQ1_S **989–990tok/s prefill /5.02–5.15tok/s generation**; record each rate separately and disclose quant-quality/resource differences.
  - If eligible, validate the32K probe, near256K retrieval, auth/SSE/multi-turn/SSD I/O and Docker recovery. Commit/push receipts and Markdown, including failures.

**Nothing for IQ3 is started:** no download, preparation, image build, inference or benchmark. Current service stays on IQ1_S,256K context,15GiB expert RAM,24GiB cap/no swap, restart unless-stopped.
