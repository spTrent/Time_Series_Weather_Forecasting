import time
import pandas as pd
from sqlalchemy import text
from src.scripts.get_weather import get_weather_data
from src.domain.cities import CITY_COORDS
from src.api.config import upsert_weather, get_engine


def year_batches(date_start: str, date_end: str):
    curr = pd.to_datetime(date_start)
    end = pd.to_datetime(date_end)
    while curr <= end:
        year_end = min(pd.Timestamp(f"{curr.year}-12-31"), end)
        yield curr.strftime("%Y-%m-%d"), year_end.strftime("%Y-%m-%d")
        curr = year_end + pd.Timedelta(days=1)

def get_history(date_start: str, date_end: str, cities: tuple[str] = tuple(CITY_COORDS), pause: float = 1.0):
    engine = get_engine()
    total = 0
    for city in cities:
        city_total = 0
        for start, end in year_batches(date_start, date_end):
            df = get_weather_data(city, start, end)
            count = upsert_weather(df, engine)
            city_total += count
            print(f'{city}: с {start} по {end}: {count}')
            time.sleep(pause)
        total += city_total
    return total


if __name__ == '__main__':
    # with get_engine().begin() as c:
    #     c.execute(text("TRUNCATE weather_hourly"))
    start_date = input('Введите начало (Год-месяц-день): ')
    end_date = input('Введите конец (Год-месяц-день): ')
    get_history(start_date, end_date)