import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import download
import smoke


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
