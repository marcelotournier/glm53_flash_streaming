SHELL := /bin/bash
.DEFAULT_GOAL := help
.NOTPARALLEL:

IMAGE ?= glm53-flash:local
CONTAINER ?= glm53-flash
MODEL_DIR ?= $(CURDIR)/models
MODEL_FILE := GLM-5.3-Flash-UD-IQ4_XS-00001-of-00005.gguf
MODEL_ID := glm-5.3-flash
HOST ?= 127.0.0.1
PORT ?= 8000
API_KEY ?= local
CTX ?= 8192
# >=24 slots/layer is required for the patch's small-batch multi-wave path.
EXPERT_CACHE ?= 24s
# Layer indices include 3 dense layers; 42 streams 39, retaining 3 MoE layers in VRAM.
CPU_MOE ?= 42
BATCH ?= 512
THREADS ?= 8
IO_THREADS ?= 8
MEMORY ?= 24g
BUILD_JOBS ?= 4
DOWNLOAD_JOBS ?= 4
STARTUP_TIMEOUT ?= 1800
REQUEST_TIMEOUT ?= 1800
EXPERIMENT ?= $(shell date -u +%Y%m%dT%H%M%SZ)
GEN_TOKENS ?= 128
ENGINE ?= exl3
BENCH_CONTAINER ?= glm53-flash-$(ENGINE)
PROMPT_REPEATS ?= 1600
export CONTAINER HOST PORT API_KEY STARTUP_TIMEOUT REQUEST_TIMEOUT

.PHONY: help download verify image start wait up stop restart recreate remove logs status smoke bench test restart-test unit check
help: ## Show automation targets
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "%-16s %s\n", $$1, $$2}'

download: ## Resume download and SHA256-verify all five pinned IQ4_XS shards (~157 GB)
	python3 scripts/download.py --dest "$(MODEL_DIR)" --jobs $(DOWNLOAD_JOBS)

verify: ## Rehash every model shard against model.lock.json
	python3 scripts/download.py --dest "$(MODEL_DIR)" --verify

image: ## Build CUDA sm_86 server with the pinned NVMe-streaming patch
	docker build --build-arg BUILD_JOBS=$(BUILD_JOBS) -t $(IMAGE) .

start: ## Start existing container, or create it with restart=unless-stopped
	@python3 -c 'import json,pathlib; root=pathlib.Path("$(MODEL_DIR)"); files=json.loads(pathlib.Path("model.lock.json").read_text())["files"]; assert all((root/pathlib.Path(f["path"]).name).is_file() and (root/pathlib.Path(f["path"]).name).stat().st_size == f["size"] for f in files), "Missing/incomplete shards: run make download"'
	@if docker inspect "$(CONTAINER)" >/dev/null 2>&1; then \
	  docker start "$(CONTAINER)"; \
	else \
	  docker run -d --name "$(CONTAINER)" --restart unless-stopped --init \
	    --device nvidia.com/gpu=all --security-opt label=disable \
	    --memory $(MEMORY) --memory-swap $(MEMORY) --shm-size 1g \
	    --log-opt max-size=20m --log-opt max-file=3 \
	    -p $(HOST):$(PORT):8080 -v "$(MODEL_DIR):/models:ro" \
	    --label io.local.glm53.managed-by=make "$(IMAGE)" \
	    --model /models/$(MODEL_FILE) --alias $(MODEL_ID) --no-mmproj \
	    --host 0.0.0.0 --port 8080 --api-key "$(API_KEY)" \
	    -ngl 99 --n-cpu-moe $(CPU_MOE) --load-mode none --fit off \
	    --moe-stream-cache $(EXPERT_CACHE) --moe-stream-direct --moe-stream-io-threads $(IO_THREADS) \
	    --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 \
	    --ctx-size $(CTX) --parallel 1 --batch-size $(BATCH) --ubatch-size $(BATCH) --threads $(THREADS) \
	    --cache-ram 0 --jinja --reasoning-format deepseek \
	    --chat-template-kwargs '{"reasoning_effort":"low","clear_thinking":true}' --temp 1.0 --top-p 0.95; \
	fi

wait: ## Wait for health; fail on crash/restart rather than masking startup errors
	python3 scripts/wait.py

up: download image start wait ## Download, build, start, and wait for the real model

stop: ## Stop server; stays stopped across reboots until make start
	docker stop --timeout 60 "$(CONTAINER)"

restart: ## Restart the current container and wait for readiness
	docker restart --timeout 60 "$(CONTAINER)"
	$(MAKE) wait

recreate: remove start wait ## Apply changed settings/image (does not delete model data)

remove: ## Remove only this deployment's container
	@if docker inspect "$(CONTAINER)" >/dev/null 2>&1; then docker rm -f "$(CONTAINER)"; fi

logs: ## Follow server logs
	docker logs -f --tail 100 "$(CONTAINER)"

status: ## Show container, health, restart policy and GPU usage
	docker inspect -f 'state={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{end}} restarts={{.RestartCount}} policy={{.HostConfig.RestartPolicy.Name}}' "$(CONTAINER)"
	docker stats --no-stream "$(CONTAINER)"
	nvidia-smi

smoke: wait ## Test health, authentication, model identity, chat, SSE and real disk streaming
	python3 scripts/smoke.py

bench: wait ## Measure prefill/gen tok/s; save JSON and append EXPERIMENTS.md (commit settings first)
	python3 scripts/benchmark.py --id "$(EXPERIMENT)" --max-tokens $(GEN_TOKENS)

restart-test: ## Kill the server and verify Docker automatically restarts it
	python3 scripts/restart_test.py

unit: ## Fast model-free automation tests
	python3 -m unittest discover -s tests -v

check: unit ## Check Python syntax and Dockerfile availability
	python3 -m py_compile scripts/*.py
	@test -s vendor/glm5next-moe-ssd-streaming.patch

test: check smoke restart-test ## Run local checks and real Docker integration tests

engine-bench: ## Natural-EOS OpenAI SSE benchmark for EXL3/Maya; record Git-linked prefill/gen metrics
	CONTAINER=$(BENCH_CONTAINER) python3 scripts/wait.py
	python3 scripts/engine_bench.py --id "$(EXPERIMENT)" --engine $(ENGINE) --container $(BENCH_CONTAINER) \
	  --url http://$(HOST):$(PORT) --repeats $(PROMPT_REPEATS)

include engines/exl3.mk
include engines/maya.mk
