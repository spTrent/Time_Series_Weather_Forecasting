import pandas as pd

from src.features import align_hourly_grid, build_ts_features
from tests.conftest import make_history


def test_align_hourly_grid_fills_gaps():
    df = make_history('Москва', hours=200)
    df_with_gap = df.drop(index=[50, 51])  # выкидываем 2 часа
    out = align_hourly_grid(df_with_gap)
    gaps = out['ds'].diff().dropna()
    assert gaps.max() == pd.Timedelta('1h')
    assert out['temperature_2m'].isna().sum() == 0


def test_build_ts_features_produces_expected_columns():
    df = align_hourly_grid(make_history('Москва', hours=24 * 400))
    out = build_ts_features(df)
    for col in [
        'lag_1', 'lag_8760', 'current_temp',
        'roll_mean_24h', 'month_sin', 'diff_1_day',
    ]:
        assert col in out.columns


def test_build_ts_features_last_row_is_complete():
    df = align_hourly_grid(make_history('Москва', hours=24 * 400))
    out = build_ts_features(df).dropna()
    assert not out.empty
    assert out['lag_8760'].notna().all()
