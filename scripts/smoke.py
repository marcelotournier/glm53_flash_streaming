#!/usr/bin/env python3
"""Real-model Docker checks. Writes a dated receipt; no mock/fallback model."""
import json
import os
from pathlib import Path
import subprocess
import time
import urllib.error
import urllib.request
from wait import inspect

MODEL = 'glm-5.3-flash'
BASE = f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', '8000')}"
KEY = os.getenv('API_KEY', 'local')
TIMEOUT = float(os.getenv('REQUEST_TIMEOUT', '1800'))


def request(path, payload=None, key=KEY):
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = json.dumps(payload).encode() if payload is not None else None
    return urllib.request.urlopen(urllib.request.Request(BASE + path, data, headers), timeout=TIMEOUT)


def io_stats():
    name = os.getenv('CONTAINER', 'glm53-flash')
    raw = subprocess.check_output(['docker', 'exec', name, 'sh', '-c',
                                  'for p in /proc/[0-9]*/comm; do '
                                  'read n < "$p"; if [ "$n" = llama-server ]; then '
                                  'while IFS= read -r line; do echo "$line"; done < "${p%comm}io"; '
                                  'break; fi; done'], text=True)
    return {k: int(v) for k, v in (line.split(':') for line in raw.splitlines())}


def direct_io_files():
    """Check actual open-file flags, not just requested CLI options or old logs."""
    raw = subprocess.check_output(['docker', 'exec', os.getenv('CONTAINER', 'glm53-flash'),
        'sh', '-c', 'for p in /proc/[0-9]*/comm; do read n < "$p"; '
        'if [ "$n" = llama-server ]; then for fd in "${p%comm}"fd/*; do '
        'file=$(readlink "$fd"); case "$file" in /models/*.gguf) '
        'while read key value; do if [ "$key" = flags: ]; then '
        'echo "$file $value"; fi; done < "${p%comm}fdinfo/${fd##*/}";; esac; '
        'done; break; fi; done'], text=True)
    files = [dict(zip(('path', 'flags_octal'), line.split())) for line in raw.splitlines()]
    assert len(files) >= 5, f'Missing open model shards: {files}'
    assert all(int(f['flags_octal'], 8) & os.O_DIRECT for f in files), files
    return files


def validate_chat(result):
    assert result['model'] == MODEL, result
    text = result['choices'][0]['message'].get('content') or ''
    assert 'paris' in text.lower(), f'Incorrect or truncated answer: {result}'
    assert result['usage']['completion_tokens'] > 0, result
    return text


def validate_sse(lines):
    text, reasoning, chunks, done, finish = '', '', 0, False, False
    for line in lines:
        if isinstance(line, bytes):
            line = line.decode()
        line = line.strip()
        if not line.startswith('data: '):
            continue
        data = line[6:]
        if data == '[DONE]':
            done = True
            break
        event = json.loads(data)
        assert 'error' not in event, event
        assert event.get('model') == MODEL, event
        for choice in event.get('choices', []):
            delta = choice.get('delta', {})
            text += delta.get('content') or ''
            reasoning += delta.get('reasoning_content') or ''
            chunks += 1
            finish |= choice.get('finish_reason') is not None
    assert done and finish and chunks > 1, (done, finish, chunks)
    assert 'paris' in text.lower(), (text, reasoning)
    return {'content': text, 'reasoning': reasoning, 'chunks': chunks, 'done': done}


def main():
    state = inspect()
    assert state['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped'
    assert state['State']['Running']
    command = state['Config']['Cmd']
    assert '--moe-stream-direct' in command and '--moe-stream-cache' in command
    with request('/health') as response:
        assert json.load(response)['status'] == 'ok'
    try:
        request('/v1/models', key='deliberately-wrong-key')
    except urllib.error.HTTPError as error:
        assert error.code == 401, error.code
    else:
        raise AssertionError('Invalid API key accepted')
    with request('/v1/models') as response:
        models = json.load(response)
    assert MODEL in [model['id'] for model in models['data']], models
    direct_files = direct_io_files()
    before = io_stats()
    payload = {'model': MODEL, 'messages': [{'role': 'user', 'content':
               'What is the capital of France? Answer with just the city name.'}],
               'max_tokens': 192, 'temperature': 0, 'seed': 42,
               'chat_template_kwargs': {'reasoning_effort': 'low'}}
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        chat = json.load(response)
    validate_chat(chat)
    elapsed = time.monotonic() - started
    print(f'Chat passed in {elapsed:.1f}s: {chat["choices"][0]["message"]}', flush=True)
    payload['stream'] = True
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        stream = validate_sse(response)
    stream['elapsed_s'] = time.monotonic() - started
    print(f'SSE passed in {stream["elapsed_s"]:.1f}s', flush=True)
    # Cross a default ubatch boundary to exercise double-buffered staging and its tail.
    payload['stream'] = False
    payload['messages'][0]['content'] = ('Reference filler: ' + 'alpha beta gamma delta. ' * 80 +
        '\nIgnore the filler. What is the capital of France? Answer with just the city name.')
    started = time.monotonic()
    with request('/v1/chat/completions', payload) as response:
        staged_chat = json.load(response)
    validate_chat(staged_chat)
    assert staged_chat['usage']['prompt_tokens'] > 256, staged_chat['usage']
    staged_elapsed = time.monotonic() - started
    print(f'Multi-batch prefill passed in {staged_elapsed:.1f}s', flush=True)
    after = io_stats()
    assert after['read_bytes'] > before['read_bytes'], (before, after)
    logs = subprocess.check_output(['docker', 'logs', os.getenv('CONTAINER', 'glm53-flash')],
                                   stderr=subprocess.STDOUT, text=True)
    assert 'moe stream' in logs.lower(), 'Missing streaming activity in logs'
    assert inspect()['RestartCount'] == state['RestartCount'], 'Server restarted during requests'
    receipt = {'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'container': state['Name'], 'image_id': state['Image'], 'command': command,
               'models': models, 'chat': chat, 'chat_elapsed_s': elapsed, 'stream': stream,
               'multi_batch_chat': staged_chat, 'multi_batch_elapsed_s': staged_elapsed,
               'direct_io_files': direct_files,
               'disk_read_bytes': after['read_bytes'] - before['read_bytes'],
               'restart_policy': state['HostConfig']['RestartPolicy']['Name']}
    Path('results').mkdir(exist_ok=True)
    Path('results/smoke.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(f'PASS: health/auth/model/chat/SSE/NVMe streaming; disk reads {receipt["disk_read_bytes"] / 1e9:.2f} GB')


if __name__ == '__main__':
    main()
