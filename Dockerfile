# Pinned Unsloth GLM5Next + freedomljc/xMytze NVMe expert-streaming recipe.
ARG CUDA_BUILD_IMAGE=nvidia/cuda:12.8.1-devel-ubuntu24.04@sha256:520292dbb4f755fd360766059e62956e9379485d9e073bbd2f6e3c20c270ed66
ARG CUDA_RUN_IMAGE=nvidia/cuda:12.8.1-runtime-ubuntu24.04@sha256:ebef3c171eeef0298e4eb2e4be843105edf3b8b0ac45e0b43acee358e8046867
FROM ${CUDA_BUILD_IMAGE} AS build
ARG LLAMA_REV=86ebfef2c6a0f3359a2a07d2c215d61b0fa885c9
ARG BUILD_JOBS=4
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl git cmake ninja-build g++ libcurl4-openssl-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
RUN curl -fL --retry 5 https://github.com/unslothai/llama.cpp/archive/${LLAMA_REV}.tar.gz \
    | tar xz --strip-components=1
COPY vendor/glm5next-moe-ssd-streaming.patch /tmp/streaming.patch
RUN echo 'd544c2b5f566c0b02483e1a8d6a09db0345c27a1c959b0a194fff8dac05d279b  /tmp/streaming.patch' | sha256sum -c - \
    && git apply --check /tmp/streaming.patch && git apply /tmp/streaming.patch
RUN cmake -S . -B build -G Ninja -DCMAKE_BUILD_TYPE=Release \
    -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DBUILD_SHARED_LIBS=OFF \
    -DGGML_NATIVE=OFF -DLLAMA_CURL=ON -DLLAMA_BUILD_TESTS=OFF \
    && cmake --build build -j ${BUILD_JOBS} --target llama-server
FROM ${CUDA_RUN_IMAGE}
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl libgomp1 libcurl4t64 libssl3t64 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /src/build/bin/llama-server /app/llama-server
COPY vendor/LICENSE /app/LICENSE.llama.cpp
LABEL org.opencontainers.image.source="https://github.com/xMytze/glm53-ssd-streaming" \
      io.local.llama.revision="86ebfef2c6a0f3359a2a07d2c215d61b0fa885c9" \
      io.local.streaming.revision="9900b7ab1f32ee3fcfb19c83d4862aaee9b46f5e"
ENV LLAMA_ARG_HOST=0.0.0.0 NVIDIA_TF32_OVERRIDE=0 \
    GGML_CUDA_REGISTER_HOST=1 GGML_CUDA_REGISTER_HOST_RW=1 \
    LLAMA_MOE_STREAM_STATS=1 LLAMA_MOE_STREAM_PREFETCH=0
WORKDIR /app
HEALTHCHECK --interval=30s --timeout=5s --start-period=30m --retries=3 \
    CMD curl -fsS http://127.0.0.1:8080/health || exit 1
ENTRYPOINT ["/app/llama-server"]
