# Audit claims and change requests

## Claims

- **Peyton Tom:** backend Coverage observation-window selection (`window_days=7/14/28`) and observed coverage rate. Version audited: `67b7bc82f5147d7669718b85a42580691eb41884`.
- Additional evidence: a multi-window synthetic fixture with changing maturity denominators, checked against a separate integer-arithmetic implementation. 
- Scope: existing backend analysis
- **Jiamao (Jessica) Tian:** Backend Coverage feed selection (Standard / Small / Large / XL) and eligible requests count. Version audited: `7a028df`.
- Evidence: Six synthetic requests checked across four feeds, with independently determined eligible request IDs compared against the backend results.
- Scope: existing backend analysis in `phase2-euan/coverage_analysis.py`; dashboard interactions not tested.

## PT-01 — Dashboard test

- Status: superseded as a prerequisite for Peyton's audit; no UI failure claimed.
- The original request to obtain a dashboard does not apply to this backend audit. 

## PT-02 — Verify cutoff and source scope before real windowed reporting

- Status: open, known provenance limitation; not a newly discovered calculation bug.
- Evidence: `phase2-euan/COVERAGE_HANDOFF.md` calls its cutoff provisional and documents partial-Notes-shard scope. The backend rejects a missing cutoff but cannot verify the provenance of a supplied timestamp.
- Request to the team: document the verified UTC cutoff, exact source hashes and shard scope; rerun the real-data analysis if these change. Until verified, retain provisional/partial-shard labels and do not present the results as validated full-snapshot coverage.
- Acceptance: a reproducible source manifest supports the cutoff and scope, and results identify that provenance. Any future dashboard must also follow the specifications' unverified-cutoff warning/suppression requirement; that interaction is outside this audit.


## JT-01 — Verify Coverage feed selection and eligible requests count

- **Status:** Checked; no calculation bug found in the tested cases.
- **Version audited:** `7a028df` (base commit of `jessica-module9-audit`).
- **Code:** `phase2-euan/coverage_analysis.py`, `analyze_coverage()`.
- **Feature checked:** Backend feed selection for Standard, Small, Large, and XL using the corresponding feed-specific eligibility timestamp fields.
- **Number checked:** `eligible_requests`, the count of distinct eligible `tweetId` values meeting the selected feed, date-range, and observation-window conditions.
- **Method:** Constructed six synthetic requests and independently determined the expected eligible request IDs for each feed. Ran the backend function and compared its output with the expected counts.
- **Results:**
  - Standard: expected 3, actual 3 (`101`, `102`, `106`).
  - Small: expected 1, actual 1 (`102`).
  - Large: expected 0, actual 0.
  - XL: expected 2, actual 2 (`101`, `106`).
- **Evidence:** `coverage_feed_audit_check_code.py`; all four feed checks passed when executed locally in VS Code.
- **Conclusion:** The backend selected the expected feed-specific eligibility fields and produced the correct eligible request counts for the tested cases.
- **Limitation:** This check does not validate the interactive dashboard, full production data, or the provenance of the real-data cutoff and source scope.
- **Requested change:** No backend code change requested based on these tests. Peyton's cutoff and source-provenance concern in PT-02 remains open.

## EW-01 — Preserve date-filter and gap-count regression checks

- **Euan (Yun Wei):** Coverage eligibility-date filter and `no_observed_note` count. Backend version: `93bc9a7`. Evidence: nine synthetic checks passed locally with pandas 2.3.3, including date boundaries, timezone equivalence, and gap membership. No UI or real-data validation claimed.

- Status: proposed test improvement; no calculation defect found in the tested cases.
- Evidence: the main fixture returned 5 eligible requests, 2 covered, and 3 gaps. All nine synthetic checks passed.
- Request: commit `check_date_gaps.py` and `audit_results.json` as reproducible regression evidence.
- Acceptance: all nine checks pass, including exact selected-request and gap IDs.
- Scope: backend synthetic cases only; existing PT-02 provenance limitations remain unresolved.
