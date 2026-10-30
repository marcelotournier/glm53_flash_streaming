#!/usr/bin/env python3
"""Wait for this container, rejecting crash loops and stale listeners."""
import json
import os
import subprocess
import time
import urllib.error
import urllib.request


def inspect():
    return json.loads(subprocess.check_output(['docker', 'inspect', os.getenv('CONTAINER', 'glm53-flash')]))[0]


def wait_ready(timeout=None):
    timeout = float(timeout or os.getenv('STARTUP_TIMEOUT', '1800'))
    name = os.getenv('CONTAINER', 'glm53-flash')
    url = f"http://{os.getenv('HOST', '127.0.0.1')}:{os.getenv('PORT', '8000')}/health"
    initial = inspect()['RestartCount']
    deadline = time.monotonic() + timeout
    print(f'Waiting for {name} at {url}', flush=True)
    while time.monotonic() < deadline:
        state = inspect()
        if not state['State']['Running'] or state['RestartCount'] != initial:
            raise RuntimeError(f"Container crashed: state={state['State']} restarts={state['RestartCount']}")
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if json.load(response).get('status') == 'ok':
                    print('Server ready.', flush=True)
                    return
        except (OSError, ValueError, urllib.error.URLError):
            pass
        time.sleep(2)
    raise TimeoutError(f'API not ready within {timeout}s')


if __name__ == '__main__':
    try:
        wait_ready()
    except Exception:
        subprocess.run(['docker', 'logs', '--tail', '100', os.getenv('CONTAINER', 'glm53-flash')])
        raise
