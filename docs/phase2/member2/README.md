# Phase 2 — Member 2 handoff

This folder contains the proposed Dashboard Specification contribution, not the full team's completed Phase 2 deliverable.

- [DASHBOARD_SPEC.md](DASHBOARD_SPEC.md): Concise English contribution for BUILD_SPEC.md: five sections covering page layout, metrics/charts, filters, interactions/special cases, and nine acceptance checks. Backend contracts, key/ID details and architecture are omitted.
- [dashboard-v2.png](dashboard-v2.png): updated design image. All numbers and dates are illustrative. Specification remains authoritative.
- [TEAM_HANDOFF_zh.md](TEAM_HANDOFF_zh.md): Chinese explanation and meeting agenda.
- [mockup_fixture.json](mockup_fixture.json): synthetic count fixture, not production data or backend results.
- [IMAGE_PROMPT.txt](IMAGE_PROMPT.txt): generation instructions and revision record; built-in image_gen used.

## Integration

Member 1 should integrate the specification into BUILD_SPEC.md once Members 3–6 ratify metric and data contracts. Do not duplicate conflicting definitions across documents. Preserve the approved decision register or link it from the final spec. Assign a canonical cutoff, implement and verify actual backend results, then run the required fresh-agent test before calling Phase 2 complete. This work did not fetch/merge other branches, touch source data, commit, or push.

## Changes from Phase 1 screenshot

1. Independent date/filter scopes for request-level Coverage and note-level Response; classification cannot remove uncovered requests.
2. Mature-cohort denominators and visible excluded-entity counts.
3. Explicit first-non-NMR timing with completed and no-recorded-transition counts together.
4. Rating-level helpfulness labeled with valid denominator and legacy exclusions.
5. Scatter without unsubstantiated high/low quadrants or causal prescriptions, bounded by the observation window.
6. Descriptive review candidates, definitions/quality drawer, scoped aggregate exports and empty-state rules.
