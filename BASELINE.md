# Known-good AJ target / rollback memory

Saved before unloading at user's request (2026-10-30). **Update026 (2026-10-31): user explicitly requested deleting AJ; `models/aj/` weights and derived pack are now removed.** Manifest, frozen profile, image and measured results remain as historical/reproducibility memory, NOT an immediately available local rollback.

## Exact artifacts

- Quant: **AJ-IQ2_XXS**, all routed experts, **87,346,006,560 bytes** summed over both shards.
- Manifest: `aj.lock.json`, SHA256 `382861e45b2e9da7ef814647cd94360cd83eb1bf2124093a6c5674b5b7469699`.
- HF: `aj9o9/GLM-5.3-Flash-GGUF@07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2`.
- Former local weights: `models/aj/GLM-5.3-Flash-AJ-IQ2_XXS-{00001,00002}-of-00002.gguf`; hashes in manifest, verified before later deletion.
- Former compatibility pack: `models/aj/maya-pack/`, also deleted in026. Re-download and re-pack required to restore.
- Engine image: `sha256:af26ebe63f5296347660dd6091655235c74279fac8ab8fca1fd690fc488b950d` (`glm53-maya:local`). Preserve this image.
- Source Maya `cd48762b6d4888205c130238dbc0c7f7904993cf`, ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`.
- Frozen config: **`engines/aj-baseline.json`**, SHA256 `2b34c875d977b6ca439e1821decefb42dcee63a720e41918e552f7742e03c57f` (byte-identical to AJ's winning config at `c848982`; the current `engines/maya.json` now holds the separately validated IQ1_S settings).
- Context262144, prefill32768, KV streaming on, auto elastic GPU expert cache,1200MiB reserve,12GiB expert RAM, no MTP, **MAYA_GLM_CKPT_EVERY=0**. Container24GiB/no swap; restart unless-stopped;127.0.0.1:8000/v1.

## Targets to match with Unsloth IQ1_S

| Receipt | Prompt / output tokens | Uncached prefill tok/s | Generation tok/s |
|---|---:|---:|---:|
| 011, repeated background, short answer | 32058 /2 |1047.02 |N/A (not sustained)|
| **012, repository docs/code, full natural answer** | **25558 /375** | **961.76** | **4.78** |
| 015, near256K exact needle retrieval |255099 /11 |968.03 |3.03 (short, not sustained)|

All cached-token counters0. Exact requests and configuration hashes are in `results/experiment-012-aj-repo-natural.json` etc. For a truly matched quant comparison, **replay the exact012 request**, not newly generated repo text (the repository has changed). Let generation end naturally; compare actual emitted token counts and native timings. Three-token answers are not decode benchmarks.

Auth/chat/SSE/multi-turn/real disk reads and API-SIGKILL automatic Docker recovery/manual stop/start passed (014,016). Final known-good repo commit: `c848982`.

## Restore

**Not available immediately: AJ weights and pack were deleted.** If later authorized to restore, first run `make QUANT=aj download` to download/hash-verify; then explicitly `make stop` before `make QUANT=aj pack` (packing is refused while this project's container runs). Only once ready, run `make QUANT=aj IMAGE=glm53-maya:aj-baseline recreate`. Do not recreate before files/pack are ready: it replaces the current IQ1_S container. These are future restore instructions, not actions for the IQ3 TODO. Makefile selects frozen `engines/aj-baseline.json`. Never run both quants on this GPU together. The validated IQ1_S successor is recorded separately in [IQ1S_TARGET.md](IQ1S_TARGET.md). All configurations must retain the **100,000,000,000-byte total weight ceiling**.
