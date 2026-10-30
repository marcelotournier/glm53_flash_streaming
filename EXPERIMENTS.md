# GLM-5.3-Flash experiments

Hardware: RTX 3090 24 GiB, Ryzen 5700G (8 physical cores), 27.28 GiB usable RAM, single Samsung 970 EVO Plus NVMe. Rootless Docker. Full unpruned Unsloth IQ4_XS, HF revision `621d456e93e926e4b52f85cff5f634358c1828f9`; pinned engine and patch in Dockerfile/vendor.

## Measurement rules

- **Prefill tok/s** and **generation tok/s** are llama.cpp's separate server-reported rates, not total HTTP time divided by output tokens. Record actual newly evaluated prompt tokens and cached tokens.
- Short three-token smoke replies prove functionality, **not sustained generation performance**. The longer benchmark requests 128 output tokens and requires at least 64.
- Each benchmark records its configuration Git commit, exact launch arguments, image ID, prompt, token counts, timings, wall time and resource/disk counters in `results/experiment-*.json`. Generated reports and receipts are committed after each experiment. Weights, binaries and transient logs are excluded from Git.
- `cache_prompt=false` and a zero cached-token assertion make benchmark prefill comparable. Expert-cache warmth is separate: each configuration is restarted before benchmarking; its first request starts with an empty expert cache. Later smoke tests are explicitly warm/mixed.
- No BF16-equivalence or broad model-quality claim: these are functional/performance tests on quantized weights.

## Initial implementation / smoke experiments

Defaults: `CPU_MOE=45`, `EXPERT_CACHE=24s`, `BATCH=256`, `CTX=8192`, `THREADS=8`, `IO_THREADS=8`, 24 GiB container RAM, one request slot. Two 4.24 GiB staging buffers; all five shard FDs confirmed O_DIRECT (`0140000` octal).

| ID / experiment | Prefill tok/s | Gen tok/s | New prompt / generated tokens | Cache / outcome |
|---|---:|---:|---|---|
| 000a: latest upstream metadata startup | N/A | N/A | No inference | Failed: architecture renamed to `glm5-next`; fixed by pinning compatible prior HF revision. Other four shards byte-identical. |
| 000b: compatible metadata startup | N/A | N/A | No inference | Passed: model loaded in ~11 s, healthy API; 16.48 GiB idle RAM, ~10.7 GiB inference VRAM. |
| 001a: initial factual chat | 1.23 | 1.38 | 26 / 3 | Cold expert cache, 0 cached prompt tokens. Correct answer `Paris`; HTTP 22.62 s. |
| 001b: SSE repeat | 1.44 | 4.08 | 4 / 3 | Warm/prefix-reused. Correct `Paris`, finish + `[DONE]`; HTTP 3.27 s. Rates from server task 6 log, not an extrapolation. |
| 001c: multi-batch prefill | 4.15 | 2.44 | 425 / 3 | 9 cached prefix tokens (434 total prompt). Correct `Paris`; HTTP 103.31 s. 42-layer staged sweep: 131.7 GB at 2.67 GB/s. |

Receipt for 001: [`results/experiment-001-smoke.json`](results/experiment-001-smoke.json). All requests together read **332.85 GB** of actual disk data; no server restarts/OOM. Post-test RAM 21.4 GiB, GPU 11,202 MiB including desktop. Authentication rejection also passed. These initial tests preceded Git initialization; preserved here rather than inventing a historical commit.

## Longer generation / tuning experiments

Automated entries below are appended by `make bench EXPERIMENT=<id>`.
