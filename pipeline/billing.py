import pandas as pd

def calculate_billing(aggregates_df: pd.DataFrame, rate_card_df: pd.DataFrame) -> pd.DataFrame:
    if aggregates_df.empty: return pd.DataFrame()
    
    df = aggregates_df.merge(rate_card_df, on='device_type', how='left')
    
    billing = df.groupby(['site_id', 'hour_utc', 'device_type', 'unit_price', 'currency']).agg(
        total_delivered_units=('delivered_units', 'sum')
    ).reset_index()
    
    billing['amount'] = billing['total_delivered_units'] * billing['unit_price']
    
    result = billing[['site_id', 'hour_utc', 'device_type', 'total_delivered_units', 'amount', 'currency']]
    return pd.DataFrame(result)
