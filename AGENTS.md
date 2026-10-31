# Goal / authoritative spec
Local GLM-5.3-Flash Docker service, reusing established NVMe expert streaming, real inference/lifecycle tests, Makefile automation and published experiments. **Read SPEC.md before changing settings/models.** Be concise, don't overengineer.

## CRITICAL: 100 GB total weight ceiling
- Never download for use, prepare, load, serve or benchmark weights above **100,000,000,000 bytes summed over ALL shards**. Not GiB, not per shard, not only active/resident weights. Applies to every engine/format.
- Current **Unsloth UD-IQ1_S =93,087,245,088 bytes**, three full shards, SHA256-verified (`unsloth-iq1s.lock.json`). No expert requantization/pruning/skipping.
- Preserved **AJ-IQ2_XXS =87,346,006,560 bytes**, two verified shards (`aj.lock.json`), unloaded.
- Allowed but NOT downloaded/inference-tested: Unsloth IQ1_M97,579,344,672bytes (`unsloth-iq1m.lock.json`); decode supported but no direct IQ1_M MMQ in pinned build.
- PROHIBITED: Unsloth IQ2_XXS101,844,951,904bytes (94.85GiB UI label still exceeds cap), old IQ4~157GB, EXL3~125GB. User explicitly authorized deleting IQ4/EXL3 caches in018; removed them and old root IQ4 pack. Never restore/use oversized weights. Historical manifests/reports only.
- Hard guard in scripts/download.py; startup/pack/checks enforce file sizes, manifest-bound pack marker and container quant+manifest-SHA identity. Don't bypass.

## Current state: IQ1_S parity goal COMPLETE (2026-10-31)
User asked to preserve AJ, unload it, then make IQ1_S as fast for uncached prefill and generation. **Achieved on exact matched requests**, validated and published. No pending downloads/builds/benchmarks.
- **IQ1S_TARGET.md**: exact winning artifacts/profile/settings, reproduction and caveats. **BASELINE.md**: saved AJ rollback. Preserve both weights/packs and baseline image.
- Running/healthy container `glm53-flash-maya`, `unless-stopped`,24GiB RAM/no swap, read-only IQ1_S mount. API http://127.0.0.1:8000/v1 ; model `glm-5.3-flash`; test key `local`. Loopback only; recreate to change startup args/key.
- Default Makefile **QUANT=unsloth-iq1s**; model dir `models/unsloth-iq1s`, compatibility pack `maya-pack/`. Both full expert originals and unused MTP weights remain, total93GB; MTP disabled at runtime.
- HF source `unsloth/GLM-5.3-Flash-GGUF@a38483c8cd5df544f53d70fb281afe97369d5ab6`. Manifest SHA256 `f11a71472a31b00a9f6daa00cb521745d4f22b5555b68bcd4c2208134a4fd615`. Full hashes/sizes reverified018, receipt results/experiment-018-iq1s-integrity-cleanup.json.
- Winning `engines/maya.json` SHA256 **52c9ae6ed6bec5a3411509a9a4819031dba638c75e9c54e633169ef58e3aa728**, config committed **ffbc2aba6d67a808bbac7563157459cf38dce36b**. Context262144, prefill32768, KV streaming on/32768 positions resident, GPU cache auto, reserve1200MiB.
- Env: **MAYA_GLM_RAM_GB=15**, **MAYA_GLM_READ_CHUNKS=4**, **MAYA_GLM_DISK_READERS=4**, PREFILL_LAND=78, CKPT_EVERY=0, NO_MTP=1. Native CPU lane auto-calibrated,8 threads. Same24GiB/no-swap cap as AJ.
- READERS4 reads whole parts independently for prefill, avoids batched handoff waits. RAM15 reduces decode SSD misses93→67/tok (021 vs12GiB), wait219→164ms/tok. READ_CHUNKS4 is a small gain. No new kernels.
- CKPT_EVERY0 essential: default API driver cuts32K prompt at16K and streams experts twice. Only periodic mid-prompt resume cuts disabled; whole-turn snapshots remain. Timed requests used zero prefix reuse.

## Exact runtime / preserved AJ
- Image **sha256:af26ebe63f5296347660dd6091655235c74279fac8ab8fca1fd690fc488b950d**, tags `glm53-maya:local` and preserved `glm53-maya:aj-baseline`.
- Project Maya (Strata-derived) `cd48762b6d4888205c130238dbc0c7f7904993cf`, ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`, CUDA12.8.1/sm_86, portable AVX2. Build engines/maya.Dockerfile, MIT license in container.
- AJ retained in models/aj/, HF `aj9o9/GLM-5.3-Flash-GGUF@07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2`; originalSHA manifest382861e45b2e9da7ef814647cd94360cd83eb1bf2124093a6c5674b5b7469699.
- Frozen AJ config **engines/aj-baseline.json**, SHA2562b34c875d977b6ca439e1821decefb42dcee63a720e41918e552f7742e03c57f;12GiB tier, default8readchunks/automatic prefill readers. Unit test protects it. Don't overwrite during tuning.
- Restore AJ: **make QUANT=aj IMAGE=glm53-maya:aj-baseline recreate**. Return: make QUANT=unsloth-iq1s recreate. Only one GPU engine at a time; `make start` intentionally rejects different model mounts, use recreate when switching.
- Small upstream BF16 compatibility pack/tokenizer needed for each quant; original experts unchanged. Marker .ready binds to manifest; don't repack a running server. STRATA_GGUF_PY=/opt/llama/gguf-py required by upstream packer (already fixed in image).

## Measurements / proof
Exact commits, requests, answers, manifests, image IDs, native logs/metrics and resource receipts: **EXPERIMENTS.md / results/experiment-*.json**.
- AJ012:25558 uncached repo-doc/code prompt tokens,961.76prefill/4.78gen,375 natural output tokens. AJ011:32058 synthetic tokens1047.02preff; AJ015:255099 tokens968.03preff + exact buried-code retrieval. AJ preserved as target, not running.
- IQ1_S017 unchangedAJprofile12GiB:895.61preff/3.91gen,462output. Correct, below target.
- 019 readchunks4 +pinLAND78 (same observed ring):902.09/3.97, same462output. 020 independentREADERS4:969.17/4.00, same462output; prefill parity first.
- **021 RAM15:988.78preff/5.02gen**,25558/cached0/397output,104.68s; peak21.706GiB.
- **022 cold repeat:990.14preff/5.15gen**,25558/cached0/375output,98.49s; peak22.739GiB. Same exact request/config as021, text differed due CPU/GPU placement/calibration. Both exceed AJ targets, not identical-output-token causal isolation.
- **023 exactAJ011 replay:32058/cached0,1070.58tok/s**, correctParis2tokens. GenN/A: not sustained. Peak22.75GiB.
- **024 exactAJ015 replay:255099/cached0,995.20tok/s**, exact ORCHID-SILVER-7429 retrieved from~85K;11 output/3.36gen short/non-sustained,259.48s; peak22.518GiB, noOOM/restarts. One synthetic needle, not broad quality suite.
- **025 ALL PASS**:9 unit tests, auth bad-key401/model ID, Paris chat/SSE, Tokyo follow-up,26.09GB actual disk reads immediately AFTER255K request (no restart before smoke); then API-SIGKILL automatic Docker recovery, explicit stop stays stopped, explicit start ready. API parent targeted only among direct children of /proc/1 (013 old test wrongly hit NVML helper; fixed and failure preserved).
- Never report tiny smoke replies'18/70tok/s as sustained decode. Reference64GB host20–25tok/s NOT reproduced. Both low-bit quants have quality cost; no BF16 parity or broad throughput claim.

## Hardware / resource safety
- Ryzen7 5700G,8cores/16threads, AVX2/FMA/F16C;27.28GiB usable RAM. RTX3090 24GiB sm_86, PCIe3x16, driver615.71.09. Single970 EVO Plus1TB NVMe, Btrfs; actual aligned O_DIRECT probe passed. No host filesystem/RAID changes.
- Rootless Docker29.8.1/context rootless; NVIDIA CDI `--device nvidia.com/gpu=all`; SELinux bind mounts need `--security-opt label=disable`. No Compose. User Docker service+linger enabled, no sudo needed. Unlimitedmemlock flag rejected by rootless hard limit; CUDA registration works without it.
- Winning peak≤22.75GiB under24cap, steady~20.9–21.3GiB, host available~4GiB. Crucial lesson: peak22.7 atRAM12 included~4.8GB reclaimable inactive_file; actual anon+shmem~18.1GiB. Checked this before RAM15 (idle20.73GiB<22.5guard); don't blindly subtract peak or treat pinned shmem as reclaimable. Don't increase RAM further without measuring.
- About283GiB disk free after018; models/ ~170GiB, only AJ+IQ1_S. Do not touch other user containers/images/workloads (Qwen setup etc), Steam data, or blindly prune Docker. Our obsolete oversized llama container removed; old images unused.

## Operations / measurement discipline
- make up: selected quant download+SHAverify, pinned image, idempotent pack, start/wait. make status/logs/stop/start wait/restart/recreate. Existing containers retain arguments/mounts; recreate after settings edits.
- make verify: full selected shard hashes. make test EXPERIMENT=<unique-id>:unit+real smoke+lifecycle. Do not overwrite old receipt IDs.
- **Matched benchmark:** fresh make restart, then make bench EXPERIMENT=<unique-id> REPLAY_RECEIPT=results/experiment-012-aj-repo-natural.json. Repo text has changed; don't regenerate it for cross-quant comparisons. Alternate exact requests01132K/015near256K. Cached counter0 mandatory; natural EOS, no output token cap.
- New probes: PROMPT_STYLE=repo SOURCE_CHARS=100000; PROMPT_REPEATS=6400 PREFILL_ONLY=1; NEEDLE_TEST=1 PROMPT_REPEATS=51000 (>=250Kactualtokens gate). Short responses are not sustained decode benchmarks.
- Native log /tmp/maya-engine.log in container (append across restarts; last matching phase is current); /metrics has native tiers/hardware, /status only activity. Ignore host transient results/*.log and research/.

## Git / sources / alternatives
- Public **https://github.com/marcelotournier/glm53_flash_streaming**, origin/main. **Commit AND push settings/harness BEFORE experiments; commit/push JSON+Markdown AFTER**, failures included. No dirty tracked settings, simultaneous downloads/builds/GPU engines while timing. Config hash/quant/image/mounts/requests/cache/metrics/outcomes recorded.
- Git identity GLM deployment experiments <glm-experiments@localhost>. No remote history rewrite. Weights/logs/caches/builds/research/secrets ignored; only durable experimentJSON tracked. Real API keys redacted.
- User's original linked AJ/Maya post https://x.com/ItsmeAjayKV/status/2111045102529593718 used sameAJ but46.7GB pinnedRAM/Gen4x16/12-core CPU. Our lower decode expected on smaller resident tiers; nowmatched localAJ target withIQ1_S.
- User requested official Unsloth CLI alternative check: guide/API/start docs and Studio source f863657aebd19f5cd382173c0095854184398a2c inspected. GGUF CLI wraps llama-server; smart offload CPU+mmap, not proven equivalent expert streaming. Guide3.3x mostlyB200longdecode/MTP, pp512 unchanged. Source branch86eb...same historicalbase; forkPR61 link now unrelated, upstream27754 actualGLM. Not installed/inference-benchmarked, no host agent config changes. GuideIQ3example>100GB prohibited. Details ENGINES.md; Maya achieved targets withoutCLI/MTP.
- Exact0xSero/Sybil recipe sybil-solutions/glm-flash-lite located, but125GB EXL3 prohibited/deleted. Other Strata forks Linux-untested, default80GB RAM+pruning, or204GB NVFP4; chose maintained Maya. Historical oversized experiment007 and old llama patch remain only provenance, never rerun prohibited weights.
