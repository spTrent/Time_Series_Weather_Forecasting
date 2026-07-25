import numpy as np
import pandas as pd

HOURS_PER_DAY = 24
DAYS_PER_YEAR = 365
LAGS = [1, 2, 3, HOURS_PER_DAY, HOURS_PER_DAY * DAYS_PER_YEAR]

SMOOTH_COLS = ['temperature_2m', 'surface_pressure', 'relative_humidity_2m']
FFILL_COLS = [
    'wind_speed_10m',
    'precipitation',
    'rain',
    'snowfall',
    'weathercode',
]


def add_cyclical_features(
    frame: pd.DataFrame, source: pd.Series, period: float, name: str
) -> None:
    angle = source * (2 * np.pi / period)
    frame[f'{name}_sin'] = np.sin(angle)
    frame[f'{name}_cos'] = np.cos(angle)


def align_hourly_grid(city_df: pd.DataFrame) -> pd.DataFrame:
    """Выравнивание часовой сетки одного города + заполнение пропусков.

    Вход/выход — DataFrame с колонкой ds (одна станция). Вставляет
    пропущенные часы (asfreq) и заполняет, иначе позиционные лаги уедут.
    """
    city_df = city_df.copy()
    city_df['ds'] = pd.to_datetime(city_df['ds'])
    city_df = city_df.sort_values('ds').set_index('ds').asfreq('h')
    for col in SMOOTH_COLS:
        city_df[col] = city_df[col].interpolate(method='linear')
    for col in FFILL_COLS:
        city_df[col] = city_df[col].ffill()
    city_df['precipitation'] = city_df['precipitation'].fillna(0)
    return city_df.reset_index()


def build_ts_features(city_df: pd.DataFrame) -> pd.DataFrame:
    """Единый набор признаков временного ряда для ОДНОГО города.

    Один источник правды для обучения (research/ts.ipynb) и инференса
    (WeatherUseCase.build_features). На вход — DataFrame с колонкой ds,
    отсортированный по времени и без пропусков в часовой сетке.
    """
    city_df = city_df.copy()

    for lag in LAGS:
        city_df[f'lag_{lag}'] = city_df['temperature_2m'].shift(lag)

    add_cyclical_features(city_df, city_df['ds'].dt.month, 12, 'month')
    add_cyclical_features(
        city_df, city_df['ds'].dt.dayofyear, 365.25, 'day_of_year'
    )
    add_cyclical_features(
        city_df, city_df['ds'].dt.hour, HOURS_PER_DAY, 'hour'
    )

    city_df['diff_1_hour'] = city_df['lag_1'] - city_df['lag_2']
    city_df['diff_1_day'] = city_df['lag_1'] - city_df[f'lag_{HOURS_PER_DAY}']
    city_df['press_lag_3'] = city_df['surface_pressure'].shift(3)
    city_df['press_diff_3h'] = (
        city_df['surface_pressure'] - city_df['press_lag_3']
    )

    city_df['precip_sum_24h'] = (
        city_df['precipitation'].shift(1).rolling(window=24).sum()
    )
    city_df['wind_mean_3h'] = (
        city_df['wind_speed_10m'].shift(1).rolling(window=3).mean()
    )

    for w in (3, 24):
        roll = city_df['temperature_2m'].shift(1).rolling(window=w)
        city_df[f'roll_mean_{w}h'] = roll.mean()
        city_df[f'roll_std_{w}h'] = roll.std()
        city_df[f'roll_max_{w}h'] = roll.max()
        city_df[f'roll_min_{w}h'] = roll.min()

    city_df['current_temp'] = city_df['temperature_2m']
    return city_df
