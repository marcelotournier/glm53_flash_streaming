# Engine investigation (2026-10-30)

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
