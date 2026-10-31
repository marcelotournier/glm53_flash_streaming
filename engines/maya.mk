MAYA_IMAGE ?= $(IMAGE)
MAYA_CONTAINER ?= $(CONTAINER)
MAYA_MODEL_DIR ?= $(MODEL_DIR)
MAYA_MODEL_FILE ?= $(MODEL_FILE)
MAYA_MODEL_LOCK ?= $(MODEL_LOCK)
AJ_MODEL_DIR ?= $(CURDIR)/models/aj
AJ_MODEL_FILE := GLM-5.3-Flash-AJ-IQ2_XXS-00001-of-00002.gguf

aj-download: ## Download the exact AJ-IQ2_XXS quant linked in the user's 3090/Maya post (~87 GB)
	python3 scripts/download.py --lock aj.lock.json --dest "$(AJ_MODEL_DIR)" --jobs $(DOWNLOAD_JOBS)

.PHONY: aj-download maya-image maya-pack maya-pack-force maya-start maya-wait maya-stop maya-recreate maya-logs
maya-image: ## Build pinned Linux Strata-derived Maya engine for sm_86
	docker build -f engines/maya.Dockerfile --build-arg BUILD_JOBS=$(BUILD_JOBS) -t $(MAYA_IMAGE) .

maya-pack: ## Build the selected allowed compatibility pack once; never rewrite a live pack
	python3 scripts/download.py --lock $(MAYA_MODEL_LOCK) --dest "$(MAYA_MODEL_DIR)" --check-files
	@if [[ -f "$(MAYA_MODEL_DIR)/maya-pack/.ready" ]] && cmp -s "$(MAYA_MODEL_DIR)/maya-pack/.ready" <(sha256sum $(MAYA_MODEL_LOCK)); then \
	  echo 'Verified manifest pack marker already present'; else $(MAKE) maya-pack-force; fi

maya-pack-force: ## Rebuild selected pack (server must be stopped)
	python3 scripts/download.py --lock $(MAYA_MODEL_LOCK) --dest "$(MAYA_MODEL_DIR)" --check-files
	@test "$$(docker inspect -f '{{.State.Running}}' $(MAYA_CONTAINER) 2>/dev/null || true)" != true || { echo 'Stop the server before repacking'; exit 1; }
	docker run --rm --security-opt label=disable --memory 8g --memory-swap 8g \
	  --entrypoint python3 -v "$(MAYA_MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/iq_pack.py --gguf /models/$(MAYA_MODEL_FILE) --out /models/maya-pack --compat-bf16
	docker run --rm --security-opt label=disable --memory 4g --memory-swap 4g \
	  --entrypoint python3 -v "$(MAYA_MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/strata_tokenizer.py --gguf /models/$(MAYA_MODEL_FILE) --out /models/maya-pack
	sha256sum $(MAYA_MODEL_LOCK) > "$(MAYA_MODEL_DIR)/maya-pack/.ready"

maya-start: ## Run allowed <=100GB Maya quant, no expert skipping/LoRA/pruning
	python3 scripts/download.py --lock $(MAYA_MODEL_LOCK) --dest "$(MAYA_MODEL_DIR)" --check-files
	@cmp -s "$(MAYA_MODEL_DIR)/maya-pack/.ready" <(sha256sum $(MAYA_MODEL_LOCK)) || { echo 'Missing or wrong-quant pack marker; run make pack'; exit 1; }
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then \
	  actual=$$(docker inspect -f '{{range .Mounts}}{{if eq .Destination "/models"}}{{.Source}}{{end}}{{end}}' "$(MAYA_CONTAINER)"); \
	  identity=$$(docker inspect -f '{{index .Config.Labels "io.local.glm53.manifest-sha256"}}' "$(MAYA_CONTAINER)"); \
	  [[ "$$actual" == "$(MAYA_MODEL_DIR)" && "$$identity" == "$$(sha256sum $(MAYA_MODEL_LOCK) | cut -d' ' -f1)" ]] || { echo 'Container uses different/obsolete weights; use make recreate with the selected QUANT' >&2; exit 1; }; fi
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then docker start "$(MAYA_CONTAINER)"; else \
	  docker run -d --name "$(MAYA_CONTAINER)" --restart unless-stopped --init \
	    --device nvidia.com/gpu=all --security-opt label=disable \
	    --memory 24g --memory-swap 24g --shm-size 1g \
	    --log-opt max-size=20m --log-opt max-file=3 -p $(HOST):$(PORT):8080 \
	    -v "$(MAYA_MODEL_DIR):/models:ro" -v "$(MAYA_CONFIG):/config/maya.json:ro" \
	    --label io.local.glm53.quant=$(QUANT_LABEL) --label io.local.glm53.max-weight-bytes=$(if $(filter unsloth-iq3xxs,$(QUANT)),121000000000,100000000000) \
	    --label io.local.glm53.manifest-sha256=$$(sha256sum $(MAYA_MODEL_LOCK) | cut -d' ' -f1) \
	    "$(MAYA_IMAGE)" --api-key "$(API_KEY)"; fi

maya-wait: ## Wait for Maya API, rejecting crash loops
	CONTAINER=$(MAYA_CONTAINER) python3 scripts/wait.py

maya-stop: ## Explicitly stop Maya without removing model/pack
	docker stop --timeout 60 "$(MAYA_CONTAINER)"

maya-recreate: ## Reload changed Maya configuration without touching model data
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then docker rm -f "$(MAYA_CONTAINER)"; fi
	$(MAKE) maya-start maya-wait

maya-logs: ## Follow Maya engine logs
	docker logs -f --tail 100 "$(MAYA_CONTAINER)"
