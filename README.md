# Data Engineering Technical Exercise

This bundle contains everything you need to start.

## Contents

- **`data-engineer-exercise.pdf`** — the assignment. Read this first.
- **`data/`** — the input dataset. The exercise references this directly.
  Treat it as read-only; do not modify it.
  - `data/raw/readings/*.ndjson` — 720 hourly NDJSON files, one per UTC hour
  - `data/devices.csv` — device metadata
  - `data/rate_card.csv` — billing rates
  - `data/README.md` — ground-truth totals your pipeline should match

## Quick start

1. Read `data-engineer-exercise.pdf` end to end.
2. Skim `data/README.md` to see the exact numbers your pipeline should produce.
3. Inspect a couple of `data/raw/readings/*.ndjson` files to see the batch shape
   on real data:
   ```
   head -1 data/raw/readings/2026-04-15T10.ndjson | python3 -m json.tool
   ```
4. Build the pipeline per the spec.

## How we evaluate

Your pipeline's output is compared against `data/README.md`:

- **Exact match required:** every key in `dq_summary.json` except
  `duration_seconds`, `anomalies_by_rule.R3`, and
  `anomalies_by_severity.warning`; and the row counts of
  `readings_curated`, `hourly_aggregates`, and `hourly_billing`.
- **Tolerant match:**
  - `anomalies_by_rule.R3` and `anomalies_by_severity.warning` are
    allowed to differ by ±2 from `data/README.md`. (R3 has a few
    detections at the 5σ boundary; `warning` totals R2 + R3 so it
    inherits the same band.)
  - The sum of `delivered_units` and the sum of `amount` should match
    `data/README.md` to a handful of float ULPs (i.e. tiny last-bit
    differences caused by float-summation ordering).
  - The sum of `active_seconds` should match within an absolute
    difference of ≤ 10.
- **Not checked:** the exact text of `dq_anomalies.details`, the exact text
  of timestamp strings in your output (so long as they round-trip to the
  correct UTC instant), and the wall-clock `duration_seconds`.

## Submission

Per `§8` of the PDF: source code + README + Makefile + sample stdout of a
successful run, sent to the addresses on the cover page.
