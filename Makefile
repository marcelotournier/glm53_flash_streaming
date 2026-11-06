SHELL := /bin/bash
.DEFAULT_GOAL := help
.NOTPARALLEL:

# Only explicit <=100 GB candidates; frozen AJ rollback: make QUANT=aj recreate.
QUANT ?= unsloth-iq1s
ifeq ($(QUANT),aj)
MODEL_FILE := GLM-5.3-Flash-AJ-IQ2_XXS-00001-of-00002.gguf
QUANT_LABEL := AJ-IQ2_XXS
MAYA_CONFIG ?= $(CURDIR)/engines/aj-baseline.json
else ifeq ($(QUANT),unsloth-iq1s)
MODEL_FILE := GLM-5.3-Flash-UD-IQ1_S-00001-of-00003.gguf
QUANT_LABEL := UD-IQ1_S
MAYA_CONFIG ?= $(CURDIR)/engines/iq1s-64gb.json
MAYA_MEMORY ?= 50g
else ifeq ($(QUANT),unsloth-iq3xxs)
MODEL_FILE := GLM-5.3-Flash-UD-IQ3_XXS-00001-of-00004.gguf
QUANT_LABEL := UD-IQ3_XXS
MAYA_CONFIG ?= $(CURDIR)/engines/maya.json
else
$(error Unsupported QUANT: choose aj, unsloth-iq1s or explicitly authorized unsloth-iq3xxs)
endif
MODEL_LOCK := $(QUANT).lock.json
IMAGE ?= glm53-maya:local
CONTAINER ?= glm53-flash-maya
MODEL_DIR ?= $(CURDIR)/models/$(QUANT)
HOST ?= 127.0.0.1
PORT ?= 8000
API_KEY ?= local
BUILD_JOBS ?= 4
DOWNLOAD_JOBS ?= 4
STARTUP_TIMEOUT ?= 1800
REQUEST_TIMEOUT ?= 1800
EXPERIMENT ?= $(shell date -u +%Y%m%dT%H%M%SZ)
ENGINE ?= maya
BENCH_CONTAINER ?= $(CONTAINER)
PROMPT_REPEATS ?= 1600
PREFILL_ONLY ?= 0
NEEDLE_TEST ?= 0
PROMPT_STYLE ?= repeated
SOURCE_CHARS ?= 100000
ENGINE_MODEL_LOCK ?= $(MODEL_LOCK)
REPLAY_RECEIPT ?=
export CONTAINER HOST PORT API_KEY STARTUP_TIMEOUT REQUEST_TIMEOUT MODEL_LOCK

.PHONY: help download verify image pack start wait up stop restart recreate logs status smoke bench engine-bench restart-test unit check test
help: ## Show automation targets
	@grep -h -E '^[a-zA-Z0-9_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS=":.*?## "}; {printf "%-18s %s\n", $$1, $$2}'

download: ## Resume and SHA256-verify the selected allowed quant
	python3 scripts/download.py --lock $(MODEL_LOCK) --dest "$(MODEL_DIR)" --jobs $(DOWNLOAD_JOBS)
verify: ## Rehash every selected shard and enforce the 100 GB hard limit
	python3 scripts/download.py --lock $(MODEL_LOCK) --dest "$(MODEL_DIR)" --verify
image: maya-image ## Build pinned Strata-derived Maya CUDA sm_86 image
pack: maya-pack ## Build the small compatibility pack and tokenizer once
start: maya-start ## Start the selected Maya server, restart=unless-stopped
wait: maya-wait ## Wait for the real model/API, reject crash loops
up: download image pack start wait ## Download, build, pack, serve and wait for the allowed recipe
stop: maya-stop ## Explicitly stop server; remains stopped until make start
recreate: maya-recreate ## Apply changed settings/image without deleting model data
restart: ## Restart the existing selected allowed container, then wait for readiness
	python3 scripts/download.py --lock $(MODEL_LOCK) --check-only
	$(MAKE) start
	docker restart --timeout 60 "$(CONTAINER)"
	$(MAKE) wait
logs: maya-logs ## Follow server logs
status: ## Show container health/restart policy, RAM and GPU use
	docker inspect -f 'state={{.State.Status}} health={{if .State.Health}}{{.State.Health.Status}}{{end}} restarts={{.RestartCount}} policy={{.HostConfig.RestartPolicy.Name}}' "$(CONTAINER)"
	docker stats --no-stream "$(CONTAINER)"
	nvidia-smi
smoke: wait ## Real selected model health/auth/chat/SSE/multi-turn smoke test
	python3 scripts/maya_smoke.py --id "$(EXPERIMENT)"
bench: engine-bench ## Measure separate prefill/gen rates, save JSON and append EXPERIMENTS.md
engine-bench: wait ## Natural-EOS OpenAI SSE benchmark; commit/push settings first
	python3 scripts/engine_bench.py --id "$(EXPERIMENT)" --engine $(ENGINE) --container $(BENCH_CONTAINER) \
	  --url http://$(HOST):$(PORT) --repeats $(PROMPT_REPEATS) --prompt-style $(PROMPT_STYLE) --source-chars $(SOURCE_CHARS) --model-lock $(ENGINE_MODEL_LOCK) $(if $(filter 1,$(PREFILL_ONLY)),--prefill-only,) $(if $(filter 1,$(NEEDLE_TEST)),--needle-test,) $(if $(REPLAY_RECEIPT),--replay-receipt $(REPLAY_RECEIPT),)
restart-test: ## Kill inference and verify automatic Docker recovery
	python3 scripts/restart_test.py --id "$(EXPERIMENT)"
unit: ## Fast model-free automation tests, including the hard 100 GB limit
	python3 -m unittest discover -s tests -v
check: unit ## Check Python syntax and vendored patch availability
	python3 -m py_compile scripts/*.py
	@test -s vendor/glm5next-moe-ssd-streaming.patch
test: check smoke restart-test ## Real Docker functional and recovery tests

include engines/maya.mk
