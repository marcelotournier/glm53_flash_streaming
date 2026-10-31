# Engine investigation (2026-10-30)

**Latest hard constraint: no quant above 100,000,000,000 bytes total weights (SPEC.md).** The125GB EXL3 and157GB IQ4 entries below are historical investigation only; downloads/inference stopped and startup/packing are now blocked by size guards. The active deployment is 87.35 GB AJ-IQ2_XXS; eligible Unsloth alternatives are assessed separately below.

## Exact user-linked AJ / Maya recipe (confirmed from the post)

Post: https://x.com/ItsmeAjayKV/status/2111045102529593718 (2026-10-16). Retrieved both the post and original screenshots, not inferred from a search snippet. It explicitly credits **Project Maya** and links **aj9o9/GLM-5.3-Flash-GGUF, AJ-IQ2_XXS**. This is distinct from the Sybil/0xSero EXL3 recipe below.

- Exact quant: **87,346,006,560 bytes**, two shards, 2.23 bpw, pinned HF revision `07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2` in `aj.lock.json`. The earlier IQ4_XS test used ~157 GB, so it was not a reproduction of this post.
- Its dense/attention/shared weights are Q6_K, sensitive gates/indexer Q8_0, routers/norms F32, routed gate/up IQ2_XXS and down IQ2_XXS with higher precision on edge layers. All routed experts retained; unused MTP block removed by the quantizer.
- Screenshot: 863 tok/s prefill, 20.5 tok/s displayed decode, 7.7K/256K request context, 12.8 GB VRAM expert residency and **46.7 GB pinned RAM**, 48.3% VRAM hit rate; PCIe Gen4 x16, 12-core/24-thread CPU. Different memory residency than this host's ~12 GiB RAM tier and PCIe Gen3.
- Quality tradeoff is real: model card reports AJ-IQ2_XXS WikiText PPL 4.2314 vs BF16 2.2474 and KLD0.7072 (their 30-chunk experiment, not ours). Do not silently call it the same-quality model as IQ4_XS.
- **Implemented and tested locally:** pinned Maya + hash-verified AJ, small BF16 compatibility pack, 32K prefill, 12 GiB RAM tier, 256K context. Disabling periodic16K checkpoint cuts (`MAYA_GLM_CKPT_EVERY=0`) was crucial. Repository-code/docs prefill **961.76 tok/s**, natural375-token decode **4.78 tok/s**; near-256K exact retrieval **968.03 tok/s**. Details/configuration commits: [EXPERIMENTS.md](EXPERIMENTS.md).
- EXL3 preparation/downloads are stopped and prohibited under the cap, not resumable candidates for current work. Preserve free disk space; no concurrent downloads/builds during benchmarks.

## Unsloth CLI / official GLM-5.3 guide alternative (2026-10-31)

Sources: [GLM-5.3-Flash guide](https://unsloth.ai/docs/models/glm-5.3-flash), [API/unsloth run](https://unsloth.ai/docs/basics/api), [unsloth start](https://unsloth.ai/docs/integrations/unsloth-start). Inspected Studio source at `unslothai/unsloth@f863657aebd19f5cd382173c0095854184398a2c` (`offload_planner.py`, `llama_cpp.py`, `llama_server_args.py`, prebuilt resolver and CLI).

- **Yes, `unsloth run` officially supports this model** and forwards llama-server flags. `unsloth start` additionally configures coding-agent connections; it is not an inference kernel. GGUF serving is backed by llama-server. Current CLI also exposes other engines, but that does not establish IQ1_S/GLM NVMe support in them.
- Guide's advertised3.3x gain is primarily long-context **decode**, plus MTP; on its **1xB200** IQ1_S test, pp512 is1121.80→1122tok/s (unchanged), tg32@65536 is20.66→48.99. MTP short-context58.6→86.5tok/s at two drafts. These are remote fully-resident measurements, NOT our3090 results.
- Guide recommends ~100GB combined RAM+VRAM for1-bit. Our51.28GiB combined physical RAM+VRAM is much less, and working memory also needs room. Studio's inspected smart offload planner explicitly spills weight groups to CPU and retains mmap when RAM is insufficient so the model can page. `--load-mode dio` is not evidence of Maya-style per-expert asynchronous NVMe staging/elastic prefill lending. The planner does not document a comparable expert cache/staging pipeline.
- Build-from-source guide points at `unslothai/llama.cpp` branch `glm5next/upstream`, currently **86ebfef2c6a0f3359a2a07d2c215d61b0fa885c9**, already the base of our historical NVMe-patched image (`glm53-flash:local`, image8b3ab391...). Current Studio prebuilts can be newer; do not claim this is a test of the current CLI. Guide's fork PR61 link is now unrelated (`IQ1_XS/XXS/XXXS`); upstream [PR27754](https://github.com/ggml-org/llama.cpp/pull/27754) contains the actual GLM changes/measurements. Check branch SHA, not stale link numbers.
- Guide examples use **UD-IQ3_XXS (~120GB), prohibited** here. Only our pinned/verified **UD-IQ1_S93,087,245,088bytes** may be used in an alternative arm; reuse local files, do not let CLI defaults download another quant. Disable server-side tools for a performance test (the CLI enables execution tools on localhost by default); no need to install its UI or alter host agent configurations.
- Assessment: useful alternative launcher/API, and MTP is worth considering if measured decode needs it; **not an established shortcut to961tok/s prefill on this host**. First measure IQ1_S with known-good Maya. A later bounded llama-server/CLI arm must use the same exact prompt, memory cap and quant, with no simultaneous GPU server, and honest failure/timeout receipts.
- **Local CLI prefill tok/s: N/A; generation tok/s: N/A — source/documentation review only, no inference run or speed claim.** Raw guide/source downloads remain ignored in research/; no remote installer was executed.

## Unsloth alternatives below the hard limit

Pinned repository revision `a38483c8cd5df544f53d70fb281afe97369d5ab6`, checked via the HF blob API (not rounded UI sizes):

| Quant | Total shard bytes | Decimal GB | Allowed? |
|---|---:|---:|---|
| UD-IQ1_S | 93,087,245,088 | 93.087 | Yes; `unsloth-iq1s.lock.json` |
| UD-IQ1_M | 97,579,344,672 | 97.579 | Yes; `unsloth-iq1m.lock.json` |
| UD-IQ2_XXS | 101,844,951,904 | 101.845 | **No**, even though 94.85 GiB |

Header-only range reads of both data shards, parsed with upstream Maya's own `gguf_reader`, verified the actual routed-tensor formats (including the unused MTP head):

- IQ1_S: IQ3_XXS39, IQ2_XXS28, IQ1_S56, IQ4_XS3, Q3_K1, Q2_K2.
- IQ1_M: IQ3_XXS39, IQ2_XXS42, IQ1_M42, IQ4_XS3, Q3_K1, Q2_K2.

The pinned Maya build includes direct CUDA MMQ cases for IQ1_S, IQ2_XXS, IQ3_XXS, IQ4_XS, Q2_K and Q3_K. Its CPU native-expert tests explicitly cover the real UD-IQ1_S GLM geometry. **UD-IQ1_S is therefore the preferred Unsloth prefill candidate.** IQ1_M has decode support but no direct CUDA MMQ path in this build; those expert layers use a fallback, so a smaller bit label alone does not imply faster prefill.

These are source/header compatibility checks, **not successful inference or speed measurements**. Full weight downloads must be hash-verified and pack/model smoke tests must pass before adopting either. AJ is now deployed and tested; either Unsloth variant would require a separate future experiment, without concurrent downloads during benchmarks. Neither Unsloth candidate is silently substituted for AJ in the active configuration.

## Located the single-3090 0xSero recipe

**[sybil-solutions/glm-flash-lite](https://github.com/sybil-solutions/glm-flash-lite)** (formerly `glm53-flash-offload`). This is the relevant GLM recipe, not the DGX Spark recipe found initially. Public Sybil code and `ghcr.io/0xsero` image lineage identify the connection. Source inspected at `6fe077da79a4d6fc842cf9f50cb703e4409924ca`.

Exact published NVMe image: `ghcr.io/sybil-solutions/glm53-flash-offload@sha256:aa74200f16c86588b101be2315aed2f643d148559179eef52a02599016b56e69` (v4.6-nvme). EXL3 3.05bpw weights at `turboderp/GLM-5.3-Flash-exl3`, revision `332ab457b709b7ba30dd9a448be5de03b80a7ac9`. Our `exl3.lock.json` pins content hashes, including dense/config/tokenizer files; no weights are committed.

### What makes it fast

- Prefill is an **8192-token GPU batch**, separate from decode, rather than small batches through a CPU expert compute path.
- A **117.3 GB aligned record store**, one 4 KiB-aligned record per complete expert. Deep O_DIRECT queue into pinned RAM; several-layer lookahead and overlapping NVMe reads, copy streams and GPU work.
- **Elastic VRAM expert cache**: lends up to 10 GiB back to prefill staging/activations; reclaims it for decode. No permanently reserved full expert layers starving large-batch prefill.
- Exclusive GPU/RAM expert residency avoids duplicate copies; a persistent host controller avoids per-layer host synchronization. A CPU lane handles RAM-resident decode misses.
- `nvme-exact` disables approximate CPU decode; prefill uses the exact EXL3 GPU path in either mode. "Exact" is relative to these EXL3 weights, **not BF16 equivalence**.

Published reference (not our measurements): 16 GiB cap, single RTX 3090, ~650 tok/s at 8K; ~1010 tok/s over a 93K prompt. **Reference host has EPYC 24 cores, eight RAM channels, PCIe 4 x16 and four Samsung 9100 PRO drives in RAID0 (~26 GB/s).** Our single PCIe 3 NVMe (~2.7 GB/s measured), 8-core two-channel host cannot inherit those numbers.

### Historical adaptation plan — prohibited weights, do not run

The following records the earlier plan only; main Makefile no longer includes these targets and weight-use guards reject the125GB manifest. No active EXL3 deployment exists. The plan reused the published image unchanged, with no new inference kernels. `engines/exl3.mk` automates pull/download/O_DIRECT probe/store packing+verification/start/wait/stop. 24 GiB no-swap cap, upstream small-host budget explicitly enabled, 1 GiB recurrent-state cache, 128 prefill-ring slots, CPU lane cores 2–7, feeder 0/controller 1/readers 8–15, 16 I/O threads. CDI + SELinux bind-mount settings match this rootless Docker host. No unlimited-memlock request (not permitted here; CUDA registration itself previously worked).

This host uses Btrfs, not upstream's recommended xfs/ext4. Its actual aligned O_DIRECT write/read probe passed on the store directory. The image's own probe and full packed-record verification must also pass before serving; **no filesystem repartitioning or loop devices**.

Preparation requires ~125.3 GB checkpoint +117.3 GB store plus image space; checked ~359 GiB free before starting. The oversized GGUF model is NOT an allowed fallback. Never run competing inference engines on the GPU during timing.

## Other engines investigated

| Engine | Assessment / test plan |
|---|---|
| Current pinned llama.cpp streaming patch | Historical smoke-tested engine: 7.80 prefill /1.41 gen tok/s at460 prompt tokens, NOT an8K comparison. Its157GB test quant is prohibited, not a current baseline/fallback. |
| **Project Maya** (`mw00/project-maya`, Strata-derived) | **Chosen and deployed with allowed87GB AJ:** Linux-native GLM, elastic expert tiers, tensor-core prefill, 32GB-class hosts. Pinned source `cd48762b6d4888205c130238dbc0c7f7904993cf`, upstream ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d` in `engines/maya.Dockerfile`; sm_86, portable AVX2, AJ GGUF with upstream's required BF16-compatible small-tensor pack. Explicit 12 GiB RAM tier, auto elastic prefill, no MTP, no skipping/LoRA/pruning. `engines/maya.mk` automates build/pack/start/wait. |
| `isichan-ai/Strata-GLM` | Historical investigation using oversized IQ4_XS (prohibited here); reported ~580 tok/s on 5090+128 GB. GLM path Linux explicitly untested, Windows-first packaging; less attractive than its actively maintained Maya lineage. Pin `6feb85fed9f994380b201c105851a740ec99d5e8` if tested. Disable expert skipping for fair quality. |
| `Indras-Mirror/Strata-GLM` | Linux support, but current defaults require ~80 GB free RAM, Maya-S-v2 weights and runtime abliteration/soft pruning. Do not adopt its defaults on this 27 GiB host or silently change model behavior. |
| `sergqwer/strata-glm` | Archived NVFP4 experiment (pin `ed37419fccd0c52e07d26d526a29c2098f547843`), 5090/128 GB/two NVMe, separate ~204 GB checkpoint. Prohibited by current size cap. |
| Current upstream `Niko1221/Strata` | Current README lists Qwen/DeepSeek, not GLM. Do not assume a Qwen engine can load GLM unchanged. Prefer a GLM-specific maintained fork/Maya. |

### Preparation checks

- Maya CUDA sm_86 build succeeded (152 compilation units). Initial pack attempt at configuration `d924430` stopped safely before serving: upstream's `_paths.py` requires `STRATA_GGUF_PY` explicitly even when the module imports via PYTHONPATH. Added that environment variable to the image; no inference happened, prefill/gen metrics N/A.
- Earlier EXL3 preparation was stopped on imposition of the100GB cap; no download/build jobs remain. The oversized llama container was stopped then removed; its cached weights/images are unused. No repartitioning or changes to the user's other workloads.
- Active AJ passed real auth/chat/SSE/multi-turn/disk-read smoke, near-256K buried-code retrieval, Docker API-crash recovery and explicit stop/start semantics. A final smoke also passed immediately after the255K-token request.

Results, failures, limits, configuration Git hashes and local prefill/gen rates go in `EXPERIMENTS.md`; remote claims above are only investigation context. A different quantization/runtime requires new correctness checks, not just a speed comparison.
