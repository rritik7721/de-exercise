# IoT Data Pipeline - Technical Exercise

This repository contains a idempotent data pipeline for ingesting IoT telemetry batches, performing quality checks, and generating hourly aggregates and billing reports.

## How to Run

### Setup
Ensure you have Python 3.10+ installed. Install dependencies using:
```bash
make setup
```

### Run the Pipeline
To run the full pipeline against the provided data:
```bash
make run
```
Output files will be generated in the `./out` directory.

### Run Tests
To execute the suite of unit tests verifying core logic:
```bash
make test
```

## Architecture
The pipeline is designed as a modular sequence of transformations:
1.  **Ingestion:** Scans NDJSON files, extracts batches, and enforces deduplication based on `batch_id`.
2.  **Curation:** Normalizes nested readings, joins with device metadata, and filters out pre-commissioning data.
3.  **Quality:** Applies four anomaly detection rules (R1-R4) to flag data quality issues.
4.  **Aggregation:** Computes hourly metrics per device using trapezoidal integration for `delivered_units` and calculating `active_seconds`.
5.  **Billing:** Joins aggregates with the rate card to produce site-level hourly billing summaries.
6.  **Persistence:** Saves all tables as Parquet files with canonical sorting applied.

## Storage Choice
I chose **Parquet** for all output tables. 
- **Efficiency:** Parquet's columnar format is highly efficient for the analytical workloads required in this exercise (aggregations, counts).
- **Interoperability:** It is natively supported by Pandas making it an excellent "curated" format for downstream consumption.

## Schema Choice
The `readings_curated` table uses a **wide format** (denormalized). 
- **Consumer Simplicity:** By including batch and device context (like `site_id` and `device_type`) in every row, downstream stages (Quality, Aggregation) can operate without needing complex joins, improving readability and maintenance.
- **Performance:** While wide tables use more disk space, Parquet's compression mitigates this, and the performance gain from avoiding joins is significant.

## Idempotency & Determinism
- **Deduplication:** Idempotency is enforced during ingestion by sorting batches by `(source_file, line_number)` and keeping only the first occurrence of each `batch_id`. This ensures that even with retries or interleaved files, the same batch is always chosen as the source of truth.
- **Determinism:** To ensure identical output across runs, all dataframes are explicitly sorted by their **natural keys** (e.g., `(device_id, ts, batch_id)`) immediately before being written to disk.

## Late & Out-of-order Data
The pipeline relies strictly on **event time** (`ts` from the reading) for all bucketing and calculations. 
- **Time-series Correctness:** By using `date_trunc('hour', ts)` for aggregation and bucketing, we ensure that late-arriving data (where `ingested_at` is much later than `ts`) is correctly attributed to its historical hour.
- **Sorting:** Readings within an hour are sorted by `(ts, batch_id)` before trapezoidal integration to ensure the integral is deterministic regardless of ingestion order.

## Trade-offs
- **What was cut:** I prioritized a robust Pandas-based implementation for clarity. I cut more advanced parallel processing and a more sophisticated CLI with incremental loading capabilities.
- **Next Steps:** If given more time, I would implement **incremental ingestion** (using state to track processed files) and add **data validation schemas** (like Pydantic) to the ingestion layer to catch malformed data early.

## Sample Output
```json
{
  "files_read": 720,
  "batches_total": 17247,
  "batches_unique": 16119,
  "batches_duplicate_discarded": 1128,
  "empty_batches": 40,
  "readings_total": 321115,
  "pre_commissioning_dropped": 16,
  "readings_kept": 321099,
  "anomalies_by_rule": {
    "R3": 375,
    "R1": 198,
    "R2": 148,
    "R4": 80
  },
  "anomalies_by_severity": {
    "warning": 523,
    "error": 278
  },
  "duration_seconds": 5.59
}
```
