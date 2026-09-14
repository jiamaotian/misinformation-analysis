# Technical Path

## Selected Project Area
Misinformation on Social Media

## Candidate Vision A — Improving Coverage
A Community Notes Product Manager at X must decide which groups of posts or note requests need targeted note-writing effort to reduce gaps in Community Notes coverage.

## Candidate Vision B — Improving Response Time
A Community Notes Product Manager at X must decide which types of notes need additional rating effort to reduce the time required to reach a final status.

---

## 1. Source and Access

- **Source:** X Community Notes Public Data
- **Documentation:** https://communitynotes.x.com/guide/en/under-the-hood/download-data
- **Access:** Publicly accessible in our test; no login was required.
- **File format tested:** ZIP archives containing TSV files.
- **Local processing:** Python + pandas in the course environment.
- **License / redistribution terms:** Not yet verified.

The download page currently provides five dataset categories: Notes, Ratings, Note status history, User enrollment status, and Note request data.

---

## 2. Data Tested

### Notes Data
- The download page provides **5 Notes files**.
- One Notes file was downloaded, extracted, and read successfully with pandas.
- **Tested file size:** **20,523 rows × 24 columns**
- Important fields verified:
  - `noteId`
  - `tweetId`
  - `noteAuthorParticipantId`
  - `createdAtMillis`
  - note classification / content fields

### Note Request Data
- The download page provides **1 Note request file**.
- Downloaded archive: `batSignals-00000.zip`
- Extracted file: `batSignals-00000.tsv`
- Compressed size: **36.5 MB**
- Full dataset size: **478,892 rows × 7 columns**
- Important fields verified:
  - `tweetId`
  - `noteRequestFeedEligibleAtMillis`
  - `apiSmallFeedEligibleAtMillis`
  - `apiLargeFeedEligibleAtMillis`
  - `apiXlFeedEligibleAtMillis`
  - `sourceLinks`
  - `suggestions`

### Note Status History Data
- The download page provides **1 Note status history file**.
- Extracted file: `noteStatusHistory-00000.tsv`
- Full dataset size: **3,272,318 rows × 23 columns**
- Important fields verified:
  - `noteId`
  - `noteAuthorParticipantId`
  - `createdAtMillis`
  - `currentStatus`
  - `firstNonNMRStatus`
  - `mostRecentNonNMRStatus`
  - multiple status-change timestamps

---

## 3. Access and Processing Check

The tested TSV files were successfully read with pandas.

Example:

```python
import pandas as pd

requests = pd.read_csv(
    "/Users/jiamaotian/Documents/Inbox/batSignals-00000.tsv",
    sep="\t"
)

requests.shape
```

Result:

```text
(478892, 7)
```

The Note status history file was also loaded successfully:

```text
(3272318, 23)
```

### Current Assessment
The tested datasets can be processed locally with pandas in the current course Python environment. A database does not appear necessary for the current checks, although the total size of all Notes and Ratings files should be reviewed before making a final storage decision.

---

## 4. Joinability Check

The verified identifiers support the following technical join path:

```text
Note request data
    tweetId
       ↓
Notes data
    tweetId + noteId
       ↓
Note status history
    noteId
```

### Verified Join Keys

| Dataset 1 | Dataset 2 | Join Key | Status |
|---|---|---|---|
| Note request data | Notes data | `tweetId` | Successfully tested |
| Notes data | Note status history data | `noteId` | Schema verified |

A five-row Notes sample was left-joined to the full Note request dataset using `tweetId`. The merge executed successfully: four sampled rows matched and one row was unmatched.

This was only a technical join test and should not be interpreted as a representative match rate for the full datasets.

---

## 5. Technical Fit for the Two Candidate Visions

### Vision A — Improving Coverage
The current data structure supports this Vision at a technical starting-point level.

- Note request data identifies posts associated with request activity through `tweetId`.
- Notes data also contains `tweetId`, allowing requested posts to be connected to notes.
- This makes it technically possible to examine which requested posts receive notes and which do not.

The team still needs to define what counts as a meaningful “coverage gap” before conducting the final analysis.

### Vision B — Improving Response Time
The current data structure also supports this Vision at a technical starting-point level.

- Notes data provides `noteId` and note creation information.
- Note status history data provides `noteId`, status fields, and multiple status timestamps.
- These fields make it technically possible to measure how long notes take to move from creation to later status outcomes.

The Ratings dataset has not yet been inspected, so the team has not yet verified whether rating-level fields can directly support the “additional rating effort” part of this Vision.

---

## 6. Current Technical Path

- **Storage:** Downloaded ZIP / TSV files
- **Processing:** Python + pandas
- **Join strategy:** `tweetId` for request-to-note connections; `noteId` for note-to-status connections
- **Database:** Not required at the current tested scale
- **Repository:** Keep code and documentation in Git; do not commit downloaded raw data

---

## 7. Remaining Technical Checks

1. Run an actual `noteId` merge between Notes data and Note status history data.
2. Inspect one Ratings file and confirm its format, scale, and join key(s).
3. Verify license / redistribution terms before sharing raw data.
4. Check the total size of all Notes and Ratings files before making a final storage decision.

---

## Overall Technical Conclusion

The core Community Notes data are accessible and can be processed with the current course Python environment. The tested datasets contain the identifiers needed to connect request-level, note-level, and status-history information.

The current technical path is sufficient to support both candidate Visions for the next stage of the project, with Vision A already supported by an actual `tweetId` merge test and Vision B supported by verified note/status fields and a clear `noteId` join path. Rating-level support for Vision B still requires one additional Ratings-data check.
