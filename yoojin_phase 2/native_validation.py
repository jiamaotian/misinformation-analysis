"""Full-record sequential validation accelerator, independent of cleaning indexes."""
import glob,json,shutil,subprocess
from pathlib import Path

def validate_native(root,notes=None):
    root=Path(root);success=json.loads((root/'SUCCESS.json').read_text());base=Path(__file__).parent
    build=base/'.build';build.mkdir(exist_ok=True);source=base/'verify_worker.cpp';binary=build/'verify_worker'
    if not binary.exists() or binary.stat().st_mtime_ns<max(source.stat().st_mtime_ns,(base/'full_worker.cpp').stat().st_mtime_ns):
        compiler=shutil.which('clang++') or shutil.which('g++')
        if not compiler:raise RuntimeError('No C++17 compiler. Use validate_outputs.py --engine pandas')
        subprocess.run([compiler,'-O3','-std=c++17',str(source),'-lz','-o',str(binary)],check=True)
    note_files=sorted({str(Path(p).resolve()) for pat in notes or [] for p in glob.glob(str(Path(pat).expanduser()))})
    if notes and not note_files:raise ValueError('No supplied Notes matched')
    results={'scope':'All supplied records','datasets':{}};joins=None
    for kind in success['reports']:
        report=json.loads((root/f'{kind}_validation.json').read_text())
        if report.get('max_rows') is not None:raise ValueError('Use pandas validation for bounded samples')
        files=[]
        for item in report['inputs']:
            p=Path(item['path']);stat=p.stat()
            if (stat.st_size,stat.st_mtime_ns)!=(item['bytes'],item['mtime_ns']):raise ValueError(f'Original input changed: {p}')
            files.append(str(p))
        if len({Path(f).name for f in files})!=len(files):raise ValueError('Input basenames must be unique')
        command=[str(binary),kind,str(root),str(report['cutoff_ms']),*files]
        if note_files:command+=['--notes',*note_files]
        subprocess.run(command,check=True)
        result=check_report(root,kind,report)
        results['datasets'][kind]=result
        if note_files:
            j=json.loads((root/f'{kind}_native_notes_join.json').read_text())
            for key in ['rows_matching_supplied_notes','rows_unmatched_supplied_notes','notes_without_match']+(['creation_time_mismatches','matched_response_eligible'] if kind=='status' else []):
                j['datasets'][kind].setdefault(key,0)
            if joins is None:joins=j
            else:
                joins['datasets'].update(j['datasets'])
                if kind=='status':joins['matched_notes_response_median_hours']=j['matched_notes_response_median_hours']
    if joins:(root/'integration_with_supplied_notes.json').write_text(json.dumps(joins,indent=2))
    (root/'independent_validation.json').write_text(json.dumps(results,indent=2));return results

def check_report(root,kind,report):
    root=Path(root);result=json.loads((root/f'{kind}_native_verification.json').read_text());counts=report['counts']
    for actual,expected in [('input_rows','input'),('rows','output'),('exact_duplicates_removed','exact_duplicates_removed'),('invalid_keys_retained','invalid_key_retained')]:
        if result[actual]!=counts[expected]:raise ValueError(f'Native validation count mismatch: {actual}')
    if result['checks']!='PASS' or not result['source_fields_preserved'] or not result['removed_rows_verified_against_earlier_retained_source']:raise ValueError('Native audit did not pass')
    for col,value in result['qc_counts'].items():
        if value!=counts.get(col,0):raise ValueError(f'Native QC mismatch: {col}')
    for item in report['inputs']:
        stat=Path(item['path']).stat()
        if (stat.st_size,stat.st_mtime_ns)!=(item['bytes'],item['mtime_ns']):raise ValueError('Input changed during validation')
    return result
