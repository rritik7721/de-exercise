import pandas as pd
import pytest
import numpy as np
from pipeline.ingest import dedup_raw_df
from pipeline.aggregate import aggregate_hourly
from pipeline.quality import detect_anomalies

def test_deduplication():
    # Fixture: 3 batches, two have the same batch_id
    data = [
        {"batch_id": "B1", "source_file": "file1.ndjson", "line_number": 1, "readings": []},
        {"batch_id": "B2", "source_file": "file1.ndjson", "line_number": 2, "readings": []},
        {"batch_id": "B1", "source_file": "file2.ndjson", "line_number": 1, "readings": []}, # Duplicate B1
    ]
    df = pd.DataFrame(data)
    
    deduped = dedup_raw_df(df)
    
    assert len(deduped) == 2
    assert "B1" in deduped["batch_id"].values
    assert "B2" in deduped["batch_id"].values
    # Rule: keep smallest (source_file, line_number)
    b1_row = deduped[deduped["batch_id"] == "B1"].iloc[0]
    assert b1_row["source_file"] == "file1.ndjson"

def test_trapezoidal_integration():
    # Fixture: one device, one hour, two readings
    # ts: 12:00:00 (0s) and 12:00:10 (10s)
    # rates: 10.0 and 20.0
    # Expected: 0.5 * (10 + 20) * 10 = 150.0
    
    ts1 = pd.Timestamp("2026-04-01T12:00:00Z")
    ts2 = pd.Timestamp("2026-04-01T12:00:10Z")
    
    data = [
        {
            "device_id": "dev-1",
            "site_id": "site-1",
            "device_type": "type_a",
            "ts": ts1,
            "value": 50.0,
            "rate": 10.0,
            "state": "ACTIVE",
            "batch_id": "B1"
        },
        {
            "device_id": "dev-1",
            "site_id": "site-1",
            "device_type": "type_a",
            "ts": ts2,
            "value": 60.0,
            "rate": 20.0,
            "state": "ACTIVE",
            "batch_id": "B1"
        }
    ]
    df = pd.DataFrame(data)
    df['ts'] = pd.to_datetime(df['ts'])
    
    aggregates = aggregate_hourly(df)
    
    assert len(aggregates) == 1
    row = aggregates.iloc[0]
    assert row["delivered_units"] == pytest.approx(150.0)
    assert row["samples_count"] == 2
    assert row["value_avg"] == 55.0
    assert row["active_seconds"] == 10

def test_anomaly_detection_r1():
    # R1: value < 0 or value > 1000
    # Set commissioned_at close to data to avoid R4 (silence) for thousands of hours
    devices_df = pd.DataFrame([
        {"device_id": "dev-1", "site_id": "site-1", "device_type": "type_a", "expected_interval_s": 60, "commissioned_at": "2026-04-01T12:00:00Z"}
    ])
    
    data = [
        {"device_id": "dev-1", "site_id": "site-1", "ts": pd.Timestamp("2026-04-01T12:00:00Z"), "value": 500.0, "state": "ACTIVE", "batch_id": "B1"},
        {"device_id": "dev-1", "site_id": "site-1", "ts": pd.Timestamp("2026-04-01T12:01:00Z"), "value": 1001.0, "state": "ACTIVE", "batch_id": "B2"}, # Anomaly
        {"device_id": "dev-1", "site_id": "site-1", "ts": pd.Timestamp("2026-04-01T12:02:00Z"), "value": -1.0, "state": "ACTIVE", "batch_id": "B3"},   # Anomaly
    ]
    df = pd.DataFrame(data)
    df['ts'] = pd.to_datetime(df['ts'])
    
    anomalies = detect_anomalies(df, devices_df)
    
    # Filter for R1 to be safe
    r1_anomalies = anomalies[anomalies["rule_id"] == "R1"]
    
    assert len(r1_anomalies) == 2
    assert "B2" in r1_anomalies["batch_id"].values
    assert "B3" in r1_anomalies["batch_id"].values
