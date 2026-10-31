# Goal and authoritative spec
Implement a local GLM-5.3-Flash Docker server using established NVMe expert-streaming recipes. Automate with Makefile, restart unless manually stopped, test real inference, and record/publish experiments. Read **SPEC.md** before changing models or settings.

## CRITICAL: never use weights larger than 100 GB
- Hard ceiling: **100,000,000,000 bytes total across all model weight shards**, not per shard, active parameters, resident memory, or GiB. Applies to every engine/format, including benchmarks and preparation for use.
- Active **AJ-IQ2_XXS =87,346,006,560 bytes**; `aj.lock.json` pins both shards and hashes.
- Allowed Unsloth alternatives: **UD-IQ1_S =93,087,245,088 bytes**, **UD-IQ1_M =97,579,344,672 bytes**. Pinned manifests are `unsloth-iq1s.lock.json` / `unsloth-iq1m.lock.json`. Header/kernel compatibility checked; full inference NOT tested on these.
- **UD-IQ2_XXS =101,844,951,904 bytes is prohibited** despite being 94.85 GiB. The earlier 157 GB IQ4 and 125 GB EXL3 candidates are prohibited too. Their inference/downloads were explicitly stopped when user imposed the cap; do not resume them. Historical reports/manifests remain only for provenance.
- `scripts/download.py` enforces the cap before download/check/startup; active startup also checks every shard size and a manifest-bound pack marker. Do not bypass these guards.

## Current task — Unsloth IQ1_S comparison (user request)
- User requests preserving the successful AJ target, unloading it, and making Unsloth IQ1_S match its uncached prefill and sustained generation.
- AJ server explicitly STOPPED; GPU down to112MiB. Preserve AJ weights/pack/image. **BASELINE.md + engines/aj-baseline.json** freeze exact artifacts, hashes, performance and rollback instructions.
- Allowed IQ1_S manifest93,087,245,088bytes verified for cap; download into models/unsloth-iq1s (never use larger IQ2_XXS). No AJ inference during tuning.
- Compare by replaying exact experiment012 request (repo source has changed), natural EOS, cached0, rates separately. Targets961.76 prefill /4.78 sustained gen tok/s;32K probe1047.02, near256K968.03.
- IQ1_S download running in background, log results/unsloth-iq1s-download.log (PID67053 initially); discover liveprocess rather than assume. Needs~93GB, filesystem125GiB free at start; preserve30GiB+ free, no other downloads.
- Added QUANT=unsloth-iq1s default / QUANT=aj rollback to frozenconfig, manifest-SHA+quant labels and testidentityguards. Benchmark supports REPLAY_RECEIPT for exact012 request and includes native /metrics +config +memorypeak. Coldrestart forreplays, enforcecached0.
- UseralsoasksUnslothCLIalternative: officialguide+API+start docsread; Studio sourcepinnedf863657aebd19f5cd382173c0095854184398a2c inspected. CLI GGUF backedbyllama-server; guide3.3x mostlyB200longdecode/MTP, prefillunchanged; RAMmmapspillnotprovenMaya-styleNVMe. Guidebranch86eb...sameoldbase; forkPR61nowstale/unrelated. DocumentedENGINES.md; NOT benchmarked/installed. GuideIQ3example>100GBprohibited.
- Experiment017 planned: IQ1_S same32K/256K/12GiB/noCKPTcuts profile, exact012 replay; target961.76 prefill/4.78 gen. If needed bounded upstream tuning: RAMtier15GiB (under24GiBcap), readchunks4 vs8, CPUlane controls; no expert skipping/pruning/requantization. Next downloadverify/pack/start, baseline then inspect actual bottlenecks. Commit/push each arm.

## Previous known-good deployment (now unloaded)
- Active recipe is **Project Maya (Strata-derived) + AJ-IQ2_XXS**, the EXACT quant/engine in user's post: https://x.com/ItsmeAjayKV/status/2111045102529593718 . Confirmed original post + screenshots, not inferred from a search snippet.
- Public repo: https://github.com/marcelotournier/glm53_flash_streaming ; origin/main. Use authenticated `gh`; never publish credentials.
- Container: `glm53-flash-maya`; local image `glm53-maya:local`; API http://127.0.0.1:8000/v1 ; model `glm-5.3-flash`; default test key `local`. Loopback-only, auth enforced. `make stop` explicitly stops it.
- Weights: `models/aj/`, pinned HF revision `07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2`. Both full shards SHA256-verified. Small upstream compatibility pack (~0.88 GiB) converts required small tensors to BF16; original expert weights unchanged. Marker: `models/aj/maya-pack/.ready` matches `aj.lock.json` hash.
- Engine source `mw00/project-maya@cd48762b6d4888205c130238dbc0c7f7904993cf`, ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`; CUDA12.8.1 sm_86, portable AVX2. Docker build in `engines/maya.Dockerfile`; no new inference kernels.
- Settings: `engines/maya.json`: 262144 logical context, KV streaming on (32768 DSA positions resident), 32768 prefill batch, auto elastic GPU expert cache, 1200 MiB VRAM reserve, explicit **12 GiB expert RAM tier**, no MTP (AJ quant omits head), no skipping/pruning/LoRA/abliteration. Container **24 GiB RAM, no swap**. Native GLM metrics report 8 CPU threads.
- Essential speed fix: **MAYA_GLM_CKPT_EVERY=0**. Default API driver otherwise cuts at16K even with32K prefill, streaming experts twice. Whole-turn snapshots remain; periodic mid-prompt resume checkpoints disabled. Source/docs confirm this is an upstream setting, not numerical shortcut.
- Native diagnostic log inside container: `/tmp/maya-engine.log`; host transient logs in ignored `results/*.log`. `/metrics` exposes engine/GPU/tier data; `/status` is only current activity.

## Hardware / environment
- Ryzen7 5700G,8 physical cores/16 threads, AVX2/FMA/F16C;27.28 GiB usable RAM.
- RTX3090 24 GiB, PCIe3 x16; NVIDIA driver615.71.09. Single Samsung970 EVO Plus1TB NVMe, Btrfs, actual O_DIRECT probe passed. No formatting/RAID/mount changes.
- Rootless Docker29.8.1, context rootless, NVIDIA CDI `--device nvidia.com/gpu=all`; bind mounts need `--security-opt label=disable`. No Compose.
- User Docker service + login linger already enabled. No sudo used. Unlimited memlock flag is rejected by rootless hard limit; CUDA host registration works without it.
- Do not touch user's other containers/images/workloads (e.g. existing Qwen setup). Removed ONLY our obsolete stopped oversized `glm53-flash` container to prevent accidental startup. Historical oversized weights/images remain unused; do not blindly prune Docker or delete cached weights.

## Measurements / validation
All exact configuration commit hashes, recipes, token counts, cache states and receipts are in **EXPERIMENTS.md** and `results/experiment-*.json`. Main findings:
- 007: historical oversized IQ4 Maya test187.28tok/s, no longer an allowed model. Never rerun it under current cap.
- 008 AJ:16058 uncached prompt,727.09tok/s; tiny2-token answer, NOT sustained decode.
- 009/010 AJ:configured32K batch but default16K periodic cuts;~731/728tok/s over32058 uncached tokens. Native log proved two16K calls.
- 011 AJ, checkpoint cuts disabled:32058 uncached tokens, **1047.02tok/s** TTFT-based; correct short answer, native1069tok/s/one pass. Synthetic repeated background, no reused prefix.
- 012 AJ:less-repetitive100000-character own-repo docs/code,25558 prompt/cached0, **961.76tok/s prefill +4.78tok/s generation**,375 natural output tokens,104.82s total. Coherent three-paragraph Rayleigh/sunset answer. This is sustained decode sample; reference64GB host's20–25tok/s NOT reproduced here.
- 013:auth/chat/SSE/multiturn/disk reads passed. Initial lifecycle harness accidentally killed Python NVML helper (PID ordering), not API; failure recorded honestly. API respawned helper, no Docker crash occurred.
- 014:corrected lifecycle targets ONLY Python direct child of `/proc/1/task/1/children`. **ALL PASSED**:7 unit tests, bad-key401, model ID, Paris chat/SSE, Tokyo follow-up,20.08GB actual disk reads; real API SIGKILL auto-recovery, manual stop stays stopped, explicit start restores readiness. Short smoke gen rates are NOT benchmark results.
- 015 AJ: **255099 uncached prompt tokens**, **968.03tok/s prefill**, exact buried-code retrieval (`ORCHID-SILVER-7429`) from one-third through document;11 natural output tokens,267.07s total. Memory peak19,757,936,640bytes (~18.40GiB), below24GiB cap. One synthetic near-full-context needle check, not broad long-context quality suite.
- 016 PASSED after015 without restart: auth/chat/SSE/multiturn and26.93GBactualdiskreads, verifying state reset after the255K request. Implementation complete; server left healthy and running unless-stopped. No pending downloads/builds/benchmarks. Optional Unsloth inference/quality/speed comparison is future work, not needed to establish achieved AJ prefill target.

## Operations
- `make up`: allowed AJ download+hash verify, pinned image build, idempotent pack, start/wait.
- `make start wait`, `make stop`, `make restart`, `make recreate`, `make logs`, `make status`.
- Edit tracked `engines/maya.json`, then **make recreate** to apply settings/file mounts. Do not repack a running server; `maya-pack-force` refuses this. Existing containers retain original CLI args.
- `make bench EXPERIMENT=<unique-id>`; `PROMPT_STYLE=repo SOURCE_CHARS=100000` for docs/code, `PROMPT_REPEATS=6400 PREFILL_ONLY=1` for32K probe. Natural EOS, no imposed generation cap. `NEEDLE_TEST=1 PROMPT_REPEATS=51000` is near256K retrieval (requires >=250000 actual prompt tokens).
- `make test EXPERIMENT=<unique-id>`: unit + real smoke + lifecycle. JSON/Markdown append-only experiment names; don't overwrite prior receipts.
- Bench script rejects dirty tracked settings; restart before comparative arms, no simultaneous downloads/builds. Report uncached prompt processing separately from generation, not total HTTP time/output tokens. Tiny answers are not sustained decode.

## Git / publication requirements
- **Commit AND push as work progresses.** Commit/push settings/harness BEFORE an experiment; record its full configuration hash, model manifest, image, mounts, prompt/counters, outcome and metrics. Commit/push receipts and Markdown AFTER each run, failures included.
- Local Git automation identity: GLM deployment experiments <glm-experiments@localhost>. No remote history rewrite.
- `.gitignore` excludes weights, logs, scratch `research/`, caches/build artifacts, secrets and transient results; only durable `results/experiment-*.json` / historical restart receipt are tracked. Redact real API keys in receipts.
- Repo live requirements: SPEC.md; user-facing setup/current metrics README.md; recipe/alternative analysis ENGINES.md; full measurement ledger EXPERIMENTS.md.

## Research and caveats
- User's actual linked AJ post uses87GB hand-mixed2.23bpw quant, not157GB IQ4. Screenshots show46.7GB pinnedRAM +12.8GB VRAM experts, Gen4x16,12-core CPU. Our smaller RAM tier/Gen3 platform explains lower decode. Quantization has real quality cost; don't claim BF16 parity.
- Also located exact 0xSero/Sybil single3090 NVMe recipe: `sybil-solutions/glm-flash-lite`, image digest `aa74200f16c86588b101be2315aed2f643d148559179eef52a02599016b56e69`. Its125GB EXL3 weights violate cap, so preparation/inference stopped and targets not included in main Makefile. Engine mechanisms inspired investigation; not active deployment.
- Current upstream Strata README doesn't list GLM. Windows-first isichan GLM port Linux untested; Indras fork defaults80GB+LoRA/pruning; archived NVFP4 Strata fork needs204GB model. Chose maintained Linux-native Strata-derived Maya instead.
- Unsloth93GB IQ1_S is preferred allowed Unsloth prefill candidate: inspected actual shard headers;56 routed IQ1_S tensors have direct MMQ support.97.6GB IQ1_M has42 IQ1_M tensors with decode support but no direct MMQ path in this build. These are compatibility findings, not successful inference/quality/speed claims. Do not download/claim an improvement without a separate measured experiment.
