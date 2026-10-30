# Goal
Implement GLM-5.3-Flash locally in Docker, reusing established NVMe expert-streaming recipes. Use Makefile automation, restart unless manually stopped, and run real Docker server smoke tests. Work autonomously. Keep this file as live memory.

## Git / publication workflow (user requirement)
- Public remote: https://github.com/marcelotournier/glm53_flash_streaming (origin, main). Use authenticated `gh` CLI to manage GitHub; never publish credentials.
- **Commit AND push as work progresses.** Before every experiment, commit/push the exact settings and harness; record that full commit hash in the JSON receipt and EXPERIMENTS.md. After each experiment (including failures), record separate prefill/gen tok/s, token counts, cache state, settings, outcome and limitations, then commit/push the receipts + Markdown report.
- Keep weights, logs, scratch research, caches, build outputs and secrets out of Git via .gitignore. Preserve small reproducibility manifests, vendored licensed patch, scripts and durable JSON receipts.
- Do not rewrite existing experiment commit history just to tidy scratch files; untrack them in a cleanup commit. No pushes containing real API keys. Final working tree should be clean and pushed.

## Machine (2026-10-30)
- Ryzen 7 5700G: 8 cores / 16 threads, AVX2; 27.28 GiB usable RAM.
- RTX 3090: 24 GiB, sm_86; NVIDIA driver 615.71.09.
- Single Samsung 970 EVO Plus 1TB NVMe, Btrfs, initially 514 GiB free.
- Rootless Docker 29.8.1, context rootless, NVIDIA CDI (`--device nvidia.com/gpu=all`). No Compose plugin. SELinux: use `--security-opt label=disable` for read-only bind model directory.
- User Docker service already enabled; login linger already enabled. No sudo required.

## Research / decision
- User's '0xzero' likely 0xSero: https://github.com/0xSero/GLM-5.3-Flash-DGX-Spark . Read recipe: needs 128 GB unified RAM, ARM/Blackwell kernels; not usable unchanged on 3090 + 27 GB RAM. Keep all experts rather than pruning (their quality evidence favors lower-bit full models over expert removal).
- Reuse https://github.com/xMytze/glm53-ssd-streaming at 9900b7ab1f32ee3fcfb19c83d4862aaee9b46f5e, based on freedomljc upstream PR #25294 + full-layer prefill staging and CUDA correctness fix.
- Patch vendored in `vendor/`, MIT license. SHA256 d544c2b5f566c0b02483e1a8d6a09db0345c27a1c959b0a194fff8dac05d279b.
- Exact Unsloth llama.cpp base 86ebfef2c6a0f3359a2a07d2c215d61b0fa885c9. Build CUDA 12.8.1, sm_86, jobs=4.
- Model: unpruned Unsloth UD-IQ4_XS, five shards ~157 GB, pinned revision and SHA256s in `model.lock.json`. First shard is metadata-only (~9 MB), intentionally upstream rewritten; download all five.
- NVMe O_DIRECT expert reads, all 42 routed MoE layers on CPU (`CPU_MOE=45`, layer count includes 3 leading dense layers), dense tensors on GPU, exact 24 expert-cache slots/layer (~12 GiB), two 4.24 GiB staging sets, initial 8K context / batch 256, one request slot. 24 GiB container RAM limit, no swap. TF32 disabled per recipe. No mirror/prefetch on this single SSD.
- Read the patch: <32-token multi-wave batches require at least 3*top_k = 24 slots; initial 10 GiB idea would be too small. Use `EXPERT_CACHE=24s`.
- Tested rootless unlimited memlock: prohibited by daemon hard limit; removed `--ulimit memlock=-1`. Actual CUDA host registration will be checked in server logs. Rootless-compatible settings avoid sudo.
- Native chat template supports `reasoning_effort=low/high/max`, NOT `enable_thinking=false`; corrected launch kwargs to low effort + clear_thinking.
- Also examined sqliteai/warp (CPU, requires separate conversion) and strata-glm (Blackwell NVFP4); chose existing GGUF/llama.cpp patch instead.

## Work in progress
- Created Dockerfile, Makefile, resumable hash-verified downloader, pinned model manifest.
- Background `make download` -> `results/download.log`; `make image` -> `results/build.log`.
- Implemented wait/smoke/restart-test scripts, README and six passing model-free unit tests (`make check`). Smoke includes auth, factual chat, SSE, >256-token staged prefill, real disk-read counters and streaming log evidence. Receipts will be in results/.
- CUDA build/run images pinned by digest in Dockerfile. Build ongoing (350 compilation units); model download ongoing with two resumable workers.
- Build succeeded, CUDA binary --version/--help executed in Docker with GPU; results/engine-{version,help}.txt. Model download resumed with four workers to avoid a serial last-shard bottleneck.
- Important adaptation: recipe's `--n-cpu-moe 42` leaves THREE ~3.3 GiB routed layers on GPU (it counts dense leading layers). Default changed to 45 to stream all 42 routed layers and fit 24 GB VRAM.
## Pause checkpoint (historical, 2026-10-30 ~15:34 local)
- All five full-model shards downloaded and hash verified. No background download/build/test jobs remain.
- First startup failed: HF latest revision renamed GGUF architecture `glm5next` -> `glm5-next`, incompatible with the recipe's pinned engine. Fixed by pinning the PREVIOUS official HF revision `621d456e93e926e4b52f85cff5f634358c1828f9` in model.lock.json. Only metadata shard changed (9,429,859 bytes, SHA eec97673e9acb38f8682250e778f88991e731771bab8d3c0b787985949aacefa); the other ~157 GB are byte-identical, reverified. Incompatible metadata retained at research/incompatible-upstream-header.gguf for audit. Do not revert to latest HF metadata.
- Recreated container `glm53-flash`: RUNNING, Docker HEALTHY, restart policy unless-stopped, restart count 0. Real 320,759,404,382-parameter IQ4_XS model loaded in ~11 seconds. /health and authenticated /v1/models pass at http://127.0.0.1:8000, model glm-5.3-flash, API key local.
- Idle usage: 16.48 GiB host/container RAM of 24 GiB cap, ~10.7 GiB inference VRAM. Two staging sets are actually 4.24 GiB each, both successfully pinned with CUDA despite not requesting unlimited rootless memlock.
- Full real-model GENERATION/SSE/multi-batch prefill and automatic crash-recovery tests are NOT run yet. Six automation unit tests passed earlier. Do not call implementation finished until real generation/recovery checks pass.
- Next on resume: `make smoke` then `make restart-test`, inspect correctness/performance, update README/AGENTS and final receipts. Potential test issue: default server verbosity suppresses INFO-level O_DIRECT startup evidence; smoke.py currently requires 'O_DIRECT' in docker logs. Either increase log verbosity via a supported flag before recreation, or verify actual O_DIRECT open-file flags instead. Do not weaken real I/O verification. Update README initial staging estimate and pin-compatibility note after tests.
- Paused agent work, leaving the requested persistent Docker server running. `make stop` explicitly stops it.

## Resumed / experiments (2026-10-30)
- User requests gen+prefill tok/s reports in Markdown and experiments tracked with Git. Initialized local main repo with local automation identity (GLM deployment experiments <glm-experiments@localhost>); later user explicitly requested public GitHub remote and ongoing commits/pushes (workflow above).
- Initial real smoke PASS: correct Paris answer for chat, SSE, and 434-token staged prompt; bad-key rejected; actual five open GGUF FDs checked for O_DIRECT bit (0140000), not inferred from CLI. Actual disk reads +332.85 GB, no restart.
- Initial smoke rates (short 3-token replies only): cold prefill 1.23 / gen 1.38 tok/s; warm SSE prefill 1.44 / gen 4.08; multi-batch prefill 4.15 / gen 2.44. Not sustained decode benchmarks. RAM after 21.4 GiB, GPU 11202 MiB including desktop.
- Full measurements in EXPERIMENTS.md, original receipt results/experiment-001-smoke.json. Added make bench/script for >=64-token decode, zero reused prompt tokens, Git-linked JSON receipts and automatic Markdown entries. Commit settings BEFORE each bench; commit results AFTER.
- Automatic crash recovery PASS: inference SIGKILL, Docker restarted automatically, restart count 0→1, healthy API again. Receipt results/restart.json; experiment 002 in EXPERIMENTS.md.
- Paused again immediately after crash test; then resumed per user request to publish and continue. Public-repo cleanup excludes research scratch and transient results while retaining original history.
- Public remote created with gh and pushed. Cleanup commit 8fb1427 removes scratch research/transient results from tracked tree; no weights or real keys published.
- Experiment 003 baseline PASS, configuration 8fb1427bbdcda8e4d2b2ad4603b0b0d5606b85a5: freshly restarted CPU_MOE=45, cache24s, batch256. Prefill 4.12 tok/s (460 new prompt, cached0), gen 1.34 tok/s (128 output), wall206.34s, disk537.62GB, RAM21.32GiB, GPU11170MiB including desktop. Full receipt and Markdown tracked; commit/push next.
- Experiment 004 PASS, config b1f45d35c629d6fba679ecc0ed056d316462f6b5: ONLY BATCH256→512. Prefill7.43 tok/s (~80% above baseline), gen1.34 tok/s unchanged, 460 uncached prompt/128 output, wall156.95s, disk406.16GB, RAM21.2GiB, GPU11300MiB. Retain batch512. Receipt/report committed+pushed after test.
- Experiment 005 candidate: ONLY CPU_MOE45→43 at batch512/cache24s, retaining the last two routed layers in VRAM. Baseline GPU11300MiB leaves ~13GiB; expected additional resident experts fit with headroom. Recreate and test; revert if OOM/correctness/performance regresses. No result claimed yet.
- Next: compare results, final smoke including a >current-ubatch prompt, crash/manual-stop checks and documentation. Commit AND push settings before experiments and results after. Keep final server running unless-stopped.

