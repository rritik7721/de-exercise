import pandas as pd
import numpy as np

def detect_anomalies(df: pd.DataFrame, devices_df: pd.DataFrame) -> pd.DataFrame:
    anomalies = []

    # R1: value_out_of_range
    r1 = df[(df['value'] < 0) | (df['value'] > 1000)].copy()
    if not r1.empty:
        r1['rule_id'] = 'R1'
        r1['severity'] = 'error'
        r1['details'] = r1['value'].astype(str)
        anomalies.append(r1)

    # R2: fault_state
    r2 = df[df['state'] == 'FAULT'].copy()
    if not r2.empty:
        r2['rule_id'] = 'R2'
        r2['severity'] = 'warning'
        r2['details'] = 'FAULT'
        anomalies.append(r2)

    # R3: value_spike
    for device_id, group in df.sort_values(['ts', 'batch_id']).groupby('device_id'):
        if len(group) < 31: continue
        
        # Population std dev (ddof=0)
        
        rolling = group['value'].rolling(window=30)
        mu = rolling.mean().shift(1)
        sigma = rolling.std(ddof=0).shift(1)
        
        # rule: sigma > 0 and |val - mu| > 5 * sigma
        spike_mask = (sigma > 0) & (np.abs(group['value'] - mu) > 5 * sigma)
        r3_group = group[spike_mask].copy()
        
        if not r3_group.empty:
            r3_group['rule_id'] = 'R3'
            r3_group['severity'] = 'warning'
            z_score = (r3_group['value'] - mu[spike_mask]) / sigma[spike_mask]
            r3_group['details'] = z_score.map(lambda x: f"{x:.2f}")
            anomalies.append(r3_group)

    # R4: device_silence
    r4_rows = []
    silent_candidates = devices_df[devices_df['expected_interval_s'] <= 300]
    
    for _, dev in silent_candidates.iterrows():
        dev_id = dev['device_id']
        dev_data = df[df['device_id'] == dev_id]
        if dev_data.empty: continue
        
        device_max_ts = dev_data['ts'].max()
        first_hour = pd.to_datetime(dev['commissioned_at']).ceil('h')
        last_hour = device_max_ts.floor('h')
        
        if first_hour > last_hour: continue
        
        all_hours = pd.date_range(start=first_hour, end=last_hour, freq='h')
        existing_hours = dev_data['ts'].dt.floor('h').unique()
        
        silent_hours = set(all_hours) - set(existing_hours)
        
        for h in silent_hours:
            r4_rows.append({
                'rule_id': 'R4',
                'device_id': dev_id,
                'site_id': dev['site_id'],
                'ts': h,
                'severity': 'error',
                'batch_id': None,
                'details': h.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            })
            
    if r4_rows:
        anomalies.append(pd.DataFrame(r4_rows))

    if not anomalies:
        return pd.DataFrame(columns=['rule_id', 'device_id', 'site_id', 'ts', 'severity', 'batch_id', 'details'])

    dq_anomalies = pd.concat(anomalies, ignore_index=True)
    
    dq_anomalies = dq_anomalies.sort_values(['rule_id', 'device_id', 'ts', 'batch_id'])
    dq_anomalies = dq_anomalies.drop_duplicates(subset=['rule_id', 'device_id', 'ts'], keep='first')
    
    return pd.DataFrame(dq_anomalies[['rule_id', 'device_id', 'site_id', 'ts', 'severity', 'batch_id', 'details']])
