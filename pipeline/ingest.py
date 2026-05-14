import pandas as pd
import json
from pathlib import Path
from typing import Tuple

def make_raw_df(data_dir: Path) -> Tuple[pd.DataFrame, int]:
    ndjsons_dir = data_dir / 'raw' / 'readings'
    all_batches = []
    file_list = list(ndjsons_dir.glob('*.ndjson'))
    
    for filename in file_list:
        rel_path = filename.relative_to(data_dir).as_posix()
        with open(filename, 'r') as f:
            for n, line in enumerate(f):
                batch = json.loads(line)
                batch['source_file'] = rel_path
                batch['line_number'] = n
                all_batches.append(batch)

    return pd.DataFrame(all_batches), len(file_list)

def dedup_raw_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return df
    df = df.sort_values(by=['source_file', 'line_number'], ascending=[True, True])
    df = df.drop_duplicates(subset=['batch_id'], keep='first')
    return df

def create_curated_readings(df: pd.DataFrame, devices_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame, int]:
    if df.empty:
        return pd.DataFrame(), pd.DataFrame(), 0
        
    empty_batches_df = df[df['readings'].str.len() == 0].copy()
    df_explode = df[df['readings'].str.len() > 0].explode(column='readings', ignore_index=True)
    reading_normalized = pd.json_normalize(df_explode['readings'].tolist()) # type: ignore

    curated = pd.concat([
        df_explode.drop(columns=['readings']).reset_index(drop=True),
        reading_normalized.reset_index(drop=True)
    ], axis=1)

    curated['ts'] = pd.to_datetime(curated['ts'])
    curated = curated.merge(devices_df[['device_id', 'commissioned_at']], on='device_id', how='left')
    curated['commissioned_at'] = pd.to_datetime(curated['commissioned_at'])
    
    pre_comm_mask = curated['ts'] < curated['commissioned_at']
    pre_comm_dropped = int(pre_comm_mask.sum())
    
    curated = curated[~pre_comm_mask].copy()
    curated = curated.drop(columns=['commissioned_at'])

    return curated, empty_batches_df, pre_comm_dropped
