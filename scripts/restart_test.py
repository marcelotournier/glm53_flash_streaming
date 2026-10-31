#!/usr/bin/env python3
"""Crash PID of inference (not docker stop), check unless-stopped recovery."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
from wait import inspect, wait_ready
from model_identity import require_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--id', required=True)
    args = parser.parse_args()
    if not args.id.replace('-', '').isalnum():
        raise ValueError('Use an alphanumeric/hyphen ID')
    path = Path(f'results/experiment-{args.id}-restart.json')
    if path.exists():
        raise RuntimeError(f'{path} already exists')
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    name = os.getenv('CONTAINER', 'glm53-flash')
    before = inspect()
    assert before['State']['Running']
    manifest = require_model(before)
    quant = before['Config']['Labels']['io.local.glm53.quant']
    assert before['HostConfig']['RestartPolicy']['Name'] == 'unless-stopped'
    # Docker's restart policy only becomes active after 10s of uptime.
    time.sleep(11)
    # --init runs as PID 1; terminate the API parent, not a recoverable Maya backend worker.
    killed = subprocess.run(['docker', 'exec', name, 'sh', '-c',
                    'read children </proc/1/task/1/children; '
                    'for pid in $children; do read n < "/proc/$pid/comm"; '
                    'case "$n" in python3*) kill -KILL "$pid"; exit 0;; esac; done; exit 1'])
    # Docker can tear down the exec shell just after the API dies; recovery below is the actual assertion.
    if killed.returncode not in (0, 137):
        raise RuntimeError(f'Could not signal the API process: exit {killed.returncode}')
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
    restarted_count = after['RestartCount']
    subprocess.run(['docker', 'stop', '--timeout', '60', name], check=True)
    time.sleep(4)
    stopped = inspect()
    assert not stopped['State']['Running'] and stopped['RestartCount'] == restarted_count
    subprocess.run(['docker', 'start', name], check=True)
    wait_ready()
    receipt = {'configuration_commit': commit, 'tested_at': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
               'model_manifest': manifest, 'restart_count_before': before['RestartCount'],
               'restart_count_after': after['RestartCount'], 'policy': 'unless-stopped',
               'running': inspect()['State']['Running'], 'manual_stop_stayed_stopped': True}
    Path('results').mkdir(exist_ok=True)
    path.write_text(json.dumps(receipt, indent=2) + '\n')
    with Path('EXPERIMENTS.md').open('a') as report:
        report.write(f'\n### {args.id}-restart — {quant} Maya lifecycle\n\n- Config `{commit}`; receipt [{path}]({path}).\n'
                     '- PASS: API SIGKILL automatically recovered; explicit stop stayed stopped; explicit start restored readiness.\n'
                     '- Prefill tok/s: N/A; generation tok/s: N/A (lifecycle-only experiment).\n')
    print('PASS: Docker crash recovery and explicit stop/start semantics; API ready again')


if __name__ == '__main__':
    main()
