MAYA_IMAGE ?= glm53-maya:local
MAYA_CONTAINER ?= glm53-flash-maya

.PHONY: maya-image maya-pack maya-start maya-wait maya-stop maya-logs
maya-image: ## Build pinned Linux Strata-derived Maya engine for sm_86
	docker build -f engines/maya.Dockerfile --build-arg BUILD_JOBS=$(BUILD_JOBS) -t $(MAYA_IMAGE) .

maya-pack: ## Index existing GGUF for Maya, upgrade required small tensors and export tokenizer
	docker run --rm --security-opt label=disable --memory 8g --memory-swap 8g \
	  --entrypoint python3 -v "$(MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/iq_pack.py --gguf /models/$(MODEL_FILE) --out /models/maya-pack --compat-bf16
	docker run --rm --security-opt label=disable --memory 4g --memory-swap 4g \
	  --entrypoint python3 -v "$(MODEL_DIR):/models" "$(MAYA_IMAGE)" \
	  tools/strata_tokenizer.py --gguf /models/$(MODEL_FILE) --out /models/maya-pack

maya-start: ## Run Maya on existing unmodified GGUF, no skipping/LoRA/pruning
	@if docker inspect "$(MAYA_CONTAINER)" >/dev/null 2>&1; then docker start "$(MAYA_CONTAINER)"; else \
	  docker run -d --name "$(MAYA_CONTAINER)" --restart unless-stopped --init \
	    --device nvidia.com/gpu=all --security-opt label=disable \
	    --memory 24g --memory-swap 24g --shm-size 1g \
	    --log-opt max-size=20m --log-opt max-file=3 -p $(HOST):$(PORT):8080 \
	    -v "$(MODEL_DIR):/models:ro" -v "$(CURDIR)/engines/maya.json:/config/maya.json:ro" \
	    "$(MAYA_IMAGE)"; fi

maya-wait: ## Wait for Maya API, rejecting crash loops
	CONTAINER=$(MAYA_CONTAINER) python3 scripts/wait.py

maya-stop: ## Explicitly stop Maya without removing model/pack
	docker stop --timeout 60 "$(MAYA_CONTAINER)"

maya-logs: ## Follow Maya engine logs
	docker logs -f --tail 100 "$(MAYA_CONTAINER)"
