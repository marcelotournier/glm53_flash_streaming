# GLM-5.3-Flash · RTX 3090 · NVMe streaming

Local Docker server using the existing **Project Maya** (Strata-derived) engine and **Unsloth UD-IQ1_S**, **93.09 GB** of weights. It now matches/exceeds the saved AJ recipe's measured uncached prefill and generation on the matched workloads.

- **Current 64 GB RAM profile/results:** [RAM64_RESULTS.md](RAM64_RESULTS.md): 40 GiB expert cache, **9.91–10.23 tok/s generation / ~1265 tok/s uncached prefill** on the matched 25,558-token request.
- **Historical 32 GB target, exact settings/weights:** [IQ1S_TARGET.md](IQ1S_TARGET.md).
- **Historical AJ baseline:** [BASELINE.md](BASELINE.md), `engines/aj-baseline.json`. AJ weights/pack were deleted at the user's request; config/manifest/image/results remain, not an instant local rollback.
- **IQ3 completed:** [IQ3_RESULTS.md](IQ3_RESULTS.md); exact pinned IQ3 manifest has a user-authorized 121 GB exception. IQ3 preserved/stopped; IQ1_S is active.
- **MTP tests:** [MTP_RESULTS.md](MTP_RESULTS.md); keep MTP off (n2/n3 were slower on the earlier 32 GB setup, not retested after this upgrade).
- **All experiments, configuration hashes and receipts:** [EXPERIMENTS.md](EXPERIMENTS.md).

## Hard limit and quality

**Default limit: 100,000,000,000 bytes summed across all shards.** Only the exact pinned IQ3 manifest has an explicit 121 GB exception; see [SPEC.md](SPEC.md). Active IQ1_S totals **93,087,245,088 bytes**, pinned in `unsloth-iq1s.lock.json`; all three full-file SHA256s and sizes passed verification. The downloader, pack/startup and benchmark guards enforce the limit. Old oversized IQ4 and incomplete EXL3 weights were deleted at the user's request; their measurements are historical only.

All routed experts retained, original GGUF expert weights unchanged. No expert skipping, pruning, LoRA, abliteration or cloud fallback. MTP is disabled. Low-bit quantization has a real quality cost; neither quant is claimed equivalent to BF16. CPU/GPU arithmetic placement can change greedy answers between starts.

## Measured on this host

RTX3090 24GiB, Ryzen5700G, now **58.73 GiB usable RAM** after the 64 GB DDR4 upgrade (previously 27.28 GiB), single PCIe3 NVMe. **Same exact25,558-token repository-code/docs request** replayed from experiment012, fresh engine each arm, cached prompt tokens0, temperature0/seed42, natural-end generation without an output cap:

| Experiment / quant | Expert RAM | Uncached prefill | Generation | Output tokens |
|---|---:|---:|---:|---:|
|012 AJ saved baseline|12GiB|961.76 tok/s|4.78 tok/s|375|
|017 IQ1_S initial|12GiB|895.61 tok/s|3.91 tok/s|462|
|020 IQ1_S independent prefill readers|12GiB|969.17 tok/s|4.00 tok/s|462|
|**021 IQ1_S winning profile**|**15GiB**|**988.78 tok/s**|**5.02 tok/s**|397|
|**022 IQ1_S cold repeat**|**15GiB**|**990.14 tok/s**|**5.15 tok/s**|375|
|036 IQ1_S unchanged profile, upgraded host|15GiB|988.02 tok/s|5.11 tok/s|397|
|**037 IQ1_S 64 GB tuned**|**40GiB**|**1265.74 tok/s**|**10.23 tok/s**|344|
|**038 IQ1_S 64 GB cold repeat**|**40GiB**|**1265.40 tok/s**|**9.91 tok/s**|301|

Additional exact-request comparisons:

| Workload | AJ uncached prefill | IQ1_S uncached prefill |
|---|---:|---:|
|32,058-token synthetic short-answer probe|1047.02 tok/s|**1070.58 tok/s**|
|255,099-token buried-code retrieval|968.03 tok/s|**995.20 tok/s**|

The255K request retrieved the exact audit code buried roughly one-third into the document. One synthetic needle is not a broad long-context quality evaluation. Its11-token reply and the32K probe's2-token reply are **not sustained decode measurements**. The longer answers above are the decode samples; outputs differ, so comparisons are same-task, not identical-token work. These numbers do not promise the same speed for every prompt size/style. The64GB reference's20–25tok/s decode is **not** reproduced here.

## What made IQ1_S fast

Pinned upstream engine, no new inference kernels. Current IQ1_S default: **`engines/iq1s-64gb.json`**, **40 GiB expert RAM / 50 GiB container limit, no container swap**. Original **`engines/maya.json`** remains unchanged for 32 GB hosts; historical hashes/source/image IDs in IQ1S_TARGET.md.

- **32768-token prefill**, **262144 context**, KV streaming on; auto elastic GPU expert cache,1200MiB VRAM reserve.
- **`MAYA_GLM_CKPT_EVERY=0`**: prevents the API driver splitting a32K prompt into two16K expert sweeps. Whole-turn snapshots remain; periodic mid-prompt resume checkpoints are disabled.
- **`MAYA_GLM_DISK_READERS=4`**: independent whole-part prefill readers improved copy overlap.
- **`MAYA_GLM_READ_CHUNKS=4`**, **`MAYA_GLM_PREFILL_LAND=78`**.
- **40 GiB expert RAM tier** after the upgrade, up from15GiB: disk reads fell ~67→23/output token. Original 15 GiB/24 GiB profile is preserved. Keep OS/desktop headroom; host swap is still enabled, although container swap is disabled. See RAM64_RESULTS.md for measured peaks and caveats.

No prefix reuse was used in timed comparisons. Typical chat prefix caching remains available.

## Run / operate

Linux, rootless Docker with NVIDIA CDI, Python3, make, curl and local NVMe. Rootless Docker user service and login linger are already enabled on this host. No sudo, repartitioning, RAID or daemon changes required.

```sh
make up                       # IQ1_S default now REQUIRES the upgraded 64 GB host
make status
make logs
make test EXPERIMENT=<unique-id>
make stop                     # explicitly stopped: stays stopped across daemon/host restarts
make start wait
make recreate                 # apply changed config/image; does not delete model data
make verify                   # rehash all selected shards
```

For a 32 GB host / original profile: `make MAYA_CONFIG="$PWD/engines/maya.json" MAYA_MEMORY=24g recreate`. Other quants keep their previous 24 GiB default. Memory/config changes require recreation, not just restart.

**`--restart unless-stopped`** handles process crashes; health status alone does not restart a live process. Real auth/chat/SSE/multi-turn/SSD-I/O smoke passed after the255K request; actual API-SIGKILL recovery and manual stop/start semantics passed too (025), alongside nine unit tests. Server left healthy and running.

API: **http://127.0.0.1:8000/v1** · model **`glm-5.3-flash`** · test key **`local`**. Loopback binding intentional. Use a private key and authenticated TLS proxy before remote exposure; recreate after changing startup arguments.

```sh
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer local' -H 'Content-Type: application/json' \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"Why is the sky blue?"}],"stream":true,"chat_template_kwargs":{"enable_thinking":false}}'
```

AJ is no longer locally installed. A future authorized restore requires re-download/hash verification, then stopping IQ1_S before packing and recreating; see BASELINE.md. Do not run a bare AJ recreate against missing weights, and never run both engines on this GPU. No model downloads or pack changes were needed for the RAM upgrade.

Packing converts only required small tensors/tokenizer for upstream compatibility; it does not requantize the experts. Manifest markers make it idempotent. Repacking a running server is refused. Existing containers retain startup arguments; **recreate** when changing settings, weights or keys.

## Reproduce measurements

Commit/push settings BEFORE timing; commit/push receipts and Markdown AFTER, failures included. Use unique experiment IDs; keep downloads, builds and other GPU workloads out of measurements.

```sh
make restart
make bench EXPERIMENT=<unique-id> \
  REPLAY_RECEIPT=results/experiment-012-aj-repo-natural.json
```

Replay is important: regenerating repo text now changes the benchmark corpus. Other probes: `REPLAY_RECEIPT=results/experiment-011-aj-32k-no-periodic-cuts.json` or `results/experiment-015-aj-near256k-retrieval.json`, restarting first. For new workloads, `PROMPT_STYLE=repo SOURCE_CHARS=100000`, `PROMPT_REPEATS=6400 PREFILL_ONLY=1`, or `NEEDLE_TEST=1 PROMPT_REPEATS=51000` are available.

Receipts capture configuration commit, manifest, image, mounts/identity, full request/answer, native timings, cache counts, peak memory and native I/O diagnostics. Prefill is prompt tokens/TTFT (includes first-token overhead); decode excludes prefill. Short factual smoke rates are not decode benchmarks.

## Reused work and alternatives

- [Project Maya](https://github.com/mw00/project-maya), pinned `cd48762b6d4888205c130238dbc0c7f7904993cf`, ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`, CUDA12.8.1/sm_86 + AVX2. MIT license included in container.
- [Unsloth GLM GGUF](https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF), IQ1_S revision pinned in manifest. [Original Z.ai model](https://huggingface.co/zai-org/GLM-5.3-Flash).
- [Original AJ/Maya post](https://x.com/ItsmeAjayKV/status/2111045102529593718) and [AJ quant](https://huggingface.co/aj9o9/GLM-5.3-Flash-GGUF): replicated first; configuration/results retained, local weights deleted in026.
- Official **Unsloth CLI/GLM guide alternative** reviewed in [ENGINES.md](ENGINES.md). Its GGUF backend is llama-server; advertised3.3x is mainly B200 long-context decode/MTP, not a demonstrated NVMe-prefill gain here. CLI not locally inference-benchmarked; no installer/UI/host agent changes needed for achieved Maya results.
- 0xSero/Sybil NVMe recipe and earlier MIT llama.cpp streaming patch investigated; oversized weights prohibited/deleted. Research/provenance in ENGINES.md and vendor/.

No model weights, logs, scratch research, caches or secrets tracked in Git. Live operations memory: [AGENTS.md](AGENTS.md).
