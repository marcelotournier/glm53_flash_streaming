# GLM-5.3-Flash · RTX 3090 · NVMe streaming

A Dockerized local model server, reusing **Project Maya** (Strata-derived) and the exact **AJ-IQ2_XXS** quant linked in [this single-3090 recipe](https://x.com/ItsmeAjayKV/status/2111045102529593718).

## Hard constraint: weights must not exceed 100 GB

See **[SPEC.md](SPEC.md)**. The active model is **87,346,006,560 bytes** across two shards, pinned and SHA256-verified via `aj.lock.json`. The downloader, startup and benchmark automation reject manifests above **100,000,000,000 bytes total**, not per shard. Earlier 157 GB IQ4 and 125 GB EXL3 candidates are prohibited and stopped; their reports remain historical only.

AJ is a 2.23-bpw hand-mixed quantization, not a full-quality replacement for BF16. All routed experts remain; the unused MTP head is absent. Its model card reports a significant quantization-quality tradeoff. No expert skipping, LoRA, abliteration or runtime pruning is enabled here.

## Run

Linux, an NVIDIA RTX 3090 24 GiB, rootless Docker with NVIDIA CDI, Python 3, make, curl, and internal NVMe storage are required. This host has a Ryzen 5700G and 27.28 GiB usable RAM. Docker is capped at 24 GiB with container swap disabled. Leave room for ~87 GB weights, a small compatibility pack and the CUDA build/image.

```sh
make up                 # download+verify, build pinned Maya, pack once, start and wait
make test EXPERIMENT=validation-001
make status
make logs
make stop               # stays stopped, including across reboots
make start wait         # reuse the allowed model/container
```

The server uses **`--restart unless-stopped`**. Docker restarts crashes and resumes it after daemon/host restarts unless manually stopped. Rootless Docker itself must be enabled at boot; the user service and linger are already enabled here. A Docker unhealthy status alone does not restart a live process.

API: **http://127.0.0.1:8000/v1** · model **`glm-5.3-flash`** · default key **`local`**. Loopback binding is intentional. Use a private key and authenticated TLS proxy before exposing it remotely.

```sh
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer local' -H 'Content-Type: application/json' \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"Why is the sky blue?"}],"stream":true,"chat_template_kwargs":{"enable_thinking":false}}'
```

Unlike the earlier llama.cpp template, Maya explicitly supports `enable_thinking=false`. Generation tests let answers finish naturally. Context is configured at 262,144 tokens; configured capacity is not itself proof of successful long-context retrieval.

## Settings and experiments

- Engine settings: `engines/maya.json` (context, prefill batch, 12 GiB RAM expert tier, worker count, GPU reserve). Run **`make recreate`** after changing them; existing containers retain their original arguments and file mounts.
- `make verify`: rehash both allowed weight shards.
- `make pack`: build upstream's required small BF16-compatible tensors and tokenizer. It does **not** duplicate/requantize all experts. A manifest marker makes this idempotent; `make maya-pack-force` refuses to rewrite a running server's pack.
- `make smoke EXPERIMENT=<unique-id>`: real model, authentication rejection, factual chat, SSE framing, multi-turn state and actual disk-read counters.
- `make restart-test EXPERIMENT=<unique-id>`: kill the API process, verify Docker recovery, verify explicit stop stays stopped, then start again.
- `make bench EXPERIMENT=<unique-id>`: long unique prompt and natural-end answer; records uncached prefill (prompt tokens / TTFT) and generation separately. `PROMPT_REPEATS=3200 PREFILL_ONLY=1` is a ~16K-token prefill probe with a naturally short factual answer; its decode rate is **not sustained throughput**.

**Commit and push settings before experiments.** The benchmark records the configuration Git hash, exact quant manifest, image ID, mounts, settings, token counts, cache policy, response, timings and outcome. Commit/push the JSON receipt and Markdown report after each run. Keep tests isolated from downloads/builds and other GPU workloads.

Reports: **[EXPERIMENTS.md](EXPERIMENTS.md)** · recipe/engine research: **[ENGINES.md](ENGINES.md)** · live operations memory: **[AGENTS.md](AGENTS.md)**.

The target is **800–1000 tok/s uncached prefill**, not cached-prefix throughput. Only local measured results count. The reference post used a smaller quant and 46.7 GB pinned expert RAM; this host has less memory and a PCIe 3 NVMe/CPU platform. Results from different prompt sizes, quants, cache states or measurement methods are not direct speedup comparisons.

## Reused work

- [Project Maya](https://github.com/mw00/project-maya), Strata-derived GLM engine, pinned source `cd48762b6d4888205c130238dbc0c7f7904993cf` and ggml `3cf03257f219afbe7334045ff7c6a06ac68c627d`, CUDA 12.8.1/sm_86. MIT license included in the container.
- [AJ-IQ2_XXS GGUF](https://huggingface.co/aj9o9/GLM-5.3-Flash-GGUF), revision `07c62fcdeaf1c05d22bd123c3da8058a1b1e63e2`; [original Z.ai model](https://huggingface.co/zai-org/GLM-5.3-Flash), MIT.
- [0xSero/Sybil GLM NVMe recipe](https://github.com/sybil-solutions/glm-flash-lite): investigated its elastic cache, aligned O_DIRECT expert store and large-batch staging. Its pinned 3.05-bpw weights exceed the current size limit, so it is **not an allowed active candidate**.
- Earlier llama.cpp work: the unchanged MIT [xMytze/freedomljc expert-streaming patch](https://github.com/xMytze/glm53-ssd-streaming) remains in `vendor/` with its license/checksum for experiment provenance, not as the default deployment.

No model weights, logs, scratch research, caches or secrets are tracked in Git. No cloud fallback or invented performance numbers.
