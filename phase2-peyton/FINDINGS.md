# Peyton — Phase 2 cleaning findings

## Completed full-file results

The notebook ran successfully on all rows of the user-confirmed `notes-00001.tsv` and `batSignals-00000.tsv`.

| Check | Notes | Note Request |
|---|---:|---:|
| Input rows | 15,430 | 499,888 |
| Cleaned rows | 15,430 | 499,888 |
| Exact duplicate rows removed | 0 | 0 |
| Conflicting primary-key rows | 0 | 0 |
| Missing or invalid tweet IDs | 0 | 0 |

All note IDs were present and valid under the positive-decimal format check. All Notes creation timestamps converted successfully and were positive. No nonblank checked binary indicators fell outside 0/1.

**Missing fields:** `believable`, `harmful`, and `validationDifficulty` are empty in all 15,430 Notes rows. `sourceLinks` is empty in 379,877 request rows (76.0%). These fields were retained without imputation. Other original fields contain no empty or whitespace-only values. Nonempty structured text such as `[]` is not counted as a blank string.

**Eligibility timestamps:** the following counts are nonpositive source values. Their originals are retained, their UTC dates are missing, and flags identify them. All observed nonpositive values are `-1`; no undocumented interpretation is assigned to that sentinel.

| Field | Nonpositive rows |
|---|---:|
| noteRequestFeedEligibleAtMillis | 470,723 |
| apiSmallFeedEligibleAtMillis | 470,395 |
| apiLargeFeedEligibleAtMillis | 326,414 |
| apiXlFeedEligibleAtMillis | 200 |

There were no blank or malformed eligibility timestamp strings. That does not establish that every timestamp represents an actual eligibility event.

**Tweet relationships:** 4,254 distinct tweets appear in both files, 5,432 only in Notes, and 495,634 only in Note Request. Notes contains 9,686 distinct tweets across 15,430 notes; repeated tweet IDs were retained. Unmatched tweets were retained and no raw-table merge was performed.

**Changes made:** preserved every original field and row; added UTC dates, source-row references, and quality flags. Both cleaned CSVs were reloaded and their original fields compared with the inputs. Input source hashes remained unchanged. Synthetic edge-case checks and execution of every notebook cell passed.

**Limitations:** the actual source snapshot/download date and observation cutoff have not been confirmed. Future-date validation is therefore not claimed. These results describe the two agreed files, not all Community Notes data. The original mention of `notes-00002.tsv` was replaced by `notes-00001.tsv` with the user's explicit confirmation. Review the records and these findings before submitting them as your work.
