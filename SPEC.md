# GLM-5.3-Flash server specification

## CRITICAL — quantization size restriction

**Never download for use, load, serve, or benchmark a quantization whose total model weights exceed 100 GB.**

- **100 GB means 100,000,000,000 bytes**, summed across all weight shards/files of the model, not per shard and not just its active experts.
- Applies to every format and engine, including GGUF, EXL3, Strata/Maya, llama.cpp, and alternatives.
- No exception for CPU/NVMe offload, lower resident RAM, or faster benchmark results.
- Size must be checked against a pinned, hash-verified manifest before download or startup.
- Prior experiments with larger models remain historical records only. Those runtimes are stopped and must not be restarted.
- The 157 GB Unsloth IQ4_XS and 125 GB EXL3 candidates are **prohibited** under this requirement.
- The exact user-linked **AJ-IQ2_XXS** candidate is **87,346,006,560 bytes** across two shards and is within the limit. Its pinned manifest is `aj.lock.json`.
- User-selected active **UD-IQ1_S =93,087,245,088 bytes**, fully verified and benchmarked. Allowed **UD-IQ1_M =97,579,344,672 bytes** remains compatibility-only, not inference-tested. Manifests: `unsloth-iq1s.lock.json` / `unsloth-iq1m.lock.json`.
- Unsloth **UD-IQ2_XXS =101,844,951,904 bytes is prohibited**, even if a UI labels it 94.85 GiB. Do not confuse GB with GiB.

User imposed this restriction explicitly during implementation. Keep it in force across future sessions and experiments.

## Current verified target (2026-10-31): Unsloth parity achieved

User requested preserving/unloading AJ, then matching its961.76tok/s prefill and4.78tok/s natural-answer generation with IQ1_S. **Achieved on exact-request comparisons**; artifacts and reproducibility in [IQ1S_TARGET.md](IQ1S_TARGET.md), historical AJ recipe in [BASELINE.md](BASELINE.md). AJ weights/pack were subsequently deleted at the user's request (026); only config/manifest/image/results remain.

- 021/022: exact25,558-token AJ012 request replay, cached0, **988.78–990.14tok/s prefill and5.02–5.15tok/s generation**,397/375 natural output tokens. No output cap. Same task, not identical output text; CPU/GPU arithmetic placement can cause greedy drift.
- 023: exact32,058-token AJ011 short probe, **1070.58tok/s** uncached vsAJ1047.02.
- 024: exact255,099-token AJ015 buried-code retrieval, **995.20tok/s** uncached vsAJ968.03; exact code recovered from~85K. Short11-token decode is not a sustained sample.
- Winning profile:32Kprefill,256Kcontext/KV streaming,15GiB expert RAM,4independentprefillreaders,4readchunks,78landing slots, periodiccheckpointcuts0. Same24GiB/no-swap cap; largest observed benchmark peak22.75GiB. NoMTP/expert skipping/pruning/requantization.
- 025: nine unit tests, authenticated chat/SSE/multi-turn/real disk reads immediately after255K, API-SIGKILL automatic Docker recovery and explicit stop/start passed. IQ1_S left healthy/running unless-stopped; AJ was unloaded at validation and its weights/pack later deleted in026.
- User-authorized cleanup018 removed unused IQ4/EXL3 weights/old IQ4 pack, preserved AJ/IQ1_S, and fully reverified all3IQ1_S hashes. Further user-authorized026 removed AJ weights/pack; now about365GiB free, only IQ1_S remains.
- Official Unsloth CLI guide/source reviewed as alternative (ENGINES.md), not locally inference-benchmarked; no claim its B200/MTP numbers apply here. Maya met targets without it. These measurements are not broad quality/speed guarantees.

## Next session TODO — do not start now

Test IQ3_XXS as requested in [TODO.md](TODO.md), but **the100GB ceiling remains unchanged**. Known Unsloth UD-IQ3_XXS (~120GB) is blocked unless an eligible <=100GB variant is verified or the user explicitly approves changing the limit. No IQ3 downloads, preparation, builds or tests started; do not treat this TODO as a cap override.

## Previous verified AJ implementation (2026-10-30, weights now deleted)

- Preserved allowed baseline: **AJ-IQ2_XXS, 87,346,006,560 bytes**, pinned and hash-verified. Project Maya/Strata-derived CUDA engine; 32K prefill, periodic 16K checkpoint cuts disabled, 256K configured context.
- Experiment 012: **25,558 uncached repository-code/doc prompt tokens at 961.76 tok/s**; 375 natural-end output tokens at **4.78 tok/s**.
- Experiment 015: **255,099 uncached prompt tokens at 968.03 tok/s**; exact buried audit-code retrieval passed; peak container RAM 19,757,936,640 bytes (~18.40 GiB), below 24 GiB cap.
- Experiment 014: real Docker auth/chat/SSE/multi-turn/disk-I/O smoke, automatic API-crash recovery and explicit stop/start semantics passed. Experiment 016 repeated the smoke successfully after the near-full-context request, without restarting. Seven model-free automation tests pass.
- The prefill target is demonstrated on these workloads. The 64 GB reference's 20–25 tok/s sustained decode is not reproduced; short-answer smoke rates are not substitutes for the 375-token measurement. IQ1_S is now separately benchmarked above; IQ1_M remains compatibility-only.

## Deployment and performance

- Model: GLM-5.3-Flash, locally served on this machine; reuse existing inference engines/recipes.
- Hardware: one RTX 3090 24 GiB, Ryzen 5700G, 27.28 GiB usable RAM, one NVMe SSD. Bound container RAM and disable container swap.
- Docker automation through Makefile; restart policy `unless-stopped`; keep the API loopback-bound by default.
- Prioritize uncached prefill. Target **800–1000 tok/s**, adapting the user's AJ-IQ2_XXS / Project Maya recipe; do not claim the target without local measurements.
- Reference context target: 256K. Validate memory fit, correctness and context independently of throughput.
- Run actual generation/SSE/lifecycle smoke tests. Record prefill and generation rates separately, including failures and short-sample caveats.
- Commit and push settings before experiments; record the exact configuration commit, quant manifest, settings, token counts, cache policy and metrics in JSON and Markdown; commit and push results afterward.
- Exclude weights, logs, caches, build artifacts, scratch research and secrets from Git.
