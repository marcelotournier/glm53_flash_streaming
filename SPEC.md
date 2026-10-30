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

User imposed this restriction explicitly during implementation. Keep it in force across future sessions and experiments.

## Deployment and performance

- Model: GLM-5.3-Flash, locally served on this machine; reuse existing inference engines/recipes.
- Hardware: one RTX 3090 24 GiB, Ryzen 5700G, 27.28 GiB usable RAM, one NVMe SSD. Bound container RAM and disable container swap.
- Docker automation through Makefile; restart policy `unless-stopped`; keep the API loopback-bound by default.
- Prioritize uncached prefill. Target **800–1000 tok/s**, adapting the user's AJ-IQ2_XXS / Project Maya recipe; do not claim the target without local measurements.
- Reference context target: 256K. Validate memory fit, correctness and context independently of throughput.
- Run actual generation/SSE/lifecycle smoke tests. Record prefill and generation rates separately, including failures and short-sample caveats.
- Commit and push settings before experiments; record the exact configuration commit, quant manifest, settings, token counts, cache policy and metrics in JSON and Markdown; commit and push results afterward.
- Exclude weights, logs, caches, build artifacts, scratch research and secrets from Git.
