import argparse
import time
from typing import Generator

import pandas as pd
from sqlalchemy import text

from src.domain.cities import CITY_COORDS
from src.repositories.config import get_engine
from src.repositories.scripts.get_weather import get_weather_data
from src.repositories.sqlalchemy_weather_repository import (
    SqlAlchemyWeatherRepository,
)


def truncate_table() -> None:
    with get_engine().begin() as conn:
        conn.execute(text('TRUNCATE weather_hourly'))


def year_batches(date_start: str, date_end: str) -> Generator:
    curr = pd.to_datetime(date_start)
    end = pd.to_datetime(date_end)
    while curr <= end:
        year_end = min(pd.Timestamp(f'{curr.year}-12-31'), end)
        yield curr.strftime('%Y-%m-%d'), year_end.strftime('%Y-%m-%d')
        curr = year_end + pd.Timedelta(days=1)


def get_history(
    date_start: str,
    date_end: str,
    cities: tuple[str, ...] = tuple(CITY_COORDS),
    pause: float = 1.0,
) -> int:
    repo = SqlAlchemyWeatherRepository(engine=get_engine())
    total = 0
    for city in cities:
        city_total = 0
        for start, end in year_batches(date_start, date_end):
            df = get_weather_data(city, start, end)
            count = repo.upsert(df)
            city_total += count
            print(f'{city}: с {start} по {end}: {count}')
            time.sleep(pause)
        total += city_total
    return total


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Загрузка истории Open-Meteo')
    parser.add_argument(
        '--truncate',
        action='store_true',
        help='очистить weather_hourly перед загрузкой',
    )
    args = parser.parse_args()
    if args.truncate:
        truncate_table()
    start_date = input('Введите начало (Год-месяц-день): ')
    end_date = input('Введите конец (Год-месяц-день): ')
    get_history(start_date, end_date)
