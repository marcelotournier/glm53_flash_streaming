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
- Allowed Unsloth alternatives: **UD-IQ1_S =93,087,245,088 bytes** and **UD-IQ1_M =97,579,344,672 bytes** (pinned manifests `unsloth-iq1s.lock.json` / `unsloth-iq1m.lock.json`). Compatibility is assessed in ENGINES.md; neither is silently made the active model.
- Unsloth **UD-IQ2_XXS =101,844,951,904 bytes is prohibited**, even if a UI labels it 94.85 GiB. Do not confuse GB with GiB.

User imposed this restriction explicitly during implementation. Keep it in force across future sessions and experiments.

## Current task (2026-10-31)

User requests **preserving and unloading the AJ baseline**, then making **Unsloth UD-IQ1_S** match its **961.76 tok/s uncached prefill and4.78 tok/s sustained generation**. Saved exact config, image, weights, hashes and rollback in **BASELINE.md**. AJ is stopped, not a competing GPU workload. Compare with the exact experiment012 request, not changed repo text. IQ1_S remains93,087,245,088bytes; no model above100GB permitted. Investigate official Unsloth CLI as an alternative too; separate source/guide findings from actual local benchmark results.

## Previous verified AJ implementation (2026-10-30, now unloaded)

- Active allowed quant: **AJ-IQ2_XXS, 87,346,006,560 bytes**, pinned and hash-verified. Project Maya/Strata-derived CUDA engine; 32K prefill, periodic 16K checkpoint cuts disabled, 256K configured context.
- Experiment 012: **25,558 uncached repository-code/doc prompt tokens at 961.76 tok/s**; 375 natural-end output tokens at **4.78 tok/s**.
- Experiment 015: **255,099 uncached prompt tokens at 968.03 tok/s**; exact buried audit-code retrieval passed; peak container RAM 19,757,936,640 bytes (~18.40 GiB), below 24 GiB cap.
- Experiment 014: real Docker auth/chat/SSE/multi-turn/disk-I/O smoke, automatic API-crash recovery and explicit stop/start semantics passed. Experiment 016 repeated the smoke successfully after the near-full-context request, without restarting. Seven model-free automation tests pass.
- The prefill target is demonstrated on these workloads. The 64 GB reference's 20–25 tok/s sustained decode is not reproduced; short-answer smoke rates are not substitutes for the 375-token measurement. Unsloth alternatives are size/kernel-compatibility checked, not inference-benchmarked.

## Deployment and performance

- Model: GLM-5.3-Flash, locally served on this machine; reuse existing inference engines/recipes.
- Hardware: one RTX 3090 24 GiB, Ryzen 5700G, 27.28 GiB usable RAM, one NVMe SSD. Bound container RAM and disable container swap.
- Docker automation through Makefile; restart policy `unless-stopped`; keep the API loopback-bound by default.
- Prioritize uncached prefill. Target **800–1000 tok/s**, adapting the user's AJ-IQ2_XXS / Project Maya recipe; do not claim the target without local measurements.
- Reference context target: 256K. Validate memory fit, correctness and context independently of throughput.
- Run actual generation/SSE/lifecycle smoke tests. Record prefill and generation rates separately, including failures and short-sample caveats.
- Commit and push settings before experiments; record the exact configuration commit, quant manifest, settings, token counts, cache policy and metrics in JSON and Markdown; commit and push results afterward.
- Exclude weights, logs, caches, build artifacts, scratch research and secrets from Git.
