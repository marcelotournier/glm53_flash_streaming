# GLM-5.3-Flash · RTX 3090 · NVMe streaming

A local, OpenAI-compatible **real GLM-5.3-Flash** server in rootless Docker. All experts are retained; the model is Unsloth's **UD-IQ4_XS** quantization (~157 GB). Dense weights run on the GPU; routed experts stream from NVMe through a bounded RAM cache. No cloud fallback.

## Run

Requires Linux, NVIDIA CDI, Docker, Python 3, curl, make, ~180 GB free **internal NVMe** space for weights/builds, a 24 GB NVIDIA GPU, and ~27 GB usable host RAM. The CUDA binary targets RTX 3090 (`sm_86`). The first build/download takes time.

```sh
make up          # download+verify, build, start, wait
make test        # unit checks + actual model chat/SSE/disk reads + crash recovery
make status
make logs
make stop        # explicitly stops it; stays stopped until make start
make start wait  # reuse the existing container
```

The container uses **`--restart unless-stopped`**. Docker restarts it after crashes and daemon/host restarts, unless you manually stopped it. Rootless Docker itself must start at boot (`systemctl --user enable docker`, login linger); these were already enabled on this machine. An unhealthy status by itself does not cause Docker to restart a process.

API: **http://127.0.0.1:8000/v1**, model **`glm-5.3-flash`**, key **`local`** by default. Loopback-only binding is intentional. Use an authenticated TLS proxy before exposing it remotely.

```sh
curl -sS http://127.0.0.1:8000/v1/chat/completions \
  -H 'Authorization: Bearer local' -H 'Content-Type: application/json' \
  -d '{"model":"glm-5.3-flash","messages":[{"role":"user","content":"What is the capital of France?"}],"max_tokens":256,"stream":true}'
```

GLM reasons before answering. `max_tokens` includes reasoning; allow enough tokens. Reasoning and answer are returned separately. The template uses low reasoning effort by default; this is not an unsupported "disable thinking" switch.

## Automation / settings

Run `make help` for every target. No Compose installation is required.

- `make download`: resumable `.part` downloads, pinned HF revision, size + SHA256 checks, atomic final rename. Existing corrupted shards fail rather than silently overwrite.
- `make verify`: rehash all five shards against `model.lock.json`.
- `make image`: build the pinned engine and vendored patch.
- `make smoke`: checks health, bad-key rejection, model ID, factual chat answer, SSE chunks/finish/`[DONE]`, increasing real process disk-read counters, and streaming log evidence. Receipt: `results/smoke.json`.
- `make bench EXPERIMENT=<unique-id>`: measures separate prefill/generation tok/s with a 128-token generation request and writes a Git-linked receipt plus `EXPERIMENTS.md` entry. Commit configuration changes first; restart before each comparative run for an empty expert cache.
- `make restart-test`: kills inference, waits for Docker's automatic restart and API recovery. Receipt: `results/restart.json`.
- `make recreate`: replace the container using current settings/image; preserves all model data.
- `make remove`: delete only the container, not its weights.

Make variables can be overridden, e.g. `make recreate PORT=8001 CTX=16384`. **Existing containers keep their original arguments**: use `recreate`, not `start`, to apply changes. Set the same overrides when running client-side tests. Set `API_KEY` to a private value if required; don't commit it.

Initial resource plan: 8K context, one request slot, batch/ubatch 256, all 42 routed MoE layers on CPU (`CPU_MOE=45`, including the three leading dense layer indices), **24 cache slots per layer** (~12 GiB), two 4.24 GiB full-layer staging buffers, 8 compute threads and 8 I/O threads. Container RAM is capped at 24 GiB with no swap. The cache must have at least 24 slots for the patch's small-batch path. Increasing it can OOM this host. Expert I/O bypasses the page cache with O_DIRECT; weights are a read-only bind mount, never embedded in the image.

**Storage-bound inference is not GPU-resident speed.** This host has a single PCIe 3 NVMe drive and little RAM relative to a 146 GiB expert set. Expect slow cold starts/prefill and substantial disk reads. Bigger context and high concurrency are not claimed. Vision and speculative decoding are intentionally disabled. The smoke receipt records actual timings rather than a borrowed benchmark.

## Reused work / reproducibility

- [0xSero's GLM-5.3-Flash recipes](https://github.com/0xSero/GLM-5.3-Flash-DGX-Spark): reviewed first; their 128 GB unified-memory ARM/Blackwell recipe cannot run unchanged here. Their recommendation to retain experts rather than prune informed this choice.
- [xMytze/glm53-ssd-streaming](https://github.com/xMytze/glm53-ssd-streaming), commit `9900b7ab1f32ee3fcfb19c83d4862aaee9b46f5e`: **existing experimental MIT patch**, incorporating [freedomljc's llama.cpp PR #25294](https://github.com/ggml-org/llama.cpp/pull/25294), bounded cache, O_DIRECT worker pool, full-layer prefill staging, and a CUDA MMQ fix. Vendored verbatim with checksum and license in `vendor/`.
- Unsloth [llama.cpp](https://github.com/unslothai/llama.cpp) base `86ebfef2c6a0f3359a2a07d2c215d61b0fa885c9`, CUDA 12.8.1, `sm_86`, TF32 disabled.
- [Unsloth GGUF weights](https://huggingface.co/unsloth/GLM-5.3-Flash-GGUF), pinned in `model.lock.json` to revision `621d456e93e926e4b52f85cff5f634358c1828f9`; later metadata uses incompatible `glm5-next` architecture spelling instead of this engine's `glm5next`. The four data shards are unchanged. [Original Z.ai model](https://huggingface.co/zai-org/GLM-5.3-Flash). First shard is intentionally metadata-only; **all five shards** are required.

The streaming patch's original author labels it AI-written and experimental, tested on one RTX 5090 machine. This deployment must be judged by its own recorded 3090 tests, not assumed numerically identical to BF16. No expert pruning, custom inference engine, or invented benchmark numbers.

`AGENTS.md` is the live implementation/operations log, including final hardware measurements and any remaining limitations.
