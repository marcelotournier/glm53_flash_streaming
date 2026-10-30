# Existing 0xSero/Sybil NVMe engine, not a new inference implementation.
EXL3_IMAGE := ghcr.io/sybil-solutions/glm53-flash-offload@sha256:aa74200f16c86588b101be2315aed2f643d148559179eef52a02599016b56e69
EXL3_CONTAINER ?= glm53-flash-exl3
EXL3_MODEL_DIR ?= $(CURDIR)/models/exl3
EXL3_STORE_DIR ?= $(CURDIR)/models/exl3-store
EXL3_CACHE_DIR ?= $(CURDIR)/models/exl3-cache
EXL3_MODE ?= nvme
EXL3_MEMORY ?= 24g
EXL3_CHUNK ?= 8192
EXL3_CTX ?= 131072

.PHONY: exl3-image exl3-download exl3-probe exl3-pack exl3-verify exl3-start exl3-wait exl3-up exl3-stop exl3-recreate exl3-logs
exl3-image: ## Pull the exact published 0xSero/Sybil NVMe runtime
	docker pull "$(EXL3_IMAGE)"

exl3-download: ## Download and hash-verify pinned EXL3 3.05bpw (~125 GB)
	python3 scripts/download.py --lock exl3.lock.json --dest "$(EXL3_MODEL_DIR)" --jobs $(DOWNLOAD_JOBS)

exl3-probe: ## Test actual O_DIRECT on this host before building the expert store
	mkdir -p "$(EXL3_STORE_DIR)" "$(EXL3_CACHE_DIR)"
	docker run --rm --security-opt label=disable -v "$(EXL3_STORE_DIR):/nvx" \
	  "$(EXL3_IMAGE)" python3 /opt/glm53/docker/preflight.py odirect /nvx

exl3-pack: ## Prohibited 125GB candidate: hard size guard rejects before packing
	python3 scripts/download.py --lock exl3.lock.json --check-only
	$(MAKE) exl3-probe
	docker run --rm --name glm53-exl3-pack --security-opt label=disable --memory 12g --memory-swap 12g \
	  -v "$(EXL3_MODEL_DIR):/models:ro" -v "$(EXL3_STORE_DIR):/nvx" \
	  -e GLM53_PACK_THREADS=4 "$(EXL3_IMAGE)" pack-store

exl3-verify: ## Prohibited 125GB candidate: guarded historical verification target
	python3 scripts/download.py --lock exl3.lock.json --check-only
	docker run --rm --security-opt label=disable --memory 12g --memory-swap 12g \
	  -v "$(EXL3_MODEL_DIR):/models:ro" -v "$(EXL3_STORE_DIR):/nvx:ro" \
	  -e GLM53_PACK_THREADS=4 "$(EXL3_IMAGE)" verify-store

exl3-start: ## Prohibited 125GB candidate: hard size guard rejects before startup
	python3 scripts/download.py --lock exl3.lock.json --check-only
	@mkdir -p "$(EXL3_CACHE_DIR)"
	@if docker inspect "$(EXL3_CONTAINER)" >/dev/null 2>&1; then docker start "$(EXL3_CONTAINER)"; else \
	  docker run -d --name "$(EXL3_CONTAINER)" --restart unless-stopped --init \
	    --device nvidia.com/gpu=all --security-opt label=disable \
	    --memory $(EXL3_MEMORY) --memory-swap $(EXL3_MEMORY) --shm-size 1g \
	    --log-opt max-size=20m --log-opt max-file=3 -p $(HOST):$(PORT):30000 \
	    -v "$(EXL3_MODEL_DIR):/models:ro" -v "$(EXL3_STORE_DIR):/nvx:ro" \
	    -v "$(EXL3_CACHE_DIR):/root/.cache" \
	    -e GLM53_MODE=$(EXL3_MODE) -e GLM53_MODEL_DOWNLOAD=0 -e GLM53_EC_MAX_SLOTS=1376 \
	    -e GLM53_NV_SMALL_BELOW_GB=25 -e GLM53_NV_MARGIN_GB=2 \
	    -e GLM53_RCS_GB=1 -e GLM53_NV_THREADS=16 -e GLM53_NV_PIECE_KB=1024 \
	    -e GLM53_NV_CPU_CPUS=2-7 -e GLM53_NV_CPU_THREADS=6 \
	    -e GLM53_MAIN_CPUS=0 -e GLM53_NV_CTL_CPU=1 -e GLM53_NV_READER_CPUS=8-15 \
	    "$(EXL3_IMAGE)" -cs $(EXL3_CTX) -chunk_size $(EXL3_CHUNK); fi

exl3-wait: ## Wait for EXL3 health, rejecting crash loops
	CONTAINER=$(EXL3_CONTAINER) python3 scripts/wait.py

exl3-up: exl3-image exl3-download exl3-pack exl3-start exl3-wait ## Prepare and run published NVMe engine

exl3-stop: ## Explicitly stop EXL3; leaves model and expert store intact
	docker stop --timeout 60 "$(EXL3_CONTAINER)"

exl3-recreate: ## Apply changed EXL3 settings without deleting weights/store
	@if docker inspect "$(EXL3_CONTAINER)" >/dev/null 2>&1; then docker rm -f "$(EXL3_CONTAINER)"; fi
	$(MAKE) exl3-start exl3-wait

exl3-logs: ## Follow EXL3 engine logs
	docker logs -f --tail 100 "$(EXL3_CONTAINER)"
