"""Verify five fixed follow-up expectations against unchanged raw files and outputs."""
from pathlib import Path
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from cleaning import ROOT, sha

csv.field_size_limit(1_000_000_000)

def verify(root=ROOT):
    root = Path(root)
    out = root / 'validation/followup_verification.json'
    out.unlink(missing_ok=True)
    expectation_path = root / 'validation/expected_records.json'
    expected = json.loads(expectation_path.read_text())
    cases = {c['tweetId']: c for c in expected['cases']}
    cutoff = int(datetime.fromisoformat(expected['cutoff_utc'].replace('Z', '+00:00')).timestamp() * 1000)
    manifest = json.loads((root / 'evidence/source_manifest.json').read_text())
    raw = root / 'data/raw'
    sources = []
    for entry in manifest:
        path = raw / entry['file']
        if not path.is_file():
            raise FileNotFoundError(f'Missing original file: {path}. Preserve the original data/raw directory.')
        print('Checking source hash:', entry['file'], flush=True)
        if path.stat().st_size != entry['bytes'] or sha(path) != entry['sha256']:
            raise ValueError(f'Original snapshot differs: {path}')
        sources.append(path)
    evidence = json.loads((root / 'evidence/full_data_checks.json').read_text())
    if evidence['cutoff_utc'] != expected['cutoff_utc']:
        raise ValueError('Cutoff differs from fixed expectations')
    if evidence['conflicting_note_ids'] != 0:
        raise ValueError('This five-case verifier needs review for a snapshot with conflicting note IDs')
    requests = [p for p in sources if p.name.startswith('batSignals-')]
    if len(requests) != 1:
        raise ValueError('Expected exactly one request source')
    raw_eligibility = {}
    with requests[0].open(encoding='utf-8', newline='') as stream:
        for row in csv.DictReader(stream, delimiter='\t'):
            tid = row['tweetId'].strip()
            if tid in cases:
                raw_eligibility[tid] = int(row['noteRequestFeedEligibleAtMillis'].strip())
    if set(raw_eligibility) != set(cases):
        raise ValueError('Missing selected requests')
    unique_rows = {tid: set() for tid in cases}
    times = {tid: [] for tid in cases}
    raw_counts = {tid: 0 for tid in cases}
    duplicates = {tid: 0 for tid in cases}
    for path in sources:
        if not path.name.startswith('notes-'):
            continue
        print('Reading original records:', path.name, flush=True)
        with path.open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream, delimiter='\t'):
                tid = row['tweetId'].strip()
                if tid not in cases:
                    continue
                raw_counts[tid] += 1
                digest = hashlib.sha256(json.dumps(row, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
                if digest in unique_rows[tid]:
                    duplicates[tid] += 1
                    continue
                unique_rows[tid].add(digest)
                stamp = row['createdAtMillis'].strip()
                if re.fullmatch(r'[0-9]+', row['noteId'].strip()) and re.fullmatch(r'[0-9]{1,15}', stamp):
                    value = int(stamp)
                    if 0 < value <= 253402300799999 and raw_eligibility[tid] <= value <= cutoff:
                        times[tid].append(value)
    sample_path = root / 'data/sample/coverage_sample.csv'
    cleaned_path = root / 'evidence/coverage_cleaned.csv'
    if not cleaned_path.exists():
        cleaned_path = root / 'data/processed/coverage_cleaned.csv'
    if not cleaned_path.exists():
        raise FileNotFoundError('Keep your existing full coverage_cleaned.csv when applying this update.')
    def selected(path):
        found = {}
        with path.open(encoding='utf-8', newline='') as stream:
            for row in csv.DictReader(stream):
                if row['tweetId'] in cases:
                    if row['tweetId'] in found:
                        raise ValueError('Duplicate selected tweetId in ' + str(path))
                    found[row['tweetId']] = row
        if set(found) != set(cases):
            raise ValueError('Selected records missing from ' + str(path))
        return found
    sample, cleaned = selected(sample_path), selected(cleaned_path)
    results = []
    for tid, fixed in cases.items():
        computed = {'eligibility_ms': raw_eligibility[tid], 'qualifying_note_count': len(times[tid]), 'first_qualifying_note_ms': min(times[tid]) if times[tid] else None}
        for field, value in computed.items():
            if value != fixed[field]:
                raise ValueError(f'Raw calculation differs from fixed expectation: {tid} {field}')
            for label, rows in [('sample', sample), ('cleaned', cleaned)]:
                actual = None if rows[tid][field] == '' else int(rows[tid][field])
                if actual != value:
                    raise ValueError(f'{label} differs from raw calculation: {tid} {field}')
        recent = (cutoff - raw_eligibility[tid]) / 86400000 < 7
        if sample[tid]['recent_under_7_days'].lower() != str(recent).lower():
            raise ValueError('Recent-request flag differs')
        results.append({'tweetId': tid, 'raw_note_rows': raw_counts[tid], 'exact_duplicates': duplicates[tid], **computed, 'recent_under_7_days': recent, 'match': True, 'reason': fixed['reason']})
    result = {'status': 'PASS', 'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'chronology': expected['purpose'], 'source_hashes_match': True, 'expectations_sha256': sha(expectation_path), 'sample_sha256': sha(sample_path), 'cleaned_sha256': sha(cleaned_path), 'cases': results}
    out.write_text(json.dumps(result, indent=2) + '\n')
    from make_report import generate
    generate(root)
    print('PASS: 5 fixed cases match original data, full cleaned output and sample. REPORT.pdf and REPORT.md updated.')
    return result

if __name__ == '__main__':
    verify()
