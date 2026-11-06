# Validated Unsloth IQ1_S target / memory

> Historical 32 GB-host profile. After the 64 GB DDR4 upgrade, the default is `engines/iq1s-64gb.json`, 40 GiB expert RAM / 50 GiB container cap, with 9.91–10.23 tok/s generation. See [RAM64_RESULTS.md](RAM64_RESULTS.md). To reproduce this document's original profile, explicitly use `MAYA_CONFIG="$PWD/engines/maya.json" MAYA_MEMORY=24g` when recreating.

User requested matching the saved AJ baseline's prefill and generation. **Achieved on the matched workloads, 2026-10-31.** AJ's historical manifest/config/image/results remain in [BASELINE.md](BASELINE.md); its weights/pack were deleted in026 at the user's request.

## Exact weights and runtime

- **Unsloth UD-IQ1_S: 93,087,245,088 bytes** across all three GGUF shards, including the unused MTP weights. Below the mandatory100,000,000,000-byte ceiling.
- Repo/revision: `unsloth/GLM-5.3-Flash-GGUF@a38483c8cd5df544f53d70fb281afe97369d5ab6`.
- Local originals: `models/unsloth-iq1s/GLM-5.3-Flash-UD-IQ1_S-0000{1,2,3}-of-00003.gguf`.
- Manifest/hashes: **`unsloth-iq1s.lock.json`**, SHA256 `f11a71472a31b00a9f6daa00cb521745d4f22b5555b68bcd4c2208134a4fd615`. All full-file SHA256s and byte sizes reverified in018; receipt `results/experiment-018-iq1s-integrity-cleanup.json`.
- Upstream small BF16 compatibility pack: `models/unsloth-iq1s/maya-pack/`. No expert requantization; all routed experts retained. Manifest-bound `.ready` marker, read-only runtime mount, quant+manifest-SHA container labels.
- Image: **`sha256:af26ebe63f5296347660dd6091655235c74279fac8ab8fca1fd690fc488b950d`**, same pinned Project Maya image as AJ. Source `cd48762b6d4888205c130238dbc0c7f7904993cf`, ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`, CUDA12.8.1/sm_86 + AVX2.
- Winning config: **`engines/maya.json`**, committed in `ffbc2aba6d67a808bbac7563157459cf38dce36b`; SHA256 **`52c9ae6ed6bec5a3411509a9a4819031dba638c75e9c54e633169ef58e3aa728`**. Later experiment commits change reports/harness, not this profile.

## Winning settings

| Setting | Value |
|---|---|
| Logical context / prefill batch |262144 /32768|
| KV streaming |on,32768 positions GPU-resident|
| GPU expert cache / reserve |auto elastic /1200MiB|
| Expert RAM tier |**15GiB**, vs12GiB AJ baseline|
| Container RAM / swap |24GiB /disabled|
| `MAYA_GLM_CKPT_EVERY` |0: no periodic16K cuts; whole-turn snapshots retained|
| `MAYA_GLM_READ_CHUNKS` |**4**, vs default8|
| `MAYA_GLM_DISK_READERS` |**4**, independent whole-part prefill readers|
| `MAYA_GLM_PREFILL_LAND` |78, pinned to the initial IQ1_S baseline's observed ring|
| `MAYA_GLM_NO_MTP` |1|

No expert skipping, pruning, LoRA or abliteration. CPU lane uses native automatic calibration (8 threads); CPU/GPU arithmetic placement can change greedy text across starts. Same seed does not promise identical text. No BF16 quality equivalence claim.

## Measured parity

Exact AJ requests replayed after cold restarts, **cached tokens0**, temperature0/seed42, no imposed output cap, natural EOS:

| Workload | AJ baseline prefill / gen tok/s | IQ1_S prefill / gen tok/s |
|---|---:|---:|
|25,558-token repository docs/code request|961.76 /4.78 (375 output)|988.78 /5.02 (397 output), repeat990.14 /5.15 (375 output)|
|32,058-token synthetic short-answer probe|1047.02 /N/A|1070.58 /N/A|
|255,099-token exact buried-code retrieval|968.03 /3.03 (short)|995.20 /3.36 (short)|

See021–024 in [EXPERIMENTS.md](EXPERIMENTS.md). Short answers are NOT sustained generation measurements. The larger real answers are the decode comparison; output text/counts differ between quants/runs, so this is same-task performance, not identical-token causal isolation or a broad benchmark suite. Reference64GB host's20–25tok/s is not reproduced.

Peak observed across winning-profile benchmark runs **22.75GiB**, below24GiB; steady reported usage about20.9–21.3GiB. Reclaimable filesystem cache makes total cgroup peak a poor estimate of incremental pinned RAM; actual anon+shmem was checked before increasing the tier. Native decode SSD misses93→67/tok in021 versus the12GiB baseline; read wait219→164ms/tok. No OOM or unsolicited restarts.

## Validation and operations

- 024 retrieved exact `ORCHID-SILVER-7429` buried ~85K tokens into the255K document. One synthetic needle, not a long-context quality suite.
- 025 PASSED after that request: auth rejection/model ID/Paris chat/SSE/Tokyo follow-up +26.09GB actual disk reads, nine unit tests, real API-SIGKILL Docker recovery, manual stop stays stopped, explicit start restores readiness.
- Running container `glm53-flash-maya`, policy `unless-stopped`; API `http://127.0.0.1:8000/v1`, model `glm-5.3-flash`, test key `local`. Loopback only.
- `make start wait`, `make stop`, `make recreate`, `make test EXPERIMENT=<unique-id>` select IQ1_S by default. Do not edit live pack or run another GPU engine concurrently.
- Reproduce matched request: `make restart`, then `make bench EXPERIMENT=<unique-id> REPLAY_RECEIPT=results/experiment-012-aj-repo-natural.json`. Commit/push settings first.
- AJ weights/pack deleted in026; no instant local rollback. Any future restore requires explicit re-download/hash verification and packing before replacing IQ1_S (BASELINE.md). Preserve the active IQ1_S weight set, pack and image.
- Unsloth CLI guide reviewed in ENGINES.md; not installed or inference-benchmarked. Its documented llama-server wrapper/mmap spill is not what produced these results; no MTP needed to meet the target.
- Cleanup018 removed obsolete IQ4/EXL3 weights;026 subsequently removed AJ weights/pack. About365GiB free, only IQ1_S remains under models/. Next-session IQ3_XXS investigation is in [TODO.md](TODO.md), blocked for known~120GB Unsloth quant by the unchanged100GB ceiling. Nothing started for IQ3; no downloads/builds/tuning jobs running.
