import pandas as pd
from src.db import get_engine

df = pd.read_csv('data/weather_clean.csv', parse_dates=['ds'])
df.to_sql(
    'weather_hourly',
    con=get_engine(),
    if_exists='append',
    index=False,
    chunksize=10000,
    method='multi'
)
