import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import download
import smoke
import model_identity


class AutomationTests(unittest.TestCase):
    def test_manifest(self):
        lock = json.loads(Path('model.lock.json').read_text())
        self.assertEqual(len(lock['files']), 5)
        self.assertEqual(len(lock['revision']), 40)
        for entry in lock['files']:
            self.assertEqual(len(entry['sha256']), 64)
            self.assertGreater(entry['size'], 1000000)

    def test_hard_100gb_limit(self):
        self.assertEqual(download.validate_manifest({'files': [{'size': 100_000_000_000}]}), 100_000_000_000)
        with self.assertRaises(ValueError):
            download.validate_manifest({'files': [{'size': 60_000_000_000}, {'size': 40_000_000_001}]})
        for name in ('model.lock.json', 'exl3.lock.json'):
            with self.assertRaises(ValueError):
                download.validate_manifest(json.loads(Path(name).read_text()))
        self.assertEqual(download.validate_manifest(json.loads(Path('aj.lock.json').read_text())), 87_346_006_560)
        self.assertEqual(download.validate_manifest(json.loads(Path('unsloth-iq1s.lock.json').read_text())), 93_087_245_088)
        self.assertEqual(download.validate_manifest(json.loads(Path('unsloth-iq1m.lock.json').read_text())), 97_579_344_672)

    def test_authorized_iq3_manifest(self):
        lock = json.loads(Path('unsloth-iq3xxs.lock.json').read_text())
        self.assertEqual(download.validate_manifest(lock), 120_367_571_840)
        lock['files'][0]['size'] += 1
        with self.assertRaises(ValueError):
            download.validate_manifest(lock)

    def test_frozen_aj_baseline(self):
        self.assertEqual(download.sha256(Path('engines/aj-baseline.json')),
                         '2b34c875d977b6ca439e1821decefb42dcee63a720e41918e552f7742e03c57f')

    def test_iq1s_memory_profiles(self):
        self.assertEqual(download.sha256(Path('engines/maya.json')),
                         '52c9ae6ed6bec5a3411509a9a4819031dba638c75e9c54e633169ef58e3aa728')
        original = json.loads(Path('engines/maya.json').read_text())
        expanded = json.loads(Path('engines/iq1s-64gb.json').read_text())
        self.assertEqual(expanded['env']['MAYA_GLM_RAM_GB'], '40')
        expanded['env']['MAYA_GLM_RAM_GB'] = '15'
        self.assertEqual(expanded, original)

    def test_quant_identity(self):
        for lock in ('aj.lock.json', 'unsloth-iq1s.lock.json'):
            manifest = json.loads(Path(lock).read_text())
            state = {'Config': {'Labels': {
                'io.local.glm53.quant': manifest['files'][0]['path'].split('/')[0],
                'io.local.glm53.manifest-sha256': download.sha256(Path(lock))}},
                'Mounts': [{'Destination': '/models', 'RW': False}]}
            self.assertEqual(model_identity.require_model(state, lock), manifest)
            state['Config']['Labels']['io.local.glm53.manifest-sha256'] = 'wrong'
            with self.assertRaises(AssertionError):
                model_identity.require_model(state, lock)

    def test_patch_integrity(self):
        self.assertEqual(download.sha256(Path('vendor/glm5next-moe-ssd-streaming.patch')),
                         'd544c2b5f566c0b02483e1a8d6a09db0345c27a1c959b0a194fff8dac05d279b')

    def test_existing_download_integrity(self):
        with tempfile.TemporaryDirectory() as directory:
            dest = Path(directory)
            (dest / 'test.gguf').write_bytes(b'GGUFtest')
            item = {'path': 'q/test.gguf', 'size': 8,
                    'sha256': hashlib.sha256(b'GGUFtest').hexdigest()}
            download.fetch({}, item, dest, verify_only=True)
            (dest / 'test.gguf').write_bytes(b'corrupt!')
            with self.assertRaises(RuntimeError):
                download.fetch({}, item, dest, verify_only=True)

    def test_missing_download_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(RuntimeError):
                download.fetch({}, {'path': 'test.gguf'}, Path(directory), verify_only=True)

    def test_chat_validation(self):
        result = {'model': smoke.MODEL, 'choices': [{'message': {'content': 'Paris'}}],
                  'usage': {'completion_tokens': 1}}
        self.assertEqual(smoke.validate_chat(result), 'Paris')
        result['choices'][0]['message']['content'] = ''
        with self.assertRaises(AssertionError):
            smoke.validate_chat(result)

    def test_sse_validation(self):
        events = [{'model': smoke.MODEL, 'choices': [{'delta': {'role': 'assistant'}}]},
                  {'model': smoke.MODEL, 'choices': [{'delta': {'content': 'Paris'},
                                                    'finish_reason': 'stop'}]}]
        lines = [('data: ' + json.dumps(e)).encode() for e in events] + [b'data: [DONE]']
        self.assertEqual(smoke.validate_sse(lines)['content'], 'Paris')
        with self.assertRaises(AssertionError):
            smoke.validate_sse(lines[:-1])
        events[1]['choices'][0]['delta']['content'] = 'Berlin'
        with self.assertRaises(AssertionError):
            smoke.validate_sse(['data: ' + json.dumps(e) for e in events] + ['data: [DONE]'])


if __name__ == '__main__':
    unittest.main()
