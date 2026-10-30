MAYA_IMAGE ?= glm53-maya:local
MAYA_CONTAINER ?= glm53-flash-maya
MAYA_MODEL_DIR ?= $(AJ_MODEL_DIR)
MAYA_MODEL_FILE ?= $(AJ_MODEL_FILE)
MAYA_MODEL_LOCK ?= aj.lock.json
AJ_MODEL_DIR ?= $(CURDIR)/models/aj
AJ_MODEL_FILE := GLM-5.3-Flash-AJ-IQ2_XXS-00001-of-00002.gguf

aj-download: ## Download the exact AJ-IQ2_XXS quant linked in the user's 3090/Maya post (~87 GB)
	python3 scripts/download.py --lock aj.lock.json --dest "$(AJ_MODEL_DIR)" --jobs $(DOWNLOAD_JOBS)

.PHONY: maya-image maya-pack maya-start maya-wait maya-stop maya-recreate maya-logs
maya-image: ## Build pinned Linux Strata-derived Maya engine for sm_86
	docker build -f engines/maya.Dockerfile --build-arg BUILD_JOBS=$(BUILD_JOBS) -t $(MAYA_IMAGE) .

maya-pack: ## Index the allowed AJ GGUF for Maya; convert required small tensors and tokenizer
	python3 scripts/download.py --lock $(MAYA_MODEL_LOCK) --check-only
	docker run --rm --security-opt label=disable --memory 8g --memory-swap 8g \
	  --entrypoint python3 -v "$(MAYA_MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/iq_pack.py --gguf /models/$(MAYA_MODEL_FILE) --out /models/maya-pack --compat-bf16
	docker run --rm --security-opt label=disable --memory 4g --memory-swap 4g \
	  --entrypoint python3 -v "$(MAYA_MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/strata_tokenizer.py --gguf /models/$(MAYA_MODEL_FILE) --out /models/maya-pack

maya-start: ## Run allowed <=100GB Maya quant, no expert skipping/LoRA/pruning
	python3 scripts/download.py --lock $(MAYA_MODEL_LOCK) --check-only
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then \
	  actual=$$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/models"}}{{.Source}}{{end}}{{end}}' "$(MAYA_CONTAINER)"); \
	  [[ "$$actual" == "$(MAYA_MODEL_DIR)" ]] || { echo 'Container uses a different/obsolete weight directory; use make maya-recreate' >&2; exit 1; }; fi
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then docker start "$(MAYA_CONTAINER)"; else \
	  docker run -d --name "$(MAYA_CONTAINER)" --restart unless-stopped --init \
	    --device nvidia.com/gpu=all --security-opt label=disable \
	    --memory 24g --memory-swap 24g --shm-size 1g \
	    --log-opt max-size=20m --log-opt max-file=3 -p $(HOST):$(PORT):8080 \
	    -v "$(MAYA_MODEL_DIR):/models:ro" -v "$(CURDIR)/engines/maya.json:/config/maya.json:ro" \
	    "$(MAYA_IMAGE)"; fi

maya-wait: ## Wait for Maya API, rejecting crash loops
	CONTAINER=$(MAYA_CONTAINER) python3 scripts/wait.py

maya-stop: ## Explicitly stop Maya without removing model/pack
	docker stop --timeout 60 "$(MAYA_CONTAINER)"

maya-recreate: ## Reload changed Maya configuration without touching model data
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then docker rm -f "$(MAYA_CONTAINER)"; fi
	$(MAKE) maya-start maya-wait

maya-logs: ## Follow Maya engine logs
	docker logs -f --tail 100 "$(MAYA_CONTAINER)"
