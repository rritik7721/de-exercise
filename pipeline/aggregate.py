import pandas as pd
import numpy as np

def aggregate_hourly(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()

    df = df.copy()
    df['hour_utc'] = df['ts'].dt.floor('h')
    
    df = df.sort_values(['device_id', 'hour_utc', 'ts', 'batch_id'])
    
    results = []
    
    for (device_id, hour_utc), group in df.groupby(['device_id', 'hour_utc']):
        samples_count = len(group)
        value_avg = group['value'].mean()
        value_min = group['value'].min()
        value_max = group['value'].max()
        
        # Trapezoidal integral: 0.5 * (rate_i + rate_{i+1}) * delta_t
        if samples_count > 1:
            rates = group['rate'].to_numpy()

            times_ns = group['ts'].values.astype('datetime64[ns]').astype(np.int64)
            times = times_ns // 1_000_000_000
            
            delta_t = np.diff(times)
            avg_rates = 0.5 * (rates[:-1] + rates[1:])
            delivered_units = np.sum(avg_rates * delta_t)
            
            states = group['state'].to_numpy()
            active_mask = states[:-1] == 'ACTIVE'
            active_seconds_float = np.sum(delta_t[active_mask])

            active_seconds = int(pd.Series([active_seconds_float]).round().iloc[0])
            active_seconds = max(0, min(3600, active_seconds))
        else:
            delivered_units = 0.0
            active_seconds = 0
            
        results.append({
            'device_id': device_id,
            'site_id': group['site_id'].iloc[0],
            'device_type': group['device_type'].iloc[0],
            'hour_utc': hour_utc,
            'samples_count': samples_count,
            'value_avg': value_avg,
            'value_min': value_min,
            'value_max': value_max,
            'delivered_units': delivered_units,
            'active_seconds': active_seconds
        })

    return pd.DataFrame(results)
