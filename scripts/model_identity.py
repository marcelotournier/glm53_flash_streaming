"""Bind Maya tests to the actual selected <=100 GB quant, not merely its API alias."""
import hashlib
import json
import os
from pathlib import Path
from download import validate_manifest


def require_model(state, lock=None):
    path = Path(lock or os.getenv('MODEL_LOCK', 'aj.lock.json'))
    raw = path.read_bytes()
    manifest = json.loads(raw)
    validate_manifest(manifest)
    quant = manifest['files'][0]['path'].split('/')[0]
    labels = state['Config']['Labels']
    assert labels.get('io.local.glm53.quant') == quant, 'Wrong quant container'
    assert labels.get('io.local.glm53.manifest-sha256') == hashlib.sha256(raw).hexdigest(), 'Wrong manifest container'
    assert any(m['Destination'] == '/models' and not m['RW'] for m in state['Mounts']), 'Weights must be read-only'
    return manifest
