# 64 GB DDR4 upgrade — IQ1_S results

**Generation improved from 5.11 to 9.91–10.23 tok/s (1.94–2.00×). Uncached prefill improved from 988 to ~1265 tok/s (+28%).** IQ1_S left healthy/running with the new profile; IQ3 preserved/stopped.

## Matched measurements

Same exact AJ012 request: **25,558 prompt tokens, cached0**, temperature0/seed42, natural EOS, no output cap. Same pinned model/image; no downloads, pack changes, expert modifications or MTP. No concurrent builds/downloads/other inference during timing. 036 used the existing newly started post-upgrade engine; 037/038 each followed fresh container recreation.

| Receipt | Expert RAM | Container cap | Prefill tok/s¹ | Generation tok/s | Output tokens | Wall seconds |
|---|---:|---:|---:|---:|---:|---:|
|036 unchanged profile, upgraded host|15 GiB|24 GiB|988.02|5.11|397|103.43|
|037 tuned|40 GiB|50 GiB|1265.74|10.23|344|53.72|
|038 cold repeat|40 GiB|50 GiB|1265.40|9.91|301|50.46|

¹ Prompt tokens / time to first text token, including first-token overhead. Native prefill for036/037 was 989.8/1268.9 tok/s. Decode excludes prefill.

Extra installed RAM alone did not enlarge the old fixed 15 GiB cache. With the expanded tier, native disk reads fell **67.23→22.67 per output token**, disk wait **163.05→56.26 ms/token** (036→037). CPU lane remained automatically calibrated at 8 threads. Auto-sized GPU expert slots changed 2268→2184; arithmetic placement and answer lengths differ, so these are matched-task measurements, not identical-output continuations or strict single-variable kernel isolation. Answers were coherent sky explanations; no broad quality-equivalence claim.

## Final settings and artifacts

- Host: Ryzen 5700G, RTX 3090 24 GiB, same NVMe; upgraded DDR4 exposes **63,067,250,688 bytes / 58.73 GiB usable RAM**.
- New IQ1_S default: `engines/iq1s-64gb.json`, SHA256 `caaab8d9010f0d12cfcc93110bfa6031c7d90eb89c8bb88bc06173dfc22e83f8`.
- **`MAYA_GLM_RAM_GB=40`**, **50 GiB container limit / container swap disabled** (`--memory=50g --memory-swap=50g`). Other quants retain the old profile/24 GiB default.
- Unchanged: 262144 context, 32768 prefill, KV streaming, auto GPU cache/reserve1200 MiB, readers4/chunks4, landing78, periodic checkpoint cuts0, MTP off.
- Original `engines/maya.json` preserved byte-for-byte, SHA256 `52c9ae6ed6bec5a3411509a9a4819031dba638c75e9c54e633169ef58e3aa728`; unit test protects both profiles.
- Same 93,087,245,088-byte IQ1_S manifest and image `sha256:af26ebe63f5296347660dd6091655235c74279fac8ab8fca1fd690fc488b950d`. No change to model size limits or the exact IQ3 exception.
- Profile/harness committed and pushed **before** tuned timing in `afc1a07`; later receipts record their exact configuration commits. Full requests, answers, native logs, limits, host memory and cgroup memory events are in `results/experiment-036-*.json` through `041-*.json` and [EXPERIMENTS.md](EXPERIMENTS.md).

## Memory safety and context validation

- Tuned benchmark cgroup peaks: 037 **49.58 GiB**, 038 **47.61 GiB**, 039 **46.94 GiB**, 040 **46.98 GiB**, below 50 GiB. 037 peak includes inactive file cache; steady anon+shmem ~46.14 GiB. No max/OOM events or container swap in these receipts.
- Host available memory was roughly 6–7 GiB during tuned benchmarks. **Host swap remains enabled**: usage rose from zero before tuning to ~1.74 GiB after the long-context test and ~1.8 GiB after lifecycle validation. This includes other host pages; zero container swap does not mean zero host swapping. No host VM/swappiness settings changed. Do not increase the tier further; lower it if desktop/workload headroom becomes inadequate.
- 039 exact AJ011 replay: **32,058 prompt tokens/cached0, 1245.50 tok/s prefill**, correct Paris answer.
- 040 exact AJ015 replay: **255,099 prompt tokens/cached0, 1124.04 tok/s prefill**, exact `ORCHID-SILVER-7429` recovered. Host available 7.19 GiB afterward.
- The 2-/11-token context replies are **not sustained decode benchmarks**. One synthetic needle is not a broad long-context quality suite. No claim of fully resident inference, exhaustive optimum, or the reference's 20–25 tok/s.

## Functional checks / final state

041 passed **11 unit tests**, Python syntax checks, bad-key401/model ID, real chat/SSE/multi-turn and **13.21 GB real disk reads immediately after the 255K request without restarting first**. Then API-SIGKILL automatic Docker recovery and explicit stop/stays-stopped/start semantics passed; API ready again. Short smoke rates are not throughput results.

IQ1_S left healthy/running, loopback `http://127.0.0.1:8000/v1`, model `glm-5.3-flash`, restart `unless-stopped`, new 40 GiB profile/50 GiB cap, MTP off. MTP was not rebenchmarked after this RAM upgrade.

## Reproduce

```sh
make recreate  # upgraded 64 GB host only; applies new IQ1_S default
make bench EXPERIMENT=<unique-id> \
  REPLAY_RECEIPT=results/experiment-012-aj-repo-natural.json
```

Commit/push settings before timing and results afterward. Original profile / 32 GB host:

```sh
make MAYA_CONFIG="$PWD/engines/maya.json" MAYA_MEMORY=24g recreate
```

Do not use the new 64 GB default on a 32 GB host. Existing containers retain limits/config until recreation. IQ3 was not retuned or benchmarked in this upgrade session.
