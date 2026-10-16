"""Full-file audit and independent record checks. Run expectations BEFORE preparation."""
from pathlib import Path
from datetime import datetime, timedelta, timezone
import argparse
import hashlib
import json
import duckdb

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'outputs/peyton-inspection'
EVIDENCE = ROOT / 'evidence/peyton'
SOURCE = Path.home() / 'Downloads/ratings-00007.tsv'

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def connect():
    con = duckdb.connect()
    con.execute("SET memory_limit='2GB'")
    con.execute('SET threads=2')
    con.execute("SET temp_directory='outputs/peyton-inspection/duckdb-temp'")
    return con

def read(con, path, name, delimiter):
    import csv
    with path.open(newline="") as stream:
        names = next(csv.reader(stream, delimiter=delimiter))
    literal = lambda value: "'" + value.replace("'", "''") + "'"
    forced = '[' + ','.join(literal(c) for c in names) + ']'
    con.execute(f"CREATE VIEW {name} AS SELECT * FROM read_csv({literal(str(path))}, delim={literal(delimiter)}, header=true, all_varchar=true, force_not_null={forced}, parallel=false)")

def save(name, obj):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / name).write_text(json.dumps(obj, indent=2, ensure_ascii=False) + '\n')

def expectations():
    path = EVIDENCE / 'record_expectations.json'
    if path.exists():
        raise SystemExit('Expectations already exist: preserve them for independent verification.')
    con = connect()
    read(con, SOURCE, 'source', '\t')
    cases = [
        ('ordinary', "suggestion = '' AND helpfulnessLevel = 'HELPFUL'", 'Keep the optional blank and all source strings.'),
        ('post_sentinel', "ratedOnTweetId = '-1'", 'Keep the sentinel; its meaning is unconfirmed, so do not invent a post ID.'),
        ('whitespace_suggestion', "suggestion <> '' AND regexp_full_match(suggestion, '\\s*')", 'Keep whitespace-only optional text exactly; flag it as blank.'),
        ('nonempty_suggestion', "length(trim(suggestion)) > 0", 'Preserve contributor text, punctuation, and meaningful differences.'),
        ('leading_zero_participant', "starts_with(raterParticipantId, '0')", 'Participant IDs are opaque text: preserve the leading zero.'),
    ]
    records = []
    for label, condition, reason in cases:
        cursor = con.execute('SELECT * FROM source WHERE ' + condition + ' LIMIT 1')
        values = cursor.fetchone()
        assert values is not None, label
        raw = dict(zip([x[0] for x in cursor.description], values))
        # Independent standard-library integer arithmetic, not pandas conversion.
        ms = int(raw['createdAtMillis'])
        expected_date = (datetime(1970, 1, 1, tzinfo=timezone.utc) + timedelta(milliseconds=ms)).isoformat(timespec='milliseconds')
        records.append({'case': label, 'reason': reason, 'original': raw,
                        'expected_original_fields': raw.copy(), 'expected_utc': expected_date,
                        'expected_invalid_rating_date': False})
        print('Expectation saved for', label, flush=True)
    assert len({(r['original']['noteId'], r['original']['raterParticipantId']) for r in records}) == 5
    save('record_expectations.json', {'source_sha256': digest(SOURCE),
         'method': 'AI-assisted expectations saved before preparation; datetime integer arithmetic independent of pandas.',
         'records': records})

def duplicates():
    con = connect()
    read(con, SOURCE, 'source', '\t')
    result = {'source_sha256': digest(SOURCE), 'scope': 'Entire source file; exact string comparisons across chunk boundaries',
              'decision': 'Retain every source row; repeated individual IDs represent multiple ratings, not duplicate records.'}
    for name, grouping in [('exact_rows', 'ALL'), ('note_rater_pairs', 'noteId, raterParticipantId'),
                           ('note_ids', 'noteId'), ('rater_ids', 'raterParticipantId')]:
        cols = '*' if grouping == 'ALL' else grouping
        row = con.execute(f'''SELECT count(*), coalesce(sum(n),0), coalesce(sum(n-1),0)
            FROM (SELECT {cols}, count(*) AS n FROM source GROUP BY {grouping} HAVING count(*) > 1)''').fetchone()
        result[name] = dict(zip(['repeated_groups', 'rows_in_repeated_groups', 'extra_rows_beyond_first'], map(int, row)))
        print(name, result[name], flush=True)
    result['rows'] = con.execute('SELECT count(*) FROM source').fetchone()[0]
    save('duplicate_audit.json', result)

def verify(records_only=False):
    con = connect()
    read(con, OUT / 'ratings_prepared.csv', 'prepared', ',')
    expected = json.loads((EVIDENCE / 'record_expectations.json').read_text())
    assert digest(SOURCE) == expected['source_sha256']
    results = []
    predicates = ' OR '.join('(noteId=? AND raterParticipantId=?)' for _ in expected['records'])
    keys = [value for case in expected['records'] for value in
            (case['original']['noteId'], case['original']['raterParticipantId'])]
    cursor = con.execute('SELECT * FROM prepared WHERE ' + predicates, keys)
    names = [x[0] for x in cursor.description]
    actual_records = [dict(zip(names, row)) for row in cursor.fetchall()]
    for case in expected['records']:
        original = case['original']
        matches = [r for r in actual_records if r['noteId'] == original['noteId']
                   and r['raterParticipantId'] == original['raterParticipantId']]
        assert len(matches) == 1
        actual = matches[0]
        same = all(actual[k] == v for k, v in case['expected_original_fields'].items())
        date_match = datetime.fromisoformat(actual['rating_date_utc']) == datetime.fromisoformat(case['expected_utc'])
        flag_match = actual['invalid_rating_date'].lower() == str(case['expected_invalid_rating_date']).lower()
        results.append({'case': case['case'], 'reason': case['reason'], 'original': original,
                        'expected_utc': case['expected_utc'], 'actual': actual,
                        'all_original_fields_match': same, 'date_matches': date_match, 'flag_matches': flag_match,
                        'matches': same and date_match and flag_match})
    assert all(r['matches'] for r in results)
    save('record_checks.json', results)
    text = ['# Text preservation and five independent record checks', '',
            'Expectations were saved before preparation. All source strings were intentionally preserved; no unsupported text repairs were applied.', '',
            '| Case | Field | Before (JSON quoted) | After (JSON quoted) | Matches |', '|---|---|---|---|---|']
    for r in results:
        for c in ['raterParticipantId', 'helpfulnessLevel', 'suggestion', 'ratedOnTweetId', 'suggestionId']:
            quote = lambda x: json.dumps(x, ensure_ascii=False).replace('|', '&#124;').replace('<', '&lt;').replace('>', '&gt;')
            text.append(f"| {r['case']} | {c} | {quote(r['original'][c])} | {quote(r['actual'][c])} | Yes |")
    text += ['', 'All five dates and flags also matched; see `record_checks.json` for original, expected, actual, and reasons.']
    (EVIDENCE / 'text_before_after.md').write_text('\n'.join(text) + '\n')
    if records_only:
        print('PASS: all five saved records match the independent expectations.', flush=True)
        return
    # Check serialized output against the source in original record order.
    cols = list(expected['records'][0]['original'])
    before = json.loads((OUT / 'inspection_manifest.json').read_text())['rows']
    after = 0
    # Streaming row-order comparison avoids a huge all-column hash join.
    import pandas as pd
    import itertools
    old = pd.read_csv(SOURCE, sep='\t', dtype='string', keep_default_na=False, chunksize=100_000)
    new = pd.read_csv(OUT / 'ratings_prepared.csv', dtype='string', keep_default_na=False, chunksize=100_000)
    checked = 0
    missing = {c: 0 for c in cols}
    for a, b in itertools.zip_longest(old, new):
        assert a is not None and b is not None
        assert a.equals(b[cols]), 'Serialized original values changed'
        checked += len(a)
        after += len(b)
        for c in cols:
            missing[c] += int(b[c].str.strip().eq('').sum())
    assert checked == before == after
    save('reconciliation.json', {'starting_rows': before, 'final_rows': after, 'removed_rows': 0,
        'original_fields': len(cols), 'original_values_changed': 0, 'serialized_rows_verified': checked,
        'blank_or_whitespace_after': missing, 'prepared_sha256': digest(OUT / 'ratings_prepared.csv')})
    print('Five record checks and full serialized-source preservation passed.', flush=True)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('stage', choices=['expectations', 'duplicates', 'verify', 'records'])
    stage = parser.parse_args().stage
    if stage == 'records':
        verify(records_only=True)
    else:
        globals()[stage]()
