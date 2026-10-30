#!/usr/bin/env python3
"""Crash PID of inference (not docker stop), check unless-stopped recovery."""
import json
import os
from pathlib import Path
import subprocess
import time
from wait import inspect, wait_ready


def main():
    name = os.getenv('CONTAINER', 'glm53-flash')
    before = inspect()
    assert before['State']['Running']
    assert before['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped'
    # Docker's restart policy only becomes active after 10s of uptime.
    time.sleep(11)
    # --init runs as PID 1; terminate the actual child server to simulate a crash.
    subprocess.run(['docker', 'exec', name, 'sh', '-c',
                    'for p in /proc/[0-9]*/comm; do read n < "$p"; '
                    'if [ "$n" = llama-server ]; then id=${p#/proc/}; '
                    'kill -KILL "${id%/comm}"; exit 0; fi; done; exit 1'], check=True)
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        after = inspect()
        if after['RestartCount'] > before['RestartCount'] and after['State']['Running']:
            break
        time.sleep(1)
    else:
        raise RuntimeError('Docker did not automatically restart inference')
    wait_ready()
    after = inspect()
    receipt = {'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'restart_count_before': before['RestartCount'],
               'restart_count_after': after['RestartCount'], 'policy': 'unless-stopped',
               'running': after['State']['Running']}
    Path('results').mkdir(exist_ok=True)
    Path('results/restart.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print('PASS: automatic restart after inference SIGKILL; API ready again')


if __name__ == '__main__':
    main()
