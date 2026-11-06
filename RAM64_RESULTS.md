# 64 GB DDR4 upgrade

User authorized RAM-cache tuning and fresh throughput benchmarks. Host reports 63,067,250,688 bytes (58.73 GiB) usable RAM; same Ryzen 5700G / RTX 3090. No model/image changes, downloads or MTP. IQ3 preserved/stopped.

## Control

036: unchanged `engines/maya.json`, 15 GiB expert tier, 24 GiB/no-swap container: **988.02 tok/s prefill, 5.11 tok/s generation**, 397 output tokens. Exact AJ012 request, 25,558 prompt tokens, cached0, natural EOS. Engine was newly started after the hardware upgrade; no inference before this benchmark in this session. Receipt records the pre-existing startup time. Extra system RAM alone does not enlarge the fixed tier.

## Tuning plan

Preserve original `engines/maya.json` and MTP profiles. New IQ1_S default `engines/iq1s-64gb.json` starts at 40 GiB expert RAM with a 50 GiB container limit, no container swap. Other quants retain the old profile/24 GiB limit. Measure real pinned/anonymous memory and host availability before considering more RAM. Keep 32K prefill, 256K context, readers4/chunks4 and MTP off unchanged. Benchmark exact AJ012 after fresh recreation, with no concurrent build/download/inference. Settings committed/pushed before timing. Benchmark receipts now include container limits, host memory before/after and cgroup memory events/swap.

Reproduce original profile on this host: `make MAYA_CONFIG="$PWD/engines/maya.json" MAYA_MEMORY=24g recreate`. Use `make recreate` for the new IQ1_S default. Do not use the new default on a 32 GB host.

## First tuned result

037: **1265.74 tok/s prefill / 10.23 tok/s generation**, 344 output tokens, cached0. About **2.00x decode / 1.28x prefill** versus today's unchanged-profile control. Native disk reads fell 67.23→22.67 per output token, disk wait 163.05→56.26 ms/token. Native CPU lane remained 8 threads. Auto-sized VRAM slots changed 2268→2184; same auto-cache setting, not identical numerical placement/output tokens.

Peak cgroup memory 49.58 GiB includes ~3.22 GiB inactive file cache; steady unreclaimable anon+shmem ~46.14 GiB. No cgroup max/OOM events or container swap. Host available memory ~6 GiB; host swap usage rose from zero before tuning to ~361 MiB (other host pages, container swap remains zero). Do not increase the tier further: reserve desktop/OS headroom. 038 fresh recreation repeat: **1265.40 tok/s prefill / 9.91 tok/s generation**, 301 output tokens, cached0. Decode improvement range **1.94–2.00x**, prefill **1.28x** versus036. Answers are coherent but not identical output-token continuations; placement/calibration can change greedy output. Context/function validation pending. No claim of fully resident inference, exhaustive tuning, broad quality equivalence or the reference's 20–25 tok/s.
