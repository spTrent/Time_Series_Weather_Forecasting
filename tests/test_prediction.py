from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.domain.exceptions.exceptions import (
    InsufficientHistoryException,
    InvalidCityException,
    NoDataException,
)
from src.domain.forecast import ForecastPoint
from src.use_cases.prediction import WeatherUseCase
from tests.conftest import FakeModelsRepo, FakeWeatherRepo, make_history


def make_uc(df):
    return WeatherUseCase(FakeWeatherRepo(df), FakeModelsRepo())


def test_invalid_city_raises():
    uc = make_uc(make_history())
    with pytest.raises(InvalidCityException):
        uc.now_in_city('Готэм')


def test_to_naive_local_aware_converts_and_strips_tz():
    uc = make_uc(make_history())
    aware = datetime(2026, 7, 20, 14, tzinfo=ZoneInfo('UTC'))
    got = uc.to_naive_local('Находка', aware)  # UTC+10
    assert got.tzinfo is None
    assert got == datetime(2026, 7, 21, 0, 0)


def test_to_naive_local_naive_is_treated_as_local():
    uc = make_uc(make_history())
    naive = datetime(2026, 7, 20, 14, 37)
    assert uc.to_naive_local('Москва', naive) == datetime(2026, 7, 20, 14, 0)


def test_predict_no_history_raises_no_data():
    # история далеко в прошлом -> в окно now-368d..now ничего не попадает
    old_end = datetime(2000, 1, 1)
    uc = make_uc(make_history('Москва', hours=48, end=old_end))
    with pytest.raises(NoDataException):
        uc.predict('Москва', datetime.now() + timedelta(hours=24))


def test_predict_insufficient_history_raises():
    uc = make_uc(make_history('Москва', hours=48))  # < чем нужно для lag_8760
    now = uc.now_in_city('Москва')
    with pytest.raises(InsufficientHistoryException):
        uc.predict('Москва', now + timedelta(hours=24))


def test_predict_returns_sorted_forecast_points():
    city = 'Москва'
    now = make_uc(make_history()).now_in_city(city)
    uc = make_uc(make_history(city, hours=24 * 400, end=now))
    res = uc.predict(city, now + timedelta(hours=72))
    assert res
    assert all(isinstance(p, ForecastPoint) for p in res)
    assert [p.ts for p in res] == sorted(p.ts for p in res)
    assert all(now < p.ts <= now + timedelta(hours=168) for p in res)


def test_get_from_archive_returns_point():
    city = 'Москва'
    now = make_uc(make_history()).now_in_city(city)
    uc = make_uc(make_history(city, hours=24 * 10, end=now))
    past = now - timedelta(hours=5)
    res = uc.get_from_archive(city, past)
    assert len(res) == 1
    assert isinstance(res[0], ForecastPoint)
    assert res[0].ts == past


def test_get_from_archive_missing_raises_no_data():
    uc = make_uc(make_history('Москва', hours=24))
    with pytest.raises(NoDataException):
        uc.get_from_archive('Москва', datetime(1999, 1, 1, 0))
