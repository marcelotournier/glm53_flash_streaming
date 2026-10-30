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

### 007-maya-iq4 — maya — 2026-10-30T20:25:53Z

- Configuration commit: `4446ee2869461848f1c02ee3e434cad5182a66c1`; receipt: [results/experiment-007-maya-iq4.json](results/experiment-007-maya-iq4.json).
- **Prefill: 187.28 tok/s; generation: 1.65 tok/s.** Prompt=8072, generated=341, cached=0; wall=249.39s. TTFT-based prefill includes first-token overhead; synthetic repeated background, natural-end answer.
- Outcome=PASS; finish=stop; error=None; RAM=15.27GiB / 24GiB.
- Native timings independently report 187.4 tok/s prefill; TTFT 43.10s. Coherent three-paragraph explanation, no reasoning text. Model download paused throughout; Docker image pull still active (possible storage contention). Different prompt size/protocol from experiments003–005, so **not** a matched 24x-engine-speedup claim.

### 008-aj-16k-prefill — maya — 2026-10-30T20:54:44Z

- Configuration commit: `cc037debfca2c87a4230cac42fa363406f522436`; receipt: [results/experiment-008-aj-16k-prefill.json](results/experiment-008-aj-16k-prefill.json).
- **Prefill: 727.09 tok/s; generation: N/A tok/s.** Prompt=16058, generated=2, cached=0; wall=22.57s. TTFT-based prefill includes first-token overhead; synthetic repeated background, natural-end answer.
- Outcome=PASS; finish=stop; error=None; RAM=17.85GiB / 24GiB.
- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.

### 009-aj-32k-prefill — maya — 2026-10-30T20:57:32Z

- Configuration commit: `84b681fe941052d0ec621cfa157be801fb31643d`; receipt: [results/experiment-009-aj-32k-prefill.json](results/experiment-009-aj-32k-prefill.json).
- **Prefill: 731.28 tok/s; generation: N/A tok/s.** Prompt=32058, generated=2, cached=0; wall=44.32s. TTFT-based prefill includes first-token overhead; synthetic repeated background, natural-end answer.
- Outcome=PASS; finish=stop; error=None; RAM=20.44GiB / 24GiB.
- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.

### 010-aj-32k-diagnostic — maya — 2026-10-30T21:02:03Z

- Configuration commit: `d5401df12b9e3eba20234972f338da76675dfab1`; receipt: [results/experiment-010-aj-32k-diagnostic.json](results/experiment-010-aj-32k-diagnostic.json).
- **Prefill: 728.21 tok/s; generation: N/A tok/s.** Prompt=32058, generated=2, cached=0; wall=44.50s. TTFT-based prefill includes first-token overhead; synthetic repeated background, natural-end answer.
- Outcome=PASS; finish=stop; error=None; RAM=17.93GiB / 24GiB.
- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.
- Native diagnostic proved the 32K allocation fits, but the API driver's default **periodic checkpoint every16K** split the prompt into two calls:16384tokens/21.73s +15673tokens/21.57s, each streaming experts again. Next test uses documented `MAYA_GLM_CKPT_EVERY=0` to remove that extra sweep; whole-turn snapshots remain. No new kernels or weight modifications.

### 011-aj-32k-no-periodic-cuts — maya — 2026-10-30T21:04:43Z

- Configuration commit: `1d8dbaf1a2209033af3c973498dc50780a6170e3`; receipt: [results/experiment-011-aj-32k-no-periodic-cuts.json](results/experiment-011-aj-32k-no-periodic-cuts.json).
- **Prefill: 1047.02 tok/s; generation: N/A tok/s.** Prompt=32058, generated=2, cached=0; wall=31.11s. TTFT-based prefill includes first-token overhead; synthetic repeated background, natural-end answer.
- Native log: ONE32057-token pass in29.98s (1069tok/s), vs two16K passes in010. 800–1000 target met/exceeded on this32Ksyntheticprobe, not a promise for every prompt size. Logical context remains262144; no prefix reuse or expert pruning. Actual generation speed remains to be measured on a longer answer.
- Outcome=PASS; finish=stop; error=None; RAM=17.93GiB / 24GiB.
- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.

### 012-aj-repo-natural — maya — 2026-10-30T22:23:27Z

- Configuration commit: `d3c79650c87aa656365a4a1bfe2c8accd19cd0a1`; receipt: [results/experiment-012-aj-repo-natural.json](results/experiment-012-aj-repo-natural.json).
- **Prefill: 961.76 tok/s; generation: 4.78 tok/s.** Prompt=25558, generated=375, cached=0; wall=104.82s. TTFT-based prefill includes first-token overhead; prompt style=repo, natural-end answer.
- Outcome=PASS; finish=stop; error=None; RAM=17.78GiB / 24GiB.

### 013-aj-validation-smoke — AJ Maya functional checks

- Config `6ef9c6a89b899c1f4f0d5df98b16e01c8491c977`; receipt [results/experiment-013-aj-validation-smoke.json](results/experiment-013-aj-validation-smoke.json).
- factual chat: prefill=5.1 tok/s; gen=5.2 tok/s; wall=5.69s (short factual answer, NOT sustained speed).
- SSE repeat (warm): prefill=4.8 tok/s; gen=13.5 tok/s; wall=0.36s (short factual answer, NOT sustained speed).
- multi-turn state: prefill=5.9 tok/s; gen=5.9 tok/s; wall=3.90s (short factual answer, NOT sustained speed).
- PASS: auth rejection, model ID, chat, SSE, multi-turn and 26.84 GB real disk reads.

### 013-aj-validation-restart — harness failure (not a deployment failure)

- Config `6ef9c6a89b899c1f4f0d5df98b16e01c8491c977`; receipt [results/experiment-013-aj-validation-restart-failure.json](results/experiment-013-aj-validation-restart-failure.json).
- Prefill tok/s: N/A; generation tok/s: N/A (lifecycle-only check).
- Test selected the first `python3*` process by PID-directory ordering, which was the NVML telemetry helper, not the API. The API stayed healthy and correctly respawned that helper; Docker restart count stayed0 because its main process never died.
- Fix the test to select only the Python child directly parented by PID1 (`docker-init`), then rerun. Do not claim automatic API crash recovery passed on this failed test.

### 014-aj-final-validation-smoke — AJ Maya functional checks

- Config `b9c867e18b24f0d9d86b462501ca71e1eb7c3ae0`; receipt [results/experiment-014-aj-final-validation-smoke.json](results/experiment-014-aj-final-validation-smoke.json).
- factual chat: prefill=6.3 tok/s; gen=46.6 tok/s; wall=4.34s (short factual answer, NOT sustained speed).
- SSE repeat (warm): prefill=30.4 tok/s; gen=70.4 tok/s; wall=0.06s (short factual answer, NOT sustained speed).
- multi-turn state: prefill=6.6 tok/s; gen=17.3 tok/s; wall=3.21s (short factual answer, NOT sustained speed).
- PASS: auth rejection, model ID, chat, SSE, multi-turn and 20.08 GB real disk reads.

### 014-aj-final-validation-restart — AJ Maya lifecycle

- Config `b9c867e18b24f0d9d86b462501ca71e1eb7c3ae0`; receipt [results/experiment-014-aj-final-validation-restart.json](results/experiment-014-aj-final-validation-restart.json).
- PASS: API SIGKILL automatically recovered; explicit stop stayed stopped; explicit start restored readiness.
- Prefill tok/s: N/A; generation tok/s: N/A (lifecycle-only experiment).

### 015-aj-near256k-retrieval — maya — 2026-10-30T22:43:14Z

- Configuration commit: `1553b65d07f26148f3e577007ac7cbc573735477`; receipt: [results/experiment-015-aj-near256k-retrieval.json](results/experiment-015-aj-near256k-retrieval.json).
- **Prefill: 968.03 tok/s; generation: 3.03 tok/s.** Prompt=255099, generated=11, cached=0; wall=267.07s. TTFT-based prefill includes first-token overhead; prompt style=repeated, natural-end answer.
- Exact `ORCHID-SILVER-7429` retrieved from the sole audit record roughly one-third into the document (~85K tokens). This verifies retrieval well beyond the32K GPU-resident DSA window, not just a large configured API limit. One synthetic needle, not a general long-context quality claim. Native prefill968.6tok/s; peak memory19,757,936,640bytes (~18.40GiB) below24GiB cap. The11-token generation rate is NOT sustained.
- Outcome=PASS; finish=stop; error=None; RAM=17.85GiB / 24GiB.
- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.
