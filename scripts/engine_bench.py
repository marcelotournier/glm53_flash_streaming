#!/usr/bin/env python3
"""Cross-engine OpenAI SSE benchmark: uncached long prompt, natural-end generation."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import urllib.request
from download import validate_manifest


def get(url):
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return json.load(response)
    except (OSError, ValueError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    parser.add_argument('--engine', required=True, choices=['exl3', 'maya', 'llama'])
    parser.add_argument('--container', required=True)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--repeats', type=int, default=1600)
    parser.add_argument('--model-lock', type=Path, default=Path('aj.lock.json'))
    parser.add_argument('--prompt-style', choices=['repeated', 'repo'], default='repeated')
    parser.add_argument('--source-chars', type=int, default=100000)
    parser.add_argument('--prefill-only', action='store_true', help='Natural short factual answer; decode rate is not sustained')
    parser.add_argument('--needle-test', action='store_true', help='Near-256K retrieval check; requires >=250000 prompt tokens')
    args = parser.parse_args()
    model_manifest = json.loads(args.model_lock.read_text())
    validate_manifest(model_manifest)
    if not args.id.replace('-', '').isalnum():
        raise ValueError('Use an alphanumeric/hyphen experiment ID')
    path = Path(f'results/experiment-{args.id}.json')
    if path.exists():
        raise RuntimeError(f'{path} already exists')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    if subprocess.check_output(['git', 'status', '--porcelain', '--untracked-files=no'], text=True).strip():
        raise RuntimeError('Commit and push settings before measuring')
    state = json.loads(subprocess.check_output(['docker', 'inspect', args.container]))[0]
    command = (state['Config'].get('Cmd') or []).copy()
    if '--api-key' in command:
        command[command.index('--api-key') + 1] = '<redacted>'
    nonce = secrets.token_hex(12)
    if args.prompt_style == 'repo':
        sources = [Path(p) for p in ('README.md', 'SPEC.md', 'ENGINES.md', 'Makefile')]
        sources += sorted(Path('scripts').glob('*.py'))
        corpus = '\n\n'.join(f'FILE: {p}\n{p.read_text()}' for p in sources)
        background = (corpus * (args.source_chars // len(corpus) + 1))[:args.source_chars]
    else:
        background = 'alpha beta gamma delta. ' * args.repeats
    needle = 'ORCHID-SILVER-7429' if args.needle_test else None
    if needle:
        at = len(background) // 3
        background = (background[:at] + '\n[AUDIT RECORD]\nThe retrieval_code is ' + needle +
                      '. Preserve it exactly for the final question.\n[END AUDIT RECORD]\n' + background[at:])
        args.prefill_only = True
    instruction = 'Read this document and retain its AUDIT RECORD.' if needle else 'Background notes to ignore:'
    prompt = (f'Independent benchmark {nonce}. {instruction}\n' + background +
              '\nIgnore the background notes. Explain why the sky is blue in three paragraphs. '
              'Mention Rayleigh scattering and why sunsets look red. Answer directly without thinking aloud.')
    if args.prefill_only:
        prompt = prompt[:prompt.index('\nIgnore the background notes.')] + (
            '\nIgnore the background notes. What is the capital of France? Answer only with the city name.')
    if needle:
        prompt = prompt[:prompt.index('\nIgnore the background notes.')] + (
            '\nWhat is the exact retrieval_code from the AUDIT RECORD? Return only that code, no other words.')
    payload = {'model': 'glm-5.3-flash', 'messages': [{'role': 'user', 'content': prompt}],
               'temperature': 0, 'seed': 42, 'stream': True,
               'stream_options': {'include_usage': True}, 'cache_prompt': False,
               'chat_template_kwargs': {'enable_thinking': False, 'reasoning_effort': 'low'}}
    before = get(args.url + '/stats')
    started = time.monotonic()
    first = last = None
    text = reasoning = ''
    usage, native_timings, finish = {}, {}, None
    done = False
    error = None
    try:
        req = urllib.request.Request(args.url + '/v1/chat/completions', json.dumps(payload).encode(),
            {'Content-Type': 'application/json', 'Authorization': 'Bearer ' + os.getenv('API_KEY', 'local')})
        with urllib.request.urlopen(req, timeout=float(os.getenv('REQUEST_TIMEOUT', '1800'))) as response:
            for line in response:
                line = line.decode().strip()
                if not line.startswith('data:'):
                    continue
                body = line[5:].strip()
                if body == '[DONE]':
                    done = True
                    break
                event = json.loads(body)
                if event.get('error'):
                    raise RuntimeError(event['error'])
                if event.get('usage'):
                    usage = event['usage']
                if event.get('timings'):
                    native_timings = event['timings']
                for choice in event.get('choices', []):
                    delta = choice.get('delta', {})
                    content = delta.get('content') or ''
                    think = delta.get('reasoning_content') or ''
                    if content or think:
                        now = time.monotonic()
                        first = first or now
                        last = now
                    text += content
                    reasoning += think
                    finish = choice.get('finish_reason') or finish
    except Exception as exc:
        error = repr(exc)
    elapsed = time.monotonic() - started
    final = json.loads(subprocess.check_output(['docker', 'inspect', args.container]))[0]
    prompt_n, gen_n = usage.get('prompt_tokens', 0), usage.get('completion_tokens', 0)
    prefill = prompt_n / (first - started) if first and prompt_n else None
    decode = (gen_n - 1) / (last - first) if first and last > first and gen_n > 1 else None
    cached = usage.get('prompt_tokens_details', {}).get('cached_tokens')
    expected = needle.lower() if needle else ('paris' if args.prefill_only else 'rayleigh')
    passed = (error is None and done and finish == 'stop' and prompt_n > 256 and
              gen_n >= (1 if args.prefill_only else 32) and expected in text.lower() and final['State']['Running'] and
              final['RestartCount'] == state['RestartCount'] and (cached is None or cached == 0) and
              (not args.needle_test or prompt_n >= 250000))
    receipt = {'id': args.id, 'engine': args.engine, 'prompt_style': args.prompt_style,
        'prefill_only': args.prefill_only, 'needle_code': needle, 'configuration_commit': commit,
        'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'image_id': state['Image'], 'command': command, 'mounts': state['Mounts'],
        'container_started_at': state['State']['StartedAt'],
        'model_manifest': model_manifest,
        'environment': [e for e in state['Config']['Env'] if e.startswith(('GLM53_', 'MAYA_', 'STRATA_'))],
        'request': payload, 'usage': usage, 'native_timings': native_timings, 'finish_reason': finish,
        'content': text, 'reasoning': reasoning, 'done': done, 'elapsed_s': elapsed,
        'ttft_s': first - started if first else None, 'prefill_tok_s': prefill, 'generation_tok_s': decode,
        'metric': 'prompt_tokens/TTFT; (completion_tokens-1)/(last-first text token); natural EOS, no output cap',
        'cache_policy': 'fresh engine recommended, independent nonce, cache_prompt=false; cached counter may be unavailable',
        'stats_before': before, 'stats_after': get(args.url + '/stats'), 'passed': passed, 'error': error}
    receipt['docker_stats'] = json.loads(subprocess.check_output(['docker', 'stats', '--no-stream',
        '--format', '{{json .}}', args.container], text=True))
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    pp = f'{prefill:.2f}' if prefill is not None else 'N/A'
    tg = f'{decode:.2f}' if decode is not None else 'N/A'
    report = (f'\n### {args.id} — {args.engine} — {receipt["tested_at"]}\n\n'
        f'- Configuration commit: `{commit}`; receipt: [{path}]({path}).\n'
        f'- **Prefill: {pp} tok/s; generation: {tg} tok/s.** '
        f'Prompt={prompt_n}, generated={gen_n}, cached={cached if cached is not None else "counter unavailable"}; '
        f'wall={elapsed:.2f}s. TTFT-based prefill includes first-token overhead; prompt style={args.prompt_style}, natural-end answer.\n'
        f'- Outcome={"PASS" if passed else "FAIL"}; finish={finish}; error={error}; '
        f'RAM={receipt["docker_stats"]["MemUsage"]}.\n'
        + ('- Prefill-only probe: factual short answer; gen rate is NOT sustained throughput.\n' if args.prefill_only else ''))
    with Path('EXPERIMENTS.md').open('a') as stream:
        stream.write(report)
    print(report, flush=True)
    if not passed:
        raise RuntimeError('Benchmark/correctness gate failed; receipt preserved')


if __name__ == '__main__':
    main()
