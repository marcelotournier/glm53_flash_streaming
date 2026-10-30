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

## Prefill-first objective (user update)

Prioritize **uncached prefill throughput**, aiming for hundreds of tok/s if the hardware can genuinely sustain it. Do not confuse prompt-cache reuse with prefill or claim the target before measuring. Current benchmark uses only 460 prompt tokens, so larger ubatches cannot be evaluated fairly without a longer prompt.

Measured staged reads are ~2.66–2.67 GB/s. A ~130 GB cold expert sweep alone costs roughly 49 s; a 512-token batch therefore has an ideal disk-only ceiling near 10 tok/s. Amortizing a sweep over 2K/4K/8K tokens raises that ceiling to roughly 40/80/160 tok/s **before compute**, but GPU activation/buffer memory may prevent those batch sizes. These are estimates, not measured results. The original 240 tok/s recipe uses two much faster NVMes, 64 GB RAM and a 32 GB GPU, not this host.

Next experiments should lengthen the uncached prompt, increase batch/ubatch (2048, then 4096 if safe), and move resident experts back to RAM if activation VRAM requires it. Preserve the full model and single-request metric; record failed/OOM cases too.

## Longer generation / tuning experiments

Automated entries below are appended by `make bench EXPERIMENT=<id>`.

### 002 — Docker crash recovery (2026-10-30)

- Configuration commit: `1ee8b52`; receipt: [`results/restart.json`](results/restart.json).
- Killed the actual inference child with SIGKILL. Docker automatically restarted it; API ready again. Restart count 0 → 1, policy `unless-stopped`.
- Prefill tok/s: **N/A**; generation tok/s: **N/A** (lifecycle-only test; no generation request).
- Paused at user's request immediately after this test. Sustained 128-token benchmark and tuning have not run yet.

### 003-baseline — 2026-10-30T19:47:38Z

- Configuration commit: `8fb1427bbdcda8e4d2b2ad4603b0b0d5606b85a5`; receipt: [results/experiment-003-baseline.json](results/experiment-003-baseline.json).
- Settings: CPU_MOE=45, cache=24s, batch/ubatch=256, context=8192.
- **Prefill: 4.12 tok/s; generation: 1.34 tok/s.** New prompt=460, cached=0, generated=128; wall=206.34s; disk read=537.62 GB.
- RAM=21.32GiB / 24GiB; GPU used/total=11170, 24576 MiB; outcome=PASS.

### 004-batch512 — 2026-10-30T19:51:17Z

- Configuration commit: `b1f45d35c629d6fba679ecc0ed056d316462f6b5`; receipt: [results/experiment-004-batch512.json](results/experiment-004-batch512.json).
- Settings: CPU_MOE=45, cache=24s, batch/ubatch=512, context=8192.
- **Prefill: 7.43 tok/s; generation: 1.34 tok/s.** New prompt=460, cached=0, generated=128; wall=156.95s; disk read=406.16 GB.
- RAM=21.2GiB / 24GiB; GPU used/total=11300, 24576 MiB; outcome=PASS.

### 005-gpu2 — 2026-10-30T19:54:47Z

- Configuration commit: `5a697ba8f7e08da0f98de4ce0bdda57fe730b5b3`; receipt: [results/experiment-005-gpu2.json](results/experiment-005-gpu2.json).
- Settings: CPU_MOE=43, cache=24s, batch/ubatch=512, context=8192.
- **Prefill: 7.80 tok/s; generation: 1.41 tok/s.** New prompt=460, cached=0, generated=128; wall=149.02s; disk read=384.81 GB.
- RAM=20.62GiB / 24GiB; GPU used/total=18373, 24576 MiB; outcome=PASS.

### 006-gpu3 — interrupted before benchmark (2026-10-30)

- Configuration commit: `e0c5c5757e37b547207e5fd1ac8d5e32d774c397`.
- CPU_MOE=42, cache24s, batch512: startup succeeded; healthy API, GPU21,511/24,576 MiB. Benchmark request did **not** start before the user pause; no benchmark process remains.
- Prefill tok/s: **N/A**; generation tok/s: **N/A** (not measured). Do not treat this as a throughput result.
- User changed priority to maximizing prefill; the next comparison must use longer prompts/larger batches rather than further small-prompt decode tuning.
