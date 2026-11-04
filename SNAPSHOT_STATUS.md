# Snapshot evidence and current analysis policy

On November 2, 2026, Peyton designated **October 2, 2026 at 23:59:59.999 UTC** as the shared provisional cutoff for notes, requests, ratings, and status history. This is recorded in `dashboard_policy.json`. It supersedes earlier analysis-cutoff proposals for the new dashboard, but does not verify original download dates or snapshot completeness.

The following records are historical provenance and have not been rewritten:

| Evidence | What it establishes |
|---|---|
| `phase2-peyton/evidence/manifest.json` | Notes/request source hashes; `snapshot_label` and `cutoff_utc` are explicitly null. |
| `yoojin_phase 2/evidence/ratings_validation.json` and `status_cleaning_report.json` | Both cleaners used cutoff `1790985599999` = October 2, 2026 23:59:59.999 UTC. Source paths and filesystem modification times are recorded, but those times are not proof of a download date or complete observation through that cutoff. |
| `phase2-euan/COVERAGE_HANDOFF.md` and `BUILD_SPEC.md` section 4.2 | Different provisional coverage cutoff, October 16, 2026 04:02 UTC, based on a download-page display; input hashes/sizes differ between handoffs. |
| `yoojin_phase 2/README.md` | Explicitly says team agreement and common snapshot remain unconfirmed. |

The new app consistently applies the recorded October 2 cutoff in exploratory mode. It does not
claim that choosing the same date reconciles different source snapshots. The data owner still needs
to establish observation coverage through that date for each supplied shard. Maximum event timestamps,
local file modification times, and dates when files were copied are not substitutes.

The import supplied a different dataset from Jessica's prior saved aggregates. The newly validated
joins and calculations therefore use the supplied files directly; the old figures remain available
only in the separate saved-results explorer.

Validation covers every cleaned status/rating row, reconciles all QC totals and row counts to the
existing reports, checks status ID uniqueness and matched rating pair uniqueness, and records hashes
and join gaps. It does not claim raw-source preservation was independently rechecked here.
