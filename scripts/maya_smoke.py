#!/usr/bin/env python3
"""Real allowed-quant Maya smoke: auth, chat, SSE, multi-turn state and disk I/O."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import urllib.error
from download import validate_manifest
from smoke import request, io_stats, validate_sse
from wait import inspect


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    if not args.id.replace('-', '').isalnum():
        raise ValueError('Use an alphanumeric/hyphen ID')
    path = Path(f'results/experiment-{args.id}-smoke.json')
    if path.exists():
        raise RuntimeError(f'{path} already exists')
    manifest = json.loads(Path('aj.lock.json').read_text())
    validate_manifest(manifest)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    state = inspect()
    assert state['State']['Running']
    assert state['Config']['Labels'].get('io.local.glm53.quant') == 'AJ-IQ2_XXS', 'Wrong/obsolete model container'
    assert state['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped'
    assert any(m['Destination'] == '/models' and not m['RW'] for m in state['Mounts'])
    with request('/health') as response:
        assert json.load(response)['status'] == 'ok'
    try:
        request('/v1/models', key='wrong-key-for-auth-test')
    except urllib.error.HTTPError as error:
        assert error.code == 401, error.code
    else:
        raise AssertionError('Bad API key accepted')
    with request('/v1/models') as response:
        models = json.load(response)
    assert 'glm-5.3-flash' in [m['id'] for m in models['data']]
    before = io_stats()
    payload = {'model': 'glm-5.3-flash', 'messages': [{'role': 'user', 'content':
        'What is the capital of France? Answer only with the city name.'}], 'temperature': 0,
        'chat_template_kwargs': {'enable_thinking': False, 'reasoning_effort': 'low'}}
    rows = []
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        chat = json.load(response)
    assert 'paris' in (chat['choices'][0]['message'].get('content') or '').lower(), chat
    assert chat['choices'][0]['finish_reason'] == 'stop', chat
    rows.append(('factual chat', chat.get('timings', {}), time.monotonic() - started))
    payload['stream'] = True
    payload['stream_options'] = {'include_usage': True}
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        stream = validate_sse(response)
    rows.append(('SSE repeat (warm)', stream['timings'], time.monotonic() - started))
    payload['stream'] = False
    payload['messages'] += [{'role': 'assistant', 'content': 'Paris'}, {'role': 'user',
        'content': 'Now name the capital of Japan. Answer only with the city name.'}]
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        turn = json.load(response)
    assert 'tokyo' in (turn['choices'][0]['message'].get('content') or '').lower(), turn
    assert turn['choices'][0]['finish_reason'] == 'stop', turn
    rows.append(('multi-turn state', turn.get('timings', {}), time.monotonic() - started))
    after = io_stats()
    assert after['read_bytes'] > before['read_bytes'], 'No real NVMe reads during inference'
    final = inspect()
    assert final['State']['Running'] and final['RestartCount'] == state['RestartCount']
    receipt = {'configuration_commit': commit, 'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'image_id': state['Image'], 'model_manifest': manifest, 'models': models, 'chat': chat,
        'stream': stream, 'multi_turn': turn, 'disk_read_bytes': after['read_bytes'] - before['read_bytes'],
        'phases': [{'name': n, 'timings': t, 'wall_s': w} for n, t, w in rows], 'passed': True}
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    report = f'\n### {args.id}-smoke — AJ Maya functional checks\n\n- Config `{commit}`; receipt [{path}]({path}).\n'
    for name, timings, wall in rows:
        pp, tg = timings.get('prompt_per_second'), timings.get('predicted_per_second')
        report += (f'- {name}: prefill={pp if pp is not None else "N/A"} tok/s; '
                   f'gen={tg if tg is not None else "N/A"} tok/s; wall={wall:.2f}s '
                   '(short factual answer, NOT sustained speed).\n')
    report += f'- PASS: auth rejection, model ID, chat, SSE, multi-turn and {receipt["disk_read_bytes"] / 1e9:.2f} GB real disk reads.\n'
    with Path('EXPERIMENTS.md').open('a') as output:
        output.write(report)
    print(report)


if __name__ == '__main__':
    main()
