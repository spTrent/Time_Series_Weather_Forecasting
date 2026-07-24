import time
import pandas as pd
from sqlalchemy import text
from get_weather import CITY_COORDS, get_weather_data
from src.db import upsert_weather, get_engine


def year_butches(date_start: str, date_end: str):
    curr = pd.to_datetime(date_start)
    end = pd.to_datetime(date_end)
    while curr <= end:
        year_end = min(pd.Timestamp(f"curr.year-12-31"), end)
        yield curr.strftime("%Y-%m-%d"), year_end.strftime("%Y-%m-%d")
        curr = year_end + pd.Timedelta(days=1)

def get_history(date_start: str, date_end: str, cities: tuple[str] = tuple(CITY_COORDS), pause: float = 1.0):
    total = 0
    for city in cities:
        city_total = 0
        for start, end in year_butches(date_start, date_end):
            df = get_weather_data(city, start, end)
            count = upsert_weather(df)
            city_total += count
            print(f'{city}: с {start} по {end}: {count}')
            time.sleep(pause)
        total += city_total
    return total

with get_engine().begin() as c:
    c.execute(text("TRUNCATE weather_hourly"))
get_history("2015-01-01", "2026-07-23")