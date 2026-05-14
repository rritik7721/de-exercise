import argparse
import os
import sys
import logging
import json
import time
import pandas as pd
from pathlib import Path

from pipeline.ingest import make_raw_df, dedup_raw_df, create_curated_readings
from pipeline.quality import detect_anomalies
from pipeline.aggregate import aggregate_hourly
from pipeline.billing import calculate_billing

logger = logging.getLogger(__name__)

def run_pipeline(data_dir_str: str, out_dir_str: str):
    logger.info(f"Starting pipeline. Input: {data_dir_str}, Output: {out_dir_str}")
    start_time = time.time()
    data_dir = Path(data_dir_str)
    out_dir = Path(out_dir_str)
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Load metadata
    logger.debug("Loading metadata...")
    devices_df = pd.read_csv(data_dir / 'devices.csv')
    rate_card_df = pd.read_csv(data_dir / 'rate_card.csv')
    logger.info(f"Loaded {len(devices_df)} devices and {len(rate_card_df)} rate card entries.")

    # 2. Ingest
    logger.debug("Ingesting raw data...")
    raw_batches, files_read = make_raw_df(data_dir)
    batches_total = len(raw_batches)
    logger.info(f"Read {files_read} files, found {batches_total} total batches.")
    
    deduped_batches = dedup_raw_df(raw_batches)
    batches_unique = len(deduped_batches)
    logger.info(f"De-duplicated batches: {batches_unique} unique batches ({batches_total - batches_unique} duplicates discarded).")
    
    readings_total = int(deduped_batches['readings'].str.len().sum())
    
    logger.debug("Creating curated readings...")
    curated_df, empty_batches_df, pre_comm_dropped = create_curated_readings(deduped_batches, devices_df)
    logger.info(f"Curated {len(curated_df)} readings. Dropped {len(empty_batches_df)} empty batches and {pre_comm_dropped} pre-commissioning readings.")
    
    # 3. Quality
    logger.info(f"Running quality checks on {len(curated_df)} readings...")
    anomalies_df = detect_anomalies(curated_df, devices_df)
    logger.info(f"Quality checks complete. Input: {len(curated_df)} readings, Output: {len(anomalies_df)} anomalies detected.")

    # 4. Aggregate
    logger.info(f"Aggregating {len(curated_df)} readings into hourly data...")
    aggregates_df = aggregate_hourly(curated_df)
    logger.info(f"Aggregation complete. Input: {len(curated_df)} readings, Output: {len(aggregates_df)} hourly aggregate records.")

    # 5. Billing
    logger.info(f"Calculating billing for {len(aggregates_df)} hourly aggregates...")
    billing_df = calculate_billing(aggregates_df, rate_card_df)
    logger.info(f"Billing calculation complete. Input: {len(aggregates_df)} hourly aggregates, Output: {len(billing_df)} billing records.")


    # 6. Persistence
    logger.info(f"Persisting results to {out_dir}...")
    
    # Canonical sorts per PDF
    curated_df = curated_df.sort_values(['device_id', 'ts', 'batch_id'])
    anomalies_df = anomalies_df.sort_values(['rule_id', 'device_id', 'ts'])
    aggregates_df = aggregates_df.sort_values(['device_id', 'hour_utc'])
    billing_df = billing_df.sort_values(['site_id', 'hour_utc', 'device_type'])

    curated_df.to_parquet(out_dir / 'readings_curated.parquet', index=False)
    anomalies_df.to_parquet(out_dir / 'dq_anomalies.parquet', index=False)
    aggregates_df.to_parquet(out_dir / 'hourly_aggregates.parquet', index=False)
    billing_df.to_parquet(out_dir / 'hourly_billing.parquet', index=False)
    logger.info("Persistence complete.")

    # 7. DQ Summary
    duration = time.time() - start_time
    summary = {
        "files_read": files_read,
        "batches_total": batches_total,
        "batches_unique": batches_unique,
        "batches_duplicate_discarded": batches_total - batches_unique,
        "empty_batches": len(empty_batches_df),
        "readings_total": readings_total,
        "pre_commissioning_dropped": pre_comm_dropped,
        "readings_kept": len(curated_df),
        "anomalies_by_rule": anomalies_df['rule_id'].value_counts().to_dict(),
        "anomalies_by_severity": anomalies_df['severity'].value_counts().to_dict(),
        "duration_seconds": round(duration, 2)
    }
    
    for rule in ['R1', 'R2', 'R3', 'R4']:
        if rule not in summary['anomalies_by_rule']:
            summary['anomalies_by_rule'][rule] = 0
    for sev in ['error', 'warning']:
        if sev not in summary['anomalies_by_severity']:
            summary['anomalies_by_severity'][sev] = 0

    with open(out_dir / 'dq_summary.json', 'w') as f:
        json.dump(summary, f, indent=2)
    
    logger.info(f"Pipeline finished in {duration:.2f} seconds.")
    print(json.dumps(summary, indent=2))

def main():
    parser = argparse.ArgumentParser(description="Data Pipeline")
    parser.add_argument("-d", "--data-dir", default="./data", help="Directory containing input data")
    parser.add_argument("-o", "--out-dir", default="./out", help="Directory for output files")
    
    args = parser.parse_args()
    run_pipeline(args.data_dir, args.out_dir)

if __name__ == "__main__":
    main()
