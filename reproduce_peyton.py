"""Run the cleaning script, then a fresh notebook kernel, and compare saved outputs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import nbformat
from nbclient import NotebookClient
from jupyter_client import KernelManager

root = Path(__file__).resolve().parent
out = root / 'outputs/peyton-inspection'
evidence = root / 'evidence/peyton'

def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def hashes():
    return {p.name: digest(p) for p in sorted(out.iterdir()) if p.suffix in {'.csv', '.json'}}

assert (evidence / 'record_expectations.json').exists(), 'Save expectations before executing preparation.'
if '--notebook-only' not in sys.argv:
    subprocess.run([sys.executable, '-u', 'clean_peyton.py'], cwd=root, check=True)
before = hashes()
print('Script run finished; starting a fresh notebook kernel.', flush=True)
notebook = nbformat.read(root / 'peyton-tom.ipynb', as_version=4)
manager = KernelManager(kernel_name='python3')
manager.kernel_spec.argv = [sys.executable, '-m', 'ipykernel_launcher', '-f', '{connection_file}']
class ProgressClient(NotebookClient):
    def process_message(self, msg, cell, cell_index):
        if msg['msg_type'] == 'stream':
            print(msg['content']['text'], end='', flush=True)
        return super().process_message(msg, cell, cell_index)

client = ProgressClient(notebook, km=manager, timeout=None, resources={'metadata': {'path': str(root)}})
try:
    client.execute()
finally:
    if manager.has_kernel:
        manager.shutdown_kernel(now=True)
nbformat.write(notebook, root / 'peyton-tom.ipynb')
after = hashes()
assert before == after, 'Script and notebook outputs differ'
report = {'method': 'Clean script process followed by fresh notebook kernel and all cells in order',
          'python': sys.version, 'script_command': f'{sys.executable} clean_peyton.py',
          'notebook': 'peyton-tom.ipynb', 'all_output_hashes_match': True,
          'script_outputs': before, 'notebook_outputs': after,
          'code_hashes': {p: digest(root / p) for p in ['clean_peyton.py', 'verify_peyton.py', 'reproduce_peyton.py', 'requirements-peyton.txt']}}
(evidence / 'reproducibility.json').write_text(json.dumps(report, indent=2)+'\n')
print('PASS: script and fresh-kernel notebook outputs match byte for byte.', flush=True)
