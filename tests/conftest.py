from datetime import datetime, timedelta

import joblib
import numpy as np
import pandas as pd

from src.repositories.config import MODELS_DIR

FEATURE_COLUMNS = joblib.load(
    MODELS_DIR / 'feature_schema.joblib'
)['feature_columns']


def make_history(city='Москва', hours=24 * 400, end=None):
    if end is None:
        end = datetime.now().replace(minute=0, second=0, microsecond=0)
    idx = pd.date_range(end - timedelta(hours=hours - 1), end, freq='h')
    n = len(idx)
    return pd.DataFrame({
        'city': city,
        'ds': idx,
        'temperature_2m': 15 + 5 * np.sin(np.arange(n) * 2 * np.pi / 24),
        'relative_humidity_2m': 60.0,
        'precipitation': 0.0,
        'rain': 0.0,
        'snowfall': 0.0,
        'weathercode': 1,
        'wind_speed_10m': 3.0,
        'surface_pressure': 1010.0,
    })


class FakeWeatherRepo:
    def __init__(self, df):
        self._df = df

    def load_archive(self, city, start_time, end_time):
        d = self._df
        mask = (d['ds'] >= start_time) & (d['ds'] <= end_time)
        return d[mask].copy()

    def upsert(self, df):
        return len(df)


class FakeModelsRepo:
    feature_columns = FEATURE_COLUMNS
    models_count = 7

    def predict(self, day, data):
        return 20.0 + day
