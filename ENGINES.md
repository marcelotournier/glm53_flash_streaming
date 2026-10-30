# Engine investigation (2026-10-30)

**Latest hard constraint: no quant above 100,000,000,000 bytes total weights (SPEC.md).** The125GB EXL3 and157GB IQ4 entries below are historical investigation only; downloads/inference stopped and startup/packing are now blocked by size guards. Only87.35GB AJ-IQ2_XXS is an allowed active candidate.

## Exact user-linked AJ / Maya recipe (confirmed from the post)

Post: https://x.com/ItsmeAjayKV/status/2111045102529593718 (2026-10-16). Retrieved both the post and original screenshots, not inferred from a search snippet. It explicitly credits **Project Maya** and links **aj9o9/GLM-5.3-Flash-GGUF, AJ-IQ2_XXS**. This is distinct from the Sybil/0xSero EXL3 recipe below.

- Exact quant: **87,346,006,560 bytes**, two shards, 2.23 bpw, pinned HF revision `07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2` in `aj.lock.json`. The earlier IQ4_XS test used ~157 GB, so it was not a reproduction of this post.
- Its dense/attention/shared weights are Q6_K, sensitive gates/indexer Q8_0, routers/norms F32, routed gate/up IQ2_XXS and down IQ2_XXS with higher precision on edge layers. All routed experts retained; unused MTP block removed by the quantizer.
- Screenshot: 863 tok/s prefill, 20.5 tok/s displayed decode, 7.7K/256K request context, 12.8 GB VRAM expert residency and **46.7 GB pinned RAM**, 48.3% VRAM hit rate; PCIe Gen4 x16, 12-core/24-thread CPU. Different memory residency than this host's ~12 GiB RAM tier and PCIe Gen3.
- Quality tradeoff is real: model card reports AJ-IQ2_XXS WikiText PPL 4.2314 vs BF16 2.2474 and KLD0.7072 (their 30-chunk experiment, not ours). Do not silently call it the same-quality model as IQ4_XS.
- Plan: reuse our working pinned Maya build, download+verify the exact AJ quant, build its own small compatibility pack, tune 16K/32K prefill batches and memory budget; target800–1000 but record only actual uncached measurements. Do not replace measured numbers with the post's claim.
- Storage priority: stop/resume EXL3 checkpoint preparation as needed; its separate117GB expert store must not crowd out this exact requested reproduction. Existing partial downloads remain resumable; never exceed disk free-space reserves.

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

These are source/header compatibility checks, **not successful inference or speed measurements**. Full weight downloads must be hash-verified and pack/model smoke tests must pass before adopting either. Finish the exact user-linked AJ quant first; avoid concurrent downloads during benchmarks. Neither Unsloth candidate is silently substituted for AJ in the active configuration.

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

### Adaptation here

Reuse the published image unchanged; no new inference kernels. `engines/exl3.mk` automates pull/download/O_DIRECT probe/store packing+verification/start/wait/stop. 24 GiB no-swap cap, upstream small-host budget explicitly enabled, 1 GiB recurrent-state cache, 128 prefill-ring slots, CPU lane cores 2–7, feeder 0/controller 1/readers 8–15, 16 I/O threads. CDI + SELinux bind-mount settings match this rootless Docker host. No unlimited-memlock request (not permitted here; CUDA registration itself previously worked).

This host uses Btrfs, not upstream's recommended xfs/ext4. Its actual aligned O_DIRECT write/read probe passed on the store directory. The image's own probe and full packed-record verification must also pass before serving; **no filesystem repartitioning or loop devices**.

Preparation requires ~125.3 GB checkpoint +117.3 GB store plus image space; checked ~359 GiB free before starting. Keep the working GGUF engine as a fallback. Never run competing inference engines on the GPU during timing.

## Other engines worth testing

| Engine | Assessment / test plan |
|---|---|
| Current pinned llama.cpp streaming patch | Working and smoke-tested. Best recorded small-prompt result 7.80 prefill /1.41 gen tok/s at 460 prompt tokens; not an 8K-prefill comparison. Keep as exact GGUF baseline/fallback. |
| **Project Maya** (`mw00/project-maya`, Strata-derived) | High-value candidate: Linux-native, current GLM support, elastic expert tiers, large tensor-core prefill, 32 GB-class hosts. Can reuse existing GGUF or new EXL3, avoiding another weight download. Testing pinned source `cd48762b6d4888205c130238dbc0c7f7904993cf`, upstream ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d` in `engines/maya.Dockerfile`; sm_86, portable AVX2, existing GGUF with upstream's required BF16-compatible small-tensor pack. Explicit 12 GiB RAM tier, auto elastic prefill, no MTP, no skipping/LoRA/pruning. `engines/maya.mk` automates build/pack/start/wait. |
| `isichan-ai/Strata-GLM` | Reuses our exact Unsloth IQ4_XS; reported ~580 tok/s on 5090+128 GB. GLM path Linux explicitly untested, Windows-first packaging; less attractive than its actively maintained Maya lineage. Pin `6feb85fed9f994380b201c105851a740ec99d5e8` if tested. Disable expert skipping for fair quality. |
| `Indras-Mirror/Strata-GLM` | Linux support, but current defaults require ~80 GB free RAM, Maya-S-v2 weights and runtime abliteration/soft pruning. Do not adopt its defaults on this 27 GiB host or silently change model behavior. |
| `sergqwer/strata-glm` | Archived NVFP4 experiment (pin `ed37419fccd0c52e07d26d526a29c2098f547843`), 5090/128 GB/two NVMe, separate ~204 GB checkpoint. Poor first candidate here. |
| Current upstream `Niko1221/Strata` | Current README lists Qwen/DeepSeek, not GLM. Do not assume a Qwen engine can load GLM unchanged. Prefer a GLM-specific maintained fork/Maya. |

### Preparation checks

- Maya CUDA sm_86 build succeeded (152 compilation units). Initial pack attempt at configuration `d924430` stopped safely before serving: upstream's `_paths.py` requires `STRATA_GGUF_PY` explicitly even when the module imports via PYTHONPATH. Added that environment variable to the image; no inference happened, prefill/gen metrics N/A.
- EXL3 image pull and hash-verified checkpoint download run in parallel; disk/RAM monitored. Existing llama server explicitly stopped during engine transition, not crashed. No repartitioning or changes to the user's other workloads.

Results, failures, limits, configuration Git hashes and local prefill/gen rates go in `EXPERIMENTS.md`; remote claims above are only investigation context. A different quantization/runtime requires new correctness checks, not just a speed comparison.
