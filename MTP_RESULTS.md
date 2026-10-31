# IQ1_S MTP n=2 / n=3

User requested benchmarking the already downloaded IQ1_S with two and three MTP drafts. No downloads, pack rewrites, engine builds or expert modifications. Preserved winning `engines/maya.json`; separate profiles `engines/iq1s-mtp-n2.json` and `engines/iq1s-mtp-n3.json` committed/pushed in `5883f56` before testing.

## Matched cold request results

Exact replay of AJ012, **25,558 prompt tokens / cached 0**, greedy, natural EOS/no output cap, fresh recreation per profile. Same pinned image, IQ1_S manifest, 256K context, 32K prefill, 15 GiB expert RAM and 24 GiB/no-swap cap.

| Receipt | Mode | Native prefill tok/s | Streamed generation tok/s | Output tokens | Drafts accepted/proposed | Disk reads/output token |
|---|---|---:|---:|---:|---:|---:|
| 032 | MTP off | 988.0 | **5.19** | 397 | 0/0 | 67.23 |
| 033 | Fixed n=2 | 947.2 | **2.10** | 373 | 198/348 (56.9%) | 170.37 |
| 034 | Fixed n=3 | 944.7 | **1.58** | 429 | 242/558 (43.4%) | 230.81 |

Both MTP runs completed with coherent sky explanations. These are single runs on identical requests, not identical-output continuations: CPU placement/numerical paths and output lengths differ, so not strict identical-token causal isolation or broad quality validation. n=2 was ~60% slower decode, n=3 ~70% slower than off. No speed benefit here.

## Exact MTP meaning / evidence

The pinned source `cd48762b6d4888205c130238dbc0c7f7904993cf`, `src/core/glm_mtp.cu`, defines n as **draft tokens per round**, not total verify-window size (which includes the pending token). Profiles remove `MAYA_GLM_NO_MTP`, set `MAYA_GLM_MTP_DECODE=1`, `MAYA_GLM_MTP_DRAFT=n`, `MAYA_GLM_MTP_FIXED=n`, `MAYA_GLM_MTP_ADAPT=0`, and enable trace. These map to the engine's STRATA aliases. Native timing counters confirm nonzero proposed/accepted drafts; n=2 proposed 348 draft tokens and n=3 proposed 558. This is forced one-GPU MTP; the pinned engine does not enable it by default on this NVIDIA GPU.

MTP loads an extra NextN layer and reduces trunk GPU expert slots (2268 off vs 2193 total including draft slots on). Verification processes extra speculative rows/experts, and observed disk wait rises from **159.73 ms/output token** off to **400.29** (n2) / **539.01** (n3). Acceptance cannot compensate for the extra NVMe traffic on this machine. This is not evidence against MTP on fully resident hardware.

Peak cgroup memory: off **24.00 GiB (at cap)**, n2 **22.98 GiB**, n3 **23.56 GiB**. Requests passed but no spare-headroom claim; do not increase RAM tier. Full native timings, resource counters, exact requests and image/config identities in `results/experiment-032-*.json` through `034-*.json`.

## Final state / reproduction

Restored IQ1_S **MTP off**, healthy/running. 035 post-restore auth/chat/SSE/multi-turn/disk-I/O smoke passed. IQ3 weights/pack preserved, not running. No lifecycle retest specifically for MTP profiles; existing restore smoke does not prove their crash recovery.

Use `make QUANT=unsloth-iq1s recreate` for normal service. For n=2: `make QUANT=unsloth-iq1s MAYA_CONFIG="$PWD/engines/iq1s-mtp-n2.json" recreate` (replace n2 with n3 for three drafts), then benchmark an exact saved request with a fresh unique receipt ID. Keep tracked settings/results committed and pushed before each timed test.
