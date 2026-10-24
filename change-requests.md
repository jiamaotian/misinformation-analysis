# Audit claims and change requests

## Claims

- **Peyton Tom:** backend Coverage observation-window selection (`window_days=7/14/28`) and observed coverage rate. Version audited: `67b7bc82f5147d7669718b85a42580691eb41884`.
- Additional evidence: a multi-window synthetic fixture with changing maturity denominators, checked against a separate integer-arithmetic implementation. 
- Scope: existing backend analysis

## PT-01 — Dashboard test

- Status: superseded as a prerequisite for Peyton's audit; no UI failure claimed.
- The original request to obtain a dashboard does not apply to this backend audit. 

## PT-02 — Verify cutoff and source scope before real windowed reporting

- Status: open, known provenance limitation; not a newly discovered calculation bug.
- Evidence: `phase2-euan/COVERAGE_HANDOFF.md` calls its cutoff provisional and documents partial-Notes-shard scope. The backend rejects a missing cutoff but cannot verify the provenance of a supplied timestamp.
- Request to the team: document the verified UTC cutoff, exact source hashes and shard scope; rerun the real-data analysis if these change. Until verified, retain provisional/partial-shard labels and do not present the results as validated full-snapshot coverage.
- Acceptance: a reproducible source manifest supports the cutoff and scope, and results identify that provenance. Any future dashboard must also follow the specifications' unverified-cutoff warning/suppression requirement; that interaction is outside this audit.