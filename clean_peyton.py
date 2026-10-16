"""Peyton Module 6: inspect every column, review rules, then optionally prepare.
Run from misinformation-analysis: python clean_peyton.py
Code sections match peyton-tom.ipynb. No rows or original fields are changed.
"""


# %% Peyton Tom — Module 6: inspect before cleaning
from pathlib import Path
from collections import Counter
import hashlib
import json
import pandas as pd
from IPython.display import display

source = Path.home() / "Downloads" / "ratings-00007.tsv"
output = Path("outputs/peyton-inspection")
output.mkdir(parents=True, exist_ok=True)
CHUNK_SIZE = 100_000
PREPARE_DATA = True  # Reviewed: preserve every source value and row; add date and flag only.
# Only supply a verified snapshot cutoff. Do not guess it from the latest event.
SNAPSHOT_CUTOFF = None  # Example format: "2026-09-19T00:00:00Z"
cutoff = pd.to_datetime(SNAPSHOT_CUTOFF, utc=True) if SNAPSHOT_CUTOFF else None

source_before = source.stat()
with source.open("rb") as stream:
    source_hash = hashlib.file_digest(stream, "sha256").hexdigest()
columns = pd.read_csv(source, sep="\t", nrows=0).columns.tolist()
required = {"noteId", "raterParticipantId", "createdAtMillis", "helpfulnessLevel"}
assert required.issubset(columns), "Review the source schema before continuing."
print("Source:", source, "| Columns:", len(columns))
print("SHA-256:", source_hash)


# %% 1. Proposed rules for every column
binary_columns = [c for c in columns if c in {"agree", "disagree", "helpful", "notHelpful"}
                  or c.startswith("helpful") or c.startswith("notHelpful")]
binary_columns = [c for c in binary_columns if c != "helpfulnessLevel"]
id_columns = [c for c in ["noteId", "raterParticipantId", "ratedOnTweetId", "suggestionId"] if c in columns]
category_columns = binary_columns + [c for c in ["helpfulnessLevel", "version", "ratingSourceBucketed"] if c in columns]
known_helpfulness = {"HELPFUL", "SOMEWHAT_HELPFUL", "NOT_HELPFUL"}
rules = []
for col in columns:
    if col in binary_columns:
        rule, check = "Preserve; flag values other than 0 or 1", "Missing count and unexpected binary count"
    elif col in id_columns:
        rule, check = "Keep original text; flag blank/format/sentinel concerns", "Original ID strings unchanged"
    elif col == "createdAtMillis":
        rule, check = "Preserve milliseconds; optionally add UTC date", "Integer syntax, parse failures, nonpositive values, cutoff if supplied"
    elif col == "helpfulnessLevel":
        rule, check = "Preserve exact categories; flag unexpected labels", "Full-file category counts reconcile"
    elif col == "suggestion":
        rule, check = "Preserve text and blanks; do not infer missing means bad rating", "Empty/whitespace counts and nonempty examples"
    else:
        rule, check = "Preserve; review observed values before proposing changes", "Missing, whitespace, and observed examples"
    rules.append({"column": col, "proposed_rule": rule, "verification": check})
rules = pd.DataFrame(rules)
display(rules)


# %% 2. Inspect the entire file and flag suspicious values
def flag_chunk(raw):
    flags = pd.DataFrame(index=raw.index)
    for col in columns:
        values = raw[col]
        flags[col + "__blank"] = values.str.strip().eq("")
        if col in binary_columns:
            flags[col + "__unexpected_binary"] = ~values.isin(["0", "1"]) & ~flags[col + "__blank"]
    for col in id_columns:
        if col == "raterParticipantId":
            # Opaque participant IDs: no undocumented length/format requirement.
            flags[col + "__surrounding_space"] = raw[col].ne(raw[col].str.strip())
        else:
            flags[col + "__format_or_sentinel"] = ~raw[col].str.fullmatch(r"[0-9]+", na=False) & raw[col].ne("")
    values = raw["createdAtMillis"]
    integer = values.str.fullmatch(r"-?[0-9]+", na=False)
    numbers = pd.to_numeric(values.where(integer), errors="coerce")
    dates = pd.to_datetime(numbers.where(numbers.gt(0)), unit="ms", utc=True, errors="coerce")
    flags["invalid_rating_date"] = dates.isna()
    flags["nonpositive_timestamp"] = numbers.le(0).fillna(False)
    if cutoff is not None:
        flags["date_after_cutoff"] = dates.gt(cutoff)
    flags["unexpected_helpfulness"] = ~raw["helpfulnessLevel"].isin(known_helpfulness) & raw["helpfulnessLevel"].ne("")
    flags["repeated_pair_within_chunk"] = raw.duplicated(["noteId", "raterParticipantId"], keep=False)
    return flags, dates

profile = {c: {"empty": 0, "whitespace_only": 0, "outer_whitespace": 0, "examples": []} for c in columns}
frequencies = {c: Counter() for c in category_columns}
overflow = set()
flag_counts = Counter()
review_parts = []
review_count = 0
rows = 0
date_min = None
date_max = None
for raw in pd.read_csv(source, sep="\t", dtype="string", keep_default_na=False, chunksize=CHUNK_SIZE):
    flags, dates = flag_chunk(raw)
    flag_counts.update({c: int(flags[c].sum()) for c in flags})
    for col in columns:
        values = raw[col]
        stripped = values.str.strip()
        profile[col]["empty"] += int(values.eq("").sum())
        profile[col]["whitespace_only"] += int((stripped.eq("") & values.ne("")).sum())
        profile[col]["outer_whitespace"] += int(values.ne(stripped).sum())
        examples = profile[col]["examples"]
        if len(examples) < 3:
            for value in values.loc[values.ne("")].head(100).unique():
                if value not in examples and len(examples) < 3:
                    examples.append(value)
        if col in frequencies and col not in overflow:
            counts = values.value_counts().to_dict()
            if len(frequencies[col].keys() | counts.keys()) <= 1000:
                frequencies[col].update(counts)
            else:
                overflow.add(col)
                frequencies[col].clear()
    valid_dates = dates.dropna()
    if not valid_dates.empty:
        low, high = valid_dates.min(), valid_dates.max()
        date_min = low if date_min is None else min(date_min, low)
        date_max = high if date_max is None else max(date_max, high)
    if review_count < 50:
        # A blank optional suggestion alone is not a suspicious rating.
        concerns = flags.drop(columns=[c for c in flags if c.endswith("__blank") and c not in
            ["noteId__blank", "raterParticipantId__blank", "createdAtMillis__blank", "helpfulnessLevel__blank"]])
        chosen = raw.loc[concerns.any(axis=1)].head(50 - review_count).copy()
        chosen.insert(0, "source_row", chosen.index + 1)
        if not chosen.empty:
            review_parts.append(chosen)
            review_count += len(chosen)
    rows += len(raw)
    if rows % 1_000_000 == 0:
        print(f"Inspected {rows:,} rows")

profile_table = pd.DataFrame.from_dict(profile, orient="index").rename_axis("column").reset_index()
profile_table["rows_inspected"] = rows
profile_table["examples"] = profile_table["examples"].map(json.dumps)
decisions = rules.merge(profile_table, on="column", validate="one_to_one")
flags_table = pd.DataFrame(sorted(flag_counts.items()), columns=["flag", "rows_flagged"])
category_table = pd.DataFrame([{"column": c, "value": v, "count": count}
                              for c, counts in frequencies.items() for v, count in counts.items()],
                             columns=["column", "value", "count"])
for col in category_columns:
    if col not in overflow:
        assert sum(frequencies[col].values()) == rows

decisions.to_csv(output / "column_rules_and_evidence.csv", index=False)
flags_table.to_csv(output / "flag_counts.csv", index=False)
category_table.to_csv(output / "category_counts.csv", index=False)
if review_parts:
    pd.concat(review_parts).to_csv(output / "flagged_sample.csv", index=False)
else:
    pd.DataFrame(columns=["source_row"] + columns).to_csv(output / "flagged_sample.csv", index=False)
manifest = {"source": str(source), "sha256": source_hash, "rows": rows, "columns": columns,
            "source_bytes": source_before.st_size, "earliest_rating_utc": str(date_min),
            "latest_rating_utc": str(date_max), "snapshot_cutoff": SNAPSHOT_CUTOFF,
            "incomplete_category_counts": sorted(overflow), "pandas_version": pd.__version__,
            "duplicate_check_scope": "Repeated note/rater pairs within chunks only; no removal"}
(output / "inspection_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Inspection: {rows:,} rows; 0 source values changed; 0 rows removed.")
print("Observed rating dates:", date_min, "to", date_max)
display(decisions)
display(flags_table.loc[flags_table["rows_flagged"].gt(0)])
if cutoff is None:
    print("Unresolved: no verified snapshot cutoff; future-date check was not performed.")


# %% 3. Review the evidence before preparing the analysis table
if PREPARE_DATA:
    # Stream the full file to disk; never concatenate 26 million rows in memory.
    temporary = output / "ratings_prepared.csv.partial"
    final = output / "ratings_prepared.csv"
    written = 0
    invalid_dates = 0
    sample_parts = []
    sample_count = 0
    for raw in pd.read_csv(source, sep="\t", dtype="string", keep_default_na=False, chunksize=CHUNK_SIZE):
        integer = raw["createdAtMillis"].str.fullmatch(r"-?[0-9]+", na=False)
        numbers = pd.to_numeric(raw["createdAtMillis"].where(integer), errors="coerce")
        dates = pd.to_datetime(numbers.where(numbers.gt(0)), unit="ms", utc=True, errors="coerce")
        prepared = raw.copy()
        prepared["rating_date_utc"] = dates
        prepared["invalid_rating_date"] = dates.isna()
        assert len(prepared) == len(raw)
        assert prepared[columns].equals(raw), "An original field was changed"
        prepared.to_csv(temporary, mode="w" if written == 0 else "a", header=written == 0, index=False)
        if sample_count < 50:
            sample = prepared.head(50 - sample_count)
            sample_parts.append(sample)
            sample_count += len(sample)
        invalid_dates += int(dates.isna().sum())
        written += len(prepared)
    assert written == rows
    if written == 0:
        pd.DataFrame(columns=columns + ["rating_date_utc", "invalid_rating_date"]).to_csv(temporary, index=False)
    # Original source must still be the inspected file.
    with source.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == source_hash
    temporary.replace(final)
    if sample_parts:
        pd.concat(sample_parts).to_csv(output / "prepared_sample.csv", index=False)
    changes = pd.DataFrame([
        {"step": "Load all source fields as text", "rows_before": rows, "rows_after": rows,
         "original_values_changed": 0, "details": "No row selection or ID conversion"},
        {"step": "Add rating_date_utc", "rows_before": rows, "rows_after": written,
         "original_values_changed": 0, "details": f"Milliseconds represented as UTC in NEW column; {invalid_dates} missing derived dates"},
        {"step": "Add invalid_rating_date flag", "rows_before": rows, "rows_after": written,
         "original_values_changed": 0, "details": "Flags retained; no exclusions or category changes"},
    ])
    changes.to_csv(output / "transformation_report.csv", index=False)
    display(changes)
else:
    print("Inspection only. No cleaned dataset was written; review the rules and flags first.")
assert source.stat().st_size == source_before.st_size
assert source.stat().st_mtime_ns == source_before.st_mtime_ns
