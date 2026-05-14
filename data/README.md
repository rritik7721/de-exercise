# Exercise dataset — ground-truth totals

This file documents the expected output of a correctly implemented pipeline
against the shipped fixture. Counts are deterministic; the dataset was
generated from a fixed seed.

## Pipeline summary (`dq_summary.json`)

| Key | Expected value |
| --- | --- |
| `files_read` | 720 |
| `batches_total` | 17247 |
| `batches_unique` | 16119 |
| `batches_duplicate_discarded` | 1128 |
| `empty_batches` | 40 |
| `readings_total` | 321115 |
| `pre_commissioning_dropped` | 16 |
| `readings_kept` | 321099 |

## Anomalies

| Rule | Count |
| --- | --- |
| R1 — value_out_of_range | 198 |
| R2 — fault_state | 148 |
| R3 — value_spike | 375 |
| R4 — device_silence | 80 |

| Severity | Count |
| --- | --- |
| error | 278 |
| warning | 523 |

## Hourly aggregates (`hourly_aggregates`)

| Metric | Expected value |
| --- | --- |
| Row count | 8368 |
| Sum of `delivered_units` across all rows | 1431672.4692 |
| Sum of `active_seconds` across all rows | 25175114 |

## Hourly billing (`hourly_billing`)

| Metric | Expected value |
| --- | --- |
| Row count | 5744 |
| Sum of `amount` across all rows | 692003.7815 |

All rows have `currency = EUR`.

## Notes

- **Row counts and most anomaly counts above are exact.** Your pipeline must
  produce the same number of rows in `readings_curated`, `hourly_aggregates`,
  `hourly_billing`, and `dq_anomalies` per rule, and the same values for
  every key in `dq_summary.json` (except `duration_seconds`, which is
  implementation-specific and not checked).
- **R3 count (375) reflects strict application of the spec rule** to every
  reading at position ≥ 30 in each device's `readings_curated` timeline. It
  includes both deliberately-injected spikes and naturally-occurring large
  deviations that follow R1 outliers (because the prior-30 window briefly
  inflates `µ`/`σ`). A small handful of these detections sit within 0.01 of
  the 5σ boundary, so a correct implementation may produce a value in the
  range **373–377**; that range is acceptable. Do not try to filter to only
  "intended" spikes.
- **`anomalies_by_severity.warning` (523) inherits R3's tolerance.** Because
  `warning = R2 + R3` and R2 is exact (148), a correct implementation may
  produce `warning` in the range **521–525**. `anomalies_by_severity.error`
  is exact (= R1 + R4 = 198 + 80 = 278).
- **Floating-point sums (`Sum of delivered_units`, `Sum of amount`)**
  should match the figures above to within a few units of last-place
  precision. Small differences from float-operation ordering inside your
  data engine are fine.
- **`Sum of active_seconds`** is a sum of per-hour rounded integers, but
  each per-hour value comes from a float sum that depends on the order of
  additions inside your engine's group-by. The absolute difference between
  your sum and the figure above should be **≤ 10**.
- The figures here include anomalous readings inside the hourly
  aggregates, as required by `§4.3`.
