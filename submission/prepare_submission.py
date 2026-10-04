"""Export 50 preserved Notes rows and check five records. No Ratings scan."""
import argparse
import csv
from pathlib import Path

# Rules and expected results are defined before reading actual records.
CHECK_IDS = [
    '2014495336161829107',  # unusual tweetId; retain all source fields
    '2014121093532098991',  # missing classification; retain all source fields
    '2077499944613937440',
    '2035025007030473042',
    '2022480596937978339',
]
EXPECTED = 'All original fields unchanged; record retained.'
REASON = 'No reliable correction or imputation is available; no deletion rule applies.'

def read_rows(path, delimiter):
    with path.open(encoding='utf-8', newline='') as stream:
        reader = csv.DictReader(stream, delimiter=delimiter)
        return reader.fieldnames, list(reader)

def write_rows(path, columns, rows):
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--notes', type=Path, default=Path.home() / 'Downloads/notes-00002.tsv')
    parser.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    columns, original = read_rows(args.notes, '\t')
    by_id = {row['noteId']: row for row in original}
    assert len(by_id) == len(original), 'Duplicate Notes key'
    assert all(key in by_id for key in CHECK_IDS), 'Verification ID unavailable'

    # Include all difficult cases, the specified normal cases, then first remaining rows.
    selected = {row['noteId'] for row in original
                if row['tweetId'] == '-1' or row['classification'] == ''}
    selected.update(CHECK_IDS)
    for row in original:
        if len(selected) >= 50:
            break
        selected.add(row['noteId'])
    sample = [row for row in original if row['noteId'] in selected]
    assert len(sample) == 50
    sample_path = args.output_dir / 'notes_cleaned_sample.csv'
    write_rows(sample_path, columns, sample)
    actual_columns, exported = read_rows(sample_path, ',')
    assert actual_columns == columns
    assert sample == exported, 'Export changed source values or row order'
    exported_by_id = {row['noteId']: row for row in exported}

    checks = []
    for key in CHECK_IDS:
        before, after = by_id[key], exported_by_id[key]
        match = before == after
        assert match, key
        checks.append({
            'noteId': key,
            'case': 'Missing classification and tweetId=-1' if before['classification'] == ''
                    else 'tweetId=-1' if before['tweetId'] == '-1' else 'Regular record',
            'original_tweetId': before['tweetId'],
            'original_classification': before['classification'],
            'original_isCollaborativeNote': before['isCollaborativeNote'],
            'expected': EXPECTED,
            'reason': REASON,
            'actual_tweetId': after['tweetId'],
            'actual_classification': after['classification'],
            'actual_isCollaborativeNote': after['isCollaborativeNote'],
            'all_original_fields_match': 'Yes' if match else 'No',
        })
    for check in checks:
        print(check)
    report = [
        f'Notes source records: {len(original):,}',
        f'Exported sample records: {len(exported)}',
        f'Original/exported columns: {len(columns)}/{len(actual_columns)}',
        'All sample values and source order preserved: Yes',
        f'tweetId=-1 sample records: {sum(r["tweetId"] == "-1" for r in exported)}',
        f'Missing classification sample records: {sum(r["classification"] == "" for r in exported)}',
        'Five full-record comparisons matched: 5/5',
        'Selection: all tweetId=-1 or missing-classification rows, specified normal verification IDs, then first remaining rows to 50; original order retained.',
        'This is an intentionally selected verification sample, not a random or representative sample.',
        'No source data, missing values, or identifiers were modified.',
    ]
    print('\n'.join(report))

if __name__ == '__main__':
    main()
