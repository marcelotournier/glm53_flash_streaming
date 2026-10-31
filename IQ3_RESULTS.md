# IQ3_XXS — validated, slower than IQ1_S

User explicitly authorized the pinned 120,367,571,840-byte Unsloth UD-IQ3_XXS after the 027 size blocker. SPEC.md records the manifest-only exception (121 GB); other models retain 100 GB. All four downloaded shards SHA256-verified; compatibility pack built without expert pruning/requantization. IQ1_S weights, pack and winning settings preserved.

Settings committed/pushed before testing: `25bb355727cfd80ffd188b72cc0a3df2332e4536`. Image `sha256:af26ebe63f5296347660dd6091655235c74279fac8ab8fca1fd690fc488b950d`; unchanged `engines/maya.json` (15 GiB expert RAM, 4 readers/chunks, 32K prefill, 256K context, KV streaming, MTP off). 24 GiB container RAM, no swap. Manifest: `unsloth-iq3xxs.lock.json`, SHA256 `0a1930c5a568e98d638df88e36b7f3d9cc60b818ed095c9d10a3466070b82442`.

| Receipt | Exact replay | Cached | Native prefill tok/s | Generation tok/s | Result |
|---|---|---:|---:|---:|---|
| 028 | AJ012, 25,558 tokens | 0 | 798.10 | 3.02 | Correct sky explanation, 439 tokens, natural EOS |
| 029 | AJ011, 32,058 tokens | 0 | 888.80 | N/A | Paris, 2 tokens |
| 030 | AJ015, 255,099 tokens | 0 | 836.90 | N/A | Exact ORCHID-SILVER-7429, 11 tokens |

Generation for 028 uses streamed token timing (native rounded 3.0). Short 029/030 replies are not sustained decode measurements. All were cold engine replays, same exact requests as historical targets. IQ1_S 021/022 achieved ~989–990 prefill /5.02–5.15 generation on the 25,558-token request; IQ3 is slower with this unchanged profile. Different outputs/token counts and CPU placement preclude identical-output causal isolation. No broad quality superiority claim.

Memory peaks: 028 **23.81 GiB**, 029 **24.00 GiB (at the limit)**, 030 **22.80 GiB**. Successful requests do not imply comfortable memory headroom. Do not increase RAM tier. No tuning attempted. Current post-validation memory.events has oom=0/oom_kill=0; counters reset across lifecycle tests, so that is not historical proof for every request.

031: 10 unit tests, auth rejection/model ID, chat/SSE/multi-turn and **39.34 GB actual disk reads** passed immediately after the 255K request, without a restart before smoke. Automatic API-crash recovery and explicit stop/start semantics passed; IQ3 server left healthy/running. See `results/experiment-028-*.json` through `031-*.json` and EXPERIMENTS.md for exact receipts/log excerpts. One initial 029 command was rejected before inference by the dirty-settings guard (028 results not yet committed); results were committed/pushed, then the correct AJ011 replay path used. No failed inference concealed.

## Operations

Default Makefile quant remains IQ1_S deliberately. For the currently running IQ3 use explicit `make QUANT=unsloth-iq3xxs status`, `stop`, `start`, `restart`, `test`, or `bench`.

Return to preserved IQ1_S: `make QUANT=unsloth-iq1s recreate`. Return to IQ3: `make QUANT=unsloth-iq3xxs recreate`. Only one GPU engine at a time; do not repack a running model. No new build is needed.
