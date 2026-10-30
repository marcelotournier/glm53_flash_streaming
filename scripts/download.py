#!/usr/bin/env python3
"""Resumable, hash-verified download from a pinned HF manifest (stdlib + curl)."""
import argparse
import concurrent.futures
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


MAX_MODEL_BYTES = 100_000_000_000  # CRITICAL user requirement: total quant, decimal GB


def validate_manifest(lock):
    total = sum(item['size'] for item in lock['files'])
    if total > MAX_MODEL_BYTES:
        raise ValueError(f'PROHIBITED quant: {total:,} bytes exceeds the 100 GB total-weight limit (SPEC.md)')
    if total <= 0:
        raise ValueError('Empty model manifest')
    return total


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def fetch(lock, item, dest, verify_only=False):
    target = dest / Path(item['path']).name
    if target.exists():
        if target.stat().st_size != item['size'] or sha256(target) != item['sha256']:
            raise RuntimeError(f'Invalid existing shard: {target}; refusing to overwrite')
        print(f'Verified {target}', flush=True)
        return
    if verify_only:
        raise RuntimeError(f'Missing shard: {target}')
    partial = target.with_suffix(target.suffix + '.part')
    url = f"https://huggingface.co/{lock['repo']}/resolve/{lock['revision']}/{item['path']}"
    print(f'Downloading {target} ({item["size"]:,} bytes)', flush=True)
    subprocess.run(['curl', '--fail', '--location', '--silent', '--show-error',
                    '--retry', '12', '--retry-all-errors', '--retry-delay', '5',
                    '--connect-timeout', '30', '--speed-limit', '1024', '--speed-time', '120',
                    '--continue-at', '-', '--output', str(partial), url], check=True)
    if partial.stat().st_size != item['size'] or sha256(partial) != item['sha256']:
        raise RuntimeError(f'Invalid downloaded shard: {partial}')
    partial.rename(target)
    print(f'Verified {target}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dest', type=Path, default=Path('models'))
    parser.add_argument('--lock', type=Path, default=Path('model.lock.json'))
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--jobs', type=int, default=2)
    parser.add_argument('--check-only', action='store_true', help='Validate the hard size limit without downloading')
    parser.add_argument('--check-files', action='store_true', help='Validate the size limit and presence/size of all cached files')
    args = parser.parse_args()
    lock = json.loads(args.lock.read_text())
    validate_manifest(lock)
    if args.check_files:
        for item in lock['files']:
            target = args.dest / Path(item['path']).name
            if not target.is_file() or target.stat().st_size != item['size']:
                raise RuntimeError(f'Missing/incomplete weight file: {target}; run make download')
        print('All pinned weight files present, within the 100 GB total-weight limit')
        return
    if args.check_only:
        print('Manifest is within the 100 GB total-weight limit')
        return
    args.dest.mkdir(parents=True, exist_ok=True)
    needed = 0
    for item in lock['files']:
        target = args.dest / Path(item['path']).name
        partial = target.with_suffix(target.suffix + '.part')
        if not target.exists():
            needed += max(0, item['size'] - (partial.stat().st_size if partial.exists() else 0))
    if not args.verify and shutil.disk_usage(args.dest).free < needed + 10 * 1024**3:
        raise RuntimeError('Insufficient space: leave at least 10 GiB free after download')
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        list(pool.map(lambda item: fetch(lock, item, args.dest, args.verify), lock['files']))


if __name__ == '__main__':
    main()
