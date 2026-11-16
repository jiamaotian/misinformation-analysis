"""One command: two fresh runs, byte comparison, and regenerated report."""
import json, platform, shutil, subprocess, sys, tempfile
from pathlib import Path
import pandas as pd
import reportlab
from cleaning import ROOT, sha
from make_report import generate

if __name__=='__main__':
 output=ROOT/'evidence'
 for old in ('reproducibility.json',):
  (output/old).unlink(missing_ok=True)
 subprocess.run([sys.executable,str(ROOT/'cleaning.py')],check=True)
 with tempfile.TemporaryDirectory(prefix='coverage-rerun-') as temp:
  subprocess.run([sys.executable,str(ROOT/'cleaning.py'),'--out',temp],check=True)
  files=sorted(p.name for p in output.iterdir() if p.is_file())
  checks={name:sha(output/name)==sha(Path(temp)/name) for name in files}
  assert all(checks.values()),checks
 result={'status':'PASS','fresh_process_runs':2,'output_hashes_match':checks,'python':platform.python_version(),'pandas':pd.__version__,'reportlab':reportlab.Version}
 (output/'reproducibility.json').write_text(json.dumps(result,indent=2)+'\n')
 for src,dst in [('coverage_cleaned.csv','data/processed/coverage_cleaned.csv'),('coverage_sample.csv','data/sample/coverage_sample.csv')]:
  (ROOT/dst).parent.mkdir(parents=True,exist_ok=True); shutil.copy2(output/src,ROOT/dst)
 generate()
 print('PASS: fresh runs match. REPORT.pdf and REPORT.md regenerated.')
