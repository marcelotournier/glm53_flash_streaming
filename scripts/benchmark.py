#!/usr/bin/env python3
"""Measure real prefill/decode, preserve a receipt, append EXPERIMENTS.md."""
import argparse
import json
from pathlib import Path
import subprocess
import time
from smoke import MODEL, direct_io_files, io_stats, request
from wait import inspect


def git(*args):
    return subprocess.check_output(['git', *args], text=True).strip()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True, help='Unique experiment label')
    parser.add_argument('--max-tokens', type=int, default=128)
    args = parser.parse_args()
    if not args.id.replace('-', '').replace('_', '').isalnum():
        raise ValueError('Experiment ID must be alphanumeric, hyphen or underscore')
    path = Path(f'results/experiment-{args.id}.json')
    if path.exists():
        raise RuntimeError(f'Receipt already exists: {path}; use a new experiment ID')
    commit = git('rev-parse', 'HEAD')
    if git('status', '--porcelain', '--untracked-files=no'):
        raise RuntimeError('Commit tracked configuration changes before benchmarking')
    state = inspect()
    command = state['Config']['Cmd'].copy()
    if '--api-key' in command:
        command[command.index('--api-key') + 1] = '<redacted>'
    direct = direct_io_files()
    prompt = ('Background notes (ignore this repetition): ' +
              'alpha beta gamma delta. ' * 80 +
              '\nWrite a detailed practical explanation of why the sky is blue. '
              'Use complete sentences and explain scattering, wavelengths, and sunsets. '
              'Continue for at least 300 words. Do not discuss the background notes.')
    payload = {'model': MODEL, 'messages': [{'role': 'user', 'content': prompt}],
               'max_tokens': args.max_tokens, 'temperature': 0, 'seed': 42,
               'cache_prompt': False, 'chat_template_kwargs': {'reasoning_effort': 'low'}}
    before = io_stats()
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        result = json.load(response)
    elapsed = time.monotonic() - started
    after = io_stats()
    timings = result['timings']
    usage = result['usage']
    final = inspect()
    valid = (usage['completion_tokens'] >= min(64, args.max_tokens) and
             timings['cache_n'] == 0 and timings['prompt_n'] > 256 and
             final['State']['Running'] and final['RestartCount'] == state['RestartCount'])
    resource = subprocess.check_output(['docker', 'stats', '--no-stream',
        '--format', '{{json .}}', state['Name'].lstrip('/')], text=True).strip()
    gpu = subprocess.check_output(['nvidia-smi', '--query-gpu=memory.used,memory.total',
                                   '--format=csv,noheader,nounits'], text=True).strip()
    receipt = {'id': args.id, 'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'configuration_commit': commit, 'image_id': state['Image'], 'command': command,
               'environment': state['Config']['Env'], 'request': payload, 'response': result,
               'elapsed_s': elapsed, 'disk_read_bytes': after['read_bytes'] - before['read_bytes'],
               'direct_io_files': direct, 'docker_stats': json.loads(resource),
               'gpu_memory_used_total_mib': gpu, 'passed': valid}
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    prefill = timings['prompt_per_second']
    decode = timings['predicted_per_second']
    report = (f'\n### {args.id} — {receipt["tested_at"]}\n\n'
              f'- Configuration commit: `{commit}`; receipt: [{path}]({path}).\n'
              f'- Settings: CPU_MOE={command[command.index("--n-cpu-moe") + 1]}, '
              f'cache={command[command.index("--moe-stream-cache") + 1]}, '
              f'batch/ubatch={command[command.index("--ubatch-size") + 1]}, '
              f'context={command[command.index("--ctx-size") + 1]}.\n'
              f'- **Prefill: {prefill:.2f} tok/s; generation: {decode:.2f} tok/s.** '
              f'New prompt={timings["prompt_n"]}, cached={timings["cache_n"]}, '
              f'generated={usage["completion_tokens"]}; wall={elapsed:.2f}s; '
              f'disk read={receipt["disk_read_bytes"] / 1e9:.2f} GB.\n'
              f'- RAM={receipt["docker_stats"]["MemUsage"]}; GPU used/total={gpu} MiB; '
              f'outcome={"PASS" if valid else "FAIL (inspect receipt)"}.\n')
    with Path('EXPERIMENTS.md').open('a') as stream:
        stream.write(report)
    print(report, flush=True)
    if not valid:
        raise RuntimeError('Benchmark failed validation; result still recorded')


if __name__ == '__main__':
    main()
